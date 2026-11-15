import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config as C  # noqa: E402
import findings as F  # noqa: E402
import github_ops as G  # noqa: E402

NOW = datetime(2026, 11, 15, tzinfo=timezone.utc)


class FakeGh:
    """Records calls; answers searches from a dict of token -> issue."""

    def __init__(self, existing=None, labels=(), promotions=0, comments=(), advisories=(), fail_create=()):
        self.calls, self.existing, self.labels = [], existing or {}, set(labels)
        self.promotions, self.comments, self.next_issue = promotions, list(comments), 100
        self.advisories, self.fail_create = list(advisories), set(fail_create)

    def __call__(self, args, input=None):
        self.calls.append((args[1:], input))
        a = args[1:]
        if a[:2] == ["label", "list"]:
            return 0, json.dumps([{"name": n} for n in self.labels]), ""
        if a[:2] == ["issue", "list"]:
            query = a[a.index("--search") + 1]
            if G.PROMOTED in query:
                stamp = (NOW - timedelta(days=1)).isoformat()
                return 0, json.dumps([{"number": 1, "comments": [{"body": G.PROMOTED, "createdAt": stamp}] * self.promotions}]), ""
            hits = [dict(v, body=f"Fingerprints: `{tok}`") for tok, issues in self.existing.items() if tok in query
                    for v in (issues if isinstance(issues, list) else [issues])]
            return 0, json.dumps(hits), ""
        if a[:2] == ["issue", "view"]:
            return 0, json.dumps({"comments": self.comments}), ""
        if a[:2] == ["issue", "create"]:
            if a[a.index("--title") + 1] in self.fail_create:
                return 1, "", "HTTP 502"
            self.next_issue += 1
            return 0, f"https://github.com/o/r/issues/{self.next_issue}\n", ""
        if a[0] == "api" and "POST" in a:
            return 0, json.dumps({"html_url": "https://github.com/o/r/security/advisories/GHSA-new"}), ""
        if a[0] == "api":
            state = a[a.index("--paginate") + 1].split("state=")[1].split("&")[0]
            return 0, "".join(json.dumps(adv) + "\n" for adv in self.advisories if adv["state"] == state), ""
        return 0, "", ""

    def made(self, verb):
        return [c for c in self.calls if c[0][:2] == ["issue", verb]]


def finding(**over):
    f = {
        "dimension": "bug", "category": "null-deref", "title": "Crash on empty cart",
        "file": "src/Cart.php", "symbol": "Cart::total", "line": 3, "claim": "c", "failure_scenario": "s",
        "evidence": "e", "evidence_rung": 3, "suggested_fix": "x", "confidence": "high",
    }
    f.update(over)
    out = F.merge([f])[0]
    out.update({"verdict": "confirmed", "severity": over.get("severity", "high")})
    return out


REPO_PRIVATE = {"nameWithOwner": "o/r", "visibility": "PRIVATE"}
REPO_PUBLIC = {"nameWithOwner": "o/r", "visibility": "PUBLIC"}


def file_all(gh, items, repo=REPO_PRIVATE, **cfg_over):
    cfg = dict(C.DEFAULTS, **cfg_over)
    return G.file_all(gh, items, cfg, source="checkup", sha="abc123", repo=repo, roles={}, now=NOW)


class FileTest(unittest.TestCase):
    def test_new_finding_creates_issue_with_triage_labels(self):
        gh = FakeGh()
        res = file_all(gh, [finding()])
        self.assertEqual(res[0]["action"], "created")
        args, body = gh.made("create")[0]
        labels = [args[i + 1] for i, x in enumerate(args) if x == "--label"]
        self.assertEqual(labels, ["needs-triage", "bug", "checkup", "severity:high"])
        self.assertIn(finding()["id"], body)
        created_labels = [c[0][2] for c in gh.calls if c[0][:2] == ["label", "create"]]
        self.assertIn("needs-triage", created_labels)

    def test_existing_issue_states(self):
        f = finding()
        cases = [
            ({"state": "OPEN", "stateReason": None}, (), "commented"),
            ({"state": "OPEN", "stateReason": None},
             ({"body": G.STILL_PRESENT, "createdAt": (NOW - timedelta(days=2)).isoformat()},), "unchanged"),
            ({"state": "CLOSED", "stateReason": "NOT_PLANNED"}, (), "suppressed"),
            ({"state": "CLOSED", "stateReason": "COMPLETED"}, (), "regression"),
        ]
        for issue, comments, expected in cases:
            with self.subTest(expected=expected):
                gh = FakeGh(existing={f["id"]: dict(issue, number=7, url="u", labels=[])}, comments=comments)
                self.assertEqual(file_all(gh, [f])[0]["action"], expected)
                if expected == "regression":
                    self.assertIn("Regression of #7", gh.made("create")[0][1])

    def test_prefers_the_open_issue_when_several_carry_the_fingerprint(self):
        f = finding()
        issues = [{"number": 9, "state": "CLOSED", "stateReason": "COMPLETED", "url": "u9", "labels": []},
                  {"number": 4, "state": "OPEN", "stateReason": None, "url": "u4", "labels": []}]
        res = file_all(FakeGh(existing={f["id"]: issues}), [f])[0]
        self.assertEqual((res["action"], res["issue"]), ("commented", 4))

    def test_search_hit_without_the_token_in_its_body_is_ignored(self):
        f = finding()
        gh = FakeGh()
        gh.existing = {f["id"]: {"number": 3, "state": "OPEN", "url": "u", "labels": []}}
        real = gh.__call__

        def fuzzy(args, input=None):  # GitHub returned a near match whose body lacks the token
            code, out, err = real(args, input)
            if args[1:3] == ["issue", "list"] and G.PROMOTED not in args[args.index("--search") + 1]:
                out = json.dumps([dict(h, body="pixie fp other") for h in json.loads(out)])
            return code, out, err
        self.assertEqual(file_all(fuzzy, [f])[0]["action"], "created")

    def test_one_failing_finding_does_not_stop_the_rest(self):
        bad, good = finding(symbol="a", title="bad"), finding(symbol="b", title="good")
        gh = FakeGh(fail_create={F.issue_title(bad)})
        actions = [r["action"] for r in file_all(gh, [bad, good])]
        self.assertEqual(actions, ["error", "created"])

    def test_advisory_states(self):
        sec = finding(dimension="security", category="xss")
        cases = [("draft", "advisory-exists"), ("triage", "advisory-exists"),
                 ("closed", "suppressed"), ("published", "advisory-regression")]
        for state, expected in cases:
            with self.subTest(state):
                adv = {"state": state, "html_url": "https://a/1", "description": f"Fingerprints: `{sec['id']}`"}
                gh = FakeGh(advisories=[adv])
                self.assertEqual(file_all(gh, [sec], repo=REPO_PUBLIC)[0]["action"], expected)

    def test_advisories_count_against_the_issue_cap(self):
        items = [finding(dimension="security", category="xss", symbol=str(i)) for i in range(2)]
        actions = [r["action"] for r in file_all(FakeGh(), items, repo=REPO_PUBLIC, maxIssuesPerRun=1)]
        self.assertEqual(actions, ["advisory-created", "skipped-cap"])

    def test_skips_low_severity_weak_evidence_possibly_fixed_and_stale(self):
        items = [finding(severity="medium"), finding(symbol="b", evidence_rung=2),
                 dict(finding(symbol="c"), possibly_fixed=True), dict(finding(symbol="d"), stale=True)]
        self.assertEqual(file_all(FakeGh(), items), [])

    def test_respects_issue_cap(self):
        items = [finding(symbol=str(i)) for i in range(3)]
        actions = [r["action"] for r in file_all(FakeGh(), items, maxIssuesPerRun=2)]
        self.assertEqual(actions, ["created", "created", "skipped-cap"])

    def test_security_routing(self):
        sec = finding(dimension="security", category="xss")
        cases = [("auto", REPO_PRIVATE, "created"), ("auto", REPO_PUBLIC, "advisory-created"),
                 ("report-only", REPO_PRIVATE, "report-only"), ("issues", REPO_PUBLIC, "created")]
        for mode, repo, expected in cases:
            with self.subTest(mode=mode, repo=repo["visibility"]):
                gh = FakeGh()
                self.assertEqual(file_all(gh, [sec], repo=repo, securityFindings=mode)[0]["action"], expected)
                if expected != "created":
                    self.assertEqual(gh.made("create"), [])


class PromoteTest(unittest.TestCase):
    def eligible(self, **over):
        return dict(finding(), repro={"test_path": "t", "test_code": "c", "command": "x", "output": "o"}, tier=1, **over)

    def promote(self, items, filed, promotions=0, **cfg_over):
        gh = FakeGh(promotions=promotions)
        cfg = dict(C.DEFAULTS, **cfg_over)
        return gh, G.promote(gh, items, filed, cfg, source="checkup", roles={}, now=NOW)

    def filed(self, f, labels=("needs-triage", "bug")):
        return {"id": f["id"], "issue": 5, "labels": list(labels)}

    def test_promotes_eligible_issue(self):
        f = self.eligible()
        gh, (promoted, skipped) = self.promote([f], [self.filed(f)])
        self.assertEqual(promoted, [5])
        edit = gh.made("edit")[0][0]
        self.assertIn("ready-for-agent", edit)
        self.assertIn("needs-triage", edit)

    def test_skip_reasons(self):
        f = self.eligible()
        cases = [
            ([dict(f, repro=None)], [self.filed(f)], 0, "not eligible"),
            ([dict(f, tier=3)], [self.filed(f)], 0, "not eligible"),
            ([f], [self.filed(f, labels=("bug",))], 0, "already triaged or claimed"),
            ([f], [self.filed(f, labels=("needs-triage", "agent-pr"))], 0, "already triaged or claimed"),
            ([f], [self.filed(f)], 3, "weekly PR cap reached"),
        ]
        for items, filed, promotions, reason in cases:
            with self.subTest(reason=reason):
                gh, (promoted, skipped) = self.promote(items, filed, promotions)
                self.assertEqual(promoted, [])
                self.assertEqual(skipped[0]["reason"], reason)
                self.assertEqual(gh.made("edit"), [])

    def test_cap_is_configurable(self):
        f = self.eligible()
        _, (promoted, _) = self.promote([f], [self.filed(f)], promotions=3, maxPrsPerWeek=5)
        self.assertEqual(promoted, [5])


class LabelMapTest(unittest.TestCase):
    def test_reads_role_table(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "docs/agents").mkdir(parents=True)
            (Path(tmp) / "docs/agents/pixie-labels.md").write_text(
                "| Role | Label in this repo | Meaning |\n|---|---|---|\n"
                "| `ready-for-agent` | `agent: ready` | Queued |\n| `needs-triage` | `triage` | New |\n")
            self.assertEqual(G.label_map(tmp), {"ready-for-agent": "agent: ready", "needs-triage": "triage"})


if __name__ == "__main__":
    unittest.main()

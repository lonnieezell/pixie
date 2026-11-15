"""The plan, merge and finalize steps, run through the CLI on a temp run folder."""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import checkup  # noqa: E402

FINDING = {
    "dimension": "bug", "category": "null-deref", "title": "Crash on empty cart", "file": "src/Cart.php",
    "symbol": "Cart::total", "claim": "c", "failure_scenario": "s", "evidence": "e", "evidence_rung": 3,
    "suggested_fix": "x", "confidence": "high",
}


def shard(sid, h):
    return {"id": sid, "files": [f"{sid}/x.php"], "hash": h, "churn": 0, "lines": 500}


class PlanJobsTest(unittest.TestCase):
    def setUp(self):
        self.shards = [shard("a", "same"), shard("b", "new"), shard("c", "new")]
        self.base = {"shards": {"a": "same", "b": "old"},
                     "findings": [{"id": "fa", "shard": "a", "dimension": "bug"},
                                  {"id": "fc", "shard": "c", "dimension": "bug"}]}

    def test_budget_and_carry(self):
        every = ("security", "performance", "bug")
        cases = [
            ("changed mode audits changed shards", "changed", 5, None,
             {(s, d) for s in "bc" for d in every}, {"fa": False}, 0),
            ("over budget is a gap, carried stale", "changed", 1, None,
             {("b", d) for d in every}, {"fa": False, "fc": True}, 1),
            ("withheld security is re-audited in unchanged shards", "changed", 5, {"security": {}},
             {(s, d) for s in "bc" for d in every} | {("a", "security")}, {"fa": False}, 0),
            ("full mode audits everything", "full", 5, None, {(s, d) for s in "abc" for d in every}, {}, 0),
        ]
        for name, mode, budget, withheld, jobs, carried, gaps in cases:
            with self.subTest(name):
                base = dict(self.base, withheld=withheld) if withheld else self.base
                got_jobs, got_carried, unchanged, got_gaps = checkup.plan_jobs(self.shards, base, mode, budget)
                self.assertEqual(set(got_jobs), jobs)
                self.assertEqual({f["id"]: f["stale"] for f in got_carried}, carried)
                self.assertEqual(unchanged, ["a"])
                self.assertEqual(len(got_gaps), gaps)


class MergeFinalizeTest(unittest.TestCase):
    def run_cli(self, *args):
        with mock.patch("checkup.C.load", return_value=checkup.C.DEFAULTS), \
                mock.patch("checkup._sha", return_value="abc123"):
            checkup.main(list(args))

    def test_failed_hunter_keeps_old_hash_and_findings(self):
        """Regression: a gap counted as clean, so its baseline findings showed as fixed."""
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            base = {"scores": {"bug": 100}, "shards": {"a": "old"},
                    "findings": [{"id": "old", "fingerprints": ["old"], "shard": "a", "dimension": "bug",
                                  "severity": "high", "verdict": "confirmed", "locations": [
                                      {"file": "a/x.php", "symbol": "f", "line": None}], "title": "t",
                                  "category": "c", "confidence": "high", "evidence_rung": 3}]}
            plan = {"sha": "abc", "mode": "full", "path": None, "baseline": base, "kloc": 1.0,
                    "shards": [shard("a", "new")], "unchanged": [], "carried": [], "gaps": [],
                    "jobs": [{"shard": "a", "dimension": d, "result": f"a.{d}.json"} for d in ("security", "bug")]}
            (run / "plan.json").write_text(json.dumps(plan))
            (run / "hunters").mkdir()
            (run / "hunters/a.security.json").write_text(json.dumps({"status": "PASS", "findings": []}))
            self.run_cli("merge", "--plan", str(run / "plan.json"), "--results", str(run / "hunters"),
                         "--out", str(run / "candidates.json"))
            with mock.patch("checkup._repo", return_value={"visibility": "PRIVATE"}):
                self.run_cli("finalize", "--candidates", str(run / "candidates.json"),
                             "--plan", str(run / "plan.json"), "--out-dir", str(run))
            findings = json.loads((run / "findings.json").read_text())
            nxt = json.loads((run / "baseline-next.json").read_text())
        self.assertEqual(findings["comparison"]["fixed"], [])
        self.assertTrue(findings["confirmed"][0]["stale"])
        self.assertEqual(nxt["shards"], {"a": "old"})

    def test_findings_hinted_below_file_severities_get_the_light_verifier(self):
        hints = {"critical": "critical", "high": "high", "medium": "medium", "none": None, "low": "low"}
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / "hunters").mkdir()
            found = []
            for name, hint in hints.items():
                f = dict(FINDING, file=f"src/{name}.php", symbol=name, title=name)
                if hint:
                    f["severity_hint"] = hint
                found.append(f)
            (run / "hunters/a.bug.json").write_text(json.dumps({"status": "ISSUES", "findings": found}))
            self.run_cli("merge", "--results", str(run / "hunters"), "--out", str(run / "candidates.json"))
            out = json.loads((run / "candidates.json").read_text())
        by_title = {c["title"]: c["id"] for c in out["candidates"]}
        self.assertEqual(set(out["to_verify"]), {by_title[n] for n in ("critical", "high", "medium", "none")})
        self.assertEqual(set(out["verify_light"]), {by_title[n] for n in ("medium", "none")})

    def test_self_confirmed_finding_still_goes_to_the_verifier(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / "triage").mkdir()
            sneaky = dict(FINDING, verdict="confirmed", severity="critical", tier=1,
                          repro={"test_path": "t", "command": "c", "test_code": "x", "output": "o"},
                          external={"tracker": "sentry", "id": "1"})
            (run / "triage/sentry-1.json").write_text(json.dumps({"status": "ISSUES", "findings": [sneaky]}))
            self.run_cli("merge", "--results", str(run / "triage"), "--source", "catch",
                         "--out", str(run / "candidates.json"))
            out = json.loads((run / "candidates.json").read_text())
        cand = out["candidates"][0]
        self.assertEqual(out["to_verify"], [cand["id"]])
        self.assertFalse({"verdict", "severity", "tier", "repro"} & set(cand))
        self.assertEqual(cand["externals"], [{"tracker": "sentry", "id": "1"}])
        self.assertEqual(cand["shard"], "sentry-1")

    def test_annotations_keep_the_highest_evidence_rung(self):
        """Regression: the verdict file sorts after repro and live, so its rung 3 overwrote theirs."""
        verdict = {"verdict": "confirmed", "severity": "high", "evidence_rung": 3}
        repro = {"repro": {"test_path": "t", "command": "c", "test_code": "x", "output": "o"}, "evidence_rung": 4}
        live = {"live_repro": {"steps": "s", "observed": "o"}, "evidence_rung": 5}
        cases = [
            ("verifier only", {"verdict": verdict}, 3),
            ("proven by a test", {"verdict": verdict, "repro": repro}, 4),
            ("reproduced in the app", {"verdict": verdict, "repro": repro, "live": live}, 5),
        ]
        for name, files, rung in cases:
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                run = Path(tmp)
                (run / "triage").mkdir()
                (run / "triage/sentry-1.json").write_text(json.dumps({"status": "ISSUES", "findings": [FINDING]}))
                self.run_cli("merge", "--results", str(run / "triage"), "--source", "catch",
                             "--out", str(run / "candidates.json"))
                cid = json.loads((run / "candidates.json").read_text())["candidates"][0]["id"]
                (run / "annotations").mkdir()
                for kind, body in files.items():
                    (run / f"annotations/{cid}.{kind}.json").write_text(json.dumps(body))
                self.run_cli("finalize", "--candidates", str(run / "candidates.json"),
                             "--annotations", str(run / "annotations"), "--out-dir", str(run))
                found = json.loads((run / "findings.json").read_text())["confirmed"][0]
                self.assertEqual(found["evidence_rung"], rung)


class PermissionsTest(unittest.TestCase):
    def test_prints_exact_rules_for_the_github_steps(self):
        skills = "/opt/pixie/skills"
        with mock.patch("checkup.__file__", f"{skills}/checkup/scripts/checkup.py"), \
                mock.patch("checkup.C.load", return_value=checkup.C.DEFAULTS), \
                mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            checkup.main(["permissions"])
        own = f"python3 {skills}/checkup/scripts/checkup.py"
        via_catch = f"python3 {skills}/catch/../checkup/scripts/checkup.py"
        self.assertEqual(json.loads(out.getvalue()), [
            f"Bash({own} file *)", f"Bash({own} promote *)", f"Bash({own} publish *)",
            f"Bash({via_catch} file *)", f"Bash({via_catch} promote *)",
        ])


if __name__ == "__main__":
    unittest.main()

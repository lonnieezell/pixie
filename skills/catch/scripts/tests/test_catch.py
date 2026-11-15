import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import catch  # noqa: E402
import config as C  # noqa: E402

TRACKED = ["app/Controllers/Cart.php", "src/cart/total.ts", "lib/util.py", "app/Models/User.php", "other/User.php"]
INDEX = catch.suffix_index(TRACKED)
NOW = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)


def cfg(**over):
    c = json.loads(json.dumps(C.DEFAULTS["catch"]))
    c.update(over)
    return c


class RedactTest(unittest.TestCase):
    def test_redacts_secrets_and_personal_data(self):
        cases = [
            ("user jane.doe@example.com failed", "jane.doe"),
            ("Authorization: Bearer abc.def", "abc.def"),
            ("password=hunter2 rejected", "hunter2"),
            ("from 192.168.10.4", "192.168.10.4"),
            ("card 4111 1111 1111 1111", "4111"),
            ("jwt eyJhbGciOi.eyJzdWIiOi.c2lnbmF0dXJl", "eyJhbGciOi"),
            ("key sk_live_" + "A" * 32, "sk_live_" + "A" * 6),
        ]
        for text, secret in cases:
            with self.subTest(text=text):
                self.assertNotIn(secret, catch.redact(text))

    def test_keeps_file_paths_and_truncates(self):
        path = "/var/www/html/app/Controllers/SomethingVeryLongController.php"
        self.assertEqual(catch.redact(path), path)
        self.assertTrue(catch.redact("word " * 200, 100).endswith("(truncated)"))


class FramesTest(unittest.TestCase):
    def test_parses_common_stack_formats(self):
        cases = [
            ('File "/srv/lib/util.py", line 12, in parse', "/srv/lib/util.py", 12, "parse"),
            ("#0 /var/www/app/Controllers/Cart.php(88): App\\Cart->total()", "/var/www/app/Controllers/Cart.php", 88, "App\\Cart->total"),
            ("    at total (/app/src/cart/total.ts:5:10)", "/app/src/cart/total.ts", 5, "total"),
        ]
        for text, path, line, func in cases:
            with self.subTest(text=text):
                frame = catch.parse_stack_text(text)[0]
                self.assertEqual((frame["file"], frame["line"], frame["function"]), (path, line, func))

    def test_maps_server_paths_by_unique_suffix(self):
        cases = [
            ("/var/www/app/Controllers/Cart.php", "app/Controllers/Cart.php"),
            ("C:\\build\\src\\cart\\total.ts", "src/cart/total.ts"),
            ("/srv/vendor/x/y.php", None),
            ("/deploy/app/Models/User.php", "app/Models/User.php"),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(catch.map_to_repo(raw, INDEX), expected)

    def test_ambiguous_basename_does_not_map(self):
        self.assertIsNone(catch.map_to_repo("User.php", INDEX))

    def test_keeps_in_app_frames_only_when_any(self):
        frames = [{"file": "/srv/vendor/lib.php", "line": 1, "function": "", "in_app": None},
                  {"file": "/x/app/Controllers/Cart.php", "line": 2, "function": "t", "in_app": None}]
        out = catch.attach_repo_paths(frames, INDEX)
        self.assertEqual([f["repo_path"] for f in out], ["app/Controllers/Cart.php"])


class FakeGit:
    def __init__(self, commits=(), diff="", log=""):
        self.commits, self.diff, self.log, self.diffed = set(commits), diff, log, []

    def __call__(self, *args):
        if args[0] == "cat-file":
            return (0 if args[2].split("^")[0] in self.commits else 1), ""
        if args[0] == "diff":
            self.diffed += list(args[args.index("--") + 1:])
            return 0, self.diff
        return 0, self.log


class PossiblyFixedTest(unittest.TestCase):
    def report(self, release="", last_seen="2026-11-10T00:00:00Z"):
        return {"release": release, "last_seen": last_seen,
                "frames": [{"repo_path": "app/Router.php", "line": 10},
                           {"repo_path": "app/Controllers/Cart.php", "line": 88}]}

    def test_cases(self):
        near = "@@ -86,2 +86,3 @@\n-x\n+y\n"
        far = "@@ -10,4 +10,4 @@\n-x\n+y\n"
        cases = [
            ("lines near the failing frame changed", self.report("abc1234"), FakeGit({"abc1234"}, diff=near), True),
            ("only distant lines changed", self.report("abc1234"), FakeGit({"abc1234"}, diff=far), False),
            ("release diff clean", self.report("abc1234"), FakeGit({"abc1234"}), False),
            ("edited after last seen", self.report(), FakeGit(log="2026-11-12T00:00:00+00:00"), True),
            ("edited before last seen", self.report(), FakeGit(log="2026-11-01T00:00:00+00:00"), False),
            ("unknown release falls back to time", self.report("1.2.3"), FakeGit(log="2026-11-12T00:00:00+00:00"), True),
            ("no frames", {"frames": [], "release": "", "last_seen": None}, FakeGit(), False),
        ]
        for name, report, git, expected in cases:
            with self.subTest(name):
                self.assertEqual(catch.possibly_fixed(report, git)[0], expected)

    def test_only_the_frame_closest_to_the_error_counts(self):
        git = FakeGit({"abc1234"}, diff="@@ -10,1 +10,1 @@\n")
        catch.possibly_fixed(self.report("abc1234"), git)
        self.assertEqual(git.diffed, ["app/Controllers/Cart.php"])


class SentryTest(unittest.TestCase):
    def fetch(self, url, token, body=None, accept=None):
        self.urls.append(url)
        if "/events/latest/" in url:
            return json.dumps({
                "release": {"version": "abc1234"}, "tags": [{"key": "environment", "value": "production"}],
                "entries": [{"type": "request", "data": {"headers": [["Cookie", "s=1"]]}},
                            {"type": "exception", "data": {"values": [{
                                "type": "TypeError", "value": "null total for bob@example.com",
                                "stacktrace": {"frames": [
                                    {"filename": "/srv/vendor/a.php", "lineNo": 1, "function": "v", "inApp": False},
                                    {"filename": "/srv/app/Controllers/Cart.php", "lineNo": 9, "function": "total", "inApp": True}]}}]}}],
            }), {}
        page = [{"id": "1", "count": "50", "userCount": 7, "title": "TypeError", "permalink": "https://s/1",
                 "firstSeen": "2026-11-01T00:00:00Z", "lastSeen": "2026-11-14T00:00:00Z", "level": "error"},
                {"id": "2", "count": "2", "title": "rare"}]
        return json.dumps(page), {"Link": '<x>; rel="next"; results="false"'}

    def test_builds_redacted_reports_above_threshold(self):
        self.urls = []
        c = cfg(sentry={"baseUrl": "https://sentry.io", "org": "acme", "projects": ["web"], "environment": ""})
        reports = catch.sentry_reports(c, "t", INDEX, fetch=self.fetch)
        self.assertEqual(len(reports), 1)
        r = reports[0]
        self.assertEqual((r["id"], r["events"], r["users"], r["release"]), ("sentry-1", 50, 7, "abc1234"))
        self.assertNotIn("bob@example.com", r["message"])
        self.assertEqual([f["repo_path"] for f in r["frames"]], ["app/Controllers/Cart.php"])
        self.assertNotIn("Cookie", json.dumps(r))
        self.assertIn("project=web", self.urls[0])
        self.assertIn("/organizations/acme/issues/1/events/latest/", self.urls[1])


class CoralogixTest(unittest.TestCase):
    def fetch(self, url, token, body=None, accept=None):
        self.body = body
        rows = []
        for i in range(12):
            rows.append({"metadata": [{"key": "timestamp", "value": f"2026-11-15T0{i % 9}:00:00Z"}],
                         "labels": [{"key": "applicationname", "value": "shop"}],
                         "userData": json.dumps({"message": f"Order {i} failed for a@b.co",
                                                 "stack": "at total (/app/src/cart/total.ts:5:10)"})})
        rows.append({"metadata": [], "labels": [], "userData": json.dumps({"message": "one-off"})})
        lines = [json.dumps({"queryId": {"queryId": "q"}}), json.dumps({"result": {"results": rows}})]
        return "\n".join(lines), {}

    def test_lookback_units_set_the_start_date(self):
        cases = [("30m", "2026-11-15T11:30:00Z"), ("24h", "2026-11-14T12:00:00Z"),
                 ("7d", "2026-11-08T12:00:00Z"), ("1w", "2026-11-08T12:00:00Z")]
        for lookback, start in cases:
            with self.subTest(lookback):
                c = cfg(lookback=lookback, coralogix=dict(C.DEFAULTS["catch"]["coralogix"], domain="eu2.coralogix.com"))
                catch.coralogix_reports(c, "t", INDEX, NOW, fetch=self.fetch)
                self.assertEqual(self.body["metadata"]["startDate"], start)

    def test_groups_similar_errors_and_drops_rare_ones(self):
        c = cfg(coralogix=dict(C.DEFAULTS["catch"]["coralogix"], domain="eu2.coralogix.com"))
        reports = catch.coralogix_reports(c, "t", INDEX, NOW, fetch=self.fetch)
        self.assertEqual(len(reports), 1)
        r = reports[0]
        self.assertEqual(r["events"], 12)
        self.assertNotIn("a@b.co", r["message"])
        self.assertEqual(r["frames"][0]["repo_path"], "src/cart/total.ts")
        self.assertEqual(self.body["metadata"]["startDate"], "2026-11-14T12:00:00Z")


class FetchAllTest(unittest.TestCase):
    def test_reports_missing_config_and_tokens(self):
        _, errors = catch.fetch_all(cfg(), {}, INDEX, NOW)
        self.assertIn("no source configured", errors[0])
        c = cfg(sentry={"baseUrl": "x", "org": "acme", "projects": [], "environment": ""})
        _, errors = catch.fetch_all(c, {}, INDEX, NOW)
        self.assertEqual(errors, ["sentry: SENTRY_AUTH_TOKEN is not set"])


if __name__ == "__main__":
    unittest.main()

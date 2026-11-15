import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import baseline as B  # noqa: E402
import config as C  # noqa: E402
import shards as S  # noqa: E402


class SelectTest(unittest.TestCase):
    def test_keeps_source_and_drops_excluded_tests_and_docs(self):
        blobs = {p: "x" for p in [
            "src/a.php", "README.md", "vendor/lib/x.php", "app/node_modules/y.js",
            "tests/FooTest.php", "src/b.test.ts", "src/Thing.php",
            "ui/_vendor/react.js", "third_party/z.go", ".github/scripts/ci.js", "app/.claude/hook.py",
            "public/app.min.js", "gen/api.ts",
        ]}
        kept = S.select(blobs, C.DEFAULTS["exclude"], include_tests=False, marked={"gen/api.ts"})
        self.assertEqual(sorted(kept), ["src/Thing.php", "src/a.php"])
        self.assertIn("tests/FooTest.php", S.select(blobs, [], include_tests=True))


class CodeLinesTest(unittest.TestCase):
    """KLOC counts code only, so it agrees with other line counters and doesn't double the size."""

    def test_counts_code_not_comments_blanks_or_inline_tests(self):
        cases = [
            ("blank lines", ".ts", "a();\n\n  \nb();\n", 2),
            ("line comments", ".ts", "// note\na(); // trailing\n", 1),
            ("block comment", ".js", "/**\n * doc\n */\na();\n/* one */\nb();\n", 2),
            ("code after a block comment closes", ".js", "/* x\n y */ a();\n", 1),
            ("hash comments", ".py", "# note\nx = 1\n", 1),
            ("php hash comment but not an attribute", ".php", "# note\n#[Route]\nf();\n", 2),
            ("sql comment", ".sql", "-- note\nSELECT 1;\n", 1),
            ("rust attribute is code", ".rs", "#[derive(Debug)]\nstruct A;\n", 2),
            ("rust inline tests are not counted", ".rs",
             "fn a() {}\n/// doc\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn t() {}\n}\n", 1),
        ]
        for name, suffix, text, want in cases:
            with self.subTest(name):
                self.assertEqual(S.code_lines(text, suffix), want)


class BuildTest(unittest.TestCase):
    def test_splits_big_dirs_and_orders_by_churn(self):
        blobs = {f"src/big/f{i}.php": str(i) for i in range(5)}
        blobs.update({"src/small/a.php": "a", "top.php": "t"})
        shards = S.build(blobs, size=3, churn={"src/small/a.php": 9})
        ids = [s["id"] for s in shards]
        self.assertEqual(ids[0], "src/small")
        self.assertEqual(sorted(ids), sorted([".", "src/big[f0.php..f2.php]", "src/big[f3.php..f4.php]", "src/small"]))
        self.assertTrue(all(len(s["files"]) <= 3 for s in shards))
        self.assertEqual(sum(len(s["files"]) for s in shards), 7)

    def test_packs_many_small_folders_together(self):
        blobs = {f"src/m{i:02}/f{j}.php": "x" for i in range(60) for j in range(2)}
        shards = S.build(blobs, size=20)
        self.assertEqual(len(shards), 6)
        self.assertEqual(sorted(s["id"] for s in shards)[0], "src[m00..m09]")
        self.assertEqual(sorted(f for s in shards for f in s["files"]), sorted(blobs))

    def test_hash_changes_only_when_a_blob_changes(self):
        a = S.shard_hash(["x", "y"], {"x": "1", "y": "2"})
        self.assertEqual(a, S.shard_hash(["y", "x"], {"x": "1", "y": "2"}))
        self.assertNotEqual(a, S.shard_hash(["x", "y"], {"x": "1", "y": "3"}))


class BaselineTest(unittest.TestCase):
    def test_carried_marks_findings_from_changed_shards_stale(self):
        base = {"findings": [{"id": "1", "shard": "a"}, {"id": "2", "shard": "b"}, {"id": "3", "shard": "z"}]}
        out = B.carried(base, [{"id": "a"}, {"id": "b"}], unchanged={"a"})
        self.assertEqual([(f["id"], f["stale"]) for f in out], [("1", False), ("2", True)])
        self.assertEqual(B.carried(None, [{"id": "a"}], set()), [])

    def test_unchecked_shards_keep_their_old_hash(self):
        """Regression: shards over budget or with failed hunters were stored as audited and clean."""
        shards = [{"id": "ok", "hash": "new1"}, {"id": "failed", "hash": "new2"}, {"id": "never", "hash": "new3"}]
        prev = {"shards": {"ok": "old1", "failed": "old2"}}
        doc = B.build([], {}, shards, "sha", "2026-11-15", 1.0, False, checked={"ok"}, previous=prev)
        self.assertEqual(doc["shards"], {"ok": "new1", "failed": "old2"})

    def test_hidden_security_findings_are_withheld_entirely(self):
        """Regression: redacted entries kept brute-forceable fingerprints and the shard of an open flaw."""
        sec = {"id": "s", "fingerprints": ["s"], "dimension": "security", "severity": "high", "shard": "a"}
        bug = {"id": "b", "fingerprints": ["b"], "dimension": "bug", "severity": "low", "shard": "a"}
        cases = [(True, ["b"], {"security": {"critical": 0, "high": 1, "medium": 0, "low": 0}}),
                 (False, ["s", "b"], None)]
        for hide, kept, withheld in cases:
            with self.subTest(hide=hide):
                doc = B.build([sec, bug], {}, [{"id": "a", "hash": "h"}], "sha", "d", 1.0, hide, checked={"a"})
                self.assertEqual([f["id"] for f in doc["findings"]], kept)
                self.assertEqual(doc.get("withheld"), withheld)

    def test_restore_brings_back_failed_jobs_as_stale(self):
        base = {"findings": [{"id": "1", "shard": "a", "dimension": "bug"},
                             {"id": "2", "shard": "a", "dimension": "security"}]}
        self.assertEqual([(f["id"], f["stale"]) for f in B.restore(base, {("a", "bug")})], [("1", True)])


class ConfigTest(unittest.TestCase):
    def load(self, data):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "docs/agents").mkdir(parents=True)
            (Path(tmp) / C.CONFIG_PATH).write_text(json.dumps(data))
            return C.load(tmp)

    def test_defaults_merge_with_user_file(self):
        cfg = self.load({"maxPrsPerWeek": 1, "autoFix": {"maxTier": 1}})
        self.assertEqual(cfg["maxPrsPerWeek"], 1)
        self.assertEqual(cfg["autoFix"], {"severities": ["critical", "high"], "maxTier": 1})
        self.assertEqual(cfg["maxIssuesPerRun"], 10)

    def test_user_excludes_add_to_the_defaults(self):
        cfg = self.load({"exclude": ["legacy/", "vendor/"]})
        self.assertEqual(cfg["exclude"], C.DEFAULTS["exclude"] + ["legacy/"])

    def test_rejects_bad_values(self):
        for data in ({"securityFindings": "tweet"}, {"catch": {"lookback": "1 day"}}, {"catch": {"lookback": "0h"}}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.load(data)


if __name__ == "__main__":
    unittest.main()

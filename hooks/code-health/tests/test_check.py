import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check  # noqa: E402

KM = check.find_km()

PROSE = """If the user asks for a change, and if the change is small, or if it touches
tests, then do it. While you work, if anything fails and you cannot fix it, or
if the tests do not pass, stop and report. For each file, if it is generated,
skip it; else if it is vendored, skip it; else review it. Do not continue if
the build breaks, or if CI is red, or if a reviewer has asked for changes."""

PROMPT_SOURCES = {
    ".ts": "export function buildPrompt(name: string): string {\n"
           "  return `Reviewing ${name}.\n" + PROSE + "\n`;\n}\n",
    ".php": "<?php\n\nfunction build_prompt(string $name): string\n{\n"
            "    return <<<TXT\nReviewing {$name}.\n" + PROSE + "\nTXT;\n}\n",
}

BRANCHY_SOURCES = {
    ".ts": "export function pick(a: number, b: number): string {\n"
           "  if (a > 0) { if (b > 0) { return `both`; } else { return `a`; } }\n"
           "  for (const x of [a, b]) { if (x && b || a) { return `${x}`; } }\n"
           "  return `none`;\n}\n",
    ".php": "<?php\n\nfunction pick(int $a, int $b): string\n{\n"
            "    if ($a > 0) { if ($b > 0) { return 'both'; } else { return 'a'; } }\n"
            "    foreach ([$a, $b] as $x) { if ($x && $b || $a) { return <<<T\n{$x}\nT; } }\n"
            "    return 'none';\n}\n",
}


@unittest.skipUnless(KM, "km is not installed")
class AnalyzeTest(unittest.TestCase):
    def test_prose_in_template_literals_and_heredocs_is_not_scored(self):
        for ext, source in PROMPT_SOURCES.items():
            with self.subTest(ext=ext):
                funcs, smells, lines = check.analyze(KM, source, ext)
                self.assertEqual([cc for cc, _ in funcs.values()], [0])
                self.assertEqual(smells, {})
                self.assertEqual(lines, source.count("\n") + 1)

    def test_code_around_template_literals_and_heredocs_is_still_scored(self):
        for ext, source in BRANCHY_SOURCES.items():
            with self.subTest(ext=ext):
                funcs, _, _ = check.analyze(KM, source, ext)
                self.assertGreater(funcs["pick"][0], 5)


if __name__ == "__main__":
    unittest.main()

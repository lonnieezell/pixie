import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import critique as C  # noqa: E402

INVENTORY = """# Design system

## Tokens

Source files: `tailwind.config.js`, `resources/css/app.css`

### Colours

| Role | Token | Value | Source |
|---|---|---|---|
| primary | `brand-600` | `#4f46e5` | `tailwind.config.js:12` |

## Rules

- Colours come from tokens.

## Setup offers

| Offer | Answer | Date |
|---|---|---|

## Annotations

- status: `Button` = preferred

## Rubric overrides

- drop: `type.line-length` (marketing pages use long lines on purpose)
- Dense tables are fine on admin screens.
"""


class TokenGateTest(unittest.TestCase):
    def test_reports_raw_values_with_file_and_line(self):
        cases = [
            ('<p class="text-[#333]">', ["text-[#333]"]),
            ('<div class="p-[13px] mt-4">', ["p-[13px]"]),
            ('<div class="md:w-[calc(100%-2rem)]">', ["md:w-[calc(100%-2rem)]"]),
            ("color: #4F46E5;", ["#4F46E5"]),
            ("border: 1px solid #fff", ["#fff"]),
            ("background: #11223344;", ["#11223344"]),
            ('<a href="#add">Add</a>', []),
            ("&#123; is an entity", []),
            ('<div class="mt-4 text-sm">', []),
            ("const first = items[0];", []),
        ]
        for line, expected in cases:
            with self.subTest(line=line):
                hits = C.token_hits("resources/views/a.blade.php", "x\n" + line + "\n")
                self.assertEqual([h["match"] for h in hits], expected)
                for h in hits:
                    self.assertEqual((h["file"], h["line"]), ("resources/views/a.blade.php", 2))

    def test_skips_the_inventory_token_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "resources/css").mkdir(parents=True)
            (root / "resources/css/app.css").write_text(":root { --primary: #4f46e5; }\n")
            (root / "page.tsx").write_text('<p className="text-[#333]" />\n')
            hits = C.token_gate(root, INVENTORY, ["resources/css/app.css", "page.tsx"])
            self.assertEqual([(h["file"], h["match"]) for h in hits], [("page.tsx", "text-[#333]")])


RUBRIC = """# Rubric

| ID | Check | Typical severity |
|---|---|---|
| `type.hierarchy` | One clear primary heading per screen. | S2 |
| `type.line-length` | Body text lines stay under about 80 characters. | S3 |
"""

EXTRA = """| `wdg.focus-visible` | Focus rings are visible on every control. | S2 |
"""

MANIFEST = {"url": "http://localhost:8080/orders", "shots": [
    {"file": "shots/default-390.png", "state": "default", "viewport": 390},
    {"file": "shots/default-1280.png", "state": "default", "viewport": 1280},
]}


def make_run(root):
    run = Path(root) / "run"
    (run / "shots").mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps(MANIFEST))
    (run / "axe.json").write_text("[]")
    for shot in MANIFEST["shots"]:
        (run / shot["file"]).write_bytes(b"\x89PNG")
    (run / "page.tsx").write_text("export default function Page() {}")
    neighbour = Path(root) / "list-1280.png"
    neighbour.write_bytes(b"\x89PNG")
    return run, neighbour


class BriefTest(unittest.TestCase):
    def test_critic_folder_holds_only_screenshots_rubric_and_context(self):
        with tempfile.TemporaryDirectory() as d:
            run, neighbour = make_run(d)
            critic = C.brief(run, INVENTORY, RUBRIC, EXTRA, [neighbour])
            files = sorted(str(p.relative_to(critic)) for p in critic.rglob("*") if p.is_file())
            self.assertEqual(files, [
                "context.md", "manifest.json", "neighbours/list-1280.png", "rubric.md",
                "shots/default-1280.png", "shots/default-390.png",
            ])
            rubric = (critic / "rubric.md").read_text()
            self.assertIn("`type.hierarchy`", rubric)
            self.assertIn("`wdg.focus-visible`", rubric)
            self.assertNotIn("`type.line-length`", rubric)
            context = (critic / "context.md").read_text()
            self.assertIn("Colours come from tokens.", context)
            self.assertIn("Dense tables are fine on admin screens.", context)
            self.assertNotIn("status:", context)


class AxeGateTest(unittest.TestCase):
    def test_lists_each_violation_per_screenshot_most_severe_first(self):
        report = [
            {"screenshot": "shots/default-390.png", "state": "default", "viewport": 390, "violations": [
                {"id": "region", "impact": "moderate", "help": "Content in landmarks",
                 "nodes": [{"target": ["#footer"]}]},
            ]},
            {"screenshot": "shots/default-1280.png", "state": "default", "viewport": 1280, "violations": [
                {"id": "color-contrast", "impact": "serious", "help": "Enough contrast",
                 "nodes": [{"target": [".muted"]}, {"target": ["nav > a"]}]},
            ]},
        ]
        self.assertEqual(C.axe_findings(report), [
            {"rule": "color-contrast", "impact": "serious", "help": "Enough contrast", "nodes": 2,
             "targets": [".muted", "nav > a"], "screenshot": "shots/default-1280.png", "state": "default",
             "viewport": 1280},
            {"rule": "region", "impact": "moderate", "help": "Content in landmarks", "nodes": 1,
             "targets": ["#footer"], "screenshot": "shots/default-390.png", "state": "default", "viewport": 390},
        ])


if __name__ == "__main__":
    unittest.main()

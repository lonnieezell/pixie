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

## Components

| Name | Path / import | Props and variants | When to use | Status |
|---|---|---|---|---|
| `Button` | `@/components/ui/button` | `variant` | Every action | preferred (annotation) |
| `PrimaryButton` | `@/components/PrimaryButton` | `disabled` | Don't use | legacy (annotation) |
| `<x-status-badge>` | `resources/views/components/status-badge.blade.php` | `status` | Order status | preferred (inferred: only one) |
| `AlertCell` | `view_cell('App\\Cells\\AlertCell::show')` | `type` | Flash messages | preferred (inferred: only one) |

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
            ('<div class="md:w-[calc(100%-2rem)]">', ["w-[calc(100%-2rem)]"]),
            ('<div class="data-[state=open]:bg-accent group-[.is-open]:block">', []),
            ('<div class="supports-[display:grid]:grid">', []),
            ('<div class="data-[state=open]:w-[10px] md:-mt-[3px]">', ["w-[10px]", "-mt-[3px]"]),
            ("color: #4F46E5;", ["#4F46E5"]),
            ("border: 1px solid #fff", ["#fff"]),
            ("background: #11223344;", ["#11223344"]),
            ('<a href="#add">Add</a>', []),
            ("&#123; is an entity", []),
            ("<td>#1001</td>", []),
            ('<td style="color:#333">#1001</td>', ["#333"]),
            ("<td>Order #1001</td>", []),
            ("#fab { color: red; }", []),
            ('<button data-target="#abc">', []),
            ("const theme = { text: '#333', bg: \"#fafafa\" };", ["#333", "#fafafa"]),
            ("background: linear-gradient(#fff, #000);", ["#fff", "#000"]),
            ('<div class="mt-4 text-sm">', []),
            ("const first = items[0];", []),
        ]
        for line, expected in cases:
            with self.subTest(line=line):
                hits = C.token_hits("resources/views/a.blade.php", "x\n" + line + "\n")
                self.assertEqual([h["match"] for h in hits], expected)
                for h in hits:
                    self.assertEqual((h["file"], h["line"]), ("resources/views/a.blade.php", 2))

    def test_tells_repeated_values_on_one_line_apart_by_column(self):
        hits = C.token_hits("a.tsx", '<p className="w-[10px] md:w-[10px]" />')
        self.assertEqual([(h["match"], h["column"]) for h in hits], [("w-[10px]", 15), ("w-[10px]", 27)])

    def test_skips_the_inventory_token_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "resources/css").mkdir(parents=True)
            (root / "resources/css/app.css").write_text(":root { --primary: #4f46e5; }\n")
            (root / "page.tsx").write_text('<p className="text-[#333]" />\n')
            hits, skipped = C.token_gate(root, INVENTORY, ["./resources/css/app.css", "page.tsx", "gone.tsx", "resources"])
            self.assertEqual([(h["file"], h["match"]) for h in hits], [("page.tsx", "text-[#333]")])
            self.assertEqual(skipped, ["gone.tsx", "resources"])


class ComponentGateTest(unittest.TestCase):
    def test_checks_new_components_against_the_catalogue(self):
        why = "The catalogued badge has no room for a count."
        cases = [
            ({"name": "OrderSummary", "why": why}, [], None),
            ({"name": "IconButton", "why": why}, ["Button", "PrimaryButton"], None),
            ({"name": "order-badge", "why": why}, ["<x-status-badge>"], None),
            ({"name": "<x-count-badge>", "why": why}, ["<x-status-badge>"], None),
            ({"name": "NoticeAlert", "why": why}, ["AlertCell"], None),
            ({"name": "OrderSummary", "why": "  "}, [], "no reason the catalogued components didn't fit"),
            ({"name": "OrderSummary"}, [], "no reason the catalogued components didn't fit"),
            ({"name": "button", "why": why}, ["Button", "PrimaryButton"], "same name as a catalogued component"),
            ({"name": "x-status-badge", "why": why}, ["<x-status-badge>"], "same name as a catalogued component"),
            ({"name": "alert-cell", "why": why}, ["AlertCell"], "same name as a catalogued component"),
            ({"name": "ButtonCell", "why": why}, ["Button", "PrimaryButton"], None),
            ({"name": "XButton", "why": why}, ["Button", "PrimaryButton"], None),
            ({"name": "<x-previews.order-list-dense.status-badge>", "why": why}, ["<x-status-badge>"],
             "same name as a catalogued component"),
            ({"name": "previews/order-list-dense/alert_cell", "why": why}, ["AlertCell"],
             "same name as a catalogued component"),
            ({"name": "Cell", "why": why}, [], None),
        ]
        for entry, similar, blocked in cases:
            with self.subTest(entry=entry):
                [result] = C.component_gate(INVENTORY, [{"path": "src/x.tsx", **entry}])
                self.assertEqual((result["similar"], result["blocked"]), (similar, blocked))


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
    neighbours = []
    for name in ("list", "detail"):
        (run / name / "shots").mkdir(parents=True)
        neighbours.append(run / name / "shots" / "default-1280.png")
        neighbours[-1].write_bytes(b"\x89PNG")
    return run, neighbours


class BriefTest(unittest.TestCase):
    def test_critic_folder_holds_only_screenshots_rubric_and_context(self):
        with tempfile.TemporaryDirectory() as d:
            run, neighbours = make_run(d)
            critic = C.brief(run, INVENTORY, RUBRIC, EXTRA, neighbours)
            files = sorted(str(p.relative_to(critic)) for p in critic.rglob("*") if p.is_file())
            self.assertEqual(files, [
                "context.md", "manifest.json", "neighbours/1-default-1280.png", "neighbours/2-default-1280.png",
                "rubric.md", "shots/default-1280.png", "shots/default-390.png",
            ])
            rubric = (critic / "rubric.md").read_text()
            self.assertIn("`type.hierarchy`", rubric)
            self.assertIn("`wdg.focus-visible`", rubric)
            self.assertIn("`type.line-length`", rubric)  # dropped items are suppressed at review, not hidden
            context = (critic / "context.md").read_text()
            self.assertIn("Colours come from tokens.", context)
            self.assertIn("Dense tables are fine on admin screens.", context)
            self.assertNotIn("status:", context)
            self.assertNotIn("# Direction", context)

    def test_rerunning_brief_rebuilds_the_folder(self):
        with tempfile.TemporaryDirectory() as d:
            run, neighbours = make_run(d)
            C.brief(run, INVENTORY, RUBRIC, EXTRA, neighbours)
            critic = C.brief(run, INVENTORY, RUBRIC, EXTRA, [])
            self.assertFalse((critic / "neighbours").exists())
            self.assertTrue((critic / "shots" / "default-390.png").exists())

    def test_issue_42_manifest_names_every_neighbour_and_approved_screenshot(self):
        with tempfile.TemporaryDirectory() as d:
            run, neighbours = make_run(d)
            approved, _ = make_run(Path(d) / "winner")
            cases = [
                ({"neighbours": neighbours}, {"neighbours": ["neighbours/1-default-1280.png",
                                                             "neighbours/2-default-1280.png"]}),
                ({"approved": approved}, {"approved": [
                    {"file": "approved/default-390.png", "state": "default", "viewport": 390},
                    {"file": "approved/default-1280.png", "state": "default", "viewport": 1280},
                ]}),
                ({}, {}),
            ]
            for flags, extra in cases:
                with self.subTest(flags=sorted(flags)):
                    critic = C.brief(run, INVENTORY, RUBRIC, EXTRA, flags.get("neighbours", []),
                                     approved=flags.get("approved"))
                    manifest = json.loads((critic / "manifest.json").read_text())
                    self.assertEqual(manifest, {**MANIFEST, **extra})
                    for folder in ("neighbours", "approved"):
                        on_disk = sorted(str(p.relative_to(critic)) for p in critic.glob(f"{folder}/*"))
                        listed = sorted(e if isinstance(e, str) else e["file"] for e in manifest.get(folder, []))
                        self.assertEqual(listed, on_disk)
                        self.assertEqual((critic / folder).exists(), folder in extra)

    def test_approved_direction_lets_the_critic_report_drift(self):
        drift = finding(rubric="direction.drift",
                        observed="The approved summary card above the table is missing from the production screen.")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            run, _ = make_run(d)
            approved, _ = make_run(root / "winner")
            (root / "rubric.md").write_text(RUBRIC + "| `direction.drift` | Matches the approved shot. | S2 |\n")
            (root / "found.json").write_text(json.dumps([drift]))
            base = ["--run", str(run), "--inventory", str(root / "none.md")]

            C.main(["brief", *base, "--rubric", str(root / "rubric.md")])
            C.main(["review", *base, "--findings", str(root / "found.json")])
            self.assertEqual(json.loads((run / "findings.json").read_text())["rejected"][0]["reason"],
                             "no approved screenshots to drift from")

            C.main(["brief", *base, "--rubric", str(root / "rubric.md"), "--approved", str(approved)])
            C.main(["review", *base, "--findings", str(root / "found.json")])
            self.assertEqual(len(json.loads((run / "findings.json").read_text())["accepted"]), 1)
            self.assertEqual(sorted(p.name for p in (run / "critic" / "approved").iterdir()),
                             ["default-1280.png", "default-390.png"])

            (approved / "manifest.json").write_text(json.dumps({**MANIFEST, "shots": []}))
            C.main(["brief", *base, "--rubric", str(root / "rubric.md"), "--approved", str(approved)])
            C.main(["review", *base, "--findings", str(root / "found.json")])
            self.assertEqual(json.loads((run / "findings.json").read_text())["rejected"][0]["reason"],
                             "no approved screenshots to drift from")


def finding(**over):
    f = {
        "rubric": "type.hierarchy", "severity": "S2", "screenshot": "shots/default-390.png",
        "state": "default", "viewport": 390,
        "observed": "Two headings of the same size compete at the top of the order list.",
        "fix": "Make the page title the only heading at the largest size.",
    }
    f.update(over)
    return f


class ReviewFindingsTest(unittest.TestCase):
    def review(self, findings):
        with tempfile.TemporaryDirectory() as d:
            run, neighbours = make_run(d)
            approved, _ = make_run(Path(d) / "winner")
            critic = C.brief(run, INVENTORY, RUBRIC, EXTRA, neighbours, approved=approved)
            return C.review_findings(critic, INVENTORY, findings)

    def test_rejects_findings_without_valid_citations(self):
        cases = [
            ({"rubric": ""}, "missing rubric"),
            ({"observed": "feels cramped"}, "observed is too vague"),
            ({"fix": ""}, "missing fix"),
            ({"severity": "high"}, "bad severity"),
            ({"rubric": "layout.vibes"}, "unknown rubric item"),
            ({"screenshot": "shots/empty-390.png"}, "screenshot not captured"),
            ({"screenshot": "neighbours/1-default-1280.png"}, "screenshot not captured"),
            ({"screenshot": "approved/default-390.png"}, "screenshot not captured"),
            ({"state": "loading"}, "state does not match the screenshot"),
            ({"viewport": 1280}, "viewport does not match the screenshot"),
            ({"rubric": ["type.hierarchy"]}, "rubric must be text"),
            ({"viewport": "390"}, "viewport must be a number"),
        ]
        for over, reason in cases:
            with self.subTest(over=over):
                result = self.review([finding(**over)])
                self.assertEqual(result["accepted"], [])
                self.assertEqual([r["reason"] for r in result["rejected"]], [reason])

    def test_rejects_a_reply_that_is_not_a_list_of_findings(self):
        for reply in ({"findings": [finding()]}, ["not a finding"]):
            with self.subTest(reply=reply), self.assertRaises(ValueError):
                self.review(reply)

    def test_override_suppresses_matching_finding(self):
        result = self.review([finding(rubric="type.line-length")])
        self.assertEqual((result["accepted"], result["rejected"]), ([], []))
        self.assertEqual([f["rubric"] for f in result["suppressed"]], ["type.line-length"])

    def test_ranks_accepted_findings_by_severity(self):
        result = self.review([
            finding(severity="S3"),
            finding(rubric="wdg.focus-visible", severity="S1", screenshot="shots/default-1280.png", viewport=1280),
            finding(severity="S2"),
        ])
        self.assertEqual([f["severity"] for f in result["accepted"]], ["S1", "S2", "S3"])


class CliTest(unittest.TestCase):
    def test_gates_brief_and_review_write_their_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            run, neighbours = make_run(d)
            (run / "axe.json").write_text(json.dumps([{**MANIFEST["shots"][0], "violations": [
                {"id": "region", "impact": "moderate", "help": "Landmarks", "nodes": [{"target": ["#f"]}]}]}]))
            (root / "page.tsx").write_text('<p className="text-[#333]" />\n')
            inventory, rubric, extra, found = root / "inv.md", root / "rubric.md", root / "extra.md", root / "found.json"
            inventory.write_text(INVENTORY)
            rubric.write_text(RUBRIC)
            extra.write_text(EXTRA)
            found.write_text(json.dumps([finding(), finding(rubric="type.line-length")]))
            direction = root / "direction.md"
            direction.write_text("**Dense table.** Density: high. Trades scannability for fewer clicks.\n")

            C.main(["gates", "--root", d, "--run", str(run), "--inventory", str(inventory), "--files", "page.tsx"])
            C.main(["brief", "--run", str(run), "--inventory", str(inventory), "--rubric", str(rubric),
                    "--extra", str(extra), "--direction", str(direction), "--neighbours", *map(str, neighbours)])
            C.main(["review", "--run", str(run), "--inventory", str(inventory), "--findings", str(found)])

            gates = json.loads((run / "gates.json").read_text())
            self.assertEqual([g["rule"] for g in gates["axe"]], ["region"])
            self.assertEqual([g["match"] for g in gates["tokens"]], ["text-[#333]"])
            self.assertEqual(gates["skipped"], [])
            self.assertTrue((run / "critic" / "rubric.md").exists())
            context = (run / "critic" / "context.md").read_text()
            self.assertIn("# Direction\n**Dense table.** Density: high.", context)
            review = json.loads((run / "findings.json").read_text())
            self.assertEqual([len(review[k]) for k in ("accepted", "rejected", "suppressed")], [1, 0, 1])

    def test_strict_gates_exit_1_while_anything_blocks(self):
        clean = {"violations": [], "page": '<p className="text-sm" />', "files": ["page.tsx"],
                 "components": [{"name": "OrderSummary", "path": "page.tsx", "why": "Nothing catalogued shows totals."}]}
        cases = [
            ("clean", {}, None),
            ("axe violation", {"violations": [
                {"id": "region", "impact": "moderate", "help": "Landmarks", "nodes": [{"target": ["#f"]}]}]}, 1),
            ("raw value", {"page": '<p className="text-[#333]" />'}, 1),
            ("unreadable file", {"files": ["gone.tsx"]}, 1),
            ("unjustified component", {"components": [{"name": "OrderSummary", "path": "page.tsx"}]}, 1),
        ]
        for name, over, code in cases:
            c = {**clean, **over}
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                run, _ = make_run(d)
                (run / "axe.json").write_text(json.dumps([{**MANIFEST["shots"][0], "violations": c["violations"]}]))
                (root / "page.tsx").write_text(c["page"] + "\n")
                (root / "inv.md").write_text(INVENTORY)
                (root / "components.json").write_text(json.dumps(c["components"]))
                try:
                    C.main(["gates", "--strict", "--root", d, "--run", str(run), "--inventory", str(root / "inv.md"),
                            "--components", str(root / "components.json"), "--files", *c["files"]])
                    exit_code = None
                except SystemExit as e:
                    exit_code = e.code
                self.assertEqual(exit_code, code)
                gates = json.loads((run / "gates.json").read_text())
                self.assertEqual([c["name"] for c in gates["components"]], ["OrderSummary"])

    def test_refuses_a_missing_input_file(self):
        with tempfile.TemporaryDirectory() as d:
            run, _ = make_run(d)
            (Path(d) / "r.md").write_text(RUBRIC)
            for argv in (["gates", "--run", str(run), "--components", f"{d}/gone.json"],
                         ["brief", "--run", str(run), "--rubric", f"{d}/r.md", "--direction", f"{d}/gone.md"],
                         ["brief", "--run", str(run), "--rubric", f"{d}/gone.md"],
                         ["brief", "--run", str(run), "--rubric", f"{d}/r.md", "--extra", f"{d}/gone.md"],
                         ["brief", "--run", str(run), "--rubric", f"{d}/r.md", "--approved", f"{d}/gone"],
                         ["review", "--run", str(run), "--findings", f"{d}/gone.json"]):
                with self.subTest(argv[0]), self.assertRaises(SystemExit) as exit:
                    C.main(argv)
                self.assertEqual(exit.exception.code, 2)
                self.assertFalse((run / "gates.json").exists())
                self.assertFalse((run / "critic").exists())


class AxeGateTest(unittest.TestCase):
    def test_lists_each_violation_per_screenshot_most_severe_first(self):
        report = [
            {"file": "shots/default-390.png", "state": "default", "viewport": 390, "violations": [
                {"id": "region", "impact": "moderate", "help": "Content in landmarks",
                 "nodes": [{"target": ["#footer"]}]},
            ]},
            {"file": "shots/default-1280.png", "state": "default", "viewport": 1280, "violations": [
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

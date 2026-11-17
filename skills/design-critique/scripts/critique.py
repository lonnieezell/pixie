#!/usr/bin/env python3
"""Scripted gates and critic plumbing for /design-critique."""
import argparse
import json
import os
import re
import shutil
from pathlib import Path

# A Tailwind arbitrary value: text-[#333], -mt-[3px]. Not an arbitrary variant such as data-[state=open]:,
# which is followed by `:`.
ARBITRARY = re.compile(r"(?<![\w\[-])-?[a-z][a-z0-9-]*-\[[^\]\s]+\](?!:)")
# Colours live in property values (`color: #333`, `{ text: '#333' }`), so hex is only looked for after a `:`,
# up to the end of the declaration. That skips plain text (`<td>#1001</td>`), selectors like `#fab {` and
# `href="#id"`, but not hex-like text after another colon (`Fixes: #123`, `:not(#abc)`, `href: "#add"`):
# the skill has the coordinator drop those. `[#333]` is left to ARBITRARY, and `/#abc` is a URL fragment.
VALUE = re.compile(r":([^;{}<>\n]*)")
HEX = re.compile(r"(?<![\w#&/\[])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])")


def section(inventory, name):
    """The body of one `## name` section of the inventory, or ''."""
    match = re.search(rf"^## {re.escape(name)}\n(.*?)(?=^## |\Z)", inventory, re.M | re.S)
    return match.group(1) if match else ""


def token_files(inventory):
    line = re.search(r"^Source files:(.*)$", section(inventory, "Tokens"), re.M)
    return set(re.findall(r"`([^`]+)`", line.group(1))) if line else set()


def token_hits(path, text):
    hits = []
    for number, line in enumerate(text.splitlines(), 1):
        for m in ARBITRARY.finditer(line):
            hits.append(hit(path, number, m.start() + 1, m.group(0), "arbitrary value"))
        for value in VALUE.finditer(line):
            for m in HEX.finditer(value.group(1)):
                hits.append(hit(path, number, value.start(1) + m.start() + 1, m.group(0), "raw hex"))
    return hits


def hit(path, line, column, match, kind):
    return {"file": path, "line": line, "column": column, "match": match, "kind": kind}


RUBRIC_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|")


def dropped(inventory):
    """Rubric IDs the inventory's `- drop: `ID`` override lines suppress."""
    return set(re.findall(r"^- drop:\s*`([^`]+)`", section(inventory, "Rubric overrides"), re.M))


def merge_rubric(rubric, extra):
    rows = [line for line in (extra or "").splitlines() if RUBRIC_ROW.match(line)]
    if not rows:
        return rubric
    return rubric.rstrip("\n") + "\n\n## Added for this repo\n\n| ID | Check | Typical severity |\n|---|---|---|\n" + "\n".join(rows) + "\n"


def brief(run, inventory, rubric, extra, neighbours, direction="", approved=None):
    """Build the critic's folder: screenshots, manifest, rubric and house rules. Never code. With `approved` (the run
    folder of the direction the user picked), the critic also gets its screenshots, to judge drift from."""
    run = Path(run)
    critic = run / "critic"
    shutil.rmtree(critic, ignore_errors=True)
    manifest = json.loads((run / "manifest.json").read_text())
    for shot in manifest["shots"]:
        (critic / shot["file"]).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(run / shot["file"], critic / shot["file"])
    if neighbours:
        (critic / "neighbours").mkdir()
        for number, png in enumerate(map(Path, neighbours), 1):
            shutil.copyfile(png, critic / "neighbours" / f"{number}-{png.name}")
    if approved:
        (critic / "approved").mkdir()
        for shot in json.loads((Path(approved) / "manifest.json").read_text())["shots"]:
            shutil.copyfile(Path(approved) / shot["file"], critic / "approved" / Path(shot["file"]).name)
    (critic / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (critic / "rubric.md").write_text(merge_rubric(rubric, extra))
    (critic / "context.md").write_text(
        "# House rules\n" + section(inventory, "Rules") + "\n# Rubric overrides\n" + section(inventory, "Rubric overrides")
        + ("\n# Direction\n" + direction if direction else "")
    )
    return critic


SEVERITIES = ["S1", "S2", "S3", "S4"]
REQUIRED = ["rubric", "severity", "screenshot", "state", "viewport", "observed", "fix"]
MIN_OBSERVED_WORDS = 6


def first_column(table):
    """The backticked first cell of each row of a markdown table: rubric IDs, catalogued component names."""
    return [m.group(1) for m in map(RUBRIC_ROW.match, table.splitlines()) if m]


def rubric_ids(rubric):
    return set(first_column(rubric))


def rejection(f, ids, shots, approved):
    for field in REQUIRED:
        value = f.get(field)
        if value in (None, ""):
            return f"missing {field}"
        if field == "viewport" and (not isinstance(value, int) or isinstance(value, bool)):
            return "viewport must be a number"
        if field != "viewport" and not isinstance(value, str):
            return f"{field} must be text"
    if f["severity"] not in SEVERITIES:
        return "bad severity"
    if len(f["observed"].split()) < MIN_OBSERVED_WORDS:
        return "observed is too vague"
    if f["rubric"] not in ids:
        return "unknown rubric item"
    if f["rubric"] == "direction.drift" and not approved:
        return "no approved screenshots to drift from"
    shot = shots.get(f["screenshot"])
    if not shot:
        return "screenshot not captured"
    if f["state"] != shot["state"]:
        return "state does not match the screenshot"
    if f["viewport"] != shot["viewport"]:
        return "viewport does not match the screenshot"
    return None


def review_findings(critic, inventory, findings):
    """Split the critic's findings into accepted (ranked), rejected (with a reason) and suppressed."""
    critic = Path(critic)
    ids = rubric_ids((critic / "rubric.md").read_text())
    shots = {s["file"]: s for s in json.loads((critic / "manifest.json").read_text())["shots"]}
    drop = dropped(inventory)
    approved = (critic / "approved").is_dir() and any((critic / "approved").iterdir())
    if not isinstance(findings, list) or not all(isinstance(f, dict) for f in findings):
        raise ValueError("the critic's reply must be a JSON array of finding objects")
    result = {"accepted": [], "rejected": [], "suppressed": []}
    for f in findings:
        if isinstance(f.get("rubric"), str) and f["rubric"] in drop:
            result["suppressed"].append(f)
        elif reason := rejection(f, ids, shots, approved):
            result["rejected"].append({"finding": f, "reason": reason})
        else:
            result["accepted"].append(f)
    result["accepted"].sort(key=lambda f: SEVERITIES.index(f["severity"]))
    return result


IMPACTS = ["critical", "serious", "moderate", "minor"]


def axe_findings(report):
    """One entry per axe violation per screenshot, most severe impact first."""
    found = []
    for shot in report:
        for v in shot["violations"]:
            found.append({
                "rule": v["id"], "impact": v.get("impact") or "minor", "help": v["help"],
                "nodes": len(v["nodes"]), "targets": [" ".join(map(str, n["target"])) for n in v["nodes"]][:5],
                "screenshot": shot["file"], "state": shot["state"], "viewport": shot["viewport"],
            })
    return sorted(found, key=lambda f: IMPACTS.index(f["impact"]) if f["impact"] in IMPACTS else len(IMPACTS))


def token_gate(root, inventory, files):
    """Raw values in the files, and the paths that couldn't be read (so a typo can't pass as clean)."""
    skip = {os.path.normpath(p) for p in token_files(inventory)}
    hits, skipped = [], []
    for rel in map(os.path.normpath, files):
        path = Path(root) / rel
        if not path.is_file():
            skipped.append(rel)
        elif rel not in skip:
            hits += token_hits(rel, path.read_text(errors="replace"))
    return hits, skipped


def name_words(name):
    """`<x-status-badge>`, `StatusBadge` and `status_badge` all give ['status', 'badge']: a Blade tag's `x-` is
    dropped (but not the X of `XAxis`), and so is a folder (`<x-previews.dense.status-badge>`, `previews/dense/a`)."""
    base = name.strip("<>/ ")
    base = re.split(r"[./\\]|::", base[2:] if base.startswith("x-") else base)[-1]
    return [w.lower() for w in re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z0-9]+", base)]


def kind(words):
    """The last word, which says what kind of component it is. A CI4 `Cell` or `Component` suffix doesn't count,
    so `AlertCell` is an 'alert'."""
    return words[-2:-1] if len(words) > 1 and words[-1] in ("cell", "component") else words[-1:]


def component_gate(inventory, entries):
    """For each component a design direction adds: the catalogued components of the same kind, and why it's
    blocked, if it is: the same name as a catalogued one, or no stated reason."""
    catalogue = [(name, name_words(name)) for name in first_column(section(inventory, "Components"))]
    results = []
    for entry in entries:
        words = name_words(entry["name"])
        similar = [(name, w) for name, w in catalogue if kind(w) == kind(words)]
        if words and any(w == words for _, w in similar):
            blocked = "same name as a catalogued component"
        elif not str(entry.get("why") or "").strip():
            blocked = "no reason the catalogued components didn't fit"
        else:
            blocked = None
        results.append({**entry, "similar": [name for name, _ in similar], "blocked": blocked})
    return results


def read(path):
    """A file's text, or '' when it's missing (a repo without a design inventory)."""
    return Path(path).read_text() if path and Path(path).exists() else ""


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gates", help="axe and token-compliance gates -> RUN/gates.json")
    g.add_argument("--root", default=".")
    g.add_argument("--files", nargs="*", default=[], help="repo-relative files that render the route")
    g.add_argument("--components", help="JSON list of the components a design direction adds: name, path, why")
    g.add_argument("--strict", action="store_true", help="exit 1 while any gate has a failure")
    b = sub.add_parser("brief", help="the critic's code-free folder -> RUN/critic/")
    b.add_argument("--rubric", required=True)
    b.add_argument("--extra", help="extra rubric rows from installed design skills")
    b.add_argument("--neighbours", nargs="*", default=[])
    b.add_argument("--direction", help="the design direction this screen was built to, from /design's brief")
    b.add_argument("--approved", help="run folder of the approved direction, to check the screen for drift from it")
    r = sub.add_parser("review", help="validate, suppress and rank the critic's findings -> RUN/findings.json")
    r.add_argument("--findings", required=True)
    for s in (g, b, r):
        s.add_argument("--run", required=True)
        s.add_argument("--inventory", default="docs/agents/design-system.md")
    a = p.parse_args(argv)
    for given in (getattr(a, name, None) for name in ("components", "direction", "rubric", "extra", "findings")):
        if given and not Path(given).is_file():
            p.error(f"no such file: {given}")
    if getattr(a, "approved", None) and not (Path(a.approved) / "manifest.json").is_file():
        p.error(f"no manifest.json in {a.approved}")
    run, inventory = Path(a.run), read(a.inventory)

    if a.cmd == "gates":
        axe = axe_findings(json.loads(read(run / "axe.json") or "[]"))
        tokens, skipped = token_gate(a.root, inventory, a.files)
        gates = {"axe": axe, "tokens": tokens, "skipped": skipped}
        summary = f"axe violations: {len(axe)}, raw values: {len(tokens)}, unreadable files: {skipped or 'none'}"
        blocked = []
        if a.components:
            gates["components"] = component_gate(inventory, json.loads(read(a.components)))
            blocked = [c["name"] for c in gates["components"] if c["blocked"]]
            summary += f", blocked components: {blocked or 'none'}"
        (run / "gates.json").write_text(json.dumps(gates, indent=2))
        print(f"{summary} -> {run / 'gates.json'}")
        if a.strict and (axe or tokens or skipped or blocked):
            raise SystemExit(1)
    elif a.cmd == "brief":
        print(brief(run, inventory, read(a.rubric), read(a.extra), a.neighbours, read(a.direction), a.approved))
    else:
        result = review_findings(run / "critic", inventory, json.loads(read(a.findings)))
        (run / "findings.json").write_text(json.dumps(result, indent=2))
        print(", ".join(f"{k}: {len(v)}" for k, v in result.items()) + f" -> {run / 'findings.json'}")


if __name__ == "__main__":
    main()

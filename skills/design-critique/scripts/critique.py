#!/usr/bin/env python3
"""Scripted gates and critic plumbing for /design-critique."""
import argparse
import json
import re
import shutil
from pathlib import Path

# A Tailwind arbitrary value, with any variant prefixes: text-[#333], md:w-[calc(100%-2rem)].
ARBITRARY = re.compile(r"(?<![\w\[:-])(?:[a-z][a-z0-9-]*:)*-?[a-z][a-z0-9-]*-\[[^\]\s]+\]")
# Not after `&` (an entity), and not right after `>` or before `<`: that's text, such as <td>#1001</td>.
HEX = re.compile(r"(?<![&\w#>])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w<-])")
LINK_ATTR = re.compile(r"(?:href|to)=[\"']$")


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
        spans = []
        for m in ARBITRARY.finditer(line):
            spans.append(m.span())
            hits.append({"file": path, "line": number, "match": m.group(0), "kind": "arbitrary value"})
        for m in HEX.finditer(line):
            inside = any(start <= m.start() < end for start, end in spans)
            if not inside and not LINK_ATTR.search(line[: m.start()]):
                hits.append({"file": path, "line": number, "match": m.group(0), "kind": "raw hex"})
    return hits


RUBRIC_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|")


def dropped(inventory):
    """Rubric IDs the inventory's `- drop: `ID`` override lines suppress."""
    return set(re.findall(r"^- drop:\s*`([^`]+)`", section(inventory, "Rubric overrides"), re.M))


def merge_rubric(rubric, extra, drop):
    def keep(line):
        m = RUBRIC_ROW.match(line)
        return not (m and m.group(1) in drop)

    merged = "\n".join(filter(keep, rubric.splitlines())) + "\n"
    rows = [line for line in (extra or "").splitlines() if RUBRIC_ROW.match(line) and keep(line)]
    if rows:
        merged += "\n## Added for this repo\n\n| ID | Check | Typical severity |\n|---|---|---|\n" + "\n".join(rows) + "\n"
    return merged


def brief(run, inventory, rubric, extra, neighbours):
    """Build the critic's folder: screenshots, manifest, rubric and house rules. Never code."""
    run = Path(run)
    critic = run / "critic"
    manifest = json.loads((run / "manifest.json").read_text())
    for shot in manifest["shots"]:
        (critic / shot["file"]).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(run / shot["file"], critic / shot["file"])
    if neighbours:
        (critic / "neighbours").mkdir()
        for png in map(Path, neighbours):
            shutil.copyfile(png, critic / "neighbours" / png.name)
    (critic / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (critic / "rubric.md").write_text(merge_rubric(rubric, extra, dropped(inventory)))
    (critic / "context.md").write_text(
        "# House rules\n" + section(inventory, "Rules") + "\n# Rubric overrides\n" + section(inventory, "Rubric overrides")
    )
    return critic


SEVERITIES = ["S1", "S2", "S3", "S4"]
REQUIRED = ["rubric", "severity", "screenshot", "state", "viewport", "observed", "fix"]
MIN_OBSERVED_WORDS = 6


def rubric_ids(rubric):
    return {m.group(1) for m in map(RUBRIC_ROW.match, rubric.splitlines()) if m}


def rejection(f, ids, shots):
    for field in REQUIRED:
        if f.get(field) in (None, ""):
            return f"missing {field}"
    if f["severity"] not in SEVERITIES:
        return "bad severity"
    if len(str(f["observed"]).split()) < MIN_OBSERVED_WORDS:
        return "observed is too vague"
    if f["rubric"] not in ids:
        return "unknown rubric item"
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
    result = {"accepted": [], "rejected": [], "suppressed": []}
    for f in findings:
        if f.get("rubric") in drop:
            result["suppressed"].append(f)
        elif reason := rejection(f, ids, shots):
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
                "screenshot": shot["screenshot"], "state": shot["state"], "viewport": shot["viewport"],
            })
    return sorted(found, key=lambda f: IMPACTS.index(f["impact"]) if f["impact"] in IMPACTS else len(IMPACTS))


def token_gate(root, inventory, files):
    skip = token_files(inventory)
    hits = []
    for rel in files:
        if rel not in skip:
            hits += token_hits(rel, (Path(root) / rel).read_text(errors="replace"))
    return hits


def read(path):
    """A file's text, or '' when it's missing (a repo without a design inventory)."""
    return Path(path).read_text() if path and Path(path).exists() else ""


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gates", help="axe and token-compliance gates -> RUN/gates.json")
    g.add_argument("--root", default=".")
    g.add_argument("--files", nargs="*", default=[], help="repo-relative files that render the route")
    b = sub.add_parser("brief", help="the critic's code-free folder -> RUN/critic/")
    b.add_argument("--rubric", required=True)
    b.add_argument("--extra", help="extra rubric rows from installed design skills")
    b.add_argument("--neighbours", nargs="*", default=[])
    r = sub.add_parser("review", help="validate, suppress and rank the critic's findings -> RUN/findings.json")
    r.add_argument("--findings", required=True)
    for s in (g, b, r):
        s.add_argument("--run", required=True)
        s.add_argument("--inventory", default="docs/agents/design-system.md")
    a = p.parse_args(argv)
    run, inventory = Path(a.run), read(a.inventory)

    if a.cmd == "gates":
        axe = axe_findings(json.loads(read(run / "axe.json") or "[]"))
        tokens = token_gate(a.root, inventory, a.files)
        (run / "gates.json").write_text(json.dumps({"axe": axe, "tokens": tokens}, indent=2))
        print(f"axe violations: {len(axe)}, raw values: {len(tokens)} -> {run / 'gates.json'}")
    elif a.cmd == "brief":
        print(brief(run, inventory, read(a.rubric), read(a.extra), a.neighbours))
    else:
        result = review_findings(run / "critic", inventory, json.loads(read(a.findings)))
        (run / "findings.json").write_text(json.dumps(result, indent=2))
        print(", ".join(f"{k}: {len(v)}" for k, v in result.items()) + f" -> {run / 'findings.json'}")


if __name__ == "__main__":
    main()

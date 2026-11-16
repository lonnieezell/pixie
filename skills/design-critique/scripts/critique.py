#!/usr/bin/env python3
"""Scripted gates and critic plumbing for /design-critique."""
import re
from pathlib import Path

# A Tailwind arbitrary value, with any variant prefixes: text-[#333], md:w-[calc(100%-2rem)].
ARBITRARY = re.compile(r"(?<![\w\[:-])(?:[a-z][a-z0-9-]*:)*-?[a-z][a-z0-9-]*-\[[^\]\s]+\]")
HEX = re.compile(r"(?<![&\w#])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])")
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

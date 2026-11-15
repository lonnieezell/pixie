#!/usr/bin/env python3
"""Deterministic steps of the checkup and catch pipelines. Run from the repo root.

  plan      shards the repo and decides what to audit       -> plan.json
  merge     validates agent results, dedupes, merges         -> candidates.json
  brief     prints one candidate's issue body (for agents)
  finalize  applies annotations, scores, compares, reports   -> findings.json, report.md, baseline-next.json
  file      files eligible findings on GitHub                -> filed.json
  promote   queues eligible issues for tackle, within the weekly cap (prints issue numbers)
  publish   commits baseline-next.json to the rolling baseline PR
"""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import baseline as B  # noqa: E402
import config as C  # noqa: E402
import findings as F  # noqa: E402
import github_ops as G  # noqa: E402
import shards as S  # noqa: E402

DIMENSION_AGENTS = {"security": "audit-security", "performance": "audit-performance", "bug": "audit-bugs"}


def _load(path):
    return json.loads(Path(path).read_text())


def _write(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2) + "\n")


def _sha():
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()


def _repo():
    out = G.gh(G.subprocess_run, "repo", "view", "--json", "nameWithOwner,visibility,defaultBranchRef")
    return json.loads(out)


def _result_name(shard, dimension):
    """Result file for one hunter job. Hashed, so no two shard IDs can collide on disk."""
    return f"{hashlib.sha1(shard.encode()).hexdigest()[:12]}.{dimension}.json"


def plan_jobs(shards, baseline, mode, max_shards):
    """Decide what to audit. Pure, so the budget and carry rules are testable.

    Returns (jobs, carried, unchanged, gaps). Shards over the budget aren't audited:
    their baseline findings are carried (stale if the code changed) and they're listed
    as gaps. When the baseline withholds security findings, `changed` mode can't carry
    them, so it audits the security dimension of unchanged shards too.
    """
    old = (baseline or {}).get("shards", {})
    unchanged = [s["id"] for s in shards if old.get(s["id"]) == s["hash"]]
    todo = [s["id"] for s in shards if mode == "full" or s["id"] not in unchanged]
    audit, over = todo[:max_shards], todo[max_shards:]
    jobs = [(sid, d) for sid in audit for d in F.DIMENSIONS]
    gaps = [f"shard {sid}: not audited, over the maxShards budget ({max_shards})" for sid in over]
    if mode == "changed" and "security" in (baseline or {}).get("withheld", {}):
        rest = [sid for sid in unchanged if sid not in audit]
        jobs += [(sid, "security") for sid in rest[:max_shards]]
        gaps += [f"shard {sid} / security: not audited, over the maxShards budget ({max_shards})"
                 for sid in rest[max_shards:]]
    carried = B.carried(baseline, [s for s in shards if s["id"] not in audit], unchanged)
    return jobs, carried, unchanged, gaps


def cmd_plan(a, cfg):
    tracked = S.git_blobs(".")
    blobs = S.select(tracked, cfg["exclude"], cfg["includeTests"], S.git_marked(".", tracked))
    lines = S.count_lines(".", blobs)
    shards = S.build(blobs, cfg["shardSize"], S.git_churn("."), lines)
    if a.path:
        prefix = a.path.strip("/").removeprefix("./").rstrip("/") + "/"
        shards = [s for s in shards if any(f.startswith(prefix) or f + "/" == prefix for f in s["files"])]
    base, base_ref = B.read(".")
    jobs, carried, unchanged, gaps = plan_jobs(shards, base, a.mode, cfg["maxShards"])
    plan = {
        "sha": _sha(), "mode": a.mode, "path": a.path, "baseline_ref": base_ref, "baseline": base,
        "kloc": sum(s["lines"] for s in shards) / 1000, "shards": shards, "unchanged": unchanged,
        "jobs": [{"shard": sid, "dimension": d, "agent": DIMENSION_AGENTS[d], "result": _result_name(sid, d)}
                 for sid, d in jobs],
        "carried": carried, "gaps": gaps,
        "maxFindingsPerHunter": cfg["maxFindingsPerHunter"],
    }
    _write(a.out, plan)
    print(json.dumps({"shards": len(shards), "jobs": len(jobs), "carried": len(carried),
                      "gaps": len(gaps), "baseline": base_ref}))


def cmd_merge(a, cfg):
    plan = _load(a.plan) if a.plan else None
    folder = Path(a.results)
    if plan:
        expected = {j["result"]: (j["shard"], j["dimension"]) for j in plan["jobs"]}
    else:
        expected = {p.name: None for p in sorted(folder.glob("*.json"))}
    raw, incomplete = [], []
    limit = cfg["maxFindingsPerHunter"]
    for name, job in expected.items():
        path = folder / name
        key = job or (path.stem, None)
        if not path.exists():
            incomplete.append({"shard": key[0], "dimension": key[1], "reason": "no result", "failed": True})
            continue
        try:
            res = _load(path)
        except json.JSONDecodeError:
            incomplete.append({"shard": key[0], "dimension": key[1], "reason": "not valid JSON", "failed": True})
            continue
        if not job:
            key = (res.get("shard") or path.stem, res.get("dimension"))
        if res.get("status") not in ("PASS", "ISSUES", "BLOCKED"):
            incomplete.append({"shard": key[0], "dimension": key[1], "reason": "missing status", "failed": True})
            continue
        if res["status"] == "BLOCKED":
            incomplete.append({"shard": key[0], "dimension": key[1], "failed": True,
                               "reason": "blocked: " + F.sanitize(res.get("blocked_reason", ""), 200)})
            continue
        for f in res.get("findings", [])[:limit]:
            f = F.clean(f, allow_external=a.source == "catch")
            f.setdefault("dimension", key[1])
            errors = F.validate(f)
            if errors:
                incomplete.append({"shard": key[0], "dimension": key[1],
                                   "reason": f"dropped invalid finding: {', '.join(errors)}"})
                continue
            raw.append(dict(f, shard=key[0]))
    candidates = F.merge(raw) + (plan["carried"] if plan else [])
    out = {"candidates": candidates, "incomplete": incomplete,
           "to_verify": [c["id"] for c in candidates if F.needs_verify(c)]}
    _write(a.out, out)
    print(json.dumps({"candidates": len(candidates), "to_verify": len(out["to_verify"]),
                      "incomplete": incomplete}))


def _annotations(folder):
    out = {}
    if folder and Path(folder).exists():
        for path in sorted(Path(folder).glob("*.json")):
            ann, new = out.setdefault(path.name.split(".", 1)[0], {}), _load(path)
            rung = max(ann.get("evidence_rung", 0), new.get("evidence_rung", 0))
            ann.update(new)
            if rung:
                ann["evidence_rung"] = rung
    return out


def cmd_brief(a, cfg):
    data = _load(a.candidates)
    ann = _annotations(a.annotations)
    for c in data["candidates"]:
        if c["id"] == a.id:
            c = dict(c, **ann.get(c["id"], {}))
            c.setdefault("severity", c.get("severity_hint", "medium"))
            print(F.render_brief(c, _sha(), a.source))
            return
    sys.exit(f"no candidate {a.id}")


def checked_shards(plan, incomplete):
    """Shards whose findings are current: every job on them returned, or they were
    carried unchanged. Anything else keeps its old baseline hash and is audited again."""
    failed = {i["shard"] for i in incomplete if i.get("failed")}
    return (set(plan["unchanged"]) | {j["shard"] for j in plan["jobs"]}) - failed


def cmd_finalize(a, cfg):
    data = _load(a.candidates)
    candidates, incomplete = data["candidates"], data["incomplete"]
    gaps = [f"{i.get('shard') or '-'} / {i.get('dimension') or '-'}: {i['reason']}" for i in incomplete]
    out = Path(a.out_dir)
    sha = _sha()
    scores, comparison, kloc, health, plan = None, {"first_run": True}, 0.0, None, None
    if a.plan:
        plan = _load(a.plan)
        base = plan["baseline"]
        failed = {(i["shard"], i["dimension"]) for i in incomplete if i.get("failed")}
        candidates = candidates + B.restore(base, failed)
    confirmed, other = F.apply_annotations(candidates, _annotations(a.annotations))
    if plan:
        gaps = plan["gaps"] + gaps
        kloc = plan["kloc"]
        scores = F.score(confirmed, kloc)
        checked = checked_shards(plan, incomplete)
        if plan["path"]:
            comparison = {"scoped": True}
        else:
            comparison = F.compare(scores, confirmed, base, cfg["scoreDropThreshold"],
                                   checked=checked, unchanged=set(plan["unchanged"]))
        if a.km and Path(a.km).exists():
            health = _load(a.km).get("score")
        if not plan["path"]:
            hide = G.security_mode(cfg["securityFindings"], _repo()["visibility"]) != "issues"
            doc = B.build(confirmed, scores, plan["shards"], sha,
                          datetime.now(timezone.utc).date().isoformat(), kloc, hide, checked, base)
            _write(out / "baseline-next.json", doc)
    _write(out / "findings.json", {"sha": sha, "confirmed": confirmed, "other": other, "gaps": gaps,
                                   "scores": scores, "comparison": comparison})
    (out / "report.md").write_text(F.render_report(confirmed, other, scores, comparison, gaps, sha, kloc, health))
    summary = {"confirmed": len(confirmed), "by_severity": {s: sum(1 for c in confirmed if c["severity"] == s)
                                                           for s in F.SEVERITIES},
               "scores": scores, "regressed": comparison.get("regressed", False), "gaps": len(gaps)}
    print(json.dumps(summary))


def cmd_file(a, cfg):
    data = _load(a.findings)
    repo = _repo()
    results = G.file_all(G.subprocess_run, data["confirmed"], cfg, source=a.source, sha=data["sha"], repo=repo,
                         roles=G.label_map("."), now=datetime.now(timezone.utc))
    _write(a.out, results)
    print(json.dumps(results))


def cmd_promote(a, cfg):
    data = _load(a.findings)
    promoted, skipped = G.promote(G.subprocess_run, data["confirmed"], _load(a.filed), cfg, source=a.source,
                                  roles=G.label_map("."), now=datetime.now(timezone.utc))
    _write(a.out, {"promoted": promoted, "skipped": skipped})
    print(json.dumps({"promoted": promoted, "skipped": skipped}))


def cmd_publish(a, cfg):
    print(B.publish(_load(a.file), _repo()["defaultBranchRef"]["name"], "."))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("plan"); s.add_argument("--mode", choices=["full", "changed"], default="full")
    s.add_argument("--path"); s.add_argument("--out", required=True)
    s = sub.add_parser("merge"); s.add_argument("--results", required=True); s.add_argument("--plan")
    s.add_argument("--source", choices=["checkup", "catch"], default="checkup")
    s.add_argument("--out", required=True)
    s = sub.add_parser("brief"); s.add_argument("--candidates", required=True); s.add_argument("--id", required=True)
    s.add_argument("--annotations"); s.add_argument("--source", default="checkup")
    s = sub.add_parser("finalize"); s.add_argument("--candidates", required=True); s.add_argument("--annotations")
    s.add_argument("--plan"); s.add_argument("--km"); s.add_argument("--out-dir", required=True)
    s = sub.add_parser("file"); s.add_argument("--findings", required=True); s.add_argument("--out", required=True)
    s.add_argument("--source", choices=["checkup", "catch"], required=True)
    s = sub.add_parser("promote"); s.add_argument("--findings", required=True); s.add_argument("--filed", required=True)
    s.add_argument("--source", choices=["checkup", "catch"], required=True); s.add_argument("--out", required=True)
    s = sub.add_parser("publish"); s.add_argument("--file", required=True)
    a = p.parse_args(argv)
    cfg = C.load(".")
    globals()[f"cmd_{a.cmd}"](a, cfg)


if __name__ == "__main__":
    main()

"""Read and publish docs/agents/checkup-baseline.json through a rolling PR.

The weekly run rebuilds the `checkup/baseline` branch from the default branch each
time and force-pushes it with a lease. Only this bot branch is ever force-pushed.
While its PR is open, the next run reads the baseline from that branch.
"""
import json
import subprocess
import tempfile
from pathlib import Path

import config as C
import findings as F

VOLATILE = ("sha", "date")


def build(confirmed, scores, shards, sha, date, kloc, hide_security, checked, previous=None):
    """Baseline document.

    checked: ids of shards whose findings are current. Every other shard keeps the
    previous baseline's hash, or none, so the next run audits it again and it never
    counts as clean.

    hide_security: security findings are left out entirely and only their counts by
    severity are kept. Fingerprints hash file, symbol and category, which an attacker
    could brute-force from a public repo, so even hashes would locate an open flaw.
    """
    prev_hashes = (previous or {}).get("shards", {})
    hashes = {}
    for s in shards:
        if s["id"] in checked:
            hashes[s["id"]] = s["hash"]
        elif s["id"] in prev_hashes:
            hashes[s["id"]] = prev_hashes[s["id"]]
    doc = {
        "version": 1,
        "sha": sha,
        "date": date,
        "kloc": round(kloc, 2),
        "scores": scores,
        "shards": hashes,
        "findings": [f for f in confirmed if not (hide_security and f["dimension"] == "security")],
    }
    if hide_security:
        sec = [f for f in confirmed if f["dimension"] == "security"]
        doc["withheld"] = {"security": {s: sum(1 for f in sec if f["severity"] == s) for s in F.SEVERITIES}}
    return doc


def carried(baseline, shards, unchanged):
    """Baseline findings for shards this run won't audit.

    A finding from a shard whose code changed is marked `stale`: it's kept for the
    score and the next baseline, but it isn't filed, because nobody re-checked it.
    """
    if not baseline:
        return []
    ids = {s["id"] for s in shards}
    return [dict(f, stale=f.get("shard") not in unchanged) for f in baseline.get("findings", [])
            if f.get("shard") in ids]


def restore(baseline, failed):
    """Baseline findings for (shard, dimension) jobs that failed this run, marked stale."""
    if not baseline:
        return []
    return [dict(f, stale=True) for f in baseline.get("findings", []) if (f.get("shard"), f["dimension"]) in failed]


def _git(*args, cwd=".", check=True):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, check=check)


def _open_pr(repo):
    p = subprocess.run(["gh", "pr", "list", "--head", C.BASELINE_BRANCH, "--state", "open", "--json", "number"],
                       capture_output=True, text=True, cwd=repo)
    prs = json.loads(p.stdout or "[]") if p.returncode == 0 else []
    return prs[0]["number"] if prs else None


def read(repo="."):
    """Baseline from the branch of the open baseline PR, else from HEAD, else None.

    A branch whose PR was closed without merging is ignored: a human rejected it.
    """
    refs = ["HEAD"]
    if _open_pr(repo):
        ref = f"refs/remotes/origin/{C.BASELINE_BRANCH}"
        if _git("fetch", "origin", f"+refs/heads/{C.BASELINE_BRANCH}:{ref}", cwd=repo, check=False).returncode == 0:
            refs.insert(0, ref)
    for ref in refs:
        p = _git("show", f"{ref}:{C.BASELINE_PATH}", cwd=repo, check=False)
        if p.returncode == 0:
            return json.loads(p.stdout), ref
    return None, None


def _same(text, doc):
    try:
        old = json.loads(text)
    except json.JSONDecodeError:
        return False
    strip = lambda d: {k: v for k, v in d.items() if k not in VOLATILE}  # noqa: E731
    return strip(old) == strip(doc)


def publish(doc, default_branch, repo="."):
    """Commit the baseline on a fresh branch from the default branch and open or update its PR."""
    _git("fetch", "origin", default_branch, cwd=repo)
    current = _git("show", f"origin/{default_branch}:{C.BASELINE_PATH}", cwd=repo, check=False)
    if current.returncode == 0 and _same(current.stdout, doc):
        return "unchanged"
    text = json.dumps(doc, indent=2, sort_keys=True) + "\n"
    ref = f"refs/heads/{C.BASELINE_BRANCH}"
    remote = _git("ls-remote", "--heads", "origin", ref, cwd=repo).stdout.split()
    lease = f"--force-with-lease={ref}:{remote[0] if remote else ''}"
    with tempfile.TemporaryDirectory(prefix="pixie-baseline-") as tmp:
        wt = str(Path(tmp) / "wt")
        _git("worktree", "add", "--detach", wt, f"origin/{default_branch}", cwd=repo)
        try:
            target = Path(wt) / C.BASELINE_PATH
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
            _git("add", C.BASELINE_PATH, cwd=wt)
            _git("commit", "-m", f"chore(checkup): update baseline for {doc['date']}", cwd=wt)
            _git("push", lease, "origin", f"HEAD:{ref}", cwd=wt)
        finally:
            _git("worktree", "remove", "--force", wt, cwd=repo, check=False)
    body = _pr_body(doc)
    number = _open_pr(repo)
    if number:
        subprocess.run(["gh", "pr", "edit", str(number), "--body", body], check=True, cwd=repo)
        return f"updated #{number}"
    out = subprocess.run(
        ["gh", "pr", "create", "--base", default_branch, "--head", C.BASELINE_BRANCH,
         "--title", "chore(checkup): weekly baseline", "--body", body],
        capture_output=True, text=True, check=True, cwd=repo).stdout.strip()
    return f"opened {out}"


def _pr_body(doc):
    rows = "\n".join(f"| {d} | {v} |" for d, v in doc["scores"].items())
    counts = {s: sum(1 for f in doc["findings"] if f["severity"] == s) for s in F.SEVERITIES}
    for by_sev in doc.get("withheld", {}).values():
        for s, n in by_sev.items():
            counts[s] += n
    return (
        "> *Generated by AI (pixie checkup).*\n\n"
        f"Checkup baseline for {doc['date']} at `{doc['sha'][:12]}`. Merge it to make these scores the new baseline. "
        "Until it merges, the next run reads the baseline from this branch.\n\n"
        f"| Dimension | Score |\n|---|---|\n{rows}\n\n"
        "Confirmed findings: " + ", ".join(f"{n} {s}" for s, n in counts.items()) + ".\n"
    )

"""Split a repo's tracked source files into audit shards.

A shard is a directory (or a chunk of one) of at most `size` files. Its hash
covers every file's git blob, so an unchanged shard can reuse last run's results.
"""
import hashlib
import re
import subprocess
from pathlib import Path

SOURCE_EXTS = {
    ".php", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte", ".py", ".rb",
    ".go", ".rs", ".java", ".kt", ".cs", ".swift", ".sql", ".sh",
}
TEST_DIRS = {"tests", "test", "__tests__", "spec", "specs"}
TEST_FILE = re.compile(r"(\.(test|spec)\.[a-z]+$)|(Test\.php$)|(_test\.(go|py|rb)$)|(^test_.*\.py$)")


def is_test(path):
    parts = Path(path).parts
    return bool(TEST_DIRS & set(parts[:-1])) or bool(TEST_FILE.search(parts[-1]))


def select(blobs, exclude, include_tests):
    """blobs: {path: blob_sha}. Keep source files not excluded."""
    out = {}
    for path, sha in blobs.items():
        if Path(path).suffix not in SOURCE_EXTS:
            continue
        if any(f"/{e}" in f"/{path}" for e in exclude):
            continue
        if not include_tests and is_test(path):
            continue
        out[path] = sha
    return out


def _split(prefix, paths, size):
    """A folder that fits in one shard stays whole. In a bigger folder, its loose files and
    the subfolders that fit are packed together in name order, so a tree of many tiny
    folders doesn't become one shard per folder. Subfolders too big to fit split the same way.

    A packed shard is named after its first and last member, e.g. `src[Auth..Cart]`.
    """
    if len(paths) <= size:
        return [(prefix or ".", sorted(paths))]
    depth = len(Path(prefix).parts) if prefix else 0
    units, subdirs = [], {}
    for p in paths:
        parts = Path(p).parts
        if len(parts) == depth + 1:
            units.append((parts[-1], [p]))
        else:
            subdirs.setdefault(parts[depth], []).append(p)
    out = []
    for name, files in sorted(subdirs.items()):
        if len(files) <= size:
            units.append((name, files))
        else:
            out += _split("/".join(Path(files[0]).parts[: depth + 1]), files, size)
    groups, group = [], []
    for unit in sorted(units):
        if group and sum(len(f) for _, f in group) + len(unit[1]) > size:
            groups.append(group)
            group = []
        group.append(unit)
    if group:
        groups.append(group)
    base = prefix or "."
    loose = sorted(n for n, _ in units if n not in subdirs)
    for g in groups:
        names = [n for n, _ in g]
        if len(g) == 1 and g[0][0] in subdirs:
            sid = f"{prefix}/{g[0][0]}" if prefix else g[0][0]
        elif names == loose:
            sid = base
        else:
            sid = f"{base}[{g[0][0]}..{g[-1][0]}]" if len(g) > 1 else f"{base}[{g[0][0]}]"
        out.append((sid, sorted(p for _, files in g for p in files)))
    return out


def shard_hash(files, blobs):
    data = "\n".join(f"{p} {blobs[p]}" for p in sorted(files))
    return hashlib.sha1(data.encode()).hexdigest()


def build(blobs, size, churn=None, lines=None):
    """Return shards, busiest first: [{id, files, hash, churn, lines}]."""
    churn, lines = churn or {}, lines or {}
    shards = []
    for sid, files in _split("", list(blobs), size):
        shards.append({
            "id": sid,
            "files": files,
            "hash": shard_hash(files, blobs),
            "churn": sum(churn.get(f, 0) for f in files),
            "lines": sum(lines.get(f, 0) for f in files),
        })
    return sorted(shards, key=lambda s: (-s["churn"], s["id"]))


# --- git readers (thin, not unit-tested) -------------------------------------------------

def git_blobs(repo):
    # -z and quotePath=false: git otherwise quotes non-ASCII paths, which then match no extension.
    out = subprocess.run(["git", "-C", repo, "ls-files", "-s", "-z"], capture_output=True, text=True, check=True).stdout
    blobs = {}
    for entry in filter(None, out.split("\0")):
        meta, path = entry.split("\t", 1)
        blobs[path] = meta.split()[1]
    return blobs


def git_churn(repo, since="90 days ago"):
    out = subprocess.run(
        ["git", "-C", repo, "-c", "core.quotePath=false", "log", f"--since={since}", "--name-only", "--format="],
        capture_output=True, text=True, check=True,
    ).stdout
    counts = {}
    for path in filter(None, out.splitlines()):
        counts[path] = counts.get(path, 0) + 1
    return counts


def count_lines(repo, paths):
    out = {}
    for p in paths:
        try:
            text = (Path(repo) / p).read_text(errors="replace")
        except OSError:
            continue
        out[p] = sum(1 for line in text.splitlines() if line.strip())
    return out

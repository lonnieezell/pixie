#!/usr/bin/env python3
"""Fetch recent production errors from Sentry and Coralogix as redacted reports.

  catch.py fetch --out reports.json

Reads docs/agents/checkup.json ("catch" section) and these environment variables:
  SENTRY_AUTH_TOKEN   (scope event:read)          used when catch.sentry.org is set
  CORALOGIX_API_KEY   (DataQuerying preset)       used when catch.coralogix.domain is set

Each report keeps only what triage needs: exception type, a redacted and truncated
message, stack frames mapped to repo files, counts, release and links. Request data,
headers, user data and breadcrumbs are never fetched into the report.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "checkup" / "scripts"))

import config as C  # noqa: E402

# --- redaction -----------------------------------------------------------------------

_REDACTIONS = [
    (re.compile(r"eyJ[\w-]+\.[\w-]+\.[\w-]+"), "<REDACTED:jwt>"),
    (re.compile(r"(?i)\b(bearer|token|api[_-]?key|secret|password|passwd|pwd|authorization|cookie|session)"
                r"(\s*[=:]\s*|\s+)((?:bearer|basic)\s+)?([^\s,;&\"']+)"), r"\1\2\3<REDACTED>"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "<REDACTED:email>"),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "<REDACTED:ip>"),
    (re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){4,7}[0-9a-fA-F]{1,4}\b"), "<REDACTED:ip>"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "<REDACTED:number>"),
    (re.compile(r"\b[A-Za-z0-9+_-]{32,}={0,2}"), "<REDACTED:secret>"),
]


def redact(text, limit=500):
    text = str(text or "")
    for pattern, repl in _REDACTIONS:
        text = pattern.sub(repl, text)
    return text if len(text) <= limit else text[:limit] + " …(truncated)"


# --- frame mapping -------------------------------------------------------------------

_FRAME_PATTERNS = [
    re.compile(r'File "(?P<path>[^"]+)", line (?P<line>\d+), in (?P<func>[\w<>.]+)'),       # Python
    re.compile(r"#\d+ (?P<path>[^\s(]+\.php)\((?P<line>\d+)\): (?P<func>[\w\\:>-]+)"),       # PHP
    re.compile(r"at (?P<func>[\w$.<>]+) \((?P<path>[^():]+):(?P<line>\d+):\d+\)"),           # JS/TS
    re.compile(r"(?P<path>[\w@./\\-]+\.(?:php|js|jsx|ts|tsx|mjs|cjs|py|rb|go|rs|java|kt|cs))"
               r"(?:[:(]| on line | line )(?P<line>\d+)"),                                   # generic
]


def parse_stack_text(text):
    frames, seen = [], set()
    for pattern in _FRAME_PATTERNS:
        for m in pattern.finditer(text or ""):
            key = (m.group("path"), m.group("line"))
            if key in seen:
                continue
            seen.add(key)
            frames.append({"file": m.group("path"), "line": int(m.group("line")),
                           "function": m.groupdict().get("func") or "", "in_app": None})
    return frames


def suffix_index(tracked):
    """Map every path suffix (by segments) to the tracked files ending with it."""
    index = {}
    for path in tracked:
        parts = path.split("/")
        for i in range(len(parts)):
            index.setdefault("/".join(parts[i:]), set()).add(path)
    return index


def map_to_repo(raw_path, index):
    """Longest unique suffix match of a server path against tracked files."""
    parts = raw_path.replace("\\", "/").strip("/").split("/")
    for i in range(len(parts)):
        hits = index.get("/".join(parts[i:]))
        if hits and len(hits) == 1:
            return next(iter(hits))
        if hits:
            return None
    return None


def attach_repo_paths(frames, index, limit=10):
    out = []
    for f in frames:
        repo_path = map_to_repo(f["file"], index)
        in_app = f["in_app"] if f["in_app"] is not None else repo_path is not None
        out.append(dict(f, file=redact(f["file"], 300), repo_path=repo_path, in_app=bool(in_app and repo_path)))
    app = [f for f in out if f["in_app"]]
    return (app or out)[-limit:]


# --- possibly fixed ------------------------------------------------------------------

_SHA = re.compile(r"\b[0-9a-f]{7,40}\b")


_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? ", re.M)
WINDOW = 5  # lines either side of the failing line that count as the failing code


def _touches(diff, line):
    """True when a -U0 diff changes an old-file line within WINDOW of `line`."""
    for m in _HUNK.finditer(diff):
        start, count = int(m.group(1)), int(m.group(2) or 1)
        end = start + max(count, 1) - 1  # a pure insertion (count 0) sits right after `start`
        if start <= line + WINDOW and end >= line - WINDOW:
            return True
    return False


def possibly_fixed(report, git=None):
    """True when the code at the error's own frame changed after the error was seen.

    Only the frame closest to the error counts. Routers and base controllers sit in
    every stack and change all the time, so any-frame-changed hid live errors.
    With a release commit we have, it checks whether lines near that frame changed
    since the release: frame line numbers come from the release, which is the diff's
    old side. Otherwise it falls back to whether the file was committed after the
    error was last seen. A commit isn't a deploy, so the reason says so.
    """
    git = git or _git
    top = next((f for f in reversed(report["frames"]) if f.get("repo_path")), None)
    if not top:
        return False, "no frames map to repo files"
    path, line = top["repo_path"], top.get("line")
    m = _SHA.search(report.get("release") or "")
    if m and git("cat-file", "-e", f"{m.group(0)}^{{commit}}")[0] == 0:
        code, out = git("diff", "-U0", m.group(0), "HEAD", "--", path)
        if out.strip() and (not line or _touches(out, line)):
            return True, f"{path} near line {line} changed since release {m.group(0)[:12]}"
        return False, "the failing lines are unchanged since the release"
    last_seen = _ts(report.get("last_seen"))
    if not last_seen:
        return False, "no release commit or last-seen time to compare"
    code, out = git("log", "-1", "--format=%cI", "--", path)
    if out.strip() and _ts(out.strip()) > last_seen:
        return True, f"{path} was committed after the error was last seen (not necessarily deployed)"
    return False, "the failing file is unchanged since the error was last seen"


def _ts(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _git(*args):
    p = subprocess.run(["git", *args], capture_output=True, text=True)
    return p.returncode, p.stdout


# --- HTTP ----------------------------------------------------------------------------

def _request(url, token, body=None, accept="application/json"):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", accept)
    req.add_header("User-Agent", "pixie-catch")
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode(), resp.headers


_NEXT = re.compile(r'<([^>]+)>;\s*rel="next";\s*results="true"')


# --- Sentry --------------------------------------------------------------------------

def sentry_issues(cfg, token, fetch=_request):
    s = cfg["sentry"]
    params = [("query", "is:unresolved"), ("statsPeriod", cfg["lookback"]), ("sort", "freq"), ("limit", "100")]
    params += [("project", p) for p in s["projects"]]
    if s.get("environment"):
        params.append(("environment", s["environment"]))
    url = f"{s['baseUrl'].rstrip('/')}/api/0/organizations/{s['org']}/issues/?{urllib.parse.urlencode(params)}"
    issues = []
    while url and len(issues) < cfg["maxReports"] * 3:
        text, headers = fetch(url, token)
        issues += json.loads(text)
        m = _NEXT.search(headers.get("Link", "") or "")
        url = m.group(1) if m else None
    return [i for i in issues if int(i.get("count") or 0) >= cfg["minEvents"]][: cfg["maxReports"]]


def sentry_frames(event):
    for entry in event.get("entries", []):
        if entry.get("type") != "exception":
            continue
        values = entry.get("data", {}).get("values") or []
        if not values:
            continue
        top = values[-1]
        stack = top.get("stacktrace") or top.get("rawStacktrace") or {}
        frames = [{"file": f.get("filename") or f.get("absPath") or f.get("module") or "?",
                   "line": f.get("lineNo"), "function": f.get("function") or "", "in_app": f.get("inApp")}
                  for f in stack.get("frames") or []]
        return top.get("type") or "", top.get("value") or "", frames
    return "", event.get("message") or "", []


def sentry_reports(cfg, token, index, fetch=_request):
    base = cfg["sentry"]["baseUrl"].rstrip("/")
    org = cfg["sentry"]["org"]
    out = []
    for issue in sentry_issues(cfg, token, fetch):
        text, _ = fetch(f"{base}/api/0/organizations/{org}/issues/{issue['id']}/events/latest/", token)
        event = json.loads(text)
        exc_type, message, frames = sentry_frames(event)
        release = (event.get("release") or {}).get("version") if isinstance(event.get("release"), dict) else event.get("release")
        env = next((t["value"] for t in event.get("tags", []) if t.get("key") == "environment"), "")
        out.append({
            "id": f"sentry-{issue['id']}", "tracker": "sentry", "external_id": str(issue["id"]),
            "url": issue.get("permalink", ""), "title": redact(issue.get("title"), 200),
            "exception_type": redact(exc_type, 120), "message": redact(message), "level": issue.get("level", ""),
            "events": int(issue.get("count") or 0), "users": issue.get("userCount", 0),
            "first_seen": issue.get("firstSeen"), "last_seen": issue.get("lastSeen"),
            "release": redact(release or "", 120), "environment": redact(env, 60),
            "frames": attach_repo_paths(frames, index),
        })
    return out


# --- Coralogix -----------------------------------------------------------------------

_NOISE = re.compile(r"\b(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|0x[0-9a-f]+|\d+)\b", re.I)


def _field(data, dotted):
    for part in dotted.split("."):
        if not isinstance(data, dict) or part not in data:
            return None
        data = data[part]
    return data


def _first(data, fields):
    for name in fields:
        value = _field(data, name)
        if value:
            return value if isinstance(value, str) else json.dumps(value)
    return ""


def coralogix_rows(ndjson):
    rows = []
    for line in ndjson.splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        for row in (obj.get("result") or {}).get("results", []):
            rows.append(row)
    return rows


def coralogix_reports(cfg, token, index, now, fetch=_request):
    c = cfg["coralogix"]
    minutes = int(cfg["lookback"][:-1]) * {"m": 1, "h": 60, "d": 1440, "w": 10080}[cfg["lookback"][-1]]
    body = {"query": c["query"], "metadata": {
        "syntax": "QUERY_SYNTAX_DATAPRIME", "tier": "TIER_FREQUENT_SEARCH",
        "startDate": (now - timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z"),
        "endDate": now.isoformat().replace("+00:00", "Z")}}
    text, _ = fetch(f"https://api.{c['domain']}/api/v1/dataprime/query", token, body, "application/x-ndjson")
    groups = {}
    for row in coralogix_rows(text):
        meta = {m["key"]: m["value"] for m in row.get("metadata", [])}
        labels = {m["key"]: m["value"] for m in row.get("labels", [])}
        try:
            data = json.loads(row.get("userData") or "{}")
        except json.JSONDecodeError:
            data = {"message": row.get("userData")}
        message = _first(data, c["messageFields"])
        stack = _first(data, c["stackFields"])
        template = meta.get("templateId") or _field(data, "coralogix.templateId") or meta.get("templateid")
        key = template or hashlib.sha1(_NOISE.sub("#", message.split("\n")[0]).encode()).hexdigest()[:12]
        g = groups.setdefault(key, {"count": 0, "first": None, "last": None, "message": message, "stack": stack,
                                    "labels": labels, "data": data})
        g["count"] += 1
        ts = _ts(meta.get("timestamp"))
        if ts:
            g["first"] = min(filter(None, [g["first"], ts]))
            g["last"] = max(filter(None, [g["last"], ts]))
    out = []
    for key, g in sorted(groups.items(), key=lambda kv: -kv[1]["count"]):
        if g["count"] < cfg["minEvents"]:
            continue
        first_line = g["message"].split("\n")[0]
        out.append({
            "id": f"coralogix-{key}", "tracker": "coralogix", "external_id": key, "url": "",
            "title": redact(first_line, 200), "exception_type": "", "message": redact(g["message"]),
            "level": "error", "events": g["count"], "users": None,
            "first_seen": g["first"].isoformat() if g["first"] else None,
            "last_seen": g["last"].isoformat() if g["last"] else None,
            "release": redact(str(_field(g["data"], "release") or _field(g["data"], "version") or ""), 120),
            "environment": redact(g["labels"].get("applicationname", ""), 60),
            "frames": attach_repo_paths(parse_stack_text(g["stack"] or g["message"]), index),
        })
    return out[: cfg["maxReports"]]


# --- CLI -----------------------------------------------------------------------------

def fetch_all(cfg, env, index, now):
    reports, errors = [], []
    sources = []
    if cfg["sentry"].get("org"):
        sources.append(("sentry", "SENTRY_AUTH_TOKEN", lambda t: sentry_reports(cfg, t, index)))
    if cfg["coralogix"].get("domain"):
        sources.append(("coralogix", "CORALOGIX_API_KEY", lambda t: coralogix_reports(cfg, t, index, now)))
    if not sources:
        errors.append("no source configured: set catch.sentry.org or catch.coralogix.domain in docs/agents/checkup.json")
    for name, var, run in sources:
        token = env.get(var)
        if not token:
            errors.append(f"{name}: {var} is not set")
            continue
        try:
            reports += run(token)
        except Exception as e:  # report and carry on with the other source
            errors.append(f"{name}: {type(e).__name__}: {redact(e, 300)}")
    for r in reports:
        r["possibly_fixed"], r["possibly_fixed_reason"] = possibly_fixed(r)
    return reports, errors


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("fetch")
    s.add_argument("--out", required=True)
    a = p.parse_args(argv)
    cfg = C.load(".")["catch"]
    out = subprocess.run(["git", "ls-files", "-z"], capture_output=True, text=True, check=True).stdout
    tracked = [p for p in out.split("\0") if p]  # -z: paths with spaces or non-ASCII names stay intact
    reports, errors = fetch_all(cfg, os.environ, suffix_index(tracked), datetime.now(timezone.utc))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps({"reports": reports, "errors": errors}, indent=2) + "\n")
    print(json.dumps({"reports": len(reports), "possibly_fixed": sum(r["possibly_fixed"] for r in reports),
                      "errors": errors}))


if __name__ == "__main__":
    main()

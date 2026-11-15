"""Load docs/agents/checkup.json and fill in defaults. Shared by checkup and catch."""
import copy
import json
import re
from pathlib import Path

CONFIG_PATH = "docs/agents/checkup.json"
BASELINE_PATH = "docs/agents/checkup-baseline.json"
BASELINE_BRANCH = "checkup/baseline"

DEFAULTS = {
    "maxPrsPerWeek": 3,
    "maxIssuesPerRun": 10,
    "fileSeverities": ["critical", "high"],
    "securityFindings": "auto",
    "scoreDropThreshold": 5,
    "shardSize": 20,
    "maxShards": 40,
    "maxFindingsPerHunter": 8,
    "includeTests": False,
    "exclude": [
        "vendor/", "node_modules/", "target/", "dist/", "build/", ".next/",
        "writable/", "storage/", "coverage/", "tests/fixtures/",
    ],
    "autoFix": {"severities": ["critical", "high"], "maxTier": 2},
    "catch": {
        "lookback": "24h",
        "maxReports": 20,
        "minEvents": 10,
        "sentry": {"baseUrl": "https://sentry.io", "org": "", "projects": [], "environment": ""},
        "coralogix": {
            "domain": "",
            "query": "source logs | filter $m.severity == ERROR || $m.severity == CRITICAL | limit 2000",
            "messageFields": ["message", "msg", "error.message", "exception.message", "log"],
            "stackFields": ["stack", "stacktrace", "stack_trace", "error.stack", "exception.stacktrace"],
        },
    },
}

SECURITY_MODES = ("auto", "issues", "advisory", "report-only")


def _merge(base, override):
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def load(repo_root="."):
    path = Path(repo_root) / CONFIG_PATH
    user = json.loads(path.read_text()) if path.exists() else {}
    config = _merge(DEFAULTS, user)
    # A user's exclude list adds to the defaults, so excluding one folder never re-includes vendor/.
    config["exclude"] = DEFAULTS["exclude"] + [e for e in user.get("exclude", []) if e not in DEFAULTS["exclude"]]
    if config["securityFindings"] not in SECURITY_MODES:
        raise ValueError(f"securityFindings must be one of {SECURITY_MODES}")
    if not re.fullmatch(r"[1-9]\d*[mhdw]", str(config["catch"]["lookback"])):
        raise ValueError("catch.lookback must be a number and a unit, m, h, d or w, such as 24h or 7d")
    return config

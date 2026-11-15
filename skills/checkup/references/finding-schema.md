# Findings: format, evidence and severity

Every agent in `checkup` and `catch` uses this one format, so both skills share the same pipeline from merging to filing.

## Result file

A hunter or triager writes one JSON file:

```json
{
  "shard": "src/Auth",
  "dimension": "security",
  "status": "ISSUES",
  "blocked_reason": "",
  "files_read": ["src/Auth/Login.php"],
  "findings": [ { ... } ]
}
```

- `status` is `PASS` (checked, nothing found), `ISSUES` (at least one finding) or `BLOCKED` (couldn't check; say why in `blocked_reason`). A finding-free `PASS` is a valid, useful result.
- `files_read` lists every file you opened. The coordinator uses it to tell checked code from skipped code.

## Finding

| Field | Required | Meaning |
|---|---|---|
| `dimension` | yes | `security`, `performance` or `bug` |
| `category` | yes | Short kebab-case kind, e.g. `sql-injection`, `n-plus-one`, `null-deref` |
| `title` | yes | One line a maintainer can scan |
| `file` | yes | Repo-relative path of the main location |
| `symbol` | yes | Enclosing function, method or class, e.g. `Login::attempt`. Used for the fingerprint, so name it exactly as the code does. |
| `line` | no | Line number. It goes stale, so it's never used for identity. |
| `claim` | yes | What is wrong, in one or two sentences |
| `failure_scenario` | yes | Concrete input or state → wrong result. "Could be risky" is not a scenario. |
| `evidence` | yes | The lines that carry the signal, quoted exactly. A few lines, not the whole function. |
| `evidence_rung` | yes | 1–5, see the ladder below |
| `suggested_fix` | yes | The behavior after the fix, in a sentence. Not a patch. |
| `confidence` | yes | `high`, `medium` or `low` |
| `severity_hint` | no | Your guess at severity. The verifier sets the real one. `low` hints aren't verified. |
| `root_cause` | no | A short phrase naming a shared cause, e.g. `no input validation in form requests`. Findings with the same dimension, category and root cause are merged into one issue with several locations. |
| `measured` | perf only | `true` only if a number came from running something. Otherwise the finding is inferred and can't be `critical`. |

Hunters and triagers set only the fields above. A triager also adds `external`, the error report it came from. `verdict`, `severity`, `verifier_reason`, `repro` and `tier` come only from the verifier, prover and classifier: the merge step discards them from a hunter's or triager's file, so no agent can confirm its own finding.

Issues show your text exactly as written, in code blocks: markdown, links and HTML don't render there. Write plain sentences.

## Evidence ladder

| Rung | Evidence |
|---|---|
| 1 | Someone said so: a comment, a name, a hunch |
| 2 | A real `file:line` that shows the pattern |
| 3 | A walked failure path: from an entry point, through the calls, to the wrong result, with each hop cited |
| 4 | A test or script that runs the real code and fails on the bug |
| 5 | Reproduced in the running app, or observed in production |

Issues are filed only at rung 3 or higher. Auto-fix needs rung 4. Listing the callers is not a failure path. Show the one path that breaks.

## Severity rubric (set by the verifier)

| Severity | Meaning |
|---|---|
| `critical` | Exploitable or triggered without special access, and causes data loss, data exposure, account takeover, money movement, or an outage |
| `high` | A real user or attacker can trigger it in normal use. Wrong data, a crash in a main flow, an authz gap, or a slowdown users feel (seconds, or growth with data size) |
| `medium` | Needs unusual input, state or access, or the damage is contained and recoverable |
| `low` | Edge case with small impact, or a hardening gap with no path to harm today |

Rules:
- When torn between two levels, pick the lower one. Hunters inflate. The verifier corrects for that.
- Performance findings that aren't `measured` can't be `critical`.
- For `catch`, raise one level (to at most `critical`) when the error hits many users or a main flow (checkout, login, saving work) in production, and lower one level when it only hits a non-production environment.

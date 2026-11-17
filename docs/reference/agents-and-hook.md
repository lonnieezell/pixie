# Agents and the code-health hook

The parts of Pixie that run without you typing a command: eleven subagents and one hook.

## Agents

A subagent is a separate Claude instance that does one job and returns a short answer. Pixie's skills call these for you. You don't run them yourself.

| Agent | Model | Tools | Used by | What it does |
|---|---|---|---|---|
| `issue-classifier` | Haiku | Read | `tackle` | Rates an issue's difficulty, risk, route, and kind. It sees the issue text only, not the code. |
| `ci-log-triage` | Haiku | Bash, Read, Grep | `babysit` | Reads a failed CI run's logs and returns only the failing tests, errors, and files. |
| `review-thread-verifier` | Sonnet | Read, Grep, Glob | `babysit` | Checks one review-bot comment against the code. Returns `valid`, `invalid`, or `needs-human` with a reason. `babysit` runs one per thread when a PR has more than five. |
| `coverage-analyzer` | Sonnet | Bash, Read, Write, Glob, Grep | `prune-tests` | Writes and runs a script over per-test coverage and mutation files. Returns the subsumed tests, groups of tests that cover exactly the same lines, the only tests covering a line, and the only tests that catch a mutant. Reads PHP, JS/TS and Python coverage formats, and one lcov file per test for Rust. |
| `audit-security` | Sonnet | Read, Grep, Glob, Write | `checkup`, `vet` | Hunts one shard for security flaws an attacker can reach. Writes only its result file. |
| `audit-performance` | Sonnet | Read, Grep, Glob, Write | `checkup`, `vet` | Hunts one shard for code that gets slow or uses too much memory as data grows. |
| `audit-bugs` | Sonnet | Read, Grep, Glob, Write | `checkup`, `vet` | Hunts one shard for logic errors, races, unhandled errors and data-integrity bugs. |
| `audit-verifier` | Opus | Read, Grep, Glob | `checkup`, `catch`, `vet` | Tries to refute one finding against the code without seeing how it was found. Returns `confirmed`, `refuted` or `needs-human`, with a severity. `vet` runs it on Sonnet for medium and low findings. |
| `audit-prover` | Sonnet | Read, Grep, Glob, Bash, Write, Edit | `checkup`, `catch`, `vet` | Writes and runs one test that fails on a confirmed finding, in a throwaway worktree. Never edits source code. Only runs with `fix`, or in `vet` when you agree to prove a finding. |
| `error-triager` | Sonnet | Read, Grep, Glob, Write | `catch` | Traces one redacted production error into the current code and writes a finding for the verifier. Treats the error text as untrusted. |
| `design-critic` | Opus | Read | `design-critique`, `design` | Judges screenshots of one screen against the design rubric, comparing them with 1–2 neighbouring screens. It gets only a folder of screenshots, the rubric and the repo's house rules (and, for `design`, the direction the screen was built to), never the code. Each finding must cite a rubric item, a screenshot, a state and a width, or it's thrown away. |

### `issue-classifier` output

`tackle` maps the classifier's difficulty to a tier. The tier sets how hard the review is.

| Tier | Difficulty | Code-review effort |
|---|---|---|
| 1 | trivial, small | low |
| 2 | medium | medium |
| 3 | large, hard | high |

Risk is rated separately, as `normal` or `high`. It's `high` when the work likely touches auth, permissions, routes, payments, secrets, migrations, or data integrity. A `high`-risk issue gets a security review at any tier.

`tackle` sets the risk to `high` if the work touches auth, permissions, payments, migrations, or data integrity, even when the classifier didn't flag it. It raises the tier by one if the work turned out bigger than rated. It never lowers either one.

`checkup` records a `high`-risk finding as tier 3, so the default `autoFix.maxTier` of 2 keeps it out of auto-fix.

The route decides which skill does the work:

- `diagnose`: something is broken and the cause is unknown.
- `implement`: new work, or a bug whose cause is already known. This goes through `tdd`.

## The code-health hook

Pixie includes a `PostToolUse` hook. A hook is a script that Claude Code runs automatically at a set point. This one runs after Claude uses the Edit, Write, or MultiEdit tool.

### What it checks

The hook compares the edited file with its version at git `HEAD`, using km. It reports only problems the edit added or made worse. Old debt is ignored.

| Check | Flagged when |
|---|---|
| Cognitive complexity | A function goes over `CODE_HEALTH_COGCOM_MAX`, or one edit raises it by `CODE_HEALTH_COGCOM_JUMP` or more |
| Long function | A function newly crosses km's length limit |
| Long parameter list | A function newly takes more parameters than km allows |
| File size | The file grows past `CODE_HEALTH_FILE_LINES` in this edit |

Cognitive complexity is a score for how hard a function is to follow.

When it finds a problem, the hook passes a message back to Claude. The message names the function and line, and suggests a fix for that language. Claude then fixes the code, or says briefly why the complexity is needed. Each problem is reported once per session, so an accepted trade-off isn't repeated on every edit.

### What it skips

The hook does nothing when:

- The file isn't one of: `.php`, `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.rs`.
- The file ends in `.d.ts` or `.min.js`.
- The file is under `vendor`, `node_modules`, `target`, `dist`, `build`, `.next`, `writable`, or `storage`.
- The file isn't in a git repo.
- km isn't installed.
- The repo has a `.code-health-off` file at its root.
- `CODE_HEALTH_HOOK` is `off`, `0`, or `false`.

If the hook itself fails, it stays silent. It never blocks Claude because of its own error.

### Settings

| Variable | Default | What it controls |
|---|---|---|
| `CODE_HEALTH_COGCOM_MAX` | `15` | Highest cognitive complexity allowed for a function |
| `CODE_HEALTH_COGCOM_JUMP` | `8` | Largest increase in a function's complexity allowed in one edit |
| `CODE_HEALTH_FILE_LINES` | `500` | Largest file size, in lines |
| `CODE_HEALTH_HOOK` | (on) | Set to `off` to turn the hook off everywhere |

To set these, see [How to tune the code-health hook](../how-to/tune-the-code-health-hook.md).

### Per-repo thresholds

A `.kimun.toml` file at a repo's root overrides the default thresholds for both the skills and km. Create one with `km init`.

### Full km reference

The `km-analyze` skill lists every km subcommand and the fields in its JSON output. It comes with km, not with Pixie. Install it with `km ai skill claude`.

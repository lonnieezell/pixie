---
name: checkup
description: Audit the codebase for security flaws, performance traps and bugs with parallel read-only hunter agents, verify every finding adversarially, score each dimension against a baseline, and file confirmed high and critical findings as needs-triage issues that tackle can fix. Use for /checkup, a weekly audit, or a regression check of the scores.
disable-model-invocation: true
allowed-tools: Bash(gh auth status), Bash(gh repo view:*), Bash(git rev-parse:*), Bash(git status:*), Bash(git worktree list:*), Bash(km --version), Bash(km score:*), Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/checkup.py plan *), Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/checkup.py merge *), Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/checkup.py brief *), Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/checkup.py finalize *), Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/checkup.py permissions)
---

# Checkup

Audit the code along three dimensions (security, performance, bugs), keep only findings that survive an attempt to refute them, score the result, and hand confirmed high and critical findings to GitHub as issues `tackle` can fix.

```
/pixie:checkup [scores | full] [PATH] [unattended] [fix]
/pixie:checkup permissions
```

| Argument | Effect |
|---|---|
| none | Full audit of the whole repo, interactive |
| `scores` | Regression check: audit only shards changed since the baseline, reuse the rest, report scores and deltas. Files nothing. |
| `PATH` | Audit only that folder or file. Doesn't touch the baseline. |
| `unattended` | No questions. Audits only shards changed since the baseline (every shard when there's no baseline yet), files issues and publishes the baseline (see "Unattended mode") |
| `full` | With `unattended`, re-audit every shard instead of only the changed ones. Run it now and then (say monthly), because unchanged code is otherwise never hunted again. |
| `fix` | Also proves auto-fix candidates with a failing test and queues them for `tackle` |
| `permissions` | Audits nothing. Runs `python3 ${CLAUDE_SKILL_DIR}/scripts/checkup.py permissions` and shows its output as-is: the allow rules an unattended run needs, with this install's exact paths. Then stop. |

The scripts do every step that doesn't need judgement. Run every command from the repo root, exactly as written: `plan`, `merge`, `brief` and `finalize` only write under `ai/`, so they run without a prompt. `file`, `promote` and `publish` write to GitHub, so they still ask.

Read these before starting: [finding-schema.md](references/finding-schema.md) (the format every agent uses) and [config.md](references/config.md) (settings and their defaults).

## Labels

Roles come from `docs/agents/pixie-labels.md` when it exists, as in `tackle`. This skill uses `needs-triage` for new issues and `ready-for-agent` for auto-fix. It also adds plain labels: `bug`, `checkup`, `security` or `performance`, and `severity:high` or `severity:critical`. The filing script creates any that are missing.

## 1. Prepare

1. Run `gh auth status` and `gh repo view --json nameWithOwner,visibility,viewerPermission`. Without `gh`, or without write permission, you can still audit and report. Say that filing is off, and skip steps 8–10.
2. Set `RUN=ai/checkup/DATE-HHMM`, from the current date and UTC time, so a second run never mixes in the first one's files. Make sure `ai/` is listed in `.git/info/exclude`, and add it there if it isn't, so run files never get committed.
3. Plan the run:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/checkup.py plan --mode MODE [--path PATH] --out "$RUN/plan.json"
   ```
   `MODE` is `changed` for `scores`, and for `unattended` without `full`. It's `full` otherwise. With no baseline, `changed` audits every shard. It prints the shard count, the number of hunter jobs, the number of findings carried from shards it won't audit, the gaps, and which baseline it read (the branch of the open baseline PR first, then `HEAD`). Shards over `maxShards` aren't audited: their baseline findings are carried as `stale`, which keeps them in the score but doesn't file them, and they're listed as gaps.

   **Done when** `plan.json` exists. If it reports zero jobs in `changed` mode, nothing changed: skip to step 4, which still has to run so the carried findings reach step 7.

## 2. Gather leads

Run the repo's own deterministic tools if they're installed, and save each one's output under `$RUN/leads/`. Don't install anything.

- Dependency audits: `composer audit --format=json`, `npm audit --json`, `cargo audit --json`, `pip-audit -f json`
- Static analysis already configured in the repo: PHPStan, Psalm, ESLint, `cargo clippy`
- Secret scanners if present: `gitleaks detect --no-git -f json`, `semgrep --config auto --json`
- `km score . --format json > "$RUN/km.json"` when `km --version` works

Then write `$RUN/leads.md`: one line per tool-reported problem (tool, file, line, rule, message), at most 200 lines. Hunters read it. **Done when** `leads.md` exists, even if it says "no tools available".

## 3. Hunt

For every entry in `plan.json` `jobs`, start the agent named in its `agent` field (`pixie:audit-security`, `pixie:audit-performance` or `pixie:audit-bugs`) in the background. Start up to 10 at a time, and start the next as each one finishes. Give each one this brief, and nothing else:

```
Shard: SHARD_ID
Files: SHARD_FILES
Dimension: DIMENSION
Hunting protocol: HUNTING_PATH
Finding schema: SCHEMA_PATH
Leads: LEADS_PATH
Write your result to: RESULT_PATH
Return at most MAX_FINDINGS findings.
```

- `SHARD_ID`, `SHARD_FILES`, `DIMENSION`: the job's shard ID, that shard's files, and the job's dimension, from `plan.json`
- `HUNTING_PATH`, `SCHEMA_PATH`, `LEADS_PATH`: the absolute paths of `${CLAUDE_SKILL_DIR}/references/hunting.md`, `${CLAUDE_SKILL_DIR}/references/finding-schema.md` and `$RUN/leads.md`
- `RESULT_PATH`: the absolute path of `$RUN/hunters/RESULT`, where `RESULT` is the job's `result` file name
- `MAX_FINDINGS`: `maxFindingsPerHunter` from `plan.json`

Each agent replies with one short line. Don't read the result files yourself: the merge script does.

## 4. Merge

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/checkup.py merge --plan "$RUN/plan.json" --results "$RUN/hunters" --out "$RUN/candidates.json"
```

It validates every result, keeps only the fields a hunter may set (a hunter can't set its own verdict, severity, repro or tier), drops invalid findings, dedupes by fingerprint, merges findings with a shared root cause, and adds the findings carried from the baseline. It prints `incomplete` entries. For each one whose reason is `no result`, `missing status` or `not valid JSON`, run that hunter once more with the same brief, then run merge again. Whatever is still incomplete becomes a **gap** in the report. A gap never counts as clean.

**Done when** merge has run after the retries.

## 5. Verify

For each ID in `candidates.json` `to_verify`, start `pixie:audit-verifier` in the background, up to 10 at a time. For IDs also listed in `verify_light` (hinted below `fileSeverities`, so they only affect the score unless the verifier raises them), start it with `model: "sonnet"`. Give it the candidate's JSON object from `candidates.json` and the absolute path of `finding-schema.md`. Give it nothing about how the finding was found.

Write each reply as-is to `$RUN/annotations/ID.verdict.json`, where `ID` is the candidate's ID. If a reply isn't valid JSON, run that verifier once more. If it fails again, write `{"verdict": "needs-human", "verifier_reason": "verifier returned no verdict"}`.

**Done when** every ID in `to_verify` has a `.verdict.json`.

**Live reproduction.** Off by default, because driving the app costs many tokens and the issue only gains a text note. Run it only when `docs/agents/pixie.json` sets `liveVerify.checkup` to `true` and the project has a verification skill (`.claude/skills/verify-*/`, such as one made by `create-verifier`). Then, take each `confirmed` finding with a severity in `fileSeverities` whose failure shows on a surface a user can reach (a route, a screen, a CLI command), and try to reproduce it in the running app. This reaches evidence rung 5. It adds evidence to the issue, but it doesn't replace the prover's test for auto-fix.

- Drive the app yourself, one finding at a time. Never hand it to a background agent: parallel drives would collide on the same instance.
- Prove it with text: the response body or status, a log line, CLI output, or an accessibility or DOM snapshot. Take a screenshot only when the failure is visual (layout, rendering) and text can't show it. Save it to disk without viewing it. If you must look at one, capture it at 1280×720 or smaller, since an image stays in context for the rest of the run.
- Follow the skill's Launch, Doctor, Drive and Cleanup sections, against a local instance only. Never drive production or a shared system. Use its `features/` map to find the journey that reaches the failure.
- If the failure shows the way the finding says, write `$RUN/annotations/ID.live.json` as `{"live_repro": {"steps": "STEPS", "observed": "OBSERVED"}, "evidence_rung": 5}`, with the steps you took and what the app did. Leave out secrets. If it doesn't show, write nothing: a confirmed finding stays confirmed.
- Run the skill's Cleanup once, after the last finding, and after any failed drive.

## 6. Prove and classify (`fix` only)

Skip this step without `fix`.

1. Pick candidates whose verdict is `confirmed` with high confidence and a severity listed in `autoFix.severities`, up to `maxPrsPerWeek` of them, most severe first. Proving more than you can promote wastes tokens.
2. For each one, print its brief with `python3 ${CLAUDE_SKILL_DIR}/scripts/checkup.py brief --candidates "$RUN/candidates.json" --annotations "$RUN/annotations" --id ID`. Start `pixie:audit-prover` with `isolation: "worktree"`, and give it the candidate JSON, the brief and the absolute path of `finding-schema.md`.
3. The prover's worktree holds its test, so it isn't removed automatically. Once you have its reply, find it with `git worktree list`, then run `git worktree remove --force PATH` and `git branch -D BRANCH`. If it returns `proven`, write `$RUN/annotations/ID.repro.json` as `{"repro": {"test_path", "command", "test_code", "output"}, "evidence_rung": 4}`, using the fields from its reply. If it returns `not-proven`, write nothing. The finding can still be filed, but it won't be auto-fixed.
4. For each proven candidate, write its brief to a temp file made with `mktemp`, run `pixie:issue-classifier` with only that path, and delete the file. Map `difficulty` to a tier: `trivial` or `small` → 1, `medium` → 2, `large` or `hard` → 3. Write `$RUN/annotations/ID.tier.json` as `{"tier": N}`.

## 7. Finalize

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/checkup.py finalize --candidates "$RUN/candidates.json" --annotations "$RUN/annotations" \
  --plan "$RUN/plan.json" --km "$RUN/km.json" --out-dir "$RUN"
```

It writes `findings.json`, `report.md` and, for whole-repo runs, `baseline-next.json`, and prints a summary. Scores use a formula, not judgement: see [config.md](references/config.md#scores). A shard counts as checked only when every hunter on it returned, or it was carried unchanged. Other shards keep their old hash in `baseline-next.json`, so the next run audits them again, and their baseline findings come back as `stale` instead of showing as fixed. When the security mode resolves to anything other than `issues`, `baseline-next.json` leaves security findings out entirely and keeps only their counts by severity: a fingerprint hashes the file, symbol and category, which anyone could brute-force from a public repo. A `scores` run then audits the security dimension of every shard, since there's nothing to carry.

In `scores` mode, stop here. Report the scores table, the baseline scores, whether it **regressed** (a new confirmed high or critical finding in code that changed since the baseline, more withheld high or critical findings than the baseline, or a score drop larger than `scoreDropThreshold`), the findings newly found in unchanged code, and the gaps.

## 8. File

Interactive: list the confirmed findings that would be filed (severity in `fileSeverities`, evidence rung 3 or higher), and ask once whether to file them. Unattended: file without asking.

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/checkup.py file --findings "$RUN/findings.json" --source checkup --out "$RUN/filed.json"
```

Stale findings aren't filed. The script searches GitHub for each finding's fingerprints first, preferring an open issue, and checks each hit's body for the token:
- open issue: add a "still present" comment, at most once a week
- closed as not planned or duplicate: skip it. A won't-fix decision sticks.
- closed as completed: file a new issue marked as a regression of the old one
- none: create an issue in agent-brief form with the triage labels, up to `maxIssuesPerRun`

Security findings follow `securityFindings`: `issues`, private draft `advisory`, or `report-only`. `auto` uses issues on private and internal repos and advisories on public ones. Advisories follow the same rules as issues: an open (triage or draft) one is left alone, a closed one suppresses the finding, a published one gets a new advisory marked as a regression, and new advisories count toward `maxIssuesPerRun`. Creating an advisory needs a repo admin or security manager token. If it fails, the result says `advisory-failed`: report it. Any other GitHub failure on one finding is recorded as `error`, and the rest are still filed.

## 9. Publish the baseline (whole-repo runs)

Interactive: ask once. Unattended: always.

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/checkup.py publish --file "$RUN/baseline-next.json"
```

It rebuilds the `checkup/baseline` branch from the default branch, commits `docs/agents/checkup-baseline.json`, force-pushes that bot branch with a lease, and opens or updates its PR. It never touches any other branch. Merging the PR is the human's call.

## 10. Queue auto-fixes (`fix` only)

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/checkup.py promote --findings "$RUN/findings.json" --filed "$RUN/filed.json" --source checkup --out "$RUN/promoted.json"
```

It moves eligible issues from `needs-triage` to `ready-for-agent` and comments why. An issue is eligible when it's confirmed with high confidence, has a proven repro test, has a tier at or below `autoFix.maxTier`, and is still untriaged. The weekly cap, `maxPrsPerWeek`, counts promotions by both `checkup` and `catch` over the last 7 days, read from GitHub.

This skill can't start `tackle` itself. Interactive: tell the user to run `/pixie:tackle N` for each promoted issue. Unattended: the workflow runs it (see [automation.md](references/automation.md)).

## 11. Report

End with:
- the scores table with baseline values, whether it regressed, and what was newly found in unchanged code
- counts of confirmed findings by severity, and the top five
- what was filed: created, commented, regression, suppressed, skipped by cap, advisories, report-only
- the baseline PR, and the promoted issues
- gaps and dropped findings, with reasons
- the path of `report.md`

## Unattended mode

When the arguments include `unattended`, or no human is available:
- Never ask questions. Where a step says "ask", take the unattended choice it names.
- Plan in `changed` mode unless the arguments include `full` (step 1).
- Run steps 8 and 9 for whole-repo runs, and step 10 with `fix`.
- When something is unclear, take the conservative option: don't file, and say so in the report.
- Merging, approving, closing and force-pushing to any branch other than `checkup/baseline` are never done, in any mode.

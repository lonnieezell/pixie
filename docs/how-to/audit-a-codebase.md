# How to audit a codebase with checkup

This guide shows you how to run `checkup` on a repo, read what it found, and decide what happens to each issue it files. `checkup` looks for three kinds of problems:

- **Security:** flaws an attacker can reach.
- **Performance:** code that gets slow or uses too much memory as data grows.
- **Bugs:** logic errors, races, unhandled errors and data-integrity bugs.

`checkup` only runs when you type it.

## Before you start

- You need `gh`, logged in with write access to the repo, so `checkup` can file issues. Without it, `checkup` still audits and writes a report, but files nothing.
- `km` is optional. When it's installed, the report also shows `km`'s overall health score.
- You don't need a config file. Every setting has a default. To change one, see [checkup and catch settings](../reference/checkup-config.md).

## 1. Run a full audit

From the repo root:

```text
/pixie:checkup
```

Claude will:

1. Split the code into shards of up to 20 files, busiest first.
2. Run any audit and lint tools the repo already has, such as `npm audit` or PHPStan, and pass their output on as leads. It doesn't install anything.
3. Start three read-only hunter agents per shard, one for each kind of problem.
4. Send every finding to a separate verifier that tries to prove it wrong, and sets its severity.
5. Score each dimension from 0 to 100.

A full run starts a lot of agents: three per shard, plus one verifier per finding. On a large repo, try one folder first (see [step 5](#5-audit-one-folder)).

## 2. Read the report

The report is at `ai/checkup/DATE-HHMM/report.md`. It has four parts:

- **Scores:** one per dimension, with the baseline score next to it. The first run has no baseline.
- **Confirmed findings:** the ones the verifier couldn't refute, with severity, file and title.
- **Not confirmed:** findings that were refuted, or that need a human to decide.
- **Gaps:** shards that weren't checked, with the reason. A gap is never counted as clean. The next run checks those shards again.

`checkup` adds `ai/` to `.git/info/exclude`, so run files are never committed.

## 3. File the issues

Claude lists the confirmed high and critical findings that have enough evidence, and asks once whether to file them. Say yes, and each one becomes a GitHub issue labeled `needs-triage`.

Each issue is written so `tackle` can work from it. It has a summary, the current and desired behavior, acceptance criteria, and the evidence, quoted from the code. If the repo has a verification skill, Claude also tries to reproduce each finding in the running app on your machine. When it can, the issue has a "Reproduced in the running app" section with the steps and what the app did.

`checkup` won't file the same finding twice:

- If an open issue already covers it, it adds a "still present" comment, at most once a week.
- If you closed the issue as **not planned** or **duplicate**, it never files that finding again.
- If you closed it as **completed** and the problem is back, it files a new issue marked as a regression of the old one.

On a public repo, security findings go to private draft security advisories instead of issues by default. To change that, set `securityFindings`.

## 4. Triage each issue

`needs-triage` means a human hasn't looked yet. For each issue, pick one:

| If the finding is... | Do this |
|---|---|
| Real, and you want an agent to fix it | Swap `needs-triage` for `ready-for-agent`, then run `/pixie:tackle N` |
| Real, and you'll fix it yourself | Remove `needs-triage` and fix it as usual |
| Wrong, or a risk you accept | Close it as **not planned**. `checkup` won't file it again. |

`tackle` uses the issue's reproduction test as the start of its regression test, if the issue has one.

## 5. Audit one folder

To check one area without touching the rest, give a path:

```text
/pixie:checkup src/Billing
```

A path run files issues as usual, but doesn't update the baseline.

## 6. Publish the baseline

After a whole-repo run, Claude asks whether to publish the baseline. Say yes, and `checkup` opens a PR on the `checkup/baseline` branch that commits `docs/agents/checkup-baseline.json`. Later runs compare their scores against it.

Merge that PR when you're happy with the scores. Until you merge it, later runs read the baseline from the open PR's branch. Each run updates the same PR.

## 7. Check for regressions

Once you have a baseline, check whether recent changes made things worse:

```text
/pixie:checkup scores
```

This audits only the shards that changed since the baseline and reuses the results for the rest, so it's faster and cheaper than a full run. It files nothing. It reports each score, the change from the baseline, and whether it **regressed**. A run regresses when one of these is true:

- A new confirmed high or critical finding appears in code that changed since the baseline.
- A score drops by more than `scoreDropThreshold` points (5 by default).

A finding in code that *didn't* change is listed as newly found, not as a regression. It was missed last time rather than introduced.

## 8. Let agents fix proven findings

Add `fix` to have `checkup` prove the best findings and queue them for `tackle`:

```text
/pixie:checkup fix
```

For each confirmed high or critical finding, an agent writes a test that fails on it, in a throwaway worktree. `checkup` moves an issue to `ready-for-agent` only when:

- the verifier confirmed it with high confidence,
- the test fails on the current code,
- it's no harder than `autoFix.maxTier`, and
- nobody has triaged the issue yet.

At most `maxPrsPerWeek` issues (3 by default) are queued in any 7 days, counting `checkup` and `catch` together.

`checkup` can't start `tackle` itself. Run `/pixie:tackle N` for each issue it queued. Then run `/pixie:babysit` to get the PRs green.

## Next steps

- Run `checkup` every week without you: [Schedule checkup and catch](schedule-checkup-and-catch.md).
- Turn production errors into issues the same way: [Turn production errors into issues](turn-production-errors-into-issues.md).
- Change the limits and thresholds: [checkup and catch settings](../reference/checkup-config.md).

## Related

- [`checkup` reference](../reference/skills.md#checkup)
- [How findings are verified and scored](../explanation/how-pixie-works.md#audits-trust-only-what-survives)
- [Labels, branches, and files](../reference/labels-and-branches.md)

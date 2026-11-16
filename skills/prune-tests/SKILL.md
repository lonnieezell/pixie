---
name: prune-tests
description: Prune and consolidate tests in one area of a large suite safely, using per-test coverage and scoped mutation testing. Use for 'prune tests', 'clean up tests in X', 'remove redundant tests', including unattended automation runs.
allowed-tools: Bash(gh repo view:*), Bash(gh pr list:*), Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git blame:*), Bash(git rev-parse:*), Bash(git fetch:*), Bash(git ls-remote:*), Bash(git branch --list:*), Bash(km --version), Bash(km dups:*)
---

# Prune Tests (one area at a time)

Goal: shrink and simplify the tests for ONE area (a directory, module, or namespace) without losing any real fault-detection. Never operate on the whole suite at once.

Safety contract: after pruning, for the target area,
1. the full area test set passes,
2. line + branch coverage of the area's source does not drop (or only on lines the user explicitly approves),
3. the scoped mutation score (killed mutants) does not drop.

If any of these fails, restore the tests responsible before finishing.

What counts as a good or bad test is defined once, in the `tdd` skill's references: [good-tests.md](../tdd/references/good-tests.md), [bad-tests.md](../tdd/references/bad-tests.md) and [mocking.md](../tdd/references/mocking.md). Judge categories C, D and F against them. How to run a subset of tests for each stack is in [runners.md](../tdd/references/runners.md).

## Unattended mode

Use this mode when the invoking prompt says "unattended" or no human is available (scheduled or automation runs). Never ask questions in this mode. Every other rule in this skill still applies, with these overrides:

1. **Area selection (replaces the question in Phase 0).**
   - List the candidate areas: top-level modules, directories or namespaces under the source tree that have matching tests.
   - Exclude areas with an open `prune-tests/*` PR, or one merged in the last 30 days. List the PRs and filter the branch names yourself, since GitHub's search can't match a branch-name prefix reliably:
     ```bash
     gh pr list --state open --json headRefName --limit 200 \
       --jq '.[] | select(.headRefName | startswith("prune-tests/")) | .headRefName'
     gh pr list --state merged --json headRefName,mergedAt --limit 200 \
       --jq '.[] | select(.headRefName | startswith("prune-tests/"))'
     ```
   - Rank the remaining areas by test cases per 100 non-blank source lines, highest first. Use cheap counts only; don't run coverage or mutation testing across the whole suite.
   - Pick the top area. If its scoped mutation run would take more than about 30 minutes, use its largest subdirectory instead.
   - State the chosen area, its ratio, and the next two areas in the ranking. If no eligible area remains, report that and stop.
2. **Tooling.** If the coverage driver or mutation tool is missing, don't install it and don't fall back to the coverage-only check. Report what's missing and stop.
3. **Review gate (replaces Phase 3).** Apply only rows that are low or medium risk and in categories A, B, C or E. Don't apply high-risk rows, or anything in categories D or F; list those under "Needs human review". The "always high risk / default keep" rules are never overridden.
4. **Uncertainty.** When a decision is unclear, take the conservative option (keep the test) and note it in the report.
5. **Failure.** If the safety contract can't be restored in Phase 5, reset the branch to the baseline commit recorded in Phase 1 (`git reset --hard $(cat .prune/<area>/baseline-sha)`), report what failed, and don't open a PR.
6. **Delivery (after Phase 6).** Push the `prune-tests/<area>` branch and open a PR with `gh pr create`. The PR body contains the Phase 6 report, the "Needs human review" list, and the suggested next area. Report the PR URL, and say that `/pixie:babysit` can bring the PR to green. Don't file issues in this mode.
7. **Permissions.** This skill pre-approves only read-only commands. The automation that runs it must allow `git switch`, `git add`, `git commit`, `git reset`, `git push` and `gh pr create`, or the run will stall on a prompt nobody answers.

## Phase 0: Scope

- **Clean tree.** Run `git status --porcelain`. If it prints anything, stop and say so. Never stash or discard someone's work.
- Ask the user for the target area if not given. In unattended mode, choose it as described under Unattended mode. Identify:
  - SOURCE paths for the area (what the tests exercise)
  - TEST paths for the area (what may be pruned)
- **Branch.** Find the default branch with `gh repo view --json defaultBranchRef -q .defaultBranchRef.name` (call it `DEFAULT`). If `prune-tests/<area>` already exists locally (`git branch --list`) or on the remote (`git ls-remote --heads origin prune-tests/<area>`), stop and say so; in unattended mode, report it and stop. Otherwise branch from the remote default branch:
  ```bash
  git fetch origin DEFAULT
  git switch -c prune-tests/<area> origin/DEFAULT
  ```
- Detect the stack and its tools:

  | Stack | Test runner | Per-test coverage | Mutation tool |
  |---|---|---|---|
  | PHP | PHPUnit / Pest | pcov or xdebug | Infection |
  | TS / JS | Vitest / Jest | v8 or istanbul | Stryker |
  | Python | pytest | coverage.py with test contexts | mutmut |
  | Rust | cargo test | cargo-llvm-cov, one run per test | cargo-mutants |

  For any other stack, say what's missing and stop. Offer to install a missing tool as a dev dependency (Python and Rust tools may be installed globally instead; say which). Do not proceed to deletion without a mutation tool unless the user explicitly accepts the weaker coverage-only check. (Unattended mode: see Tooling above.)
- **Tool install commit.** If you installed a dev dependency, commit only its manifest and lock file changes on their own, before Phase 1 (e.g. `chore(<area>): add Infection for mutation testing`).

## Commits

Use the repo's own convention (check `git log`). If it has none, use `test(<area>): <what changed>`. Stage by path: `git add` only the files that commit changed. Never `git add -A`, `git add .` or `git commit -a`. For a multi-line message, write it to a temp file outside the repo with the Write tool and commit with `git commit -F FILE`. Never use a heredoc or `-F -`: in some sandboxed shells the commit silently doesn't happen.

## Phase 1: Baseline (before touching anything)

First, keep `.prune/` out of git as a second guard. Add it to the repo's local exclude file, once:

```bash
grep -qxF '.prune/' "$(git rev-parse --git-path info/exclude)" || echo '.prune/' >> "$(git rev-parse --git-path info/exclude)"
```

Record the baseline commit, so a failed run can be reset to it:

```bash
mkdir -p .prune/<area> && git rev-parse HEAD > .prune/<area>/baseline-sha
```

Run only the area's tests (subset commands per stack: [runners.md](../tdd/references/runners.md)) and save the outputs to `.prune/<area>/before/`:

1. Test run: pass/fail + timing per test (JUnit XML is ideal).
2. Per-test coverage: which source lines/branches each test hits.
   - PHPUnit/Pest: `--coverage-php` or `--coverage-xml` with pcov; XML includes per-line covering tests.
   - Vitest/Jest: run with coverage per test file, or use per-test contexts if available.
   - Python: `coverage run --context=test` / `pytest --cov-context=test`.
   - Rust: cargo-llvm-cov has no per-test contexts. Run each test on its own (`cargo llvm-cov --lcov --output-path .prune/<area>/before/<test>.lcov -- --exact <test>`), one lcov file per test. This is slow, so keep Rust areas small.
3. Scoped mutation run on SOURCE paths only, using only the area's tests:
   - Infection: `--filter=<source path>` plus test framework filter for the area, `--only-covering-test-cases`, `--threads=max`, `--logger-json`.
   - Stryker: `mutate: ["<source glob>"]`, test runner limited to area tests, `coverageAnalysis: perTest`.
   - mutmut: `paths_to_mutate` set to the SOURCE paths and the test command limited to the area's tests.
   - cargo-mutants: `--file <source path>` for each source file, `--json`, with the test command limited to the area's tests.
   Record total, killed, survived, and which tests killed each mutant if the tool reports it. mutmut and cargo-mutants usually don't report per-test kills; say so in the report.

If the scoped mutation run would take more than ~30 minutes, split the area smaller.

## Phase 2: Inventory and classify (report only, no deletions)

First, run the `pixie:coverage-analyzer` agent with the area name and `.prune/<area>/before/`. Don't read the raw coverage or mutation files yourself; they can be very large. The agent writes a script that computes the subsumed tests, sole coverers and sole killers, and saves them to `.prune/<area>/coverage-analysis.json`. Use that file for category A and for the "only test covering" and "only killer" rules below.

For category C, start with `km dups <TEST paths> --format json` if `km` is installed (`km --version`). Its duplicate blocks are a cheap first list of near-duplicate tests; confirm each by reading the tests. Without `km`, find them by reading.

Build `.prune/<area>/candidates.md`, one row per candidate test with: test id, category, evidence, proposed action (delete / merge / keep), risk (low/med/high).

Categories to look for:

A. Coverage-subsumed: the test's covered lines/branches are a subset of another single test's in the area, AND the test kills no mutant that the other doesn't (if per-test kill data exists). Strongest delete signal.
   - **Keep the cover.** The test named as the cover becomes a keep. If two tests cover exactly the same lines, each looks subsumed by the other: delete only one. In a chain (T covered by U, U covered by V), delete T and U only if V stays.
   - **Pick covers that survive.** A cover must not be proposed for deletion in any other category. If it is, pick another cover from `coverage-analysis.json` or drop the row.

B. Third-party behavior: the test asserts behavior owned by a library/framework rather than by our code (e.g. that a framework's built-in validation rule rejects empty input, that the ORM persists a model, that a date lib formats dates, that the HTTP client sends headers). Delete.
   - KEEP tests that verify OUR configuration or usage of the library: our rule sets, casts, scopes, query builders, route definitions, middleware wiring. Keep at least one test per integration seam.

C. Near-duplicates: tests with the same arrange/act shape differing only in input values. Action: merge into one parameterized test (data provider / Pest dataset / `test.each` / a Rust table of cases), preserving every input case. This is the same rule `tdd` follows when extending a test.

D. Mock-only: the test only asserts that mocks were called and never asserts an observable result, and the same path is covered by a test asserting real outcomes. Delete or rewrite. Judge it against [mocking.md](../tdd/references/mocking.md): mocks of our own modules are the usual tell.

E. Trivial: plain getters/setters, constructors that just assign, constants. Delete when covered incidentally by behavior tests.

F. Over-granular: many tiny unit tests of private steps of one public operation. Action: replace with fewer tests at the public boundary that assert outcomes, keeping all distinct branches. Write the replacements to the standard in [good-tests.md](../tdd/references/good-tests.md).

Always mark as HIGH risk / default keep:
- Regression tests. Look for:
  - tests added in a bug-fix commit: check `git log --follow` / blame on the test for messages with fix, bug, regression or issue numbers, and conventional `fix(...)` subjects such as `tackle`'s `fix(#142): ...`;
  - tests named after issues, including the names `tdd` gives them: `testIssue142...`, `issue_142_...`, `"#142: ..."`.
- The ONLY test covering a given line or branch.
- Tests that are the only killer of any mutant.
- Security, auth, money, data-loss, and migration tests.

Also list (but do not act on) slow or flaky tests found along the way.

Summarize at the top of the report: counts per category, estimated tests removed, estimated runtime saved.

## Phase 3: Review gate

In unattended mode, skip this gate and use the automatic approval rules under Unattended mode.

Show the user the summary and the high/medium-risk rows. Proceed only with what they approve. Low-risk category A/B/E rows can be approved in bulk.

## Phase 4: Apply, one category per commit

Order: B (third-party) → E (trivial) → A (subsumed) → D (mock-only) → C (merge) → F (restructure).

Before applying A, re-check every A row against what B and E removed: if its cover is gone, pick another surviving cover from `coverage-analysis.json` or drop the row.

For each category:
1. Apply the changes for that category only.
2. Run the area tests; they must pass.
3. Commit (see "Commits") with a message listing the removed/merged tests and the category reason.

Rules:
- Never delete and rewrite the same behavior in one commit; a merge commit must show every original case present in the new parameterized test.
- Don't change SOURCE code. If a test can't be removed without a source change, note it and skip.
- Remove now-unused fixtures, helpers, and factories only in a final separate commit.

## Phase 5: Verify

Re-run Phase 1 into `.prune/<area>/after/` and compare:
- Coverage: list any source line/branch that went from covered to uncovered.
- Mutation: list any mutant that went from killed to survived.

For each regression, find which removed test covered or killed it (from the baseline data), restore or rewrite that test, commit the restore, and re-verify.

**At most two restore rounds.** If the contract still fails after the second, stop:
- **Attended:** show the user what still regresses and ask whether to keep trying, accept the listed regressions, or reset to the baseline commit.
- **Unattended:** follow "Failure" under Unattended mode.

## Phase 6: Report

Give the user:
- Tests before/after, runtime before/after for the area
- Coverage and mutation score before/after (should be equal or better)
- Commits made, by category
- Anything skipped and why, plus the slow/flaky list
- The "Needs human review" rows, if any
- Suggested next area (e.g. the area with the highest tests-per-source-line ratio)
- **Attended:** the branch name, and an offer to push it and open a PR. It hasn't been pushed. If they open one, `/pixie:babysit` can bring it to green.

**Filing follow-ups (attended only).** If there are "Needs human review" rows in categories D or F, offer to file them as GitHub issues, one per group of tests for the same public operation, so `tackle` can take each to a PR. Each issue lists the tests, the category, the evidence from `candidates.md` and the proposed action. Ask whether to label them `ready-for-agent`; default to no. If `docs/agents/pixie-labels.md` exists, use its label for that role instead.

Delete `.prune/` or leave it uncommitted; never commit it.

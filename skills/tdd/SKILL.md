---
name: tdd
description: "Test-driven development, red then green in vertical slices, with failing-before and passing-after evidence. Use only when the user runs /tdd or explicitly asks for TDD or a failing test first, or when another skill (such as tackle) directs you here. Do not trigger on ordinary coding requests."
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*)
---

# TDD

Make the intended behavior executable before changing production code, one slice at a time, and finish with evidence a reviewer can replay: the test that went red for the right reason, then the same test green.

Two failures this skill exists to prevent:

- **Untrustworthy red.** A test that fails for the wrong reason (typo, missing import, broken fixture) proves nothing when it turns green.
- **Worthless green.** A test that is coupled to implementation, tautological, or mostly tests mocks passes without telling you the behavior works.

## Invocation

- **By the user (`/tdd …`):** treat the arguments as the task: a bug description, a feature description, or an issue reference. An optional `mode=bug` or `mode=feature` overrides mode detection. If the current branch is the repo's default branch, ask before the first commit whether to commit there or on a new branch.
- **By another skill:** the caller supplies the task and usually the mode. Follow the caller's rules for commits, branches, and asking questions. Never block on the human: where this skill says "confirm", state your assumption in the report and continue. Where it says "stop and report", return the **Report** (below) to the caller, and don't end the turn.
- **From an issue with a Reproduction test section** (filed by `checkup` or `catch`): that test failed on the code it was filed against. Use it as the seed of the first test. Run it first: it's a trustworthy red only if it still fails for the reason the issue gives.
- **From `diagnose`:** it also passes a minimised repro, its loop command and the confirmed root cause. The repro is the seed of the first test. The loop command is the fallback check for section 5, and the red to use if no test seam reproduces the bug. The root cause goes in the commit message body.

## 0. Orient

- Read `GLOSSARY.md` (if present) so test names and interface vocabulary match the domain, and respect ADRs in the area you are touching.
- Pick the mode:
  - **Bug mode:** existing behavior is wrong. One regression slice, occasionally two.
  - **Feature mode:** new or changed behavior. Several vertical slices.
- Find the test runner and how this project runs a *subset* of tests (see [references/runners.md](references/runners.md)).

## 1. Scope the relevant tests

Large suites are slow. Never use the full suite as the baseline or the per-slice check. Build a **relevant set** instead and use it for every run in this skill.

1. List the production files you expect to touch (from the bug path or the feature plan).
2. Find the tests that exercise them, cheapest signal first:
   - The runner's own related-test feature if it has one (`vitest related`, `jest --findRelatedTests`).
   - Naming and directory conventions (`src/Foo/Bar.php` → `tests/Foo/BarTest.php`, `foo.ts` → `foo.test.ts`, Rust `#[cfg(test)] mod tests` in the same file plus `tests/` files that `use` the crate item).
   - A grep for the touched classes, functions, routes, or commands across the test directories.
   - The existing test file nearest to the seam you will test (this is also where new tests go).
3. Add one ring of **callers**: tests for modules that import or call the touched code directly. Do not chase transitive callers.
4. Write the relevant set down as concrete runnable commands (file paths, `--filter` expressions, test names). Reuse exactly these commands for every run. Each new test you write joins the set, so later slices re-run it.
5. **Time-box it.** If the baseline run (step 2) takes more than about two minutes, narrow the set to the files closest to the seam and note what you dropped. If you cannot identify any relevant tests, say so and treat the new tests you write as the relevant set.

The full suite is the CI's job. Never claim it passed unless you actually ran it.

## 2. Baseline

Run the relevant set before writing anything.

If the caller passes a baseline taken on this same unchanged tree that covered the relevant set (such as a full-suite run), use it instead of running the set again. Take its pre-existing failures that fall in the relevant set and apply the rules below to them.

- **Green:** record the command and the pass count, then continue.
- **Red:** do not fix unrelated failures. Record them as pre-existing (test names plus a one-line failure summary) and exclude them from the per-slice checks by name. If they touch the code you are about to change, stop and report, because a red baseline in your area makes every later signal ambiguous.
  - **Exception, bug mode:** if an existing failure shows the reported symptom, it *is* the bug. Use it as the first slice's red (the prediction is the reported symptom) instead of stopping.
- **Couldn't run** (missing dependencies, no test database, a setup or config error before any test runs): that's not a baseline. Try the project's documented setup (README, `CONTRIBUTING`, `composer`/`npm` scripts). If the set still won't run, stop and report.

## 3. Test list (plan, do not write)

Write down:

- **Seams:** the public interfaces you will observe behavior through, each with a one-line note on what testing there catches and what it misses.
- **Test list:** test *names only*, in the order you expect to build them. Names describe behavior ("rejects checkout when cart is empty"), not mechanism ("calls validator").
  - **Bug mode with an issue number:** the regression test's name starts with the issue, then the behavior, in the project's naming style: `testIssue142RejectsCheckoutWhenCartIsEmpty`, `issue_142_rejects_checkout_when_cart_is_empty`, or `"#142: rejects checkout when cart is empty"`. With no issue number, use the behavior alone.
  - **Extending an existing test:** say so on the list ("add case to `CartTotalTest::totals` data provider").

Confirm with the user when a seam introduces or changes a public interface, or the list has more than about five items. In bug mode, or when invoked by another skill, state the choice and continue.

The list is a plan, not a contract. Add, drop, or reorder items as each slice teaches you something. Never write the tests in bulk up front (see horizontal slicing in [references/good-tests.md](references/good-tests.md)).

## 4. The loop, once per slice

1. **Predict the red.** Before running, write the failure you expect: the assertion message, the wrong value, or the missing symbol or route.
2. **Write one test case** at an agreed seam, using the project's existing helpers and fixtures. First check whether an existing test already covers this path with different inputs. If one does, extend it: add a row to its data provider (PHPUnit `#[DataProvider]`, Pest `->with()`, Vitest `it.each`, a Rust table of cases), or turn it into one if it has several near-copies. Only write a new test when no existing one fits, and put it in the nearest existing test file. Expected values come from an independent source: a literal, a worked example, the spec, or the bug report. Never compute them the way the code does.
3. **Run it** (just that test). Compare the output to the prediction.
   - **Matches:** the red is trustworthy. Save the output for the report.
   - **Passes:** the behavior already exists or the test does not reach it. Fix the test so it reaches the behavior. In feature mode, drop the slice if the behavior really exists. In bug mode, never drop the regression slice: if no seam you can test reproduces the bug, use the fallback in section 5 (from `diagnose`, its loop command), or stop and report "not reproduced at this seam".
   - **Fails differently** (compile error, setup error, wrong assertion): fix the *test* until it fails for the predicted reason. Do not touch production code yet. A missing function or class is an acceptable red only in feature mode, and only once: stub it so the next run fails on the assertion.
4. **Make it green with the minimum.** Change only enough production code to pass this test. No speculative parameters, no handling of cases a later test will cover.
5. **Run the test, then the relevant set.** Both green, or back to step 4. If a relevant test broke, you changed a contract. If the task asks for exactly that change in behavior, update the old test in this slice and list it in the report. Otherwise fix the code, or stop and report if the change seems needed but the task didn't ask for it.
6. **Tidy on green (optional).** Restructure only code touched in this slice (names, duplication you just introduced, extracting a helper), then rerun the relevant set. Anything larger becomes a follow-up note in the report, not part of this loop.
7. **Commit** (unless the caller owns commits): the test and the fix together in one commit, made only once the tests pass. Never commit a failing test on its own.
   - **Stage by path.** `git add` only the files this slice changed. Never `git add -A`, `git add .` or `git commit -a`, which would sweep in someone's unrelated work.
   - **Message.** Use the caller's commit format. If there's none, follow the repo's own convention (check `git log`).
   - **Body.** Paste the red output from step 3, trimmed to the assertion and failure lines, so the history still shows it failed first. Replace any secret (tokens, passwords, connection strings, keys) with `<REDACTED>`. Commit history is permanent and often public. If a caller gave a root cause, state it too.

Then take the next item on the list.

**Done (feature mode):** when every requirement in the task maps to a green test or a stated skip. Re-read the task to check, since the list will have changed along the way. Put any requirement without either in the report.

## 5. When a test is impractical

Prefer no new test over a bad test. Use [references/bad-tests.md](references/bad-tests.md) to judge it, and [references/good-tests.md](references/good-tests.md) for what to aim for. If the only available test would be bad, or would need broad harness setup, production-only state, slow end-to-end infrastructure, or large unrelated fixture churn, do not force it. Use the closest executable check instead, roughly in this order:

1. A targeted script or CLI command that reproduces the behavior.
2. A focused integration check against a real local dependency (test DB, local server).
3. Browser automation or a recorded manual reproduction for UI behavior.
4. A log or output assertion, or a snapshot comparison of real output.

For 2 and 3, use the project's verification skill (`.claude/skills/verify-*/`) if it has one, unless `docs/agents/pixie.json` sets `liveVerify.tdd` to `false`. It already knows how to launch, drive and clean up the app.

The fallback still follows red → green: capture it failing before the fix and passing after. Skipping a test is always stated in the report with the reason. Never skip silently.

Keep throwaway repro scripts outside the repo (e.g. in a `mktemp -d` folder). Commit one only if it's worth keeping as a project script, and say so in the report.

## Guardrails

- Never edit a test to match a wrong implementation.
- Never weaken an existing assertion unless the expected behavior has genuinely changed, and say why in the report.
- Never update snapshots (`-u`, `--update-snapshots`, regenerated fixtures) to get green. That edits the test to match the code. Do it only when the expected behavior genuinely changed, and say so in the report.
- Mock only at system boundaries (see [references/mocking.md](references/mocking.md)). Never mock your own modules.
- Keep each test focused on one behavior. No broad fixture churn and no unrelated coverage expansion.
- Flaky behavior: make the test deterministic (inject the clock, the randomness, the ordering) and note the signal being locked down.
- When a bug reveals a whole class of failures, land the focused regression first, then list sibling cases as follow-ups.

## Report

Report evidence, not outcomes. Whether it goes to the user or to the calling skill, include:

- **Mode** and the **relevant set** commands, with anything dropped by the time-box.
- **Baseline:** pass count, plus any pre-existing failures that were excluded.
- **For each slice:** the test name (and whether it extended an existing test), the predicted failure, the actual red output (trimmed to the assertion), and the green run.
- **Changed tests:** any existing test or snapshot updated because the behavior changed, and why.
- **Requirements without a test** (feature mode), from the done check.
- **Skipped tests:** what was skipped, why, and the fallback check with its before/after output.
- **Final relevant-set run** and whether the full suite was run (usually not; CI covers it).
- **Follow-ups:** sibling cases, tidy-ups deferred, assumptions made instead of asking.

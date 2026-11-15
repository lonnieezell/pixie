---
name: untangle
description: Run code-health refactor loops: bare /untangle picks the best hotspot itself and refactors it; /untangle plus a target loops over every part of that code until it's clean.
allowed-tools: Bash(km --version), Bash(km score:*), Bash(km hotspots:*), Bash(km cogcom:*), Bash(km smells:*), Bash(km dups:*), Bash(git status:*), Bash(git diff:*), Bash(git log:*)
---
# Untangle

A wrapper around the `code-health` skill. That skill owns the km commands, the thresholds, the guided refactor loop (its mode 4) and the per-language refactoring playbook. This skill decides **what** to refactor and **how long to keep going**, then drives that loop.

**First step, always:** load the `code-health` skill with the Skill tool and follow its km usage, exclusion flags, guided loop and playbook. Don't restate or reinvent them here. If the repo has a `.kimun.toml`, its thresholds win over the defaults.

## Pick the mode from the arguments

- **No arguments** (`/untangle`) → **Auto mode**: find the single best target and refactor it without asking.
- **A target** (`/untangle the sidebar code`, `/untangle src/Billing`, `/untangle UserController`) → **Targeted mode**: refactor every part of that code until all of it is clean.

## Preflight (both modes)

1. Confirm `km` runs (`km --version`). If it's missing, stop and say so, as the `code-health` skill describes.
2. Require a clean working tree (`git status --porcelain`). If there are uncommitted changes, stop and ask. Never stash or discard someone's work.
3. If on the default branch, create `untangle/<short-slug>` and work there.
4. Find the project's test, lint and type-check commands (composer/package.json scripts, `cargo test`, phpunit, vitest, etc.) and run them once to get a baseline. Pre-existing failures are noted and left alone, but they must not get worse.

## Auto mode — choose without asking

1. Gather candidates:
   ```bash
    km hotspots . --exclude-dir vendor --exclude-dir node_modules --exclude-dir target --exclude-dir dist --exclude-dir build --exclude-dir .next --exclude-dir writable --exclude-dir storage --top 10 --format json
    km score . --exclude-dir vendor --exclude-dir node_modules --exclude-dir target --exclude-dir dist --exclude-dir build --exclude-dir .next --exclude-dir writable --exclude-dir storage --format json --bottom 15
   ```
2. Drop files that aren't worth or safe to refactor: generated code, migrations, vendored or third-party code, lockfiles, fixtures, test files themselves, and files with no realistic way to test (e.g. glue that only runs in production).
3. Rank what's left. Hotspot score (complexity × change frequency) comes first, because that's where cleanup pays back. Break ties by the lowest health score, then prefer files that already have tests.
4. Pick **one file**. Don't ask the user to confirm. 
5. State the pick in one or two sentences: the file, its hotspot rank, the worst functions with their numbers, and why it beat the runner-up.
6. Run the targeted-mode loop below with that file as the scope.

## Targeted mode — loop until clean

### 1. Resolve the target to a file set

Turn the description into concrete files. Grep for the names, follow imports and the component tree, check routes and DI wiring. "The sidebar code" might be a component, its hooks, styles-in-JS, store slice and helpers. Include the code that makes up the feature; leave out shared code it merely calls (note those as out of scope). State the file list in a line before starting. Ask only if the description could plausibly mean two unrelated areas.

### 2. Measure the whole scope

```bash
km cogcom <paths> --per-function --format json
km smells <paths> --format json
km dups <paths> --format json
```

Also note file sizes against the limit. Build a **worklist** of every finding: each function over the complexity threshold, each smell, each duplicate block inside the scope, each oversized file. Sort it worst first, grouping findings in the same function or file so they're handled together.

### 3. Work the list

For each worklist item, run the `code-health` guided loop:

- make sure tests cover the behaviour (write characterisation tests first if they don't)
- refactor in small steps, one smell at a time, using the playbook for that language
- run tests, lint and types after each step
- **commit after each green step** (`untangle: <what changed> in <file>`) so any step can be reverted on its own

After each item, re-measure the **whole scope**, not just the file you touched. Extractions can push complexity into new functions or create new duplicates. Rebuild the worklist from the fresh numbers.

### 4. Stop conditions

Stop when one of these happens:

- **Clean.** Every function in scope is at or under the complexity threshold, km reports no smells and no in-scope duplicates, and every file is under the size limit.
- **Only essential complexity remains.** Some functions are genuinely complex (parsers, state machines, protocol handling). Mark each one with a sentence on why it's essential and move on; don't contort it to hit a number.
- **No progress.** Two consecutive passes that don't improve any number. Report what's left instead of looping.
- **Safety cap.** About 25 refactor steps in one run. Report what's left and offer to continue.

### 5. Live check

Tests can miss behaviour they never covered. If the project has a verification skill (`.claude/skills/verify-*/`, such as one made by `create-verifier`), drive every feature in its `features/` map whose source the run changed (`git diff --name-only <start-commit>...HEAD`). Follow the skill's Launch, Doctor, Drive and Cleanup sections. If a feature behaves differently from the start commit, find the step that caused it, revert that step, and add a characterisation test for what it broke where a seam exists. Run the Cleanup when you're done. Skip this step if there's no verification skill, the scope has no user-facing code, or `docs/agents/pixie.json` sets `liveVerify.untangle` to `false`, and say which in the report.

### 6. Guardrails

- **Behaviour must not change.** No changes to public APIs, routes, DB schema, config keys, event names, or output formats. If cleaning something properly needs one of those, leave it and list it under "needs a decision".
- If a step breaks tests and two attempts don't fix it, revert that step (`git revert` or reset to the last green commit) and move to the next item.
- Never weaken, skip or delete tests, and never relax thresholds, lint rules or `.kimun.toml` to make the numbers pass.
- Don't push, open PRs or merge. The branch is left for the user to review.
- Stay inside the scope. Smells found in shared code outside it are listed in the report, not fixed.

## Report

Keep it short:

- **Target** (and in auto mode, why it was chosen).
- **Before → after:** per file, the worst function's complexity, smell count, duplicate count and health score. Include `km score diff . --git-ref <start-commit> --format short`.
- **What changed:** one line per commit, or grouped by theme if there are many.
- **Left as-is:** essential complexity (with the reason), items that need a decision, out-of-scope findings.
- **Branch name** and the test status at the end.
- **Live check:** the features driven and what they showed, or why it was skipped.

Offer one next step: usually the next hotspot (auto mode) or the out-of-scope shared code that kept showing up (targeted mode).
# Skills reference

Every Pixie skill, what it does, what it needs, and what it changes. Type a skill as `/pixie:<name>`, followed by any arguments.

New to Pixie? Start with the [tutorial](../tutorial/first-issue-to-pr.md) instead.

## Summary

| Skill | What it does | Example | Needs | Claude can start it on its own? |
|---|---|---|---|---|
| `babysit` | Brings open PRs to a mergeable state, oldest first | `/pixie:babysit` | `gh` | No |
| `catch` | Turns Sentry and Coralogix errors into `needs-triage` issues | `/pixie:catch` | `gh`, a Sentry or Coralogix token | No |
| `checkup` | Audits the codebase for security, performance and bugs, scores it, and files issues | `/pixie:checkup` or `/pixie:checkup scores` | `gh` to file issues; `km` optional | No |
| `code-health` | Measures code health and guides refactoring | `/pixie:code-health did my changes make it worse?` | `km` | Yes |
| `create-verifier` | Writes a project skill that drives your app like a user | `/pixie:create-verifier` | — | No |
| `diagnose` | Finds a bug's root cause, proves it, then fixes it | `/pixie:diagnose checkout total is wrong` | — | Only when asked by name |
| `how` | Explains how part of the codebase works | `/pixie:how does authentication work` | — | Yes |
| `huh` | Restates Claude's last reply in plain language | `/pixie:huh` | — | No |
| `maintain-verifier` | Keeps a verification skill in step with the app | `/pixie:maintain-verifier` | `gh` | No |
| `plan-task` | Turns a PM task into a GitHub issue with a build plan | `/pixie:plan-task` + pasted task | `gh` | Yes |
| `poke` | Pokes at one section of an app for bugs and UX gaps | `/pixie:poke the file tree in the sidebar` | `gh` to file issues (optional) | No |
| `prune-tests` | Removes redundant tests in one area without losing coverage | `/pixie:prune-tests tests/Billing` | `gh`, coverage and mutation tools | Yes |
| `setup` | Checks tools and maps Pixie's labels to your repo's names (optional) | `/pixie:setup` | `gh` for labels | No |
| `tackle` | Takes a `ready-for-agent` issue to an open PR | `/pixie:tackle 142` | `gh` | No |
| `tdd` | Builds a change test-first, red then green | `/pixie:tdd mode=bug #142` | — | Only when asked by name |
| `untangle` | Refactors a hotspot or a named area until it's clean | `/pixie:untangle src/Billing` | `km` | Yes |

**Claude can start it on its own** means Claude may load the skill when your request matches, without the slash command. For example, asking "what should we refactor?" can load `code-health`.

- **No:** the skill only runs when you type it. These skills push code, change labels, post comments, or act on your last message, so they wait for you.
- **Only when asked by name:** `diagnose` and `tdd` run when you name them, or ask for a failing test first, or when `tackle` calls them. They don't start on ordinary coding requests.

For the labels, branches, and files each skill creates, see [Labels, branches, and files](labels-and-branches.md).

## babysit

Works through a repo's open pull requests one at a time, oldest first. For each PR, it:

1. Fixes merge conflicts.
2. Answers review-bot comments. It checks each claim against the code first, then fixes it or explains why not.
3. Gets CI green.

**Arguments (all optional):**

- `owner/repo`. Defaults to the repo in the current folder.
- A PR number to start at.
- How many PRs to handle. The default is 5.

**Before it starts:** your working tree must be clean. It stops if you have uncommitted changes, and it returns you to your starting branch when it's done.

**Limits:**

- It never merges, approves, or closes a PR. It never changes branch protection.
- It never resolves or argues with a human reviewer's comment. It also leaves alone any bot thread a human has commented in.
- It skips drafts and PRs opened by bots such as Dependabot or Renovate.
- It handles at most two rounds of bot review per PR. Later bot comments go in the report.
- It only waits for bot reviews on PRs that bots have reviewed before. It skips the second round if the first round pushed nothing.
- It stops and reports when a PR needs a human decision. Examples: a human asked for changes, the fix would change behavior, or the PR comes from a fork it can't push to.
- It's safe to run again. It doesn't reply twice to a thread it already answered.

**Output:** a table of each PR's final state. The states are *Ready — awaiting approval*, *Ready*, *Waiting on human*, or *Blocked*.

## catch

Pulls recent production errors from Sentry and Coralogix and turns the real ones into issues `tackle` can fix. It shares `checkup`'s pipeline from merging onwards, so an error in code `checkup` already flagged lands on the same issue.

**Arguments (all optional):** `unattended` and `fix`, as for `checkup`.

**How it works:**

1. Fetches error groups from the configured sources over the `lookback` window, keeping those with at least `minEvents` events. It redacts emails, tokens, IPs and long secrets, and never fetches request data, headers, user data or breadcrumbs.
2. Maps each stack frame to a repo file. If the lines around the frame closest to the error changed since the error's release (or, without a release commit, if that file was committed after the error was last seen), it marks the report "possibly fixed" and doesn't file it.
3. Runs one read-only `error-triager` agent per report. It traces the frames into the current code and writes a finding with a walked failure path.
4. Sends every finding to the same fresh-context verifier `checkup` uses. A triager can't confirm its own finding, because the error text it read is untrusted. If the repo has a verification skill, it tries to reproduce each confirmed finding on a local instance of the app.
5. Files confirmed findings as `needs-triage` issues with the event and user counts. A recurring error gets a "still present" comment, at most once a week, instead of a new issue.
6. With `fix`, it proves eligible findings with a failing local test and queues them for `tackle`, within the weekly PR cap it shares with `checkup`.

**Setup:** set `catch.sentry.org` or `catch.coralogix.domain` in `docs/agents/checkup.json`, and `SENTRY_AUTH_TOKEN` or `CORALOGIX_API_KEY` in the environment. See [Turn production errors into issues](../how-to/turn-production-errors-into-issues.md) and [the catch settings](checkup-config.md#catch).

**Limits:**

- It never changes anything in Sentry or Coralogix. Resolving the error there is your job after the fix ships.
- A production error alone is never enough for auto-fix. It needs a reproduction test that fails locally.

Claude never runs this skill on its own. You must type `/pixie:catch`.

## checkup

Audits the codebase along three dimensions: security, performance and bugs. It keeps only the findings that survive an attempt to refute them, scores each dimension, and files confirmed high and critical findings as `needs-triage` issues in a form `tackle` can work from.

**Arguments (all optional):**

| Argument | Effect |
|---|---|
| none | Full audit of the whole repo |
| `scores` | Regression check. It audits only the shards that changed since the baseline, reuses the rest, and reports scores and deltas. It files nothing. |
| a path | Audits only that folder or file. It doesn't touch the baseline. |
| `unattended` | No questions. It files issues and publishes the baseline. |
| `fix` | Also proves auto-fix candidates with a failing test and queues them for `tackle` |
| `permissions` | Audits nothing. It prints the exact allow rules an unattended run needs for the steps that write to GitHub. See [Schedule checkup and catch](../how-to/schedule-checkup-and-catch.md). |

**How it works:**

1. Splits the code into shards of up to 20 files, packing small neighbouring folders together, busiest first, and runs the repo's own audit and lint tools for leads.
2. Starts three read-only hunter agents per shard, one per dimension. Each finding must name a concrete failure scenario and quote its evidence.
3. Merges duplicates and findings with a shared root cause. A fresh-context verifier on Opus tries to refute each one, then sets its severity from a fixed rubric. If the repo has a verification skill, it tries to reproduce each confirmed finding it will file in the running app, and adds what it saw to the issue.
4. Scores each dimension with a fixed formula and compares the scores with `docs/agents/checkup-baseline.json`. A new confirmed high or critical finding in code that changed since the baseline, or a drop larger than the threshold, counts as a regression. One found in unchanged code is reported as newly found instead.
5. Files issues, deduped by fingerprint against every earlier issue. A finding closed as not planned is never filed again. Security findings go to issues, private draft advisories, or the report only, depending on `securityFindings`.
6. Publishes the new baseline to a rolling `checkup/baseline` PR. When security findings don't go to issues (public repos, by default), the baseline keeps only their counts, never their locations or fingerprints.
7. With `fix`, it writes a failing reproduction test for each candidate in a throwaway worktree, and moves proven ones to `ready-for-agent`, up to `maxPrsPerWeek`.

**Output:** `ai/checkup/DATE-HHMM/report.md` with scores, confirmed findings, refuted findings and gaps, plus the filed issues and the baseline PR.

**Limits:**

- Shards it couldn't check are listed as gaps, never as clean. Their earlier findings carry over as stale, and the next run audits them again.
- It never merges, approves or closes anything, and it force-pushes only `checkup/baseline`.
- It can't start `tackle` itself. Run `/pixie:tackle N` for each promoted issue, or let the scheduled workflow do it.

Settings live in `docs/agents/checkup.json`. See [checkup and catch settings](checkup-config.md). For a walkthrough, see [Audit a codebase](../how-to/audit-a-codebase.md). To run it weekly, see [Schedule checkup and catch](../how-to/schedule-checkup-and-catch.md).

Claude never runs this skill on its own. You must type `/pixie:checkup`.

## code-health

Uses km to answer project-level questions about code quality. It picks a mode from how you phrase the request:

| You ask | What it does |
|---|---|
| "How healthy is this project?" | Gives an overall grade, the weakest areas, and the 5 worst files |
| "Did my changes make it worse?" | Compares your branch to the repo's default branch and judges only the files you changed |
| "What should we refactor?" | Ranks the top 5 hotspots and suggests a first step for each |
| "Refactor X" | Measures X, adds tests if needed, then refactors in small steps |

It skips `vendor`, `node_modules`, `target`, `dist`, `build`, `.next`, `writable`, and `storage`, the same folders the edit hook skips. It aims for every function to be at or under 15 cognitive complexity. Cognitive complexity is a score for how hard a function is to follow.

It also includes a refactoring playbook for PHP (CodeIgniter 4 and Laravel), TypeScript/React, and Rust.

## create-verifier

Writes a verification skill for the current project. A verification skill is a recipe an agent follows to start your app, use a feature the way a user would, and capture proof that it works. It works for any language or platform: web, CLI, desktop, API, and more.

**How it works:**

1. Studies the repo to learn how the app starts, how an agent can drive it, and what evidence it can capture. It asks you only what it can't find in the code.
2. Writes the skill to `.claude/skills/verify-<app>/`. The skill has sections to launch the app, check it's healthy, drive it, capture evidence, and clean up.
3. Writes a feature map: one file for each of the top 3–5 user-facing features, saying how to reach, drive, and prove each one.
4. Runs the new skill once from start to finish on one feature, and fixes what fails.

**Output:** a working, tested verification skill in your project. Other skills use it too: `tackle`, `diagnose`, `tdd`, `untangle`, `checkup`, `catch` and `poke` drive the app through it when one exists. See [Live checks](live-checks.md) to turn this off per skill.

Claude never runs this skill on its own. You must type `/pixie:create-verifier`. Run `maintain-verifier` later to keep it up to date.

## diagnose

Finds the root cause of a bug or a slowdown before fixing anything. First it builds a feedback loop: one fast command that fails on this bug. Then it shrinks the repro, tests three to five ranked guesses, and confirms the cause with real evidence. The fix goes through `tdd`.

**Argument:** the bug report or an issue reference, such as `/pixie:diagnose #142`. Add `mode=diagnose-only` to stop at the cause with no fix.

**Safety:**

- It runs loops and probes only against local or test environments. It asks before read-only checks on a shared or staging system, and it never writes to production.
- It keeps its scripts and harnesses in a temporary folder outside your repo.
- It removes all debug code before the fix, so none of it gets committed.
- Before `git bisect`, it requires a clean working tree, and it always resets bisect afterwards.

If the repo has a verification skill, it uses it to drive the app for the feedback loop and the final re-check.

**Output:** a verdict of *FIXED*, *DIAGNOSED*, *NOT REPRODUCED*, or *INCONCLUSIVE*, with the evidence behind it. Secrets are redacted.

## how

Explores the codebase and explains how a part of it works. It writes for a senior engineer who is new to that part of the system. You get a working picture of the pieces, how data moves between them, and why it's built that way. It is not a line-by-line tour.

**Argument:** your question, such as `/pixie:how are background jobs retried`.

**Output (about 400–900 words):**

1. A short version.
2. The main parts, with file paths.
3. How a request flows through them, sometimes with a diagram.
4. Why it's built this way.
5. Things that are easy to get wrong.
6. Which files to read first.

## huh

Restates Claude's last reply in plain words, without jargon. Use it when a reply is hard to follow.

Claude never runs this skill on its own. You must type `/pixie:huh`.

## maintain-verifier

Keeps a verification skill made by `create-verifier` in step with the app. Apps change, and the feature map goes stale. Run this from time to time to catch that.

**How it works:**

1. Finds the project's verification skill, and fixes missing or dead entries in its feature map.
2. Starts one read-only subagent per feature. Each one reads the source and flags places where the map no longer matches the code.
3. Drives every feature in the live app at least once, even if the source looked fine.
4. Sorts each problem into one of three kinds:
   - *Doc drift:* the map is wrong. It fixes the map.
   - *Harness gap:* the app works, but the skill can't drive it. It fixes the skill.
   - *Product gap:* the app itself is broken. It reports this to you and leaves the app code alone.

**Limits:**

- It only edits the verification skill's own folder. It never changes product code.
- It opens at most one PR per run.

**Output:** one of three results. *Clean* means nothing needed fixing. *Changed* means it opened one PR of tested fixes. *Blocked* means it couldn't finish, and it says why.

Claude never runs this skill on its own. You must type `/pixie:maintain-verifier`.

## plan-task

Turns a product manager's task description into a short implementation plan. Then it posts the plan as a GitHub issue. It works out the open questions the task leaves unanswered and copies patterns from the closest existing feature. If the task reports a bug with an unknown cause, it writes a bug report instead of a plan, so that `tackle` diagnoses the bug instead of guessing a fix.

**How to use it:**

1. Run `/pixie:plan-task` and paste the task text, either with the command or in your next message.
2. If the text has no ticket ID, Claude asks for one once. Type the ID, or pick "No ticket".
3. Claude checks open issues and PRs for the same work. If an issue already covers the task, it asks whether to go on.
4. Claude shows you the draft title and body. It asks you each open question, with its own default as the recommended answer. Ask for changes, or approve it.
5. Claude asks whether to label the issue `ready-for-agent` so `tackle` can pick it up. The default is no.
6. Claude creates the issue and replies with its URL and the `tackle` command to run next.

**Limits:**

- It writes no code. It stops once the issue exists.
- It adds only the `ready-for-agent` label, and only if you say yes. It adds assignees, milestones, or other labels only when you ask.
- If a plan needs more than about five build steps, it offers to split it into several issues, one PR each.

## poke

Pokes at **one** section of an app the way a curious, impatient user would, and sees what breaks. A section is a feature, screen, or group of components, such as the file tree or a settings panel. It looks for three kinds of problems:

1. Bugs in the code.
2. Expectation gaps. These are places where the app doesn't do what users of similar apps try by reflex. For example, a file tree that ignores the arrow keys, when VS Code and Finder both support them.
3. Problems that only show up when you use the running app.

**Argument:** the section, as a path, a feature name, or a description. You can also name apps to compare it against.

**How it works:**

1. Finds the section's code and the kinds of components it uses. Then it picks reference apps that set user expectations for each one, and builds a checklist of what users will try.
2. Picks the best way to drive the running app: the project's own verification skill (such as one made by `create-verifier`), an app automation MCP server, browser automation against the dev server, computer use, or code only. With a verification skill, it drives every entry point the feature map lists for the section.
3. Runs three passes. Two read-only subagents check code correctness and expectation gaps in the background. Meanwhile, Claude uses the live app in your conversation.
4. Merges the findings, checks each one, and ranks them from S1 (data loss, crash, or blocked task) to S4 (polish). Then it stops any dev server or app it started.

**Limits:**

- It reports findings. It doesn't fix them.
- It doesn't take destructive actions on real user data. It uses a test workspace, and asks if none exists.
- With no way to drive the app, it reviews code only and marks live-only problems as *suspected*.
- Claude never runs this skill on its own. You must type `/pixie:poke`.

**Output:** a report at `ai/poke/<date>-<section>.md`, with screenshots in a folder beside it. If `.gitignore` doesn't already ignore `ai/`, it adds that line. The report has a short summary, then one entry per finding, grouped by severity. Each entry says where the problem is, what happens, what users expect, the evidence, and a suggested fix. It ends with a list of missing features users will look for and a list of what it couldn't check.

**Follow-up:** it offers to file S1/S2 findings, or any you pick, as GitHub issues. Run `tackle` on those issues to fix them.

## prune-tests

Shrinks the tests for **one** area of a large suite without weakening them. It never works on the whole suite at once.

**Argument:** the area to prune, such as a folder, module, or namespace. If you leave it out, Claude asks.

**Safety rules.** After pruning, all three of these must hold for the area:

1. All of the area's tests pass.
2. Line and branch coverage doesn't drop.
3. The mutation score doesn't drop.

If any check fails, Claude puts back the tests that caused it.

**Before it starts:** your working tree must be clean. The `prune-tests/<area>` branch must not exist yet, locally or on the remote.

**Supported stacks:**

| Stack | Coverage | Mutation tool |
|---|---|---|
| PHP | pcov or xdebug | Infection |
| TypeScript / JavaScript | v8 or istanbul | Stryker |
| Python | coverage.py with test contexts | mutmut |
| Rust | cargo-llvm-cov, one run per test | cargo-mutants |

Rust coverage runs once per test, so keep Rust areas small. mutmut and cargo-mutants usually don't record which test caught each mutant, so the "only test that catches a mutant" rule can't be applied there.

**How it works:**

1. Creates a `prune-tests/<area>` branch from the remote default branch and records a baseline, including the starting commit.
2. Sorts tests into groups: covered by another test, testing library behavior, near-duplicates, mock-only, trivial, or too fine-grained. If `km` is installed, `km dups` gives a first list of near-duplicates. Mock-only and fine-grained tests are judged by the same rules `tdd` uses for writing tests.
3. Shows you the risky changes and waits for your approval.
4. Makes one commit per group, then checks the safety rules again. When two tests cover the same lines, it deletes only one of them, and it never deletes the test that covers a deleted one.
5. If a check fails, it puts back the tests responsible, at most twice. After that it asks you whether to keep trying, accept the listed drops, or reset to the starting commit.
6. Reports the results and the branch name, and offers to push it and open a PR. It can also file the tests that need a human as GitHub issues, and asks whether to label them `ready-for-agent`.

Some tests are always kept by default. These include bug-fix regression tests, the only test covering a line, the only test that catches a mutant, and tests for security, auth, money, data loss, or migrations. Regression tests include those named the way `tdd` names them, such as `testIssue142...`, and those added in `fix(#142): ...` commits.

**Commits:** your repo's convention. If it has none, `test(<area>): ...`. A tool it installs gets its own commit first.

**Unattended mode.** Put "unattended" in the prompt for scheduled or automated runs. In this mode, Claude:

- Picks the area itself.
- Never asks questions.
- Applies only low- and medium-risk changes.
- Opens a PR with the results. If it can't restore the safety rules, it resets the branch to the starting commit and opens no PR.
- Needs the automation to allow `git switch`, `git add`, `git commit`, `git reset`, `git push`, and `gh pr create`. The skill pre-approves only read-only commands, so without these the run stalls on a permission prompt.

## setup

Sets up the current repo for Pixie. It's optional: without it, every skill uses the default labels.

**How it works:**

1. Checks `gh` sign-in, your access to the GitHub repo, and whether `km` is on the PATH. It tells you how to fix anything missing, but installs nothing.
2. Asks whether to keep the default labels. If you say no, it asks for a label for each of the five roles. It points out existing labels that look like a match.
3. Shows you the draft of `docs/agents/pixie-labels.md`, then writes it.
4. Creates any chosen label the repo lacks, with a color and a description.
5. Offers to run `km init` if there's no `.kimun.toml`, and `/pixie:create-verifier` if there's no `verify-*` skill.

**Output:** `docs/agents/pixie-labels.md`. Commit it. `tackle`, `plan-task`, `poke` and `prune-tests` read it. When it's missing, they use the default labels.

**Limits:**

- It never passes `--force` to `gh label create`, so it doesn't change labels you already have.
- It never renames, removes, or deletes labels. If you change a mapping, the old label stays on its issues. Setup lists those issues for you.
- Without `gh` or write access, it writes the file but creates no labels.
- It needs a GitHub repo for the label steps.

Claude never runs this skill on its own. You must type `/pixie:setup`. See [Set up a repo for Pixie](../how-to/set-up-a-repo.md).

## tackle

Takes one GitHub issue from `ready-for-agent` to an open pull request. It:

1. Picks the issue. With no number, it offers the oldest ready issues. If an earlier branch or PR exists for the issue, it asks whether to continue from it.
2. Creates an `agent/<number>-<slug>` branch from the remote default branch, then claims the issue with the `agent-working` label.
3. Rates the issue's difficulty and picks a route: `diagnose` for a bug with an unknown cause, `implement` (through `tdd`) for everything else.
4. Does the work, then runs lint, simplify, and code review. Hard issues also get a security review. If the repo has a verification skill, it then drives the changed features in the running app.
5. Opens the PR and swaps the label to `agent-pr`.

**Arguments (optional):** an issue number, such as `/pixie:tackle 142`, and `unattended` for scheduled runs. With `unattended`, it needs a number and never asks: wherever it would ask, it stops before claiming the issue and says why.

If the issue has a reproduction test from `checkup` or `catch`, it uses that test as the start of its regression test.

**Before it starts:** your working tree must be clean, and you need write access to the repo.

**Limits:**

- It handles one issue per run. It never merges, approves, or closes anything.
- Commits and the PR title use conventional commits that reference the issue, such as `fix(#142): ...`.
- The PR body links the issue with `Fixes #142` for a bug or `Closes #142` for a feature. If the issue has a `**Source:**` ticket line from `plan-task`, the body links that ticket with the same word, such as `Fixes ABC-123`.
- It treats only comments from the issue author and repo members as part of the spec.
- It requires no *new* test failures. Tests that already fail on the default branch are listed in the PR.
- It doesn't wait for CI. Run `babysit` afterwards to get the PR green.
- If it gets stuck or you interrupt it, it comments on the issue and labels it `agent-blocked`.
- It posts progress to Orca worktree cards when Orca is installed. Without Orca, it skips this.

## tdd

Builds a change test-first in small slices. For each slice, it predicts how the test will fail, watches it fail for that reason, then writes the least code to pass. It runs only the tests related to the change, not the whole suite.

**Argument:** a bug, a feature, or an issue reference. Add `mode=bug` or `mode=feature` to set the mode yourself.

**How it writes tests:**

- It adds a case to an existing test or data provider when one fits, before writing a new test.
- A bug fix's regression test is named after the issue and the behavior, such as `issue_142_rejects_checkout_when_cart_is_empty`.
- It commits only the files each slice changed, so your other uncommitted work stays out. Secrets in failure output are redacted before they go into commit messages.
- Run directly on the default branch, it asks before the first commit.

When a test isn't practical, it falls back to another check that fails before the fix and passes after. If the repo has a verification skill, it uses that to drive the app for the check.

**Output:** evidence for each slice: the failing run, then the passing run. It also lists any tests it skipped and why, and any existing tests it changed.

## untangle

Drives the `code-health` refactor loop. It decides what to refactor and when to stop.

**Modes:**

- `/pixie:untangle` with no arguments: Claude picks the best hotspot itself and refactors it without asking.
- `/pixie:untangle <target>`, such as `the sidebar code` or `UserController`: Claude finds every file in that area and refactors until it's clean.

**Before it starts:**

- It needs a clean working tree. If you have uncommitted changes, it stops and asks. It never stashes or discards your work.
- If you are on the default branch, it creates `untangle/<short-slug>`.
- It runs your tests, linter, and type checker once for a baseline.

**Limits:**

- It commits after each green step, so you can revert any step on its own.
- It never changes public APIs, routes, database schema, config keys, event names, or output formats.
- It never weakens or skips tests, and it never loosens thresholds.
- It never pushes, opens a PR, or merges. You review the branch.
- It stops when the code is clean, when only truly needed complexity is left, after two passes with no progress, or after about 25 steps.
- If the repo has a verification skill, it drives the changed features in the running app at the end, and reverts any step that changed their behavior.


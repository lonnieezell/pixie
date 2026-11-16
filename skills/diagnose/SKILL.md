---
name: diagnose
description: "Diagnosis loop for bugs and performance regressions: build a failing feedback loop, minimise, test ranked hypotheses, confirm the root cause, then fix through the tdd skill. Use only when the user runs /diagnose or explicitly asks to diagnose or debug something, or when another skill (such as tackle) directs you here. Do not trigger on ordinary coding requests."
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git blame:*), Bash(git show:*), Bash(git grep:*)
---

# Diagnose

Find the first place the system went wrong, prove it with runtime evidence, and fix it there. Every shipped line traces to evidence. A change that "might help" is a hypothesis, not a fix, and it does not ship.

The whole method rests on one thing: a **tight feedback loop that goes red on this bug**. With one, bisection, hypothesis testing, and instrumentation are mechanical. Without one, reading code produces theories, not diagnoses.

## Invocation

- **By the user (`/diagnose …`):** treat the arguments as the bug report or issue reference. Add `mode=diagnose-only` to stop at a cited diagnosis with no fix.
- **By another skill:** the caller supplies the report and usually the mode. Follow the caller's rules for commits and branches. Never wait on the human: where this skill says "show the user", put it in the report and keep going. Stop only with a verdict (see **Report**): **NOT REPRODUCED** at the Phase 1 gate, **INCONCLUSIVE** when no hypothesis survives, or **DIAGNOSED** when the fix needs a decision only a human can make. Return the report so the caller can label the issue and move on. A loop that needs a human (`hitl-loop.sh`) can't run here, so it counts as no loop: report **NOT REPRODUCED** and include the prepared script for a person to run.

Modes:

- **fix** (default): all phases, with the fix handed to the `tdd` skill.
- **diagnose-only**: Phases 0–5, then report. Use this for "why is this happening", live symptoms (leaks, spinning CPU), or when the user asked for no fix.

## Phase 0: Orient and redact

- Read `GLOSSARY.md` (if present) and the ADRs in the affected area.
- Write down the **user's exact symptom**: error text, wrong value, timing, and the surface it appeared on (HTTP route, CLI command, UI screen, queue job). Later phases verify against this, not against a nearby failure.
- **Redact every secret** in anything you show: commands, outputs, captured requests. Write `<REDACTED>` in its place, read credentials from environment variables in your scripts, and quote only the lines of an artifact that carry the signal. If redacted output is not enough to diagnose, say so.
- **Pick the environment.** Loops, probes, repeat runs, fuzzing and bisection run only against local or test environments. Read-only checks on a shared or staging system need the user's OK first. **Never write to production**, and never run a loop there. If the bug only shows in production, ask for a redacted artifact or for permission to add read-only instrumentation, as in the Phase 1 stop. Prefer a test database for loops that write data, or reset state between runs, so repeat runs don't pile up junk.
- **Make a scratch folder outside the repo** (`mktemp -d`). Every loop script, harness, replay file and captured artifact goes there. Nothing in it can be committed by accident, and it survives `git bisect` checkouts. Only code changes and tagged instrumentation go in the repo.

## Phase 1: Build the feedback loop

Spend disproportionate effort here. Be creative and do not give up early. Work down the ladder in [references/feedback-loops.md](references/feedback-loops.md), cheapest rung first. Give every rung that fits this bug one serious try. Skip rungs that can't apply, with a one-line reason each. That's what "working the ladder" means below. Reproduce it **yourself, on the surface where the user saw it**, before asking anyone for anything.

Once you have *a* loop, tighten it (faster, sharper assertion, deterministic). For non-deterministic bugs, aim for a higher reproduction rate rather than a clean repro.

**Gate: no loop, no hypotheses.** Phase 1 is done when you can name **one command** you have **already run** (show it and its redacted output) that is:

- [ ] **Red-capable:** it drives the real bug path and asserts the user's exact symptom, so it can go red on this bug and green once it is fixed. "Runs without erroring" does not count. For a **performance bug**, it asserts a threshold (time, query count, memory) set from a measured baseline. Run it several times, and set the threshold clear of the variance you saw.
- [ ] **Deterministic:** the same verdict every run, or a pinned, high reproduction rate for flaky bugs. For a performance loop, the same verdict across several runs.
- [ ] **Fast:** seconds, not minutes.
- [ ] **Agent-runnable:** unattended, or with a human driven only through this skill's `scripts/hitl-loop.sh`. You prepare that script, but the user runs it with `! bash <path>`, because it reads from the keyboard. Only when the user invoked this skill directly (see Invocation).

If you catch yourself reading code to build a theory before this command exists, stop. That is the exact failure this skill prevents.

**If you cannot build a loop** after working the ladder: stop and report **NOT REPRODUCED**. List each rung you tried and why it failed. Ask for exactly what would unblock it: access to the environment that reproduces it, a redacted artifact (HAR file, log dump, core dump, timestamped recording), or permission to add temporary instrumentation where it happens.

**If it "used to work"** and you can name a good state and a bad state (commit, version, dataset), run `git bisect run <loop-command>` now, before forming theories. Bisection with a red-capable loop often hands you the cause outright. Bisect checks out old commits in the working tree, so:

- The tree must be clean (`git status --porcelain` prints nothing). If it isn't, stop and ask. Never stash or discard someone's work.
- The loop script lives in the scratch folder, not the repo, so checkouts can't remove or change it.
- The script exits `125` when a commit can't be tested (it doesn't build, or setup fails), so bisect skips it instead of blaming it.
- Old commits may run old migrations or setup code. Point the loop at a test database, never a shared one.
- Always finish with `git bisect reset`, even when bisect fails or you stop early. Check with `git status` that the repo is back on its branch.

## Phase 2: Reproduce and minimise

Run the loop and watch it go red. Confirm:

- [ ] It shows the failure the **user** described, not a different failure nearby. Wrong bug means wrong fix.
- [ ] It reproduces across runs, or at a debuggable rate.
- [ ] You captured the exact symptom output for later comparison.

Then **minimise**: cut inputs, callers, config, data, and steps **one at a time**, rerunning the loop after each cut, and keep only what makes it fail. You are done when every remaining element is load-bearing, meaning removing any one of them turns the loop green. The minimised repro shrinks the hypothesis space and becomes the seed of the regression test.

## Phase 3: Hypothesise

Generate **3–5 ranked hypotheses** before testing any of them. A single hypothesis anchors on the first plausible idea.

Seed them cheaply:

- `git log -p --since=<window> -- <suspect paths>` and `git blame` on the lines the loop implicates.
- Linked issues or PRs mentioned in those commits.
- Recent dependency, config, or schema changes.
- Persisted state, when the bug appears only after a restart or deploy: config files, caches, lock files, serialized state, migrations.

Each hypothesis must be **falsifiable**:

> If **X** is the cause, then changing **Y** will make the bug disappear, and changing **Z** will make it worse.

If you cannot state the prediction, the hypothesis is a vibe. Sharpen it or drop it.

Show the ranked list to the user (or put it in the report when invoked by a skill). Users often re-rank instantly ("we deployed a change to #3 yesterday"). Do not wait for a reply. Proceed with your ranking.

## Phase 4: Probe

Choose each probe by **how much of the remaining hypothesis space it eliminates**, not just by which hypothesis is ranked first. A probe that splits three hypotheses beats one that confirms or kills a single one.

- Each probe maps to a specific prediction from Phase 3. Change **one variable at a time**.
- Prefer a debugger or REPL over logs. Use targeted logs at the boundaries that distinguish hypotheses. Never "log everything and grep".
- **Tag every debug change** with one unique prefix for this session (for example `[DEBUG-a4f2]`), so cleanup is a single grep. That covers log lines, dumps, temporary assertions, and injected sleeps or delays (tag those in a comment).
- **Performance bugs:** measure, don't log. Capture a baseline with a timing harness, profiler, or query plan, then bisect against it.
- **Revert what refuted hypotheses motivated.** When evidence kills a hypothesis, remove every change you made because of it before moving on.
- When verification fails or a result looks too easy, suspect the observation method (stale build, cached response, wrong environment, wrong process) before the system.

Stack-specific tools are in [references/instrumentation.md](references/instrumentation.md).

## Phase 5: Root-cause gate

Do not start a fix until all of these are true:

- [ ] **Mechanism confirmed** by runtime evidence: a probe whose result only the surviving hypothesis predicts. A plausible reading of the source does not count.
- [ ] **Legitimacy question answered:** is the state that triggered the symptom one the system may legitimately be in? See [references/root-cause.md](references/root-cause.md).
  - **Yes:** the code that broke on it is the root cause. Handling the state there is the fix.
  - **No:** a check where it broke would hide the bug. Trace back to what produced the state and fix that.
- [ ] **Pattern sweep done:** search for other places with the same fault (same call shape, same assumption, same copy-pasted block). List them. Fix them in this change when they are the same root cause, otherwise list them as follow-ups.
- [ ] **Refuted-hypothesis changes reverted.**
- [ ] **Instrumentation removed:** `git grep -n --untracked 'DEBUG-<prefix>'` returns nothing, and `git status` shows no changes of yours left in the repo. Do this before the fix, because `tdd` commits as it goes and would commit any debug line left in a file it touches. The loop command lives in the scratch folder and still works without the debug lines.

In **diagnose-only** mode, stop here and write the report.

## Phase 6: Fix through tdd

Invoke the **`tdd`** skill in **bug mode**, passing:

- the minimised repro as the seed for the regression test,
- the root cause and the place the fix belongs,
- the pattern-sweep sites that are in scope,
- the Phase 1 loop command, which serves as tdd's fallback check when no good test seam exists,
- the caller's test baseline, if it gave one. Phase 5 left the tree as it was, so tdd can use it instead of running its own.

**The correct-seam rule:** a regression test is only worth writing at a seam where it exercises the real bug pattern as it occurs at the call site. If the only seams available are too shallow (a single-caller unit test for a bug that needs a chain of callers), say so. **A missing seam is itself a finding:** the architecture is preventing this bug from being locked down. Record it in the report, and let tdd use the loop command as the before/after evidence instead.

Ship the smallest change the evidence justifies. No belt-and-suspenders additions "just in case".

## Phase 7: Verify and clean up

- [ ] **Rerun the original, un-minimised Phase 1 loop** on the surface where the user saw the bug. It must be green. "Inconclusive" or a different surface is not a pass, so flag it. Unit tests show branch behavior, not that the bug is gone.
- [ ] tdd's regression test and relevant test set pass (or the missing seam is documented).
- [ ] Still no instrumentation: `git grep -n --untracked 'DEBUG-<prefix>'` returns nothing. (It was removed in Phase 5. Check again in case a later probe added some.)
- [ ] Anything started through the project's verification skill is torn down with that skill's Cleanup.
- [ ] The scratch folder deleted, or its path given to the user if they want to keep the harnesses.
- [ ] No bisect in progress (`git status` doesn't mention bisecting).
- [ ] The confirmed hypothesis and the root cause are stated in the commit or PR message, so the next person debugging here learns from it.

## Report

Lead with a verdict:

- **FIXED:** root cause confirmed and fixed, original loop green.
- **DIAGNOSED:** root cause confirmed, no fix (diagnose-only mode, or the fix needs a decision the user must make).
- **NOT REPRODUCED:** no red-capable loop. Include the rungs tried and what is needed to unblock.
- **INCONCLUSIVE:** a loop exists but no hypothesis survived. Include what was eliminated and the next probes worth trying.

Then include, all redacted:

- **Symptom** as reported, and the **loop command** with its red output (and green output if fixed).
- **Minimised repro.**
- **Hypotheses:** each one, its prediction, and the evidence that killed or confirmed it.
- **Root cause:** the mechanism, file and symbol, and the answer to the legitimacy question.
- **Pattern sweep:** other sites found, which ones were fixed, which are follow-ups.
- **Fix and tdd evidence** (fix mode), or the missing-seam finding.
- **Always-on signal:** if the deciding fact took a deep dig to find, propose the cheap, permanent signal (a log line, an assertion, a metric, a better error message) that would have shown it at first glance.

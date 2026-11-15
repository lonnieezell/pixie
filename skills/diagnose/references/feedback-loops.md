# Building and tightening a feedback loop

Build the right loop and the bug is mostly fixed. Work down this ladder, cheapest rung first, and keep going until one fits.

## The ladder

1. **Failing test** at whatever seam reaches the bug: unit, integration, or end-to-end.
2. **Curl or HTTP script** against a running dev server, asserting on status, body, or headers.
3. **CLI invocation** with a fixture input, diffing stdout against a known-good snapshot.
4. **Headless browser script** (Playwright or Puppeteer) that drives the UI and asserts on the DOM, console, or network.
5. **Replay a captured trace.** Save a real request, payload, or event log to disk and replay it through the code path in isolation.
6. **Throwaway harness.** Spin up the smallest subset of the system (one service, boundary dependencies faked) that reaches the bug path with a single call.
7. **Property or fuzz loop.** For "sometimes wrong output", run 1000 random inputs and look for the failure mode.
8. **Bisection harness.** When the bug appeared between two known states (commit, dataset, version), automate "set up state X, check, repeat" so `git bisect run` can drive it.
9. **Differential loop.** Run the same input through the old and new version (or two configs) and diff the outputs.
10. **Human-in-the-loop script.** Last resort, when a person must click or look, and only when the user invoked the skill directly. Copy `scripts/hitl-loop.sh` from this skill's folder into the scratch folder, and edit the steps. Then ask the user to run it with `! bash <path>`, since your Bash tool can't answer its prompts. The human follows a structured script and their observations come back as `KEY=VALUE` lines you can read.

## Tighten it

Treat the loop as a product. Once you have one, ask:

- **Faster?** Cache setup, skip unrelated initialisation, narrow the scope, run only the one test or route.
- **Sharper?** Assert on the specific symptom (the exact error text, the wrong value), not "didn't crash".
- **Deterministic?** Pin the clock, seed randomness, isolate the filesystem, freeze or fake the network, fix ordering.

A 30-second flaky loop is barely better than none. A 2-second deterministic one is a superpower.

## Performance loops

A slowdown has no exact symptom to assert, so assert a threshold:

1. Pick the measure that shows the problem: wall time, query count, memory, or allocations. Query count and allocations are steadier than time, so prefer them when they show the problem.
2. Run the loop several times on the bad state and note the spread.
3. Set the threshold between the good and bad numbers, clear of the spread on both sides. The loop fails above it.

Green means under the threshold on every one of several runs, not just one.

## Non-deterministic bugs

The goal is a **higher reproduction rate**, not a clean repro. A bug that shows up 50% of the time is debuggable. One that shows up 1% of the time is not.

- Run the trigger 100 times in a loop and count failures.
- Parallelise it, or add load and stress.
- Narrow the timing window: inject sleeps or delays at suspected race points. Tag each one with the session's debug prefix, so cleanup removes it.
- Shrink resources (fewer workers, a smaller pool, lower timeouts) to make contention likelier.

Keep raising the rate until the bug is debuggable, then pin the configuration that produces it so every later run uses the same rate.

## Completion check

The loop is ready when it is red-capable, deterministic (or at a pinned high rate), fast, and agent-runnable, and you have already run it once. See the Phase 1 gate in `SKILL.md`.

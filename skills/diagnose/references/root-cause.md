# Root cause, not symptom

The **symptom** is where a wrong state became visible. The **root cause** is the first place the system did something it should not have done, or failed to handle a state it should handle. Fix the root cause.

A symptom fix hides the evidence and leaves the fault free to surface somewhere else. Each one makes the system harder to reason about, because the code now carries a workaround for a bug nobody named.

## Walk back with "why"

From the symptom, ask "why did this happen?" at each step until the answer is a **wrong decision in the code**, not a consequence of an earlier one. When the chain goes dark, instrument and read the actual state. Do not guess.

## The legitimacy test

Ask: **is the state that triggered the symptom one the system may legitimately be in?**

- **Yes, the state is legitimate** (an empty cart, a user with no profile, a network timeout, a missing optional field). The code that broke on it is the root cause, and handling the state there is the fix.
- **No, the state should never exist** (an order with a negative total, a session pointing at a deleted user). A check where it broke only hides the bug. Trace back to whatever produced the state, and fix that.

## The usual ways bugs get hidden

When reviewing your own fix, or code near the bug, watch for these. Each one is acceptable only when the state it handles is legitimate:

- guards and early returns (`if (!x) return;`),
- retries,
- swallowed errors (`catch {}`, `@` suppression in PHP, `.ok()` or `unwrap_or_default()` in Rust),
- clamped or defaulted values,
- state that is silently discarded or reset.

## Other rules

- **Restart-only bugs:** if something fails only after a restart or deploy, suspect persisted state first: config files, caches (including compiled views, routes, and opcache), lock files, serialized state, and pending migrations.
- **Fix the pattern, not the instance.** Search for every place with the same fault (the same call shape, the same assumption, the same copied block) and fix them all, or list them as follow-ups when they need separate decisions.
- **Paragraph-long justifications are a smell.** If a workaround needs a long comment to explain why it is there, the code is wrong. Fix the code, not the comment.
- **Propose the always-on signal.** If the deciding fact took a deep dig to find, suggest the cheap, permanent signal (a log line, an assertion, a metric, a clearer error message) that would have shown it immediately.

# How to fix a bug

This guide shows you how to fix a bug with Pixie. You pick one of two skills, based on one question: do you already know what causes the bug?

| You know... | Use | Why |
|---|---|---|
| The cause. You can point at the wrong line or rule. | `tdd` in bug mode | It writes a regression test that fails, then fixes the code. |
| Only the symptom. Something is wrong, but you don't know why. | `diagnose` | It proves the cause before it changes any code, then hands the fix to `tdd`. |

If you're not sure, use `diagnose`. It costs more time, but it won't ship a guess.

## Fix a bug with a known cause

Run `tdd` with `mode=bug` and describe the bug. Include the issue number if there is one:

```text
/pixie:tdd mode=bug #142 the cart total ignores item quantity
```

Claude will:

1. Find the tests related to the code it will touch, and run them for a baseline.
2. Write one regression test. With an issue number, the test name starts with the issue, such as `issue_142_...`.
3. Run the test and check that it fails for the reason it predicted.
4. Fix the code with the smallest change that passes, then run the related tests again.
5. Commit the test and the fix together. The commit body includes the failing output.

If you're on the default branch, Claude asks before the first commit. Answer that you want a new branch, unless you mean to commit there.

## Find and fix a bug with an unknown cause

Run `diagnose` with the bug report or an issue reference:

```text
/pixie:diagnose checkout total is wrong when a coupon is applied
```

Claude will:

1. Build a feedback loop. This is one fast command that fails on this bug. Claude shows you the command and its failing output.
2. Shrink the repro to the smallest case that still fails.
3. Test three to five ranked guesses about the cause, and confirm one with runtime evidence.
4. Remove all its debug code.
5. Hand the fix to `tdd`, which writes the regression test and the fix.
6. Re-run the original loop to prove the bug is gone.

It ends with a verdict:

- **FIXED:** cause confirmed and fixed.
- **DIAGNOSED:** cause confirmed, but no fix. This happens in `mode=diagnose-only`, or when the fix needs your decision.
- **NOT REPRODUCED:** Claude couldn't build a failing loop. The report says what it tried and what it needs from you, such as a log file or access to an environment.
- **INCONCLUSIVE:** a loop exists, but no guess held up. The report lists what it ruled out.

### Only find the cause

To get the cause without a fix, add `mode=diagnose-only`:

```text
/pixie:diagnose mode=diagnose-only why does memory grow during the nightly import
```

### If the bug only happens on a shared server

`diagnose` runs its loops only on local or test environments. It asks before any read-only check on a shared or staging system. It never writes to production. If the bug only shows in production, expect it to ask you for a redacted artifact, such as a log dump or a HAR file.

## Hand a bug to an agent instead

If the bug is already a GitHub issue, you can let `tackle` choose for you. Add the `ready-for-agent` label and run:

```text
/pixie:tackle 142
```

`tackle` rates the issue. It sends bugs with an unknown cause to `diagnose`, and everything else to `tdd`. Then it reviews the change and opens a PR. See the [tutorial](../tutorial/first-issue-to-pr.md) for a full run.

## Related

- [`diagnose` reference](../reference/skills.md#diagnose)
- [`tdd` reference](../reference/skills.md#tdd)

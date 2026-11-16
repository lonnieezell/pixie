# Orca checkpoints

Read this only when the detection in `SKILL.md` printed `orca: on`. Orca is optional. **A missing or failing `orca` must never stop or slow the run.**

Read the saved JSON at the path the detection printed. Any existing comment may hold context the user wrote (a goal, constraints). Keep the lines that are still valid and carry them into your checkpoints rather than overwriting them.

**Posting a checkpoint:**
```bash
orca worktree set --worktree active --workspace-status STATUS \
  --comment "FIRST LINE
goal: resolve #N TITLE" --json >/dev/null 2>&1 || true
```
Leave out `--workspace-status` when the status isn't changing. If a checkpoint fails, carry on and don't retry.

**How to write the comment:**
- The first line says what just happened, where, and what's next, e.g. `confirmed root cause in OrderTotals::apply (app/Billing/OrderTotals.php); writing regression test`.
- Then add a `goal:` line plus any user lines you're keeping.
- Keep it to a few lines. It's a status snapshot, not a log.

**The checkpoints:**

| When | Status | First line |
|---|---|---|
| Claimed (step 2) | `in-progress` | `claimed #N; classifying` |
| Classified (step 3) | — | `tier T (difficulty, RISK risk), route ROUTE; starting fix` or `…; starting TDD` |
| Root cause confirmed or ruled out (diagnose route) | — | `confirmed/refuted: HYPOTHESIS (FILE); next step` |
| Moving from fix to verification, or after each meaningful TDD slice | — | `SLICE DONE (FILES); next: NEXT SLICE or review` |
| Lint done, entering review (step 5) | `in-review` | `implementation complete, tests green; running simplify, then code review (EFFORT)` |
| Code review complete | — | `code review: X fixed, Y not changed; final checks` (or `running security review` for `high` risk) |
| Security review complete (`high` risk) | — | `security review: RESULT; final checks` |
| PR opened (step 6) | `completed` | `opened PR #M for #N; ready for human review` |
| Stopped early | `completed` | `blocked: REASON; needs WHAT` |

The status shows where the agent is, not where the issue is. `in-review` covers the agent's own review phase (lint is done and simplify, code review and security review are running). `completed` means the agent has gone as far as it can, whether that ended in a PR or a blocker a human needs to see. The comment's first line says which one.

If review findings send the work back into code changes, keep the status at `in-review`. Fixing review findings is part of the review phase.

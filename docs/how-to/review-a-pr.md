# How to review someone else's pull request

This guide shows you how to have Claude review a teammate's pull request with `vet`, check its draft, and post it as one GitHub review.

`vet` is built to catch what an ordinary read of the diff misses:

- code that should have changed but didn't, such as a second implementation of an interface or a caller of a changed function
- new tests that pass even without the change, so they don't test it
- existing tests that were quietly weakened
- gaps between what the linked issue asked for and what the code does

Every finding is checked by a separate agent that tries to prove it wrong. Nothing is posted until you approve the exact text.

`vet` only runs when you type it, and it only works interactively.

## Before you start

- `gh` is installed and signed in. Check with `gh auth status`.
- You're in a local clone of the repo the PR belongs to.
- Your working tree is clean. `vet` checks out the PR's code, so it stops if you have uncommitted changes. It never stashes or discards your work.

## 1. Start the review

Pass the PR number:

```text
/pixie:vet 142
```

Or its URL, as long as it's a PR in this repo:

```text
/pixie:vet https://github.com/acme/shop/pull/142
```

Claude reads the PR, its linked issues, CI results and existing review comments. Then it works through the review on its own, and stops only to ask you the questions in step 2.

## 2. Answer its questions

Claude asks only when the answer is yours to give. You may see none of these, or several:

| Question | When | Why it asks |
|---|---|---|
| Run this PR's code? | The PR comes from a fork, and its author isn't a collaborator | Building the PR and running its tests runs a stranger's code on your machine. If you say no, Claude reviews the code without running it, and says so in the review. |
| Continue even though the PR changes Claude config? | The PR changes a `CLAUDE.md` or `AGENTS.md` file, something under `.claude/`, `.mcp.json`, or `.envrc` | Claude reads these files while it works, so a PR could change how your session behaves once it's checked out. Say no unless you've read those changes. |
| Install dependencies? | The PR changes the lockfile | Installing can run the packages' own scripts. |
| Prove the blocking findings? | Claude confirmed a high or critical finding | Claude writes a test that fails on the PR's code, so the comment comes with proof. It costs extra time and tokens, so it asks first. |

## 3. Read the draft

Claude shows you the whole review before anything goes to GitHub: a suggested verdict, the review body, and every inline comment with its file and line. Findings are grouped by how much they matter:

| Group | What it holds |
|---|---|
| **Blocking** | Confirmed high or critical bugs and security flaws, and acceptance criteria from the issue that the PR doesn't meet |
| **Should fix** | Confirmed medium problems, new tests that pass without the change, and untested code paths that handle money, auth, deletion or data integrity |
| **Question** | Things that depend on intent Claude can't see: unexplained extra changes, weakened tests with no stated reason, and findings the checker couldn't settle |
| **Nit** | Small confirmed problems, three at most |

The review body ends with a **Coverage** line saying what Claude checked and what it didn't, such as "PR code not run (fork)". Read it before you post: a clean review with a long "not checked" list is not the same as a clean review.

The suggested verdict is **Request changes** when anything is Blocking, **Comment** when there are Should fix items or Questions, and **Approve** otherwise.

## 4. Post, edit, or hold it back

Pick one:

- **Post with the suggested verdict.** Not offered on your own PR, because GitHub only lets you comment there.
- **Post as Comment only.** The findings are posted, but the review doesn't approve or block the PR.
- **Edit first.** Tell Claude what to change, such as "drop the second nit" or "soften the wording on the migration comment". It updates the draft and asks again.
- **Don't post.** The draft stays on disk for you to use however you like.

When you post, everything goes up as **one** review, so the author gets one notification. Comments on lines the PR didn't change, such as a caller it missed, go in the review body.

If the author pushes new commits while Claude is reviewing, Claude stops before posting and tells you. The line numbers may no longer match, so run `vet` again on the new commits.

## 5. Afterwards

Claude puts you back on the branch you started on, and removes the temporary copies of the code it made. It does this even if the run stops early.

The run's files stay in `ai/vet/pr-<number>-<date>-<time>/`. The draft review is `review.md` in that folder. `vet` adds `ai/` to `.git/info/exclude`, so none of it gets committed.

## If something goes wrong

| What you see | What to do |
|---|---|
| It stops because the working tree isn't clean | Commit or stash your changes yourself, then run it again. |
| It stops because the URL is from another repo | `cd` into a clone of that repo and run it there. |
| The Coverage line says the base-branch test check wasn't done | Claude couldn't run the repo's tests against the base branch, usually because of missing dependencies or setup. Check the new tests by hand: do they fail if you undo the change? |
| It stops because the PR's head moved | The author pushed during the review. Run `vet` again. |
| You didn't want it to post something it posted | Edit or delete the review comments on GitHub. Next time, use **Edit first**. |

## Related

- [`vet` reference](../reference/skills.md#vet)
- [Agents and the code-health hook](../reference/agents-and-hook.md), for the agents `vet` uses
- [Labels, branches, and files](../reference/labels-and-branches.md)

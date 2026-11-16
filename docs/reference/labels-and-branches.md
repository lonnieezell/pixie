# Labels, branches, and files

Everything Pixie adds to a repo or to GitHub: labels, branch names, commit formats, and files. Use this page to tell what a skill left behind, or to clean it up.

## GitHub labels

`tackle` uses four labels to track an issue's progress, and `checkup` and `catch` add a fifth, `needs-triage`, to the issues they file. It creates any that are missing, without changing labels you already made.

Each label below is a **role**. By default, a role's label is its name. To use different names in a repo, map them in `docs/agents/pixie-labels.md`. `/pixie:setup` writes that file for you. See [Set up a repo for Pixie](../how-to/set-up-a-repo.md).

| Role | Meaning | Who adds it | Who removes it |
|---|---|---|---|
| `needs-triage` | Filed by an agent. A human decides whether it's real. | `checkup` and `catch`, on every issue they file | You, when you triage it. Auto-fix swaps it for `ready-for-agent`. `plan-task`, when it plans from the issue. |
| `ready-for-agent` | Queued for an agent | You, `checkup` or `catch` auto-fix, or `plan-task`, `poke` or `prune-tests` when filing issues if you say yes | `tackle`, when it claims the issue |
| `agent-working` | An agent has claimed the issue | `tackle` | `tackle`, when it opens a PR or stops |
| `agent-pr` | A PR is open for the issue | `tackle` | No one. The issue closes when the PR merges. |
| `agent-blocked` | An agent stopped and needs a human. Its comment says why. | `tackle` | You, after you handle it |

`tackle` only offers issues labeled `ready-for-agent`. You can still name another issue directly, and it asks whether to go ahead.

`checkup` and `catch` also add plain labels that aren't roles: `bug`, `checkup` or `catch`, `security` or `performance`, and `severity:high` or `severity:critical`. They create any that are missing, with GitHub's default color.

If an issue has had `agent-working` for more than 24 hours, the run was probably interrupted. `tackle` asks whether to take it over.

### Label map

`tackle`, `plan-task`, `poke`, `prune-tests`, `checkup` and `catch` read `docs/agents/pixie-labels.md` if it exists. For each role, they use the label in its "Label in this repo" column. If the file is missing, they use the role names.

Labels created by `setup` get these colors. Labels created by `tackle` or `plan-task` get GitHub's default color.

| Role | Color |
|---|---|
| `needs-triage` | `#D4C5F9` (lavender) |
| `ready-for-agent` | `#0E8A16` (green) |
| `agent-working` | `#FBCA04` (yellow) |
| `agent-pr` | `#1D76DB` (blue) |
| `agent-blocked` | `#D93F0B` (red) |

## Branches

| Branch | Created by | When |
|---|---|---|
| `agent/<issue>-<short-slug>` | `tackle` | Always. It branches from the remote default branch. |
| `untangle/<short-slug>` | `untangle` | Only if you start on the default branch |
| `prune-tests/<area>` | `prune-tests` | Always. It branches from the remote default branch, and stops if the branch already exists. |
| `checkup/baseline` | `checkup` | Whole-repo runs, when it publishes the baseline. Rebuilt from the default branch each time and force-pushed with a lease. This is the only branch any Pixie skill force-pushes. |

`tdd` and `diagnose` create no branches. When you run `tdd` on the default branch, it asks before its first commit.

`babysit` checks out each PR's branch in turn. When it's done, it returns you to the branch you started on.

Pushes and PRs:

- `tackle` pushes its branch and opens a PR.
- `prune-tests` pushes and opens a PR in unattended mode. In attended mode it offers to, and does only if you say yes.
- `maintain-verifier` opens at most one PR per run.
- `checkup` opens or updates one rolling baseline PR. It never pushes code.
- `babysit` pushes fixes to existing PR branches. It never opens a PR.
- `untangle`, `tdd`, and `diagnose` never push.

## Commit messages

| Skill | Format |
|---|---|
| `tackle` | Conventional commits that reference the issue, such as `fix(#142): ...` or `feat(#142): ...`. The PR title uses the same format. |
| `tdd` | Your repo's convention, or the caller's format. One commit per slice. The body includes the failing test output. |
| `untangle` | `untangle: <what changed> in <file>`, one per green step |
| `prune-tests` | Your repo's convention, or `test(<area>): ...`. One commit per group of removed tests, listing the tests and the reason. A tool it installs gets its own commit first. |
| `babysit` | Your repo's convention. One commit per fix. |
| `checkup` | `chore(checkup): update baseline for DATE`, one per run, on `checkup/baseline` |

## Issue and PR comments

| Skill | Posts |
|---|---|
| `plan-task` | Creates the issue, or writes the plan into the source issue if you planned from one and chose to update it. Adds `ready-for-agent` only if you say yes. No other labels, assignees, or milestones unless you ask. When planning from an existing issue, removes `needs-triage` from that issue. |
| `tackle` | A claim comment, a tier comment such as `Tier 2 (medium, normal risk), route implement: ...`, and a comment saying why if it stops |
| `babysit` | A reply on every review-bot thread it handles: `Fixed in <sha>: ...`, `Not changing: ...`, or a note that it's deferred to maintainers |
| `poke` | Issues for the findings you pick, one per finding |
| `vet` | One review on the PR, with inline comments, only after you approve its exact text. The verdict is the one you pick: Comment, Request changes or Approve. |
| `prune-tests` | Issues for the tests that need a human, if you say yes. Attended mode only. |
| `checkup`, `catch` | Issues for confirmed high and critical findings, or private draft security advisories. A "still present" comment on an open issue, at most once a week. A "queued for auto-fix" comment when auto-fix promotes an issue. Each one starts with an AI-generated notice. |

## Files and folders

| Path | Created by | In git? |
|---|---|---|
| `.claude/skills/verify-<app>/` | `create-verifier`, edited by `maintain-verifier` | Yes. Commit it. |
| `ai/poke/<date>-<section>.md` and a screenshot folder beside it | `poke` | No. `poke` adds `ai/` to `.gitignore`. |
| `.prune/<area>/` | `prune-tests` | No. It's added to `.git/info/exclude`. Delete it when you're done. |
| `docs/agents/pixie-labels.md` | `setup`, or you | Yes. Commit it so everyone uses the same labels. |
| `docs/agents/design-system.md` | `design-setup`. You edit its `Annotations` and `Rubric overrides` sections. | Yes. Commit it so design work reuses the same components. |
| `docs/design/critiques/<date>-<slug>.md` and a screenshot folder beside it | `design-critique` | The report, yes. The screenshots too, unless you said yes to gitignoring them. Then `docs/design/critiques/*/` is in `.gitignore`. |
| `docs/agents/checkup.json` | You | Yes. Settings for `checkup` and `catch`. |
| `docs/agents/pixie.json` | You | Yes. Turns live checks off per skill. See [Live checks](live-checks.md). |
| `docs/agents/checkup-baseline.json` | `checkup`, through the baseline PR | Yes, once you merge the PR |
| `ai/checkup/DATE-HHMM/`, `ai/catch/DATE-HHMM/` | `checkup`, `catch` | No. They add `ai/` to `.git/info/exclude`. |
| `ai/vet/pr-<number>-<date>-<time>/` | `vet` | No. It adds `ai/` to `.git/info/exclude`. |
| `.kimun.toml` | You, with `km init` (or `setup` runs it if you say yes) | Your choice. Commit it to share thresholds. |
| `.code-health-off` | You | Your choice. It turns off the edit hook for the repo. |

`diagnose`, `tdd`, `tackle`, and `plan-task` keep scratch files in a temporary folder outside your repo. `vet` also makes a temporary worktree of the base branch outside your repo, and removes it when it finishes.

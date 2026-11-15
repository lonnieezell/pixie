---
name: setup
description: Set up a repo for Pixie. Checks that gh and km are ready, maps Pixie's four workflow labels to the names this repo uses, creates any that are missing, and offers km init and a verification skill. Optional. Every skill works with the defaults without it.
disable-model-invocation: true
allowed-tools: Bash(git remote:*), Bash(gh auth status), Bash(gh repo view:*), Bash(gh label list:*), Bash(km --version)
---

# Setup

Set up the current repo for Pixie. This is optional: with no setup, every skill uses the default labels. Run it when the repo already has its own workflow labels, or to check that everything is ready.

It writes one file, `docs/agents/pixie-labels.md`. Commit it so everyone's agents use the same labels.

Explore first, show what you found, confirm, then write. Ask one question at a time, with the recommended answer first.

## 1. Explore

Read the current state. Don't assume.

- `git remote -v`: is this a GitHub repo? If it isn't, say the label steps need GitHub and skip to step 4.
- `gh auth status`: is `gh` signed in?
- `gh repo view --json nameWithOwner,viewerPermission`: which repo, and can you create labels? That needs `WRITE`, `MAINTAIN` or `ADMIN`.
- `gh label list --json name,description --limit 200`: the labels the repo already has.
- `docs/agents/pixie-labels.md`: does an earlier run's file exist? If so, read its mapping.
- `km --version`: is km on the PATH?
- `.kimun.toml` at the repo root.
- `.claude/skills/verify-*/`: is there already a verification skill?

## 2. Report prerequisites

List what's ready and what's missing. For each missing item, give the fix. Don't install anything yourself.

- `gh` missing or signed out: install it, then run `gh auth login`. Without it, skip steps 3 and 4.
- No write permission: say so. You can still write the file, but you can't create labels.
- `km` missing: run `cargo install kimun` and make sure `~/.cargo/bin` is on the PATH Claude Code sees. `code-health` and `untangle` need it. Setup goes on without it.

## 3. Choose labels

Ask exactly one question:

> Keep Pixie's default labels? (recommended: **yes**)

On a rerun, show the current mapping from `docs/agents/pixie-labels.md` and ask whether to keep it instead.

The defaults are in [pixie-labels.md](pixie-labels.md). Each role's label equals its name.

If the repo already has labels that look like they fill a role (for example `in progress` for `agent-working`), name them in the question, so the user can map to them instead of adding duplicates.

On **no**, ask for each role's label. Every role needs its own label. Two roles can't share one, or `tackle` can't tell the states apart.

## 4. Confirm and write

1. Show the draft of `docs/agents/pixie-labels.md`, built from [pixie-labels.md](pixie-labels.md) with the chosen labels in the second column. Let the user edit it.
2. Write it. Create `docs/agents/` if needed. On a rerun, overwrite the file.
3. If `gh` is ready and you have write permission, create each chosen label the repo lacks. Quote names that contain spaces or colons:

   ```bash
   gh label create "LABEL" --color COLOR --description "MEANING"
   ```

   | Role | Color |
   |---|---|
   | `ready-for-agent` | `0E8A16` |
   | `agent-working` | `FBCA04` |
   | `agent-pr` | `1D76DB` |
   | `agent-blocked` | `D93F0B` |

   Use the meaning from the file as the description. Never pass `--force`: it overwrites colors and descriptions on labels the user already has.

4. If a rerun changed a mapping, the old label stays in GitHub and stays on any issues that have it. Say so, and list those issues with `gh issue list --label "OLD" --state open`. Don't relabel or delete anything.

## 5. Offer km init

If km is installed and there's no `.kimun.toml`, offer once: "Want me to run `km init`? It writes a `.kimun.toml` tuned to this repo, with thresholds and folders to skip." On yes, run it. On no, move on.

## 6. Offer a verification skill

If step 1 found no `verify-*` skill, offer once: "Want a verification skill, so agents can drive the app the way a user does and prove their changes work? I can make one with `/pixie:create-verifier`." On yes, run that skill. On no, move on.

## 7. Done

Tell the user:

- which files were written and which labels were created
- that `tackle`, `plan-task`, `poke` and `prune-tests` now read `docs/agents/pixie-labels.md`
- to commit `docs/agents/pixie-labels.md` (and `.kimun.toml`, if it was created)
- that they can edit the file directly later. Rerunning setup is only needed to create labels or check prerequisites again.

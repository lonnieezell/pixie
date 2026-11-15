# Set up a repo for Pixie

Use `/pixie:setup` when a repo already has its own workflow labels, or when you want to check that Pixie's tools are ready before you start. Setup is optional. Without it, every skill uses the default labels and works as usual.

Setup does four things:

- Checks that `gh` is signed in and `km` is on your PATH.
- Maps Pixie's four workflow labels to the names your repo uses, and saves the map in `docs/agents/pixie-labels.md`.
- Creates any of those labels the repo doesn't have yet.
- Offers to run `km init` and to make a verification skill, if the repo has neither.

## Before you start

- Open Claude Code in the repo you want to set up. It should have a GitHub remote.
- To create labels, you need write access to the GitHub repo. Without it, setup still writes the file but creates no labels.

## Run setup

1. Start setup:

   ```text
   /pixie:setup
   ```

2. Claude lists what's ready and what's missing. For anything missing, it tells you how to fix it. It doesn't install anything. A missing `km` doesn't stop setup. A missing or signed-out `gh` skips the label steps.

3. Claude asks whether to keep the default labels. If your repo has labels that look like they do the same job, Claude names them in the question.

   - Pick **yes** to use `ready-for-agent`, `agent-working`, `agent-pr` and `agent-blocked`.
   - Pick **no** to use your own names. Claude asks for a label for each role. Each role needs its own label, so `tackle` can tell the states apart.

4. Claude shows the draft of `docs/agents/pixie-labels.md`. Ask for changes, or approve it.

5. Claude writes the file and creates any labels the repo lacks, with a color and a description. It never changes labels you already have.

6. If you don't have a `.kimun.toml`, Claude offers to run `km init`. If you don't have a `verify-*` skill, it offers to run `/pixie:create-verifier`. Say yes or no to each one.

7. Commit the new file, so everyone's agents use the same labels:

   ```bash
   git add docs/agents/pixie-labels.md
   git commit -m "chore: add Pixie label map"
   ```

   Commit `.kimun.toml` too, if setup created it.

## Map to labels you already have

Say your repo already uses `status: queued` and `status: in progress`. Answer **no** at step 3, then give those names for `ready-for-agent` and `agent-working`. For the other two roles, give new names or keep the defaults.

The file then looks like this:

```markdown
| Role | Label in this repo | Meaning |
|---|---|---|
| `ready-for-agent` | `status: queued` | Queued for an agent |
| `agent-working` | `status: in progress` | An agent has claimed it |
| `agent-pr` | `agent-pr` | A PR is open for it |
| `agent-blocked` | `agent-blocked` | An agent stopped and needs a human. Its comment says why. |
```

From then on, `tackle` claims issues by swapping `status: queued` for `status: in progress`. When `plan-task`, `poke` and `prune-tests` offer to queue an issue, they use `status: queued`.

## Change a label later

Edit the "Label in this repo" column in `docs/agents/pixie-labels.md` and commit it. Then do one of these:

- Create the new label in GitHub yourself.
- Run `/pixie:setup` again. It creates missing labels and checks the tools again.
- Do nothing. `tackle` creates any missing label the next time it runs, without a color.

Changing the map doesn't rename anything in GitHub. The old label stays in the repo and on any issues that have it. Move those issues to the new label by hand. If you rerun setup, it lists the open issues that still have the old label.

## Undo setup

Delete `docs/agents/pixie-labels.md`. The skills go back to the default labels. Setup never deletes labels, so remove any you don't want in GitHub.

## Related

- [Labels, branches, and files](../reference/labels-and-branches.md) lists every label, its default color, and the files Pixie writes.
- [Skills reference: setup](../reference/skills.md#setup)

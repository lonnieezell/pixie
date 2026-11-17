---
name: design
description: Explore 2–4 design directions for one component, section or page of a React, Laravel Blade or CodeIgniter 4 app. Writes a text brief of directions on named axes and stops for approval, then builds each direction as a preview from the repo's catalogued components, gates and critiques the screenshots, lets the user pick or blend, deletes the losers, builds the winner into production code test-first from its state matrix, checks it for drift and writes a dated decision record.
disable-model-invocation: true
---

# Design

Explore distinct directions for one piece of UI, render them in the real app, and let the user choose with evidence in front of them. The run goes: brief, approval, previews, gates, critique, pick, clean up, converge, record. **Nothing is written to the repo until the user approves the brief.** The winner is then built into production code, with one behaviour test per state of its matrix, and checked against the screenshots the user approved.

Paths used below:
- `CRITIQUE` is `${CLAUDE_SKILL_DIR}/../design-critique`. Its `scripts/critique.py` (Python 3) runs the gates and builds the critics' folders, and its `scripts/capture.mjs` (Node) takes the screenshots. Its `references/rubric.md` is the rubric.
- `SETUP` is `${CLAUDE_SKILL_DIR}/../design-setup`. Its `references/preview-harness.md` describes previews, the state matrix, fixtures and temporary mode. Read it before step 4.

## 0. Inputs

The user names what to design (`/design the order list`, `/design the settings page`) and, optionally, asks for a wildcard. Settle the **size**:

| Size | Directions | Axes |
|---|---|---|
| A component or a section of a screen | 2 | 2 |
| A page | 3 | 3 |

The user can ask for more, up to 4 directions and 4 axes. Ask if the size isn't clear.

Make a run folder outside the repo with `mktemp -d "${TMPDIR:-/tmp}/pixie-design.XXXXXX"`, noted as `RUN`.

## 1. Inventory

**Missing `docs/agents/design-system.md`:** do a fast setup inline. Read `SETUP/SKILL.md` and follow its steps 1 to 6, with two cuts: skip the **Patterns** scan (write `Not scanned: run /pixie:design-setup to fill it.` under `## Patterns`), and from step 7 ask only offers 2 (Playwright) and 4 (preview harness), which this run needs. Tell the user `/pixie:design-setup` fills in the rest later.

**The file exists:** run the freshness check and refresh in `SETUP/SKILL.md` step 8 (its steps 1 to 6; skip its offers). A direction built on stale components can reuse one that's gone or miss one that's new.

Then read its `## Stack`, `## Tokens`, `## Components`, `## Layout shells`, `## Preview surface`, `## Launch fallback` and `## Rules`, and `liveVerify.design` in `docs/agents/pixie.json` (a missing file or key means `true`). A stack the harness doesn't cover (anything but React, Laravel Blade and CodeIgniter 4) can't be previewed: say so and stop.

## 2. Frame

Work out, from the code and by asking only what the code can't tell you:
- **Who** uses this screen, and the **task** they come to it for.
- **The data:** its real shapes, read from the types production passes (props, an API resource, a Blade component's `@props`, a view cell's properties). Note the ranges that matter: none, one, typical, too many, long text.
- **Neighbouring screens:** 1–2 that share this one's layout shell or link to it. Directions must sit well beside them.

Write these to `RUN/frame.md`, in a few lines each. The decision record's **Frame** section comes from it.

Then print a short summary of the frame, one line each for who, task, data and neighbours, so the user can stop the run or correct it before the brief is built on a wrong assumption:

```text
Frame for the order list:
- Who: warehouse staff, on a tablet at the packing desk
- Task: find the next order to pack and mark it packed
- Data: Order (id, customer, items[], status, placedAt); 0 to ~200 open orders, long customer names
- Neighbours: /orders/:id (order detail), /dashboard
```

Carry on to step 3 without waiting. If the user corrects the frame, update `RUN/frame.md` before writing the brief.

## 3. Direction brief (text only)

**Axes.** Name the design choices that matter most for this task, each as a spectrum with two named poles: `Density: compact ↔ roomy`, `Disclosure: everything at once ↔ progressive`, `Emphasis: data first ↔ action first`, `Navigation: in place ↔ separate page`. Pick axes the frame makes real trade-offs on, not cosmetic ones.

**Directions.** Each direction has:
- a short name (lowercase words, used in slugs: `dense-table`)
- its position on every axis
- the catalogued components it's built from, by their inventory names. Only `preferred` ones: never a `legacy` one.
- any new component it needs, each with why the catalogued ones don't fit
- a one-sentence trade-off: what it's good at, and what it gives up

Directions must differ on the axes: no two may sit at the same position on every axis, and each should be the clear best at something the frame cares about.

**Wildcard.** Only when the user asked for one. One extra direction that breaks a named house convention (a rule from `## Rules`, a layout shell, a catalogued pattern), labelled **Wildcard**, saying which convention it breaks and why that might pay off. Never add one on your own.

Print the brief:

```markdown
## Directions for the order list

Axes: **Density** (compact ↔ roomy), **Disclosure** (everything at once ↔ progressive)

### dense-table
- **Density:** compact. **Disclosure:** everything at once.
- **Built from:** `Table`, `Badge`, `Button` (ghost)
- **New:** none
- **Trade-off:** Fastest to scan many orders, but hard to read on a phone.

### card-stack
...
```

**Stop here for approval.** Ask with AskUserQuestion: approve the brief, or change it (an axis, a direction, a component). Revise and ask again until the user approves. Write nothing to the repo before then. Once approved, write each direction's section of the brief, with the axes line, to `RUN/directions/NAME/direction.md`.

## 4. Build the previews

The first time this step runs, before writing anything, save `git status --porcelain --untracked-files=all` to `RUN/status-before.txt`, so step 8 can tell this run's files from the user's own. Never save it again in this run: a blend or a new brief reuses it. Any existing file a direction will edit (a preview registry, a stories index) must be clean in it; if one isn't, ask the user to commit it first. Then build one preview per direction, where the inventory's `## Preview surface` says previews live, as `SETUP/references/preview-harness.md` describes. If the surface is `temporary`, build the temporary structure first, once per run (its **Temporary mode**, using the `status-before.txt` just saved).

- **Slug:** `SLUG-NAME`, where `SLUG` names the thing being designed (`order-list-dense-table`). Lowercase letters, digits and `-` only.
- **Every state** of the matrix, with the **same fixtures** in every direction, so the screenshots compare like for like.
- **Catalogued components only**, imported or called the way the inventory's `Path / import` column says. A new component the brief approved goes in a `previews` folder of its own for the direction, which the inventory scan skips, so it's never catalogued as one of the app's components: step 9 moves the winner's into the app. Blade only resolves `<x-…>` tags under `resources/views/components`, and every file in the previews folder is a preview, so:

  | Stack | New components go in | Used as |
  |---|---|---|
  | React | `previews/SLUG-NAME/` beside the preview (or beside the stories file) | an import |
  | Laravel Blade | `resources/views/components/previews/SLUG-NAME/` | `<x-previews.SLUG-NAME.count-badge>` |
  | CodeIgniter 4 | `app/Views/previews/SLUG-NAME/` | `view('previews/SLUG-NAME/count_badge', $data)` |
- Keep fixture data that holds colours (a swatch, a chart series) in its own fixture file, so the gate in step 5 reads only the direction's markup.

For each direction, write:
- `RUN/directions/NAME/files.txt`: every path this direction created, one per line, marked `created`, and every existing file it edited (a registry line, a stories index), marked `edited` with the line it added. Step 8 deletes the losers' entries from this list.
- `RUN/directions/NAME/components.json`: one entry for every component file the direction created (every `created` path in `files.txt` except the preview itself and fixture files), `[]` if none: `[{"name": "OrderSummary", "path": "src/__preview/previews/order-list-card-stack/OrderSummary.tsx", "why": "Nothing catalogued shows a total with its breakdown."}]`. A component left off this list skips the duplicate check, so check the two lists match.
- `RUN/directions/NAME/matrix.json`: the preview's matrix, as the reference's **The matrix file** shows.

## 5. Capture and gates

Get the capture tools and the app running as `CRITIQUE/SKILL.md` steps 2 and 3 describe, including its fallbacks (a browser MCP when there's no Node; stop when there's no browser at all) and the dependency-file check.

**Gate the source first.** For each direction, pass the files from its `files.txt` that hold its markup and styles (the preview and its new components, not fixture files):

```bash
python3 CRITIQUE/scripts/critique.py gates --strict --run "RUN/directions/NAME" \
  --components RUN/directions/NAME/components.json --files FILE...
```

Before the first capture there's no `axe.json`, so this checks only the source. Exit 1 means something blocks, and `RUN/directions/NAME/gates.json` says what. **A direction can't be captured or critiqued until its gates pass.** Fix it and gate again:
- `tokens` and `skipped`: triage and fix them as `CRITIQUE/SKILL.md` step 5 says, using the inventory's tokens. A hit that isn't a colour or size (a `#123` in a comment) is in a file this run wrote: reword it. A raw value the inventory's `## Rules` allows still needs the user's agreement to go on.
- `components`: `same name as a catalogued component` means use the catalogued one, or rename it if it really is different. A missing reason means write one, or use a catalogued component. Show the user each new component's `similar` list with its reason.

**Then capture** every direction, and each neighbouring screen once. The captures don't depend on each other, so run them as parallel background commands:

```bash
node CRITIQUE/scripts/capture.mjs --url "ORIGIN" --out "RUN/directions/NAME" --matrix RUN/directions/NAME/matrix.json [--storage-state RUN/auth.json]
node CRITIQUE/scripts/capture.mjs --url "NEIGHBOUR_URL" --out "RUN/neighbour-1" --viewports 1280 [--storage-state RUN/auth.json]
```

`CRITIQUE/SKILL.md` step 4 explains its exit codes and errors. Run each direction's gates again, now with its `axe.json`. An `axe` violation is fixed in the markup or the token use, never by hiding the element. Then capture and gate that direction again.

In browser-MCP mode there's no axe report: tell the user the accessibility gate couldn't run, and record that in the decision record.

## 6. Critique

**Rubric.** Use `CRITIQUE/references/rubric.md`, enriched from `frontend-design` and `web-design-guidelines` when installed, exactly as `CRITIQUE/SKILL.md` step 6 describes. Write the extra rows once, to `RUN/extra-rubric.md`.

**Briefs.** For each direction:

```bash
python3 CRITIQUE/scripts/critique.py brief --run "RUN/directions/NAME" --rubric CRITIQUE/references/rubric.md \
  [--extra RUN/extra-rubric.md] --direction RUN/directions/NAME/direction.md [--neighbours RUN/neighbour-*/shots/*.png]
```

**Critics, in parallel.** Start one `pixie:design-critic` agent per direction, all in one message. Give each only the absolute path of its own `RUN/directions/NAME/critic` folder: no code, no repo paths, and nothing about the other directions. Save each reply to `RUN/directions/NAME/critic-findings.json` (if one isn't a JSON array, ask that critic once to answer in its format), then:

```bash
python3 CRITIQUE/scripts/critique.py review --run "RUN/directions/NAME" --findings RUN/directions/NAME/critic-findings.json
```

**Fix rounds: 2 at most.** For each direction with accepted S1 or S2 findings, fix them within the direction: never by moving it towards another direction, which would erase the differences the user is choosing between. Then capture, gate and critique that direction again. After the second round, stop fixing: what's left goes in front of the user in step 7. Don't view the screenshots yourself; the critics do.

## 7. The user picks

For each direction, print: its axis positions and trade-off, its gate results, its remaining findings by severity with their titles, and the path of its `typical` screenshots at 1280 and 390 (`RUN/directions/NAME/shots/`), so the user can open them. Then ask with AskUserQuestion:

- **Pick one** of the directions.
- **Blend:** the user says what to take from which (the layout of one, the density of another). Build the blend as one more direction, with its own `direction.md` naming what it takes from where, then run steps 4 to 6 for it, with one fix round. Reuse the neighbours already captured. Then ask again.
- **None of these:** go back to step 3 with what the user said. Delete every direction's files first (step 8's deletion, for all of them), and its `RUN/directions/NAME` folder, so a reused name doesn't inherit old screenshots or an old `axe.json`.

## 8. Delete the losers

For every direction except the winner (`WINNER` below), delete each `created` path in its `files.txt` and any folder it leaves empty, and take out the line it added to each `edited` file. Then run `git status --porcelain --untracked-files=all` again and compare it with `RUN/status-before.txt`: the only new lines may be the winner's files (and the harness's own files, if this run installed or built it). Never touch a line that was already in `status-before.txt`: that's the user's work.

## 9. Converge

Build the winner into production code, test-first, as `CRITIQUE/references/convergence.md` describes: one behaviour test per state of `RUN/directions/WINNER/matrix.json`, red then green.

- **Where it goes:** the app's real locations, never a `previews` folder. Components go where the inventory's `Path / import` column puts components of their kind, and the component is used on the screen the frame names. A new component the brief approved moves out of the direction's `previews` folder to its real place, under the name the gates checked. Ask if it isn't clear where something belongs.
- **The preview is the visual reference.** Build from its source, whose components move into production anyway. The tests decide the behaviour, and the critic below checks the look. Don't view the screenshots yourself.
- **Point the preview at production.** Once every state's test passes, change the winner's preview to render the production component with the same data the tests use, and delete its copies of the new components from the `previews` folder. The preview stays as the component's matrix.

**Check the result.** Gate the production files (the components and styles this step wrote), capture the preview into `RUN/production` with the winner's matrix, then gate again with its `axe.json`. Fix and capture again until the gates pass, as in step 5, for 2 rounds at most. Anything still failing after that goes in the decision record and the summary:

```bash
mkdir -p "RUN/production"
python3 CRITIQUE/scripts/critique.py gates --strict --run "RUN/production" --files FILE...
node CRITIQUE/scripts/capture.mjs --url "ORIGIN" --out "RUN/production" --matrix RUN/directions/WINNER/matrix.json [--storage-state RUN/auth.json]
```

Then run **one critic pass** against the approved direction. `--approved` gives the critic the winner's screenshots, so it can report drift from them:

```bash
python3 CRITIQUE/scripts/critique.py brief --run "RUN/production" --rubric CRITIQUE/references/rubric.md \
  [--extra RUN/extra-rubric.md] --direction RUN/directions/WINNER/direction.md --approved RUN/directions/WINNER
```

No neighbours this time: step 6 already compared the winner with them.

Start one `pixie:design-critic` agent with only the absolute path of `RUN/production/critic`, save its reply to `RUN/production/critic-findings.json` and run `critique.py review` on it, as in step 6. Accepted `direction.drift` findings are the drift: where production no longer looks like what the user picked. Any other accepted finding is a problem production brought in. Don't fix them in this pass. Print both lists, by severity, with their screenshots, and put them in the decision record.

## 10. Record and finish

**Temporary harness.** With a `temporary` preview surface, there's no harness to keep the winner in. Ask once: install the permanent preview harness now (`SETUP/SKILL.md` step 7, offer 4, including its exclusion proof), so the winner's preview stays, or remove it with the rest. On no, delete the winner's preview files (the `created` paths in its `files.txt` that step 9 didn't move into production), remove the temporary structure as the reference's **Temporary mode** says, and note in the record that the preview wasn't kept. Step 9's production work stays: in a file both the harness and step 9 edited (a routes file), take out only the harness's lines instead of restoring the file, and when comparing with `status-before.txt`, step 9's files (production code, tests and test fixtures) are the only new lines allowed.

**Decision record.** Write `docs/design/decisions/YYYY-MM-DD-SLUG.md` from [references/decision-record.md](references/decision-record.md). Copy each direction's `typical` screenshots at 1280 and 390, and the winner's whole matrix at 1280, to `docs/design/decisions/YYYY-MM-DD-SLUG/` as `NAME-STATE-WIDTH.png`, and each screenshot a step 9 finding cites as `production-STATE-WIDTH.png`. They're already at most 1280 wide at device scale 1. If `oxipng` is on the PATH, run `oxipng -o 2 --strip safe` on the copies to shrink them further without changing a pixel.

**Gitignore the screenshots.** Ask this only if the inventory's `## Setup offers` has no **Gitignore design decision screenshots** row: "Keep design decision screenshots out of git? I'd add `docs/design/decisions/*/` to `.gitignore`. The records stay committed." On yes, add that line to `.gitignore`. Either way, add the row with the answer and the date.

**Stop what this run started.** Run the verification skill's Cleanup, or stop each process this run started. Leave the user's own processes running. Delete `RUN`.

If the run stops early, before the pick: delete every direction's files as step 8 does (there's no winner), remove any temporary structure, stop the processes and delete `RUN`. If it stops after the pick: finish deleting the losers, and leave no test red (finish the state in progress, or remove its test). Keep the winner and the production work, and leave the preview on its own copies of the components if step 9 hadn't pointed it at production yet. Write the decision record with what was built, marking convergence unfinished and leaving out what didn't run (the production critic pass, its screenshots), tell the user which states still have no test, and do the rest of step 10 (the temporary harness, the processes, `RUN`).

## Done

Tell the user:
- the winner, and where its preview lives (slug and path), or that it wasn't kept
- the production files and the tests, one per state, each of which failed before its code was written
- any gate still failing on production after 2 rounds
- the drift and other findings from the last critic pass, by severity
- the decision record's path
- what to commit: the production code and its tests, the record, the screenshots unless gitignored, the winner's preview, and the inventory if this run created or refreshed it

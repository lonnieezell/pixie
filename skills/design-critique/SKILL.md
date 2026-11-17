---
name: design-critique
description: Critique one existing screen of a running web app, a route or the screen a component appears on. Captures it at mobile and desktop widths, runs axe and a raw-colour check, then has a code-blind design-critic agent rank findings against a rubric. Saves a dated report, then asks whether to fix, file or leave the findings.
disable-model-invocation: true
---

# Design critique

Give a ranked, evidence-backed critique of one screen as it looks in the running app. The skill captures screenshots, runs scripted gates, has one code-blind critic judge the screenshots, saves a report, and then asks the user what to do with it. **Nothing is edited or filed before the user picks fix, file or leave.** The one exception is a React, Blade or CodeIgniter component's preview (step 0), which the capture needs.

`SCRIPTS` below is `${CLAUDE_SKILL_DIR}/scripts`. `critique.py` needs Python 3. `capture.mjs` needs Node and the Pixie Playwright cache (see step 2).

## 0. Inputs

The user names a route (`/orders`), a full URL, or a component. For a component in a React repo, a component or partial in a Laravel Blade repo, or a view cell or partial in a CodeIgniter 4 repo, see **A component in a React, Blade or CodeIgniter repo** below. For any other component, find the screens that render it and ask which one to capture. Also take any states the user names ("with the menu open", "after a failed save"). Work out the steps that reach each state from the page as it loads, using stable selectors (ARIA labels, `data-*` attributes, visible text) from the code. Write them as a states file:

```json
[
  {"name": "default", "steps": []},
  {"name": "menu open", "steps": [{"click": "button[aria-label=Menu]"}]},
  {"name": "failed save", "steps": [{"fill": ["#email", "not-an-email"]}, {"click": "text=Save"}, {"waitFor": "[role=alert]"}]}
]
```

Steps are `click`, `fill`, `press`, `hover` and `waitFor`. Always keep `default`.

**A component in a React, Blade or CodeIgniter repo** is captured from its preview instead, in every state of the state matrix. [preview-harness.md](../design-setup/references/preview-harness.md) (in `${CLAUDE_SKILL_DIR}/../design-setup/references/`) describes previews, the matrix, fixtures and temporary mode. Read it, then:
- Find the component's preview where the inventory's `## Preview surface` says previews live: a stories file with the six state stories, `previews/<slug>.preview.tsx` in the React harness, `resources/previews/<slug>.php` in the Blade harness, or `app/Previews/<slug>.php` in the CodeIgniter harness. If it has none, write one. If the surface is `temporary` (or the inventory is missing), build the temporary structure for this run as the reference describes, once `RUN` exists (below). Step 9 removes it.
- States the user names become interaction states, each starting from the preview state it fits (usually `typical`).
- Write `RUN/matrix.json` from the preview. Skip the states file.

The step 5 gate reads the component's files, not the preview's: fixture data such as a swatch colour isn't a raw value in the UI.

Pick 1–2 **neighbouring screens**: screens that share this one's layout shell or link to it (for a previewed component, screens that render it). The critic compares against them for consistency. Ask if none is obvious.

Make a run folder outside the repo with `mktemp -d "${TMPDIR:-/tmp}/pixie-critique.XXXXXX"`, noted as `RUN`.

## 1. Read the inventory and settings

- `docs/agents/design-system.md`: its `## Rules`, `## Rubric overrides`, `## Tokens` and `## Launch fallback`. If it's missing, say that `/pixie:design-setup` makes the critique use the repo's own rules, then carry on without them.
- `docs/agents/pixie.json`: `liveVerify.design`. A missing file or key means `true`.

## 2. Check the capture tools

Capture runs from Pixie's own cache, `~/.cache/pixie/playwright`, and never installs anything into the target repo. `/pixie:design-setup` owns that cache: read its **Install Playwright** offer (step 7, offer 2, in `${CLAUDE_SKILL_DIR}/../design-setup/SKILL.md`) for when the cache is ready and the pinned install commands.

If `node --version` works but the cache isn't ready, make that same offer now, even if the inventory records an earlier `no`: capture can't run without it. Install only on yes.

**Fallbacks.**
- **No Node, or the user says no:** use a connected browser MCP (Claude in Chrome, the built-in browser, a Tauri MCP) that can resize the viewport and save a screenshot to a file. Save each screenshot as `RUN/shots/STATE-WIDTH.png` at each width, and write `RUN/manifest.json` by hand in the shape step 4 describes. There's no axe report in this mode: say so in the report's **Not checked**.
- **No browser at all:** stop. Say that visual critique is unavailable here and what would enable it. Never critique from the code alone, and never guess at what the screen looks like.

## 3. Get the app running

Track every process this run starts. Step 9 stops them.

- **Verification skill** (`.claude/skills/verify-*/`, such as one made by `create-verifier`), unless `liveVerify.design` is `false`: follow its Launch and Doctor sections to get a usable local instance. If its auth section signs in through a browser, sign in once with Playwright (or the MCP) and save the session as a Playwright storage state at `RUN/auth.json`. Use its Cleanup in step 9. Its Evidence rules prefer text and avoid images. They don't apply here: screenshots are the evidence for this skill.
- **No verification skill, or `liveVerify.design: false`:** if there's no verification skill, recommend `/pixie:create-verifier` in one line, so later runs can launch and sign in on their own. Then use the inventory's **Launch fallback**. If it's `none` or missing, ask for the launch command and URL, or whether the app is already running. Confirm the command with the user before running it, and say what it will start.
- For a Storybook preview, also start Storybook with the command in the inventory's `## Preview surface` (or the repo's `storybook` script) unless it's already running.
- If the screen needs a signed-in user and there's no way to sign in, ask the user for test credentials or a storage state file. Never use real user accounts without asking.

Before capturing, record the dependency files' state, so step 4 can prove the capture didn't touch them:

```bash
git status --porcelain -- package.json package-lock.json npm-shrinkwrap.json yarn.lock pnpm-lock.yaml bun.lock bun.lockb
```

## 4. Capture

```bash
node SCRIPTS/capture.mjs --url "URL" --out "RUN" --states RUN/states.json [--storage-state RUN/auth.json]
node SCRIPTS/capture.mjs --url "NEIGHBOUR_URL" --out "RUN/neighbour-1" --viewports 1280 [--storage-state RUN/auth.json]
```

For a preview, capture the matrix instead of a states file. `ORIGIN` is the origin that serves the preview route (in Laravel, the app's own URL, not Vite's), or Storybook's:

```bash
node SCRIPTS/capture.mjs --url "ORIGIN" --out "RUN" --matrix RUN/matrix.json [--storage-state RUN/auth.json]
```

That captures every state at 1280 wide, plus `typical` and `overflow` at 390, and each interaction at 1280 or the widths it names. Exit 1 with "missing required states" means the preview is incomplete: add the missing states to the preview, then capture again. A shot listed under `errors` with "preview error" hit the harness's own error message (no such preview or state, or a preview that failed to load or render) or Storybook's error display (no such story): fix the preview, how it's registered (the React registry; the Blade or CodeIgniter preview's file name) or the matrix path. A timeout waiting for the preview means the page rendered neither: check the harness is mounted, or that the URL is a story. In a Laravel app, an HTTP 404 on every shot means the route isn't reached (the reference's 404 note lists the causes), and "Vite manifest not found" on every state means the app's assets aren't served: start the repo's dev script (`composer run dev`, or `npm run dev` alongside the app) and capture again. In a CodeIgniter app, an HTTP 404 on every shot means the app isn't running in development (`CI_ENVIRONMENT = development`), or `ORIGIN` isn't where the app's routes start (an app in a subfolder, or one without URL rewriting that needs `index.php/`): ask the user for an origin that serves the app at its root, such as `php spark serve` with `app.baseURL` set to match.

Capture each neighbour into its own folder (`neighbour-1`, `neighbour-2`). The default widths are 390 and 1280. A width over 1280 is refused, and screenshots are taken at device scale 1 and cut off at 4000px tall, which keeps them small.

It writes `RUN/shots/STATE-WIDTH.png`, `RUN/axe.json`, and `RUN/manifest.json`:

```json
{"url": "...", "capturedAt": "...", "shots": [{"file": "shots/default-390.png", "state": "default", "viewport": 390, "url": "..."}], "errors": [{"file": "...", "state": "...", "viewport": 390, "url": "...", "error": "..."}]}
```

Exit 3 means the cache isn't ready (go back to step 2). Exit 1 means bad options, or no screenshot could be taken: check the app is up and the URL is right. A state listed under `errors` couldn't be reached. Fix its steps and capture again, or list it under **Not checked**.

Then run the `git status --porcelain` from step 3 again. Its output must match the first run. If a dependency file changed, say so plainly in the terminal and the report.

## 5. Scripted gates

Find the files that render this screen: the route definition, the controller or page, the views and components it renders (one level of includes), and the stylesheets they use. Then:

```bash
python3 SCRIPTS/critique.py gates --run "RUN" --files FILE...
```

It writes `RUN/gates.json`:
- `axe`: one entry per axe violation per screenshot, most severe first
- `tokens`: every raw hex colour and Tailwind arbitrary value (`text-[#333]`, `p-[13px]`) in those files, with `file:line`. The token source files listed in the inventory's `## Tokens` are skipped.
- `skipped`: any `--files` path that couldn't be read. Fix the path and run the gate again, or list it under **Not checked**.

These go in the report ahead of the critic's findings. The token check is a pattern match, so look at each hit's line before reporting it. Drop any that isn't a colour or a size (an issue number in a comment such as `Fixes: #123`, an anchor such as `href: "#add"`, a selector such as `:not(#abc)`). A raw value the inventory's `## Rules` explicitly allows isn't a failure: note it as allowed.

## 6. Critique

**Rubric.** The core rubric is [references/rubric.md](references/rubric.md). If the `frontend-design` or `web-design-guidelines` skills are available, read them and turn the checks they describe that can be judged from a screenshot into extra rows, in the same table format. Prefix their IDs `fd.` and `wdg.`. Write those rows to `RUN/extra-rubric.md`.

**Brief.** Build the critic's folder:

```bash
python3 SCRIPTS/critique.py brief --run "RUN" --rubric "${CLAUDE_SKILL_DIR}/references/rubric.md" \
  [--extra RUN/extra-rubric.md] [--neighbours RUN/neighbour-*/shots/*.png]
```

Leave out `--neighbours` when no neighbour was captured.

It writes `RUN/critic/` and prints its path. The folder holds only the screenshots, the manifest, the rubric (the core rubric plus the extra rows) and `context.md` (the inventory's Rules and Rubric overrides). No source code goes in, and nothing else may be added to it. Don't view the screenshots yourself: the critic does, and each image costs tokens.

**Critic.** Start one `pixie:design-critic` agent. Give it the absolute path of `RUN/critic` and nothing else: no code, no file paths from the repo, no summary of what you think is wrong. Save its JSON reply to `RUN/critic-findings.json`. If the reply isn't a JSON array, ask it once to answer in the format its instructions give.

**Review.**

```bash
python3 SCRIPTS/critique.py review --run "RUN" --findings RUN/critic-findings.json
```

It writes `RUN/findings.json` with three lists:
- `accepted`: ranked S1 to S4
- `rejected`: each with the reason (a missing field, an observation too vague to act on, or a rubric item, screenshot, state or viewport that doesn't exist)
- `suppressed`: findings for rubric items the overrides drop

Only accepted findings are reported as findings.

## 7. Report

Write `docs/design/critiques/YYYY-MM-DD-SLUG.md`, where `SLUG` comes from the route, or the preview's slug for a component. Copy the screenshots to `docs/design/critiques/YYYY-MM-DD-SLUG/` and link them by relative path.

**Gitignore the screenshots.** Ask this only if the inventory's `## Setup offers` has no **Gitignore critique screenshots** row: "Keep critique screenshots out of git? I'd add `docs/design/critiques/*/` to `.gitignore`. The reports stay committed." On yes, add that line to `.gitignore`. Either way, add the row with the answer and the date (only when the inventory exists).

The report:

```markdown
# Design critique: ROUTE

- **URL:** URL
- **Date:** YYYY-MM-DD, commit SHORT_SHA
- **Captured with:** Playwright / BROWSER MCP, widths 390 and 1280
- **States:** default, menu open
- **Neighbours:** /orders/list

## Summary

Three to five lines: counts by severity, gate results, and the top three things to fix.

## Gates

### Accessibility (axe)

| # | Rule | Impact | Where | Screenshot |
|---|---|---|---|---|
| G1 | `color-contrast` | serious | `.muted` (2 nodes) | [default, 390](YYYY-MM-DD-SLUG/default-390.png) |

### Raw values

| # | Match | File |
|---|---|---|
| G2 | `text-[#333]` | `resources/js/Pages/Orders.tsx:48` |

## Findings

### F1 [S2] `hierarchy.primary-action`: Save and Cancel look the same
- **Screenshot:** [default, 1280](YYYY-MM-DD-SLUG/default-1280.png) (state `default`, 1280 wide)
- **Observed:** OBSERVED
- **Fix:** FIX

## Suppressed by overrides

`type.readability` (1 finding)

## Not checked

States that couldn't be captured, the axe gate in browser-MCP mode, and the count of rejected findings with their reasons.
```

Print the summary, the gate results and each finding's title in the terminal, with the report's path.

## 8. Ask once: fix, file or leave

Ask once, with AskUserQuestion:

- **Fix the top N** (default 3; the user can name numbers instead, such as `G1 F2`). Gate failures count first, then findings in rank order.
  - CSS or token changes (spacing, colour, type, layout): make them directly, using the inventory's tokens and preferred components, never new raw values.
  - Behaviour changes (a missing empty state, focus handling, a label that needs new markup): test-first, as [references/convergence.md](references/convergence.md) describes, with one test per fix for the state its finding cites.
  - Then capture the affected states again and run the gates, and say which items are gone.
- **File as issues**, as `poke` does: one GitHub issue per finding or gate failure the user picks, holding its entry from the report. Describe the screenshots in words, since they may be gitignored. Ask whether to label them `ready-for-agent`. If `docs/agents/pixie-labels.md` exists, use its label for that role.
- **Leave it**: the report is saved, and nothing else changes.

## 9. Clean up

Whatever the user picked, and also when the run stops early:
- Run the verification skill's Cleanup, or stop each process this run started. Leave the user's own processes running.
- If this run built a temporary preview structure, remove it and check `git status` matches, as the preview-harness reference's **Temporary mode** says. A preview written into a permanent harness or Storybook stays: tell the user to commit it.
- Delete `RUN`. The report and its screenshots are the evidence that stays.

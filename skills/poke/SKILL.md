---
name: poke
description: Poke at one section of an app like a curious, impatient user, finding code bugs and UX expectation gaps by driving the running app when possible. Writes a ranked report to ai/poke/.
disable-model-invocation: true
---

# Poke

Poke at ONE section of an application (a feature, screen, or component cluster) the way a curious, impatient user would, and see what breaks. Check it for:
1. **Correctness bugs** in the code
2. **Expectation gaps** — places where the UI is missing behavior, or behaves differently from what users of that *kind* of component naturally expect
3. **Live behavior problems** — found by actually operating the running app

Stack-agnostic. Works on any web, desktop-webview (Tauri, Electron), or native app; the depth of the live pass depends on what automation is available.

## Inputs

The user gives a section: a path, a feature name, or a description ("the file tree in the sidebar"). If it's ambiguous which code it maps to, find the candidates and ask once. Optional: reference apps the user wants it compared against.

## Step 1 — Scope the section

- Locate entry components, state stores, hooks/services, and backend calls the section uses (for Tauri: `invoke()` calls and the matching `#[tauri::command]` handlers).
- Identify the **component archetypes** involved (tree view, data grid, list with selection, form, modal/dialog, drag-and-drop, editor, search/filter, tabs, menus, settings panel, wizard...). A section usually has 2–4.
- For each archetype, pick 1–2 **reference apps** that set user expectations (e.g. tree → VS Code explorer / Finder; grid → Excel / Airtable; command palette → VS Code / Raycast; editor → the platform's native text editing). Use any the user named.
- Note the platform (macOS / Windows / Linux / web) — keyboard and interaction conventions differ (Cmd vs Ctrl, Delete vs Backspace, Enter-to-rename on macOS vs F2 on Windows).
- Build the **expectation checklist**: for each archetype, the reflex behaviors users of its reference apps will try. Start from [references/expectations.md](references/expectations.md) when an archetype is listed there. For any other archetype, ask: *"What would a regular user of [reference app] try first, by reflex, and be surprised not to find?"* Cover: discoverability, keyboard, mouse/trackpad, selection model, editing commit/cancel, undo, feedback, persistence, error recovery, empty/loading states, and platform conventions. Always add the general list:
  - every action has feedback; long operations show progress and are cancellable; errors say what happened and what to do; undo or confirmation for anything destructive; shortcuts match platform conventions and are discoverable (menus/tooltips); state survives reload where users expect; nothing requires knowing a hidden gesture.
- List the **edge-case data** worth trying on this section (from the Pass A list below).
- Write the **scope note**: files, archetypes, reference apps, platform, expectation checklist, edge-case data. If the section spans more than about 15 files, share the scope note with the user before Step 3.

## Step 2 — Decide how to drive the live app

Pick the best available option, in this order, and say which one you're using:

1. **Project verification skill** — if the project has a local skill that drives the app the way a user does (such as one made by `create-verifier`), use it. It already knows how to start, drive, and clean up this app.
2. **App-specific automation MCP** — if tools are connected that can screenshot, read the DOM, click/type, and read logs inside the real app (e.g. for Tauri: `@hypothesi/tauri-mcp-server` with `tauri-plugin-mcp-bridge`, or `tauri-plugin-mcp`). Real backend, real IPC, real window. Start the app in dev mode first if needed.
3. **Browser automation against the dev server** — Playwright or a connected browser tool pointed at the frontend dev server (e.g. Vite). For webview apps whose backend calls fail outside the shell, check whether the project mocks IPC (Tauri: `@tauri-apps/api/mocks` `mockIPC`); if not, note that backend-dependent flows can only be reviewed from code. Good for pure UI behavior, fast.
4. **Computer use** on the user's machine against the built app — slow but real. Use for a small number of high-value flows.
5. **Code-only** — if none of the above is available. Mark every live-only concern as *suspected*.

If no live option exists, tell the user in one line what would enable one (e.g. running `create-verifier`, or adding the Tauri MCP bridge plugin to debug builds) and continue code-only.

Track every process this run starts (dev server, app instance). Step 4 stops them.

## Step 3 — Run the passes

Start Passes A and B as background `general-purpose` subagents, which read whole code paths. Give each one the scope note, its own pass section below, and the finding format from **Report**. Tell each one it is read-only: it reports findings in that format and leaves every file unchanged. If subagents aren't available, run A and B yourself after C.

Run Pass C yourself in the main conversation while A and B work. Step 2 already set up the app here, and Pass C may need to ask the user for a test workspace.

### Pass A — Code correctness
Look for: logic errors; state that can desync (optimistic updates without rollback, stale closures, derived state duplicated in two places); race conditions (rapid repeat actions, out-of-order async responses, unmounted-component updates); unhandled errors and swallowed promise rejections; missing loading/error/empty states; edge-case data (empty, one item, thousands of items, very deep nesting, very long names, unicode/emoji, names with `/`, `.`, leading spaces, duplicates); persistence bugs (what survives reload/restart, what shouldn't); backend boundary issues (unvalidated input, path handling, errors not surfaced to UI); performance traps (re-rendering whole lists, no virtualization for large data); accessibility basics (focus management, roles, labels).

### Pass B — Expectation gaps
Check the implementation against every item on the expectation checklist. Done when every item is marked **pass**, **fail**, or **not checked** (with the reason). Each fail is a finding.

### Pass C — Live interaction (main conversation; only if Step 2 found a live option)
Operate the section like a curious real user and like an impatient one:
- Walk each primary task end to end.
- Try every item on the expectation checklist and record what actually happens.
- Abuse it: double-click fast, act during loading, use the edge-case data from the scope note, resize the window small, navigate away mid-edit, reload/restart and check persistence.
- Watch console/app logs and failed IPC/network calls during each action.
- Capture a screenshot for each confirmed visual or behavioral problem, saved in the run's screenshot folder (see **Report**).

Work in a test fixture or workspace; ask the user for one if none exists, so real user data is never touched.

## Step 4 — Merge, verify, rank, clean up

- Deduplicate across passes (a Pass B gap confirmed in Pass C becomes one finding, marked confirmed).
- Verify each remaining finding against the code or by reproducing it. Mark it **confirmed** (seen in code path or live) or **suspected** (plausible, not reproduced). Drop anything that is only taste with no user-impact argument.
- Rank by severity:
  - **S1** data loss, crash, or blocked core task
  - **S2** wrong behavior or broken expectation in a common flow
  - **S3** missing expected affordance, friction, inconsistency
  - **S4** polish

  Within a severity, list findings in the most-used flows first.
- Stop every process this run started. Leave the user's own processes running.

## Report

Write the report to `ai/poke/<YYYY-MM-DD>-<section-slug>.md` in the project root. Save screenshots in `ai/poke/<YYYY-MM-DD>-<section-slug>/` and link them from findings by relative path. If `.gitignore` doesn't already ignore `ai/`, add an `ai/` line to it.

Start the report with a 3–5 line summary: what was reviewed, how it was driven (verification skill / MCP / browser / computer use / code-only), counts by severity, and the top 3 things to fix.

Then one entry per finding, grouped by severity:

```
### [S2][confirmed] Rename commits on Esc instead of cancelling
Where: src/components/FileTree/TreeItem.tsx:142 (onBlur fires before keydown handler)
What happens: Pressing Esc during rename saves the new name.
What users expect: Esc cancels and restores the original name (VS Code, Finder).
Evidence: reproduced live; ![](2026-11-15-file-tree/rename-esc.png) / code path description
Suggested fix: handle Escape in onKeyDown, set a cancel flag checked in onBlur.
```

End with:
- **Missing features users will look for** — gaps that are features rather than bugs.
- **Not checked** — anything the chosen driving method couldn't reach, plus checklist items marked not checked.

In the terminal, reply with the summary and the report's path.

## Follow-up

Offer to file the S1/S2 findings, or any the user picks, as GitHub issues, one per finding, so `tackle` can take each one to a PR. Each issue body holds the finding entry. Describe screenshot evidence in words, since `ai/` is gitignored and the images won't reach GitHub. Ask whether to label them `ready-for-agent`. If `docs/agents/pixie-labels.md` exists, use its label for that role instead.

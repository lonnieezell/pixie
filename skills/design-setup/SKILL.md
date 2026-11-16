---
name: design-setup
description: Scan a React, Laravel Blade or CodeIgniter 4 repo and write a committed design inventory (tokens, components with preferred or legacy status, repeated markup patterns, layout shells) to docs/agents/design-system.md, so design work reuses what exists. Reruns refresh only what changed.
disable-model-invocation: true
---

# Design setup

Catalogue the design system the repo already has, and write it to `docs/agents/design-system.md`. Later design skills read this file cold, mid-task, with no memory of this run. They use it to reuse existing components, tokens and patterns instead of inventing parallel ones, and to pick the current version of a component over the legacy one. Write for that reader: concrete paths and imports, no prose they have to interpret.

The file's shape is fixed by [references/inventory-schema.md](references/inventory-schema.md). Read it before writing anything.

Explore first, then ask, then write. Ask one question at a time, with the recommended answer first. Write nothing but the inventory file without asking. The bootstrapped token file, the CLAUDE.md line and every offer in step 7 need an explicit yes.

## 0. Pick the mode

- **No `docs/agents/design-system.md`:** first run. Do steps 1 to 7.
- **The file exists:** refresh. Do step 8, then step 7 for any offer that has no row yet.

## 1. Detect the stack

Read `package.json`, `composer.json` and the config files at the root. Record framework, view engine and styling system.

| Signal | Stack |
|---|---|
| `react` in `package.json` (with `next`, `vite`, `@inertiajs/react` or `@tauri-apps/api` telling you which setup) | React web |
| `laravel/framework` in `composer.json`, views in `resources/views/**/*.blade.php` | Laravel Blade (or Laravel + Inertia React when `@inertiajs/react` is there too) |
| `codeigniter4/framework` in `composer.json`, views in `app/Views` | CodeIgniter 4 |
| `tailwindcss` (v3: `tailwind.config.*`; v4: `@import "tailwindcss"` and `@theme` in CSS) | Tailwind |
| `bootstrap` in `package.json`, a CDN link in a layout, or a Bootstrap SCSS import | Bootstrap |
| `.scss` or `.sass` files | SCSS |

React Native, Vue, Inertia-Vue and Livewire are catalogued too, but list them under "Detected but not supported" in Stack.

Never read or scan `vendor/`, `node_modules/`, `dist/`, `build/`, `public/build/`, `storage/` or `writable/`.

## 2. Choose the scanned paths

List the folders and files the scan reads. They go in the header, and the freshness check diffs exactly these, so keep them tight.

| Stack | Typical paths |
|---|---|
| React | `src/components`, `components/`, `src/layouts`, `app/` (Next), `resources/js/{Components,Layouts,Pages}` (Inertia), global CSS entry files, `tailwind.config.*` |
| Laravel Blade | `resources/views`, `app/View/Components`, `resources/css`, `resources/sass` or `resources/scss`, `tailwind.config.*` |
| CodeIgniter 4 | `app/Views`, `app/Cells`, the stylesheets the layouts link (often under `public/css` or `public/assets`), any SCSS sources |

Check each path exists. Add any other folder that clearly holds UI components or styles. If the repo is a monorepo, ask which app to catalogue.

## 3. Scan

Fill each section of the schema. Every entry names its source path.

**Tokens.** Read the real definitions:
- Tailwind v3: `theme` and `theme.extend` in `tailwind.config.*`. Tailwind v4: `@theme` blocks in CSS.
- Bootstrap and SCSS: the variables file that overrides Bootstrap (`$primary`, `$spacer`, `$border-radius`, `$font-size-base`, `$theme-colors`), and any other `$variables`.
- CSS custom properties declared on `:root` (or a theme selector such as `[data-theme]` or `.dark`).

Framework defaults the repo doesn't override get one line, not a copied table.

**Components.**
- React: exported components under the component folders. Props from the TypeScript types or `propTypes`. Variants from `cva`/`tv` configs or union-typed props such as `variant` and `size`.
- Blade: anonymous components in `resources/views/components` (`<x-name>`, with `@props`), class components in `app/View/Components`, and partials pulled in with `@include` from three or more views.
- CI4: view cells in `app/Cells` (`view_cell(...)`), and partials loaded with `$this->include()` or `view()` from three or more views.

**Status.** Decide `preferred` or `legacy` for each component, in this order:
1. A `status:` line for it in `## Annotations` decides it. This always wins.
2. Otherwise infer it, and write the reason. Look for two components that do the same job (`Button` and `PrimaryButton`, `x-alert` and `partials/alert`, a shadcn `ui/` folder next to older components). Signs of legacy: a `legacy`, `old`, `deprecated` or `v1` path or name, a `@deprecated` comment, or no use in files changed lately (`git log --since=90.days --name-only -- PATHS`). The one recent code uses is `preferred`.
3. A component with no rival is `preferred`.

Catalogue both members of a pair. Don't drop the legacy one: later skills need to know it exists so they don't use it.

**Patterns.** Find repeated markup that isn't a component yet. Collect the class lists on elements in view files (`class=` and `className=`), sort the classes in each list, and count identical lists and identical parent-child structures. Keep any that repeat at least 3 times across at least 2 files. For each, record the cleanest occurrence as `path:line`, the count, and a one-line extraction suggestion. Only suggest. Never refactor.

**Layout shells.** React: layout components and Next `layout.tsx` files. Blade: `@extends('layouts.…')` targets and `<x-…-layout>` components. CI4: `$this->extend('…')` targets with `renderSection`. Count the views that use each one.

**Preview surface.** `.storybook/` means Storybook. A `/__preview` route means the preview harness. Otherwise `temporary`.

**Launch fallback.** If `.claude/skills/verify-*/` exists, record its path. It owns launch, health check, auth and cleanup. Otherwise propose a launch command from the repo's own scripts (`npm run dev`, `php artisan serve`, `php spark serve`) and the URL it serves, and confirm it with the user in step 5.

**Rules.** Record conventions the code shows, with evidence: one icon set, no raw hex outside token files, a form-field wrapper every form uses. Don't invent rules.

## 4. Baseline target

Infer it, in this order:
1. A `browserslist` key in `package.json`, or a `.browserslistrc` file. `baseline widely available` means Widely available, `baseline newly available` means Newly available, `baseline YEAR` means Baseline YEAR. Copy any other query as is.
2. A line naming the Baseline target in `CLAUDE.md` or `AGENTS.md`.
3. Otherwise ask in step 5, with **Widely available** as the recommended answer.

Record the source with the value.

## 5. Confirm

Show a short summary: the stack, the scanned paths, counts per section, and the Baseline target. Then ask, one at a time, only what you couldn't settle:
- the Baseline target, if step 4 found none
- each pair whose status you couldn't infer with confidence. Write the user's answer into `## Annotations` as a `status:` line, so the decision is theirs and survives refreshes
- the launch command, when there's no verifier

**Empty inventory.** If the scan found no tokens and no components, offer to bootstrap a minimal token set: colours by role (primary, surface, text, muted, border, danger, success), a spacing scale, a type scale and radii. Write them where the stack expects them: an `@theme` block (Tailwind v4), `theme.extend` (Tailwind v3), a variables partial (SCSS or Bootstrap), or `:root` custom properties in the main stylesheet. Show the values first, and write them only on yes. Catalogue them with `bootstrapped` as the source.

## 6. Write the inventory

Write `docs/agents/design-system.md` from the schema's template. Create `docs/agents/` if it's missing. Put the full SHA of `HEAD` (`git rev-parse HEAD`) in `Source commit`, and today's date in `Updated`. Start `## Annotations` with any `status:` lines from step 5, and leave `## Rubric overrides` empty.

## 7. Offers

Make each offer once, and only if `## Setup offers` has no row for it yet. Record each answer as a row with today's date. Record `not offered: REASON` when the condition doesn't hold, so it isn't asked on the next run.

1. **Verifier.** If there's no `.claude/skills/verify-*/`: "Want a verification skill, so design skills can launch, sign in to and drive the app? I can make one with `/pixie:create-verifier`. Recommended, not required." On yes, run that skill, then update `## Launch fallback` to point at it.
2. **Playwright.** "Design skills capture screenshots with Playwright. Want me to install it into Pixie's own cache, `~/.cache/pixie/playwright`? It never touches this repo's `package.json`." On yes, with Node available:
   ```bash
   npm install --prefix ~/.cache/pixie/playwright --save-exact playwright@1.65.1
   PLAYWRIGHT_BROWSERS_PATH=~/.cache/pixie/playwright/browsers \
     ~/.cache/pixie/playwright/node_modules/.bin/playwright install chromium
   ```
   Keep the version pinned. Anything that runs this install later must set the same `PLAYWRIGHT_BROWSERS_PATH`. Record the version in the answer. Without Node, record `not offered: no Node`.
3. **Modern Web Guidance.** Check whether it's installed: a skill or plugin with `modern-web-guidance` in its name in the available skills list, `.claude/skills/`, `~/.claude/skills/`, or `~/.claude/plugins/installed_plugins.json`.
   - **Installed**, and the Baseline target didn't come from CLAUDE.md: "Modern Web Guidance reads the Baseline target from CLAUDE.md. Want me to add the line `Baseline target: VALUE` to this project's CLAUDE.md?" Never edit CLAUDE.md without an explicit yes. On yes, append that one line and change nothing else in the file.
   - **Not installed:** tell the user once that [Modern Web Guidance](https://developer.chrome.com/docs/modern-web-guidance) is a recommended companion for platform-level HTML, CSS and Web API guidance. Don't install it. Record `mentioned`.

## 8. Refresh

1. Read the header's `Source commit` and `Scanned paths`. If the commit isn't reachable (`git cat-file -e SHA^{commit}` fails), say so and redo steps 1 to 6 as a full scan, keeping the protected sections and `## Setup offers`.
2. Run the freshness check:
   ```bash
   git diff --name-only SHA -- PATHS
   git ls-files --others --exclude-standard -- PATHS
   ```
   The first lists files changed since the scan, committed or not. The second lists new untracked files. If both are empty, say the inventory is fresh and stop. Recheck the scanned paths too: if a new component or style folder appeared outside them, add it to the list and scan it.
3. Map each changed file to the entries whose source is that file. Refresh only those entries:
   - a changed file: re-read it and update its entries (tokens, a component's props or variants, a layout's path)
   - a deleted file: remove its entries
   - a new file: add any component, token or layout it defines
   - any changed view file: recount the patterns, and update the counts and canonical examples that moved
   Recheck the status of a changed component only when it has no `status:` annotation.
4. Edit only the affected rows and lines with the Edit tool. Never rewrite the whole file. Then update `Source commit` to `HEAD` and `Updated` to today.
5. Prove the protected sections are untouched. Save `## Annotations` and `## Rubric overrides` (from each heading to the next `##` heading or the end of the file) before editing, and compare after. If they differ, restore them from the copy.
6. Report what changed: each entry added, updated or removed, with its source file, and any changed file that mapped to no entry.

## Done

Tell the user:
- the file written or refreshed, and what changed (on a refresh)
- any token file or CLAUDE.md line written, and the Playwright install, if any
- to commit `docs/agents/design-system.md`, and to set component status and critique rules in `## Annotations` and `## Rubric overrides`. Refreshes never overwrite those two sections.

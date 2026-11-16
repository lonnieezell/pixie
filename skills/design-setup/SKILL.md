---
name: design-setup
description: Scan a React, Laravel Blade or CodeIgniter 4 repo and write a committed design inventory (tokens, components with preferred or legacy status, repeated markup patterns, layout shells) to docs/agents/design-system.md, so design work reuses what exists. Reruns refresh only what changed.
disable-model-invocation: true
---

# Design setup

Catalogue the design system the repo already has, and write it to `docs/agents/design-system.md`. Later design skills read this file cold, mid-task, with no memory of this run. They use it to reuse existing components, tokens and patterns instead of inventing parallel ones, and to pick the current version of a component over the legacy one. Write for that reader: concrete paths and imports, no prose they have to interpret.

This file says how to find each thing. [references/inventory-schema.md](references/inventory-schema.md) says how to write it down: the sections, their formats and the status rules. Read it before writing anything.

Explore first, then ask, then write. Ask one question at a time, with the recommended answer first. Write nothing but the inventory file without asking. The bootstrapped token file, the CLAUDE.md line and every offer in step 7 need an explicit yes.

## 0. Pick the mode

- **No `docs/agents/design-system.md`:** first run. Do steps 1 to 7.
- **The file exists:** refresh. Do step 8, then step 7 for any offer that has no row yet.

## 1. Detect the stack

Read `package.json`, `composer.json` and the config files at the root.

| Signal | Stack |
|---|---|
| `react` in `package.json` (with `next`, `vite`, `@inertiajs/react` or `@tauri-apps/api` telling you which setup) | React web |
| `laravel/framework` in `composer.json`, views in `resources/views/**/*.blade.php` | Laravel Blade (or Laravel + Inertia React when `@inertiajs/react` is there too) |
| `codeigniter4/framework` in `composer.json`, views in `app/Views` | CodeIgniter 4 |
| `tailwindcss` (v3: `tailwind.config.*`; v4: `@import "tailwindcss"` and `@theme` in CSS) | Tailwind |
| `bootstrap` in `package.json`, a CDN link in a layout, or a Bootstrap SCSS import | Bootstrap |
| `.scss` or `.sass` files | SCSS |
| `react-native` or `expo`; `.vue` files under the source folders; Livewire components | Detected but not supported |

Judge by the views the app actually has, not by a leftover dependency. A React Native app is unsupported even though `react` is there. A Laravel app whose screens are `.vue` files is Inertia-Vue, not Blade. A Blade app with a few Livewire components is still Blade: catalogue it, and list the Livewire components under "Detected but not supported". Unsupported parts are still catalogued; later design skills just can't preview them.

Skip the folders `code-health` skips (`vendor`, `node_modules`, `target`, `dist`, `build`, `.next`, `writable`, `storage`), plus `public/build`. That includes `vendor` folders inside the scanned paths, such as Laravel's published `resources/views/vendor`.

## 2. Choose the scanned paths

List the folders and files the scan reads. Keep them tight: the freshness check diffs exactly these.

| Stack | Typical paths |
|---|---|
| React | `src/components`, `components/`, `src/layouts`, `app/` (Next), `resources/js/{Components,Layouts,Pages}` (Inertia), global CSS entry files, `tailwind.config.*` |
| Laravel Blade | `resources/views`, `app/View/Components`, `resources/css`, `resources/sass` or `resources/scss`, `tailwind.config.*` |
| CodeIgniter 4 | `app/Views`, `app/Cells`, the stylesheets the layouts link (often under `public/css` or `public/assets`), any SCSS sources |

Check each path exists. Add any other folder that clearly holds UI components or styles. If the repo is a monorepo, ask which app to catalogue.

The inventory must match a commit. If `git status --porcelain --untracked-files=no -- PATHS` prints anything, say so and ask the user to commit those changes first. Don't stash or discard them.

## 3. Scan

Fill each section of the schema. Count with `git grep`, `sort` and `uniq -c` rather than reading view files one by one: a repo can have hundreds of them. `git grep` reads only tracked files. End every pathspec with `':!**/vendor/**'` so published package views stay out. Read a file only to get the detail a count can't give (props, variants, token values).

**Tokens.**
- Tailwind v3: `theme` and `theme.extend` in `tailwind.config.*`. Tailwind v4: `@theme` blocks in CSS.
- Bootstrap and SCSS: `git grep -nE '^\s*\$[A-Za-z0-9_-]+\s*:' -- PATHS ':!**/vendor/**'` lists every variable with its source. The overrides of Bootstrap's `$primary`, `$spacer`, `$border-radius`, `$font-size-base` and `$theme-colors` matter most.
- CSS custom properties declared on `:root` (or a theme selector such as `[data-theme]` or `.dark`).

**Components.**
- React: exported components under the component folders. Props from the TypeScript types or `propTypes`. Variants from `cva`/`tv` configs or union-typed props such as `variant` and `size`. Read the props and variant blocks, not the whole file.
- Blade: anonymous components in `resources/views/components` (`<x-name>`, with `@props`), class components in `app/View/Components`, and partials pulled in with `@include` from three or more views.
- CI4: view cells in `app/Cells` (`view_cell(...)`), and partials loaded with `$this->include()` or `view()` from three or more views.

One pass gives the usage counts for partials and layouts alike:

```bash
git grep -hoE "@(include|includeIf|extends)\(['\"][^'\"]+|<x-[a-z0-9.:-]+|(\\\$this->(include|extend)|view|view_cell)\(['\"][^'\"]+" \
  -- PATHS ':!**/vendor/**' | tr '"' "'" | sort | uniq -c | sort -rn
```

For React, count `import … from '…'` lines the same way. `@includeWhen` and `@includeUnless` take a condition first, so grep those separately when the repo uses them.

**Status.** Apply the precedence in the schema's Components notes. To infer it, look for two components that do the same job (`Button` and `PrimaryButton`, `x-alert` and `partials/alert`, a shadcn `ui/` folder next to older components). Signs of legacy: a `legacy`, `old`, `deprecated` or `v1` path or name, a `@deprecated` comment, or no use in recently changed files. Get those files once, then grep them for every candidate name in one pass:

```bash
git log --since=90.days --name-only --format= -- PATHS | sort -u
```

The one recent code uses is `preferred`. Catalogue both members of a pair: later skills need to know the legacy one exists so they don't use it.

**Patterns.** Find repeated markup that isn't a component yet. This pulls every class list out of the view files, sorts the classes inside each list so order doesn't matter, and prints each list used 3 or more times with its count and every `path:line`:

```bash
git grep -noE 'class(Name)?="[^"]+"' -- PATHS ':!**/vendor/**' | perl -lne '
  /^(.+?:\d+):class(?:Name)?="(.*)"$/ or next; push @{$h{join " ", sort split " ", $2}}, $1;
  END { for (sort { @{$h{$b}} <=> @{$h{$a}} } keys %h) { print scalar(@{$h{$_}}), "\t$_\t@{$h{$_}}" if @{$h{$_}} >= 3 } }'
```

Keep those whose occurrences span at least 2 files. Compare parent-child structure only for these candidates.

**Layout shells.** React: layout components and Next `layout.tsx` files. Blade: `@extends('layouts.…')` targets and `<x-…-layout>` components. CI4: `$this->extend('…')` targets with `renderSection`. The usage counts come from the grep above.

**Preview surface.** Look for `.storybook/`, then a `/__preview` route.

**Launch fallback.** If there's no `.claude/skills/verify-*/`, propose a launch command from the repo's own scripts (`npm run dev`, `php artisan serve`, `php spark serve`) and the URL it serves, and confirm it in step 5. With a verifier, record `none`: design skills find the verifier themselves when they run.

**Rules.** Look for conventions the code shows, with evidence: one icon set, no raw hex outside token files, a form-field wrapper every form uses.

## 4. Baseline target

Infer it, in this order:
1. A `browserslist` key in `package.json`, or a `.browserslistrc` file. `baseline widely available` means Widely available, `baseline newly available` means Newly available, `baseline YEAR` means Baseline YEAR. Copy any other query as is.
2. A line naming the Baseline target in `CLAUDE.md` or `AGENTS.md`.
3. Otherwise leave it for step 5.

## 5. Confirm

Show a short summary: the stack, the scanned paths, counts per section, and the Baseline target. Then ask, one at a time, only what you couldn't settle:
- the Baseline target, if step 4 found none. Recommend **Widely available**.
- each pair whose status you couldn't infer with confidence. Write the user's answer into `## Annotations` as a `status:` line, so the decision is theirs and survives refreshes.
- the launch command, when there's no verifier

**Empty inventory.** If the scan found no tokens and no components, offer to bootstrap a minimal token set: colours by role (primary, surface, text, muted, border, danger, success), a spacing scale, a type scale and radii. Show the values, and say where they'd go: an `@theme` block (Tailwind v4), `theme.extend` (Tailwind v3), a variables partial (SCSS or Bootstrap), or `:root` custom properties in the main stylesheet. On yes, write them there.

## 6. Write the inventory

Write `docs/agents/design-system.md` from the schema's template. Create `docs/agents/` if it's missing. Put `git rev-parse HEAD` in `Source commit`. Start `## Annotations` with any `status:` lines from step 5, and leave `## Rubric overrides` empty. Write `## Setup offers` as the table header only; step 7 adds the rows.

## 7. Offers

`## Setup offers` records the user's answers, one row per offer, named as in bold below. The file is shared, so record only answers, never this machine's state. When an offer's condition doesn't hold (a verifier exists, Playwright is already installed, no Node), skip it without writing a row, so it comes up again once things change. Ask an offer only if its condition holds and its row is missing.

1. **Run `/pixie:create-verifier`.** If there's no `.claude/skills/verify-*/`: "Want a verification skill, so design skills can launch, sign in to and drive the app? I can make one with `/pixie:create-verifier`. Recommended, not required." On yes, run that skill.
2. **Install Playwright into `~/.cache/pixie/playwright`.** It's installed when `~/.cache/pixie/playwright/node_modules/playwright/package.json` says version `1.65.1`, `node_modules/axe-core/package.json` there says `4.14.1`, and `~/.cache/pixie/playwright/browsers` has a `chromium*` folder. Needs Node. A `yes` row from a teammate doesn't count: if it isn't installed on this machine, ask again unless the row says `no`. Ask: "Design skills capture screenshots with Playwright and check accessibility with axe-core. Want me to install them into Pixie's own cache, `~/.cache/pixie/playwright`? It never touches this repo's `package.json`." On yes:
   ```bash
   npm install --prefix ~/.cache/pixie/playwright --save-exact playwright@1.65.1 axe-core@4.14.1
   PLAYWRIGHT_BROWSERS_PATH=~/.cache/pixie/playwright/browsers \
     ~/.cache/pixie/playwright/node_modules/.bin/playwright install chromium
   ```
   Keep the versions pinned, and record them in the answer. Anything that runs this install must set the same `PLAYWRIGHT_BROWSERS_PATH`.
3. **Modern Web Guidance** (MWG). It's installed if a skill with `modern-web-guidance` in its name is in your available skills list, or `grep -l modern-web-guidance ~/.claude/plugins/installed_plugins.json` finds it. It has two rows, and only the one that applies is written, so installing MWG later still brings up the CLAUDE.md offer:
   - **Add Baseline target line to CLAUDE.md**, only when MWG is installed and the Baseline target didn't come from CLAUDE.md. Ask: "Modern Web Guidance reads the Baseline target from CLAUDE.md. Want me to add the line `Baseline target: VALUE` to this project's CLAUDE.md?" Never edit CLAUDE.md without an explicit yes. On yes, append that one line and change nothing else in the file.
   - **Mention Modern Web Guidance**, only when MWG isn't installed: tell the user that [Modern Web Guidance](https://developer.chrome.com/docs/modern-web-guidance) is a recommended companion for platform-level HTML, CSS and Web API guidance. Don't install it. Record `mentioned`.

## 8. Refresh

1. Read the header's `Source commit` and `Scanned paths`. Apply the commit check from step 2. If the commit isn't reachable (`git cat-file -e SHA^{commit}` fails), say so and redo steps 1 to 6 as a full scan, carrying over the protected sections and `## Setup offers` unchanged.
2. Run the freshness check:
   ```bash
   git diff --name-status --no-renames SHA HEAD -- PATHS
   ```
   It lists each file added (`A`), modified (`M`) or deleted (`D`) since the scan. `--no-renames` makes a moved file show as a delete plus an add, so its old entries go. To catch a new component or style folder outside the scanned paths, look at the directories in `git diff --name-only --no-renames --diff-filter=A SHA HEAD` and add any that hold UI. If nothing changed, say the inventory is fresh and go to step 7.
3. Map each changed file to the entries whose source is that file. Refresh only those entries:
   - a changed file: re-read it and update its entries (tokens, a component's props or variants, a layout's path)
   - a deleted file: remove its entries
   - a new file: add any component, token or layout it defines
   - any changed view file: rerun the pattern count, and update the counts and canonical examples that moved
4. Copy `docs/agents/design-system.md` to a temp file outside the repo, as a backup. Then edit `docs/agents/design-system.md` itself, never the backup: only the affected rows and lines, with the Edit tool, never rewriting the whole file. Update `Source commit` to `HEAD` and `Updated` to today.
5. Check the protected sections didn't move:
   ```bash
   diff <(awk '/^## Annotations$/,0' BACKUP) <(awk '/^## Annotations$/,0' docs/agents/design-system.md)
   ```
   Any output means they changed: restore them from the backup. Then delete the backup.
6. Report what changed: each entry added, updated or removed, with its source file, and any changed file that mapped to no entry.

## Done

Tell the user:
- the file written or refreshed, and what changed (on a refresh)
- any token file or CLAUDE.md line written, and the Playwright install, if any
- to commit `docs/agents/design-system.md`, together with any bootstrapped token file (the next refresh needs the scanned paths committed), and to set component status and critique rules in `## Annotations` and `## Rubric overrides`. Refreshes never overwrite those two sections.

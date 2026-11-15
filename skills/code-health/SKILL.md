---
name: code-health
description: Measure and improve code health with km (kimun) for PHP, TypeScript/React and Rust. Use for "code health", "health score", "hotspots", "what should we refactor", "did this change make the code worse", or before opening a PR.
allowed-tools: Bash(km --version), Bash(km score:*), Bash(km hotspots:*), Bash(km cogcom:*), Bash(km smells:*), Bash(km dups:*), Bash(km knowledge:*)
---

# Code health with km

`km` must be on PATH. If `km --version` fails, stop and tell the user to install it with
`cargo install kimun` and add `~/.cargo/bin` to the PATH Claude Code sees. Always pass
`--format json` (or `short` for a one-liner). On whole-repo commands, exclude dependency and
build folders by writing these flags out in full in the same command (shell variables don't
carry over between Bash calls, so don't put them in a variable):

```
--exclude-dir vendor --exclude-dir node_modules --exclude-dir target --exclude-dir dist --exclude-dir build --exclude-dir .next --exclude-dir writable --exclude-dir storage
```

The commands below already include them.

A PostToolUse hook already checks every file Claude edits against git HEAD and reports new
problems. This skill covers the wider, project-level questions.

## Pick the mode from the request

### 1. "How healthy is this project?" → score
```bash
km score . --exclude-dir vendor --exclude-dir node_modules --exclude-dir target --exclude-dir dist --exclude-dir build --exclude-dir .next --exclude-dir writable --exclude-dir storage --format json --bottom 15
```
Report: grade, the weakest one or two dimensions, and the 5 worst files with the one reason
each is weak. Don't paste the JSON.

### 2. "Did my changes make it worse?" / before a PR → diff
Compare against the repo's default branch, not a hard-coded `main`. Find it first:
```bash
git symbolic-ref -q --short refs/remotes/origin/HEAD || echo "origin/$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)"
```
Use what it prints (e.g. `origin/main`, `origin/master`, `origin/develop`) as BASE:
```bash
km score diff . --git-ref BASE --format json     # or HEAD for uncommitted work
km score . --exclude-dir vendor --exclude-dir node_modules --exclude-dir target --exclude-dir dist --exclude-dir build --exclude-dir .next --exclude-dir writable --exclude-dir storage --trend BASE --gate-scope changed --fail-if-worse --format short
```
`--gate-scope changed` only judges files touched on the branch, so existing debt can't fail
it. If it got worse, name the files and dimensions responsible and offer to fix them.

### 3. "What should we refactor?" → hotspots
```bash
km hotspots . --exclude-dir vendor --exclude-dir node_modules --exclude-dir target --exclude-dir dist --exclude-dir build --exclude-dir .next --exclude-dir writable --exclude-dir storage --complexity cogcom --since 1y --top 10 --format json
```
Hotspots are complex files that also change often: that's where cleanup pays back. Rank the top
5, and for each say *why* it's costly (complexity + change frequency) and the first refactoring
step. Add `km knowledge . --top 10 --format json` if the question involves who owns the code.

### 4. "Refactor X" → guided refactor loop
1. Baseline: `km cogcom <dir> --per-function --format json` and `km smells <dir> --format json`
   on the target's directory; note the target functions' numbers.
2. Make sure tests cover the behaviour first. If none exist, write characterisation tests.
3. Refactor in small steps, one smell at a time, running tests after each.
4. Re-measure after each step; stop when every function is ≤ 15 cognitive complexity or the
   remaining complexity is essential. Report before → after numbers.

## Refactoring playbook by smell

| Smell | PHP (CI4 / Laravel) | TypeScript / React | Rust |
|---|---|---|---|
| Deep nesting / high cognitive complexity | Guard clauses; extract loop bodies to private methods; `match` or lookup arrays instead of if/else chains | Early returns; extract named helpers; move component logic into a custom hook | `let … else`, `?`, combinators (`filter_map`, `and_then`); match arms into fns |
| Long function | Private methods; Laravel action/service class; CI4 library | Smaller functions; split subcomponents | Smaller fns; impl on a small struct |
| Long parameter list | DTO / value object; pass the entity | One typed options object | Struct, or builder for optionals |
| Large file / class | Extract a cohesive class (trait only if truly shared) | Split module; colocate hooks/types/subcomponents | Submodules by responsibility |
| Duplication (`km dups`) | Shared method / base class only after the 3rd copy | Shared util or hook | Generic fn or trait |

Prefer each project's own linters for detail once km points at the area: PHPStan/Larastan and
PHPMD for PHP, ESLint (sonarjs) for TS, `cargo clippy -- -W clippy::cognitive_complexity` for Rust.

## Configuration

- `km init` writes a calibrated `.kimun.toml` for a repo (thresholds, exclusions, gate grade).
- Hook tuning via env vars: `CODE_HEALTH_COGCOM_MAX` (15), `CODE_HEALTH_COGCOM_JUMP` (8),
  `CODE_HEALTH_FILE_LINES` (500), `CODE_HEALTH_HOOK=off`. A `.code-health-off` file at a repo
  root disables the hook for that repo.
- For every km subcommand and its JSON fields, see the `km-analyze` skill.

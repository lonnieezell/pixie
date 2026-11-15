# How to clean up hotspots

This guide shows you how to find the messiest, most-changed code in a repo and refactor it safely. You use two skills:

- `code-health` measures the code and tells you where cleanup pays off.
- `untangle` does the refactoring on its own branch.

A **hotspot** is a file that is both complex and changed often. Cleaning a hotspot pays off more than cleaning complex code nobody touches.

## Before you start

- Install km. See [km (kimun)](../../README.md#km-kimun) in the README.
- Commit or stash your work. `untangle` stops if your working tree has uncommitted changes.
- Optional: run `km init` in the repo. It writes a `.kimun.toml` with thresholds tuned to this repo. Its settings win over Pixie's defaults.

## 1. Check overall health

```text
/pixie:code-health how healthy is this project?
```

Claude gives an overall grade, the weakest areas, and the five worst files, with one reason for each.

## 2. Find the hotspots

```text
/pixie:code-health what should we refactor?
```

Claude ranks the top five hotspots. For each, it explains why the file is costly and suggests a first step.

## 3. Refactor

You have two choices.

**Let Claude pick.** Run `untangle` with no arguments:

```text
/pixie:untangle
```

Claude picks the single best hotspot without asking. It skips generated code, migrations, vendored code, and test files. It tells you which file it picked and why.

**Name the area.** Run `untangle` with a target:

```text
/pixie:untangle src/Billing
```

The target can be a path, a class name, or a description such as `the sidebar code`. Claude turns it into a list of files and tells you what's in scope.

Either way, Claude will:

1. Create an `untangle/<short-slug>` branch if you're on the default branch.
2. Run your tests, linter, and type checker once for a baseline.
3. Write tests first if the code has none.
4. Refactor in small steps, and commit after each green step. Each commit starts with `untangle:`.
5. Stop when the code is clean, when only essential complexity is left, after two passes with no progress, or after about 25 steps.
6. If the repo has a verification skill, drive the features it changed in the running app. If one behaves differently than before, Claude reverts the step that caused it.

It never changes public APIs, routes, database schema, config keys, event names, or output formats.

## 4. Review the branch

`untangle` never pushes or opens a PR. Its report shows before and after numbers for each file, one line per commit, anything it left alone, and the live check result. Read the commits. Because each step is its own commit, you can revert any one of them alone.

When you're happy, push the branch and open a PR as usual.

## 5. Check the branch didn't make things worse

Before you open any PR, not only an `untangle` one, you can run:

```text
/pixie:code-health did my changes make it worse?
```

Claude compares your branch to the default branch and judges only the files you changed. Old debt in other files can't fail this check.

## Related

- [`code-health` reference](../reference/skills.md#code-health)
- [`untangle` reference](../reference/skills.md#untangle)
- [Tune the code-health hook](tune-the-code-health-hook.md)

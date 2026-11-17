# Pixie

![Pixie banner image](./docs/assets/pixie-banner.jpeg)

Pixie is a Claude Code plugin for my personal and professional work, adding a set of workflow skills for planning, understanding, refactoring, and shipping code.  I am constantly exploring new ways to do quality development with AI. These tools will likely change often as I continue to refine them and my own workflow changes.

Much of this work was inspired by [Matt Pocock](https://github.com/mattpocock/skills) and [Poteto](https://github.com/cursor/plugins/tree/main)'s skill bases and often tries to combine the best of their approaches, where possible. 

## Prerequisites

Install these before you install the plugin. These tools are designed to use Github for issue tracking. While I will often use other planning tools, such as Jira, for project tasks tracking, Github gets used for tracking the code being worked on.

### Claude Code

Install Claude Code and sign in. You should be able to start a session with `claude` in a terminal.

### GitHub CLI

The `babysit`, `catch`, `checkup`, `maintain-verifier`, `plan-task`, `prune-tests`, `tackle`, and `vet` skills use the GitHub CLI (`gh`) to read and write pull requests and issues. `poke` uses it only if you ask it to file its findings as issues.

1. Install `gh` if you don't have it.
2. Sign in:

   ```bash
   gh auth login
   ```

3. Check that it works:

   ```bash
   gh auth status
   ```

### km (kimun)

The `code-health` and `untangle` skills use km to measure code health. km is a code metrics tool. It reports complexity, code smells, duplicate code, and hotspots for PHP, TypeScript/React, Rust, and many other languages.

1. Install Rust with `rustup` if you don't have it. Cargo, Rust's package manager, comes with it.
2. Install km:

   ```bash
   cargo install kimun
   ```

3. Check that it works:

   ```bash
   km --version
   ```

   Cargo puts km at `~/.cargo/bin/km`. If your shell says `command not found`, add `~/.cargo/bin` to your `PATH`. The skills need it on the `PATH` that Claude Code sees too.

4. Optional: in each repo you work on, run:

   ```bash
   km init
   ```

   This writes a `.kimun.toml` file tuned to that repo. It sets thresholds, folders to skip, and the grade a change must meet. When this file exists, its settings win over the skill defaults.

### Optional: test tools for `prune-tests`

`prune-tests` needs two more tools in the project you are pruning:

- A coverage driver: pcov or xdebug for PHP, v8 or istanbul for TypeScript.
- A mutation testing tool: Infection for PHP, Stryker for TypeScript. Mutation testing makes small changes to your code and checks that a test fails for each one.

You don't need to install these up front. The skill checks for them and offers to add them as dev dependencies.

## Install the plugin

1. In a Claude Code session, install Pixie from its marketplace:

   ```text
   /plugin install pixie --marketplace lonnieezell/pixie
   ```

   This one-step command needs Claude Code 2.1.275 or later. On an older version, add the marketplace first, then install from it:

   ```text
   /plugin marketplace add lonnieezell/pixie
   /plugin install pixie@pixie
   ```

2. Check that it worked. Type `/pixie:` and you should see the Pixie skills in the list.

3. Optional: in each repo you work on, run:

   ```text
   /pixie:setup
   ```

   It checks that `gh` and `km` are ready, and lets you map Pixie's workflow labels to names your repo already uses. Skip it if the default labels are fine. See [Set up a repo for Pixie](docs/how-to/set-up-a-repo.md).

To get the latest version later, run:

```text
/plugin marketplace update pixie
```

## Quick start

This walk-through takes a few minutes. By the end, you'll know how healthy a project is and where to start cleaning it up.

1. Open a terminal in a git repo that has PHP, TypeScript, or Rust code. Start Claude Code:

   ```bash
   claude
   ```

2. Ask for a health check:

   ```text
   /pixie:code-health how healthy is this project?
   ```

   Claude runs km and reports an overall grade. It also names the weakest areas and the five worst files, with one reason for each.

3. Ask where cleanup will pay off most:

   ```text
   /pixie:code-health what should we refactor?
   ```

   Claude lists the top five hotspots. A hotspot is a file that is both complex and changed often. For each one, Claude explains why it's costly and suggests a first refactoring step.

From here, you can run `/pixie:untangle` to have Claude pick the top hotspot and fix it on a new branch.

## Skills

| Skill         | What it does                                                | Example                                            | Needs                             |
| ------------- | ----------------------------------------------------------- | -------------------------------------------------- | --------------------------------- |
| `babysit`     | Brings your open PRs to a mergeable state, oldest first     | `/pixie:babysit`                                   | `gh`                              |
| `catch`       | Turns Sentry and Coralogix errors into issues               | `/pixie:catch`                                     | `gh`, a Sentry or Coralogix token |
| `checkup`     | Audits for security, performance and bugs, then files issues | `/pixie:checkup` or `/pixie:checkup scores`       | `gh` to file issues               |
| `code-health` | Measures code health and guides refactoring                 | `/pixie:code-health did my changes make it worse?` | `km`                              |
| `create-verifier` | Writes a project skill that drives your app like a user | `/pixie:create-verifier`                           | —                                 |
| `design-setup` | Catalogues the repo's design system for design work        | `/pixie:design-setup`                              | —                                 |
| `design-critique` | Critiques one screen of the running app from screenshots | `/pixie:design-critique /orders`                   | Node and Playwright, or a browser MCP |
| `design`      | Explores 2–4 design directions and records your pick        | `/pixie:design the order list`                     | Node and Playwright, or a browser MCP |
| `diagnose`    | Finds a bug's root cause, proves it, then fixes it          | `/pixie:diagnose checkout total is wrong`          | —                                 |
| `how`         | Explains how part of the codebase works                     | `/pixie:how does authentication work`              | —                                 |
| `huh`         | Restates Claude's last reply in plain language              | `/pixie:huh`                                       | —                                 |
| `maintain-verifier` | Keeps a verification skill in step with the app      | `/pixie:maintain-verifier`                         | `gh`                              |
| `plan-task`   | Turns a PM task into a GitHub issue with a build plan       | `/pixie:plan-task` + pasted task                   | `gh`                              |
| `poke`        | Pokes at one section of an app for bugs and UX gaps         | `/pixie:poke the file tree in the sidebar`         | `gh` to file issues (optional)    |
| `prune-tests` | Removes redundant tests in one area without losing coverage | `/pixie:prune-tests tests/Billing`                 | `gh`, coverage and mutation tools |
| `setup`       | Checks tools and maps labels to your repo's names (optional) | `/pixie:setup`                                 | `gh` for labels                   |
| `tackle`      | Takes a `ready-for-agent` issue to an open PR               | `/pixie:tackle 142`                                | `gh`                              |
| `tdd`         | Builds a change test-first, red then green                  | `/pixie:tdd mode=bug #142`                         | —                                 |
| `untangle`    | Refactors a hotspot or a named area until it's clean        | `/pixie:untangle src/Billing`                      | `km`                              |
| `vet`         | Reviews someone else's PR and posts one review after you approve it | `/pixie:vet 142`                           | `gh`                              |

Some skills only run when you type them. See the [Skills reference](docs/reference/skills.md) for full details on each skill: arguments, limits, and output.

Pixie also ships eleven subagents and a code-health hook that checks every file Claude edits. See [Agents and the code-health hook](docs/reference/agents-and-hook.md).

## Documentation

New to Pixie? Start with the [tutorial](docs/tutorial/first-issue-to-pr.md). It takes one feature from a written task to a green pull request in a throwaway repo.

The [docs home](docs/README.md) lists everything:

- **Tutorial:** [Ship your first change with Pixie](docs/tutorial/first-issue-to-pr.md)
- **How-to guides:** [set up a repo](docs/how-to/set-up-a-repo.md), [fix a bug](docs/how-to/fix-a-bug.md), [clean up hotspots](docs/how-to/clean-up-hotspots.md), [find bugs and UX gaps](docs/how-to/find-ux-bugs.md), [review someone else's PR](docs/how-to/review-a-pr.md), [design a feature](docs/how-to/design-a-feature.md), [prune a test suite](docs/how-to/prune-a-test-suite.md), [tune the code-health hook](docs/how-to/tune-the-code-health-hook.md)
- **Reference:** [skills](docs/reference/skills.md), [labels, branches, and files](docs/reference/labels-and-branches.md), [agents and the code-health hook](docs/reference/agents-and-hook.md)
- **Explanation:** [How Pixie works](docs/explanation/how-pixie-works.md)

# Pixie documentation

Pixie is a Claude Code plugin with skills for planning, understanding, refactoring, and shipping code. It works from GitHub issues and pull requests.

Install it first. See [Prerequisites](../README.md#prerequisites) and [Install the plugin](../README.md#install-the-plugin) in the main README.

## Start here

1. **[Tutorial: Ship your first change with Pixie](tutorial/first-issue-to-pr.md).** Take a feature from a one-line task to a green PR in a throwaway repo. About 20 minutes.
2. **[How Pixie works](explanation/how-pixie-works.md).** How the skills fit together, and why they behave as they do.
3. The how-to guides below, when you have a specific job to do.

## Pick a skill by goal

| I want to... | Use | Guide |
|---|---|---|
| Use my repo's own label names, or check my tools | `setup` | [Set up a repo](how-to/set-up-a-repo.md) |
| Understand how part of the code works | `how` | [Skills reference](reference/skills.md#how) |
| Turn a task into a plan and an issue | `plan-task` | [Tutorial](tutorial/first-issue-to-pr.md) |
| Have an agent build an issue | `tackle` | [Tutorial](tutorial/first-issue-to-pr.md) |
| Get my open PRs mergeable | `babysit` | [Tutorial](tutorial/first-issue-to-pr.md) |
| Fix a bug I understand | `tdd mode=bug` | [Fix a bug](how-to/fix-a-bug.md) |
| Find out why something is broken | `diagnose` | [Fix a bug](how-to/fix-a-bug.md) |
| Build a change test-first | `tdd` | [Skills reference](reference/skills.md#tdd) |
| See how healthy the code is | `code-health` | [Clean up hotspots](how-to/clean-up-hotspots.md) |
| Refactor messy code | `untangle` | [Clean up hotspots](how-to/clean-up-hotspots.md) |
| Find bugs and UX gaps in the running app | `poke` | [Find bugs and UX gaps](how-to/find-ux-bugs.md) |
| Let agents drive my app | `create-verifier`, `maintain-verifier` | [Find bugs and UX gaps](how-to/find-ux-bugs.md) |
| Remove redundant tests | `prune-tests` | [Prune a test suite](how-to/prune-a-test-suite.md) |
| Audit the code for security, performance and bugs | `checkup` | [Audit a codebase](how-to/audit-a-codebase.md) |
| Turn production errors into issues | `catch` | [Turn production errors into issues](how-to/turn-production-errors-into-issues.md) |
| Run `checkup` and `catch` on a schedule | `checkup`, `catch` | [Schedule checkup and catch](how-to/schedule-checkup-and-catch.md) |
| Get Claude's last reply in plain words | `huh` | [Skills reference](reference/skills.md#huh) |
| Change or turn off the edit hook | — | [Tune the code-health hook](how-to/tune-the-code-health-hook.md) |

## All docs

**Tutorial**

- [Ship your first change with Pixie](tutorial/first-issue-to-pr.md)

**How-to guides**

- [Set up a repo for Pixie](how-to/set-up-a-repo.md)
- [Fix a bug](how-to/fix-a-bug.md)
- [Clean up hotspots](how-to/clean-up-hotspots.md)
- [Find bugs and UX gaps in a running app](how-to/find-ux-bugs.md)
- [Prune a test suite](how-to/prune-a-test-suite.md)
- [Audit a codebase with checkup](how-to/audit-a-codebase.md)
- [Turn production errors into issues with catch](how-to/turn-production-errors-into-issues.md)
- [Schedule checkup and catch](how-to/schedule-checkup-and-catch.md)
- [Tune the code-health hook](how-to/tune-the-code-health-hook.md)

**Reference**

- [Skills](reference/skills.md)
- [Labels, branches, and files](reference/labels-and-branches.md)
- [Agents and the code-health hook](reference/agents-and-hook.md)
- [checkup and catch settings](reference/checkup-config.md)
- [Live checks](reference/live-checks.md)

**Explanation**

- [How Pixie works](explanation/how-pixie-works.md)

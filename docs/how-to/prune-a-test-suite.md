# How to prune a test suite

This guide shows you how to remove redundant tests from a large suite without making it weaker. The `prune-tests` skill works on **one area** at a time, such as a folder, module, or namespace. It never works on the whole suite at once.

## Before you start

- Commit your work. `prune-tests` stops if the working tree isn't clean. It works on a new branch made from the remote default branch.
- Check for a coverage driver and a mutation testing tool in the project:

  | Stack | Coverage driver | Mutation tool |
  |---|---|---|
  | PHP | pcov or xdebug | Infection |
  | TypeScript | v8 or istanbul | Stryker |
  | Python | coverage.py | mutmut |
  | Rust | cargo-llvm-cov | cargo-mutants |

  Mutation testing makes small changes to your code and checks that some test fails for each one. If a tool is missing, Claude offers to add it as a dev dependency.
- To run unattended, you also need `gh`, because that mode opens a PR. The automation must also allow `git switch`, `git add`, `git commit`, `git reset`, `git push`, and `gh pr create`.

## Prune one area

Name the area:

```text
/pixie:prune-tests tests/Billing
```

If you leave it out, Claude asks.

Claude will:

1. Create a `prune-tests/<area>` branch. If that branch already exists, it stops.
2. Record a baseline: the starting commit, test results, per-test coverage, and a mutation score for the area. These go in a `.prune/` folder that git ignores.
3. Sort tests into groups: covered by another test, testing library behavior, near-duplicates, mock-only, trivial, or too fine-grained.
4. Show you a summary and the medium- and high-risk changes. **It waits for your approval here.**
5. Apply the approved changes, one commit per group.
6. Re-check coverage and the mutation score. If either dropped, it restores the tests responsible. After two rounds of restoring, it asks you what to do.
7. Report the results and offer to push the branch and open a PR. If some tests need a human, it offers to file them as GitHub issues for `tackle`.

Some tests are kept by default. These include bug-fix regression tests, the only test covering a line, the only test that catches a mutant, and tests for security, auth, money, data loss, or migrations.

If the mutation run for the area would take more than about 30 minutes, Claude splits the area smaller.

## Run it unattended

For a scheduled or automated run, put "unattended" in the prompt:

```text
/pixie:prune-tests unattended
```

In this mode Claude:

- Picks the area itself. It skips areas that already have an open `prune-tests/*` PR, or one merged in the last 30 days. It favors the area with the most tests per line of source.
- Never asks questions. When a choice is unclear, it keeps the test.
- Applies only low- and medium-risk changes. It lists the rest under "Needs human review" in the PR.
- Stops and reports if a coverage or mutation tool is missing. It won't install tools in this mode.
- Opens a PR with the results. If it can't restore the safety checks, it resets the branch to the starting commit and opens no PR. Run `/pixie:babysit` to get the PR green.

## Related

- [`prune-tests` reference](../reference/skills.md#prune-tests)

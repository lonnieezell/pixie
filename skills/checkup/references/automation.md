# Running checkup and catch on a schedule

Two example GitHub Actions workflows: a weekly `checkup` and a daily `catch`. Both can hand promoted issues to `tackle`, one process per issue. `checkup` and `catch` can't start `tackle` themselves, because `tackle` only runs when a user (or this workflow) types it.

These are starting points. Check the Claude Code install and plugin commands against the current Claude Code docs before relying on them.

## Secrets and variables

| Name | Kind | Used for |
|---|---|---|
| `ANTHROPIC_API_KEY` | secret | Claude Code |
| `PIXIE_GH_TOKEN` | secret | A fine-grained token or GitHub App token with contents, issues and pull requests write access. PRs opened with the default `GITHUB_TOKEN` don't trigger your CI workflows, so `tackle`'s PRs would never get checks. Creating security advisories also needs a repo admin or security manager. |
| `SENTRY_AUTH_TOKEN` | secret | `catch`, if Sentry is configured |
| `CORALOGIX_API_KEY` | secret | `catch`, if Coralogix is configured |
| `PIXIE_AUTOFIX` | variable | Set to `true` to pass `fix` on scheduled runs |

## Permissions

The runner is a throwaway VM, so these examples skip Claude Code's permission prompts with `--dangerously-skip-permissions`. That lets every tool run without asking. Keep the job's token limited to this one repo, and don't add secrets the job doesn't need. If you'd rather allow-list tools, replace the flag with `--allowedTools`. The run needs `python3`, `git`, `gh`, your test runner and your linters.

Don't upload `ai/` as an artifact on a public repo. The report names unfixed security findings. The scores already appear in the baseline PR.

## Weekly checkup

`.github/workflows/checkup.yml`:

```yaml
name: checkup
on:
  schedule:
    - cron: "0 6 * * 1"   # Mondays 06:00 UTC
  workflow_dispatch:
    inputs:
      fix:
        type: boolean
        default: false

permissions:
  contents: read

concurrency:
  group: pixie-checkup
  cancel-in-progress: false

jobs:
  checkup:
    runs-on: ubuntu-latest
    timeout-minutes: 180
    env:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      GH_TOKEN: ${{ secrets.PIXIE_GH_TOKEN }}
      FIX: ${{ (github.event_name == 'workflow_dispatch' && inputs.fix) || vars.PIXIE_AUTOFIX == 'true' }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.PIXIE_GH_TOKEN }}
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      # Add your project's runtime setup here (PHP + composer install, npm ci, ...) so tests can run.
      - name: Install Claude Code and Pixie
        run: |
          npm install -g @anthropic-ai/claude-code
          claude plugin marketplace add lonnieezell/pixie
          claude plugin install pixie@pixie
      - name: Git identity
        run: |
          git config user.name "pixie-bot"
          git config user.email "pixie-bot@users.noreply.github.com"
      - name: Checkup
        run: claude -p "/pixie:checkup unattended $([ "$FIX" = true ] && echo fix)" --dangerously-skip-permissions
      - name: Tackle promoted issues
        if: env.FIX == 'true'
        run: |
          RUN=$(ls -d ai/checkup/*/ | sort | tail -1)
          for n in $(jq -r '.promoted[]?' "$RUN/promoted.json" 2>/dev/null); do
            claude -p "/pixie:tackle $n unattended" --dangerously-skip-permissions || echo "tackle $n stopped; see the issue"
          done
      # Weekly runs audit only changed shards. A full run (`unattended full`) re-hunts every shard: findings newly found
      # in unchanged code don't count as a regression, but score drops can still be noisy. Raise scoreDropThreshold if this fails without a real change.
      - name: Fail on regression
        run: |
          RUN=$(ls -d ai/checkup/*/ | sort | tail -1)
          jq -e '.comparison.regressed | not' "$RUN/findings.json"
```

## Daily catch

`.github/workflows/catch.yml` is the same as above, except:

```yaml
on:
  schedule:
    - cron: "0 7 * * *"

    env:
      SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
      CORALOGIX_API_KEY: ${{ secrets.CORALOGIX_API_KEY }}

      - name: Catch
        run: claude -p "/pixie:catch unattended $([ "$FIX" = true ] && echo fix)" --dangerously-skip-permissions
      - name: Tackle promoted issues
        if: env.FIX == 'true'
        run: |
          RUN=$(ls -d ai/catch/*/ | sort | tail -1)
          for n in $(jq -r '.promoted[]?' "$RUN/promoted.json" 2>/dev/null); do
            claude -p "/pixie:tackle $n unattended" --dangerously-skip-permissions || echo "tackle $n stopped; see the issue"
          done
```

Keep `concurrency.group: pixie-checkup` the same in both workflows, so `checkup` and `catch` never run at once and can't both spend the weekly PR cap. It has no regression step. Set `catch.lookback` to match the schedule (`24h` for daily) so each run sees every error once. A recurring error comments on its existing issue at most once a week.

## What a run leaves behind

- Issues labeled `needs-triage`, or `ready-for-agent` when auto-fix promoted them
- A rolling `checkup/baseline` PR (checkup only)
- `tackle` branches and PRs for promoted issues. Run `/pixie:babysit` to bring them to green.

Nothing is ever merged, approved or closed.

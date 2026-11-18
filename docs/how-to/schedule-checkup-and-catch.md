# How to schedule checkup and catch

This guide shows you how to run `checkup` every week and `catch` every day without anyone at the keyboard, using GitHub Actions on a throwaway runner.

The workflows pass `unattended`, so the skills never ask questions. They file issues, and `checkup` publishes its baseline PR. Neither skill ever merges, approves or closes anything.

## Decide on auto-fix first

`checkup` and `catch` take `fix` to queue proven findings as `ready-for-agent`. Neither can start `tackle` itself, because `tackle` only runs when someone (or a workflow) types it. So with `fix`, you also need a step that runs `/pixie:tackle N` for each queued issue.

Leave `fix` off at first. Turn it on once you trust the issues the runs file.

## GitHub Actions

### 1. Add secrets and a variable

In the repo's **Settings → Secrets and variables → Actions**, add:

| Name | Kind | Used for |
|---|---|---|
| `ANTHROPIC_API_KEY` | secret | Claude Code |
| `PIXIE_GH_TOKEN` | secret | A fine-grained token or GitHub App token for this repo, with contents, issues and pull requests write access. Don't use the default `GITHUB_TOKEN`: PRs opened with it don't trigger your CI, so `tackle`'s PRs would never get checks. Creating security advisories also needs a repo admin or security manager. |
| `SENTRY_AUTH_TOKEN` | secret | `catch`, if you use Sentry |
| `CORALOGIX_API_KEY` | secret | `catch`, if you use Coralogix |
| `PIXIE_AUTOFIX` | variable | Set to `true` to pass `fix` on scheduled runs |

### 2. Add the weekly checkup workflow

Create `.github/workflows/checkup.yml`:

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
      - name: Fail on regression
        run: |
          RUN=$(ls -d ai/checkup/*/ | sort | tail -1)
          jq -e '.comparison.regressed | not' "$RUN/findings.json"
```

Things to adjust:

- **Runtime setup.** Add the steps your project needs so its tests and linters run, such as `composer install` or `npm ci`. The run needs `python3`, `git`, `gh`, `jq`, your test runner and your linters.
- **Incremental runs.** `unattended` audits only the shards that changed since the baseline, and reuses the findings for the rest, so a quiet week costs little. The first run, with no baseline yet, audits everything. Unchanged code is never hunted again on its own, so add a second, rarer schedule (monthly, say) that runs `/pixie:checkup unattended full`.
- **The regression step.** It fails the job when the run regressed. A full run re-hunts every shard, and hunters don't find exactly the same things each time, so scores can wobble. If the job fails without a real change, raise `scoreDropThreshold`.
- **Install commands.** Check the Claude Code install and plugin commands against the current Claude Code docs.

### 3. Add the daily catch workflow

Copy `checkup.yml` to `.github/workflows/catch.yml`, then make these changes:

1. Set the schedule to daily: `cron: "0 7 * * *"`.
2. Add the tracker tokens to the job's `env`:

   ```yaml
         SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
         CORALOGIX_API_KEY: ${{ secrets.CORALOGIX_API_KEY }}
   ```

3. Replace the last three steps with:

   ```yaml
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

`catch` has no scores, so it has no regression step.

Keep `concurrency.group: pixie-checkup` the same in both files. Then `checkup` and `catch` never run at once, and can't both spend the weekly PR cap.

### 4. Test it

Run the `checkup` workflow by hand from the **Actions** tab, with `fix` off. Check the issues it filed and the `checkup/baseline` PR.

### About the permissions flag

The runner is a throwaway VM, so the workflows skip Claude Code's permission prompts with `--dangerously-skip-permissions`. Every tool runs without asking. Keep the token limited to this one repo, and don't give the job secrets it doesn't need. If you'd rather allow-list tools, replace the flag with `--allowedTools`.

Don't upload `ai/` as a workflow artifact on a public repo. The report names unfixed security findings.

## What a run leaves behind


- Issues labeled `needs-triage`, or `ready-for-agent` when auto-fix queued them
- A rolling `checkup/baseline` PR, for whole-repo `checkup` runs. Merge it when you accept the scores.
- `tackle` branches and PRs for queued issues, if you run `tackle`. Run `/pixie:babysit` to bring them to green.

Set `catch.lookback` to match the schedule, such as `24h` for a daily run, so each run sees every error once.

## Related

- [Audit a codebase with checkup](audit-a-codebase.md)
- [Turn production errors into issues](turn-production-errors-into-issues.md)
- [checkup and catch settings](../reference/checkup-config.md)

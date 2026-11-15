# checkup and catch settings

`checkup` and `catch` read `docs/agents/checkup.json`. Every key is optional, and missing keys use the defaults below. Commit the file, so scheduled runs use the same settings.

## Defaults

```json
{
  "maxPrsPerWeek": 3,
  "maxIssuesPerRun": 10,
  "fileSeverities": ["critical", "high"],
  "securityFindings": "auto",
  "scoreDropThreshold": 5,
  "shardSize": 20,
  "maxShards": 40,
  "maxFindingsPerHunter": 8,
  "includeTests": false,
  "exclude": ["vendor/", "node_modules/", "target/", "dist/", "build/", ".next/", "writable/", "storage/", "coverage/", "tests/fixtures/"],
  "autoFix": { "severities": ["critical", "high"], "maxTier": 2 },
  "catch": {
    "lookback": "24h",
    "maxReports": 20,
    "minEvents": 10,
    "sentry": { "baseUrl": "https://sentry.io", "org": "", "projects": [], "environment": "" },
    "coralogix": {
      "domain": "",
      "query": "source logs | filter $m.severity == ERROR || $m.severity == CRITICAL | limit 2000",
      "messageFields": ["message", "msg", "error.message", "exception.message", "log"],
      "stackFields": ["stack", "stacktrace", "stack_trace", "error.stack", "exception.stacktrace"]
    }
  }
}
```

## Filing and auto-fix

| Key | Default | Meaning |
|---|---|---|
| `maxPrsPerWeek` | `3` | Most issues moved to `ready-for-agent` for auto-fix in any 7 days, by `checkup` and `catch` together. It's counted from GitHub, so it holds on CI runners that start fresh. |
| `maxIssuesPerRun` | `10` | Most new issues one run creates. Comments on existing issues don't count. |
| `fileSeverities` | `["critical", "high"]` | Severities that get an issue. Findings at other severities stay in the report. |
| `securityFindings` | `"auto"` | Where security findings go: `issues`, `advisory` (private draft security advisories), `report-only` (the local report only), or `auto`. `auto` means `issues` on private and internal repos, and `advisory` on public ones. When it resolves to anything but `issues`, the baseline keeps only the security findings' counts by severity. |
| `autoFix.severities` | `["critical", "high"]` | Severities that can be auto-fixed |
| `autoFix.maxTier` | `2` | Highest `tackle` tier, 1 to 3, that can be auto-fixed |

An issue is auto-fixed only when its finding is confirmed with high confidence, has a reproduction test that fails, sits within these limits, and the issue is still untriaged. Auto-fix only runs when you pass `fix`.

## Scope and cost

| Key | Default | Meaning |
|---|---|---|
| `shardSize` | `20` | Most files per hunter job. A folder that fits stays one shard. In a bigger folder, small subfolders and loose files are packed together, so a shard can span neighboring folders, such as `src[Auth..Cart]`. Smaller shards mean more agents, but sharper reviews. |
| `maxShards` | `40` | Most shards audited per run, busiest by git churn first. The rest are listed as gaps, never as clean. Their baseline findings carry over as stale, and the next run audits them. |
| `maxFindingsPerHunter` | `8` | Cap per hunter, so one noisy shard can't flood the run |
| `includeTests` | `false` | Audit test files too |
| `exclude` | see above | Path fragments to skip. A fragment matches anywhere in the path. Your list is added to the defaults. It doesn't replace them. |

A full run starts 3 hunters per shard, one per dimension, plus one verifier for each finding not hinted `low`. With `fix`, it adds up to `maxPrsPerWeek` provers and classifiers.

## Scores

Each dimension scores from 0 to 100:

```text
penalty = sum of the weights of confirmed findings   (critical 25, high 10, medium 3, low 1)
score   = round(100 / (1 + penalty / (4 × KLOC)))
```

`KLOC` is non-blank source lines divided by 1000, and at least 1.

| Example, in 10 KLOC | Score |
|---|---|
| No findings | 100 |
| One high finding | 80 |
| One critical finding | 62 |

Only verified findings count, so scores only move with confirmed evidence. A finding closed as not planned keeps counting, because the risk is still there. It's the same every week, so it never causes a regression.

`health` is `km`'s overall score. It's shown for reference when `km` is installed, and isn't part of the regression check.

### Regressions

| Key | Default | Meaning |
|---|---|---|
| `scoreDropThreshold` | `5` | Drop in points that counts as a regression |

A run regresses when either of these is true:

- A new confirmed high or critical finding appears in a shard whose code changed since the baseline.
- A score drops by more than `scoreDropThreshold`.

When the baseline leaves out security findings, the security dimension also regresses when it has more high or critical findings than the baseline.

A new finding in unchanged code is reported as newly found, not as a regression. `scores` runs reuse results for unchanged shards. Full runs re-hunt everything, so their scores are noisier.

## catch

| Key | Default | Meaning |
|---|---|---|
| `lookback` | `"24h"` | Window to query: a number and `m`, `h`, `d` or `w`, such as `24h` or `7d`. Match it to your schedule. |
| `maxReports` | `20` | Most error groups triaged per run |
| `minEvents` | `10` | Fewest events an error group needs to be triaged. For Sentry, this is the issue's `count`, which Sentry's docs don't say is limited to the lookback window. For Coralogix, it's counted from the rows the query returns, so the query's `limit` caps it. |
| `sentry.baseUrl` | `"https://sentry.io"` | `https://sentry.io`, your region's host, or your self-hosted URL |
| `sentry.org` | `""` | Organization slug. Setting it turns Sentry on. |
| `sentry.projects` | `[]` | Project slugs or IDs. Empty means every project. |
| `sentry.environment` | `""` | Limit to one environment, such as `production`. Empty means all. |
| `coralogix.domain` | `""` | Your region's Coralogix domain, such as `eu2.coralogix.com`, not your team's login host. Setting it turns Coralogix on. The API host is `api.` followed by the domain. |
| `coralogix.query` | see above | DataPrime query for error logs. Check it in Coralogix's explorer first. The default is a starting point. |
| `coralogix.messageFields` | see above | Dotted paths in your log JSON where the message lives, tried in order |
| `coralogix.stackFields` | see above | Dotted paths in your log JSON where the stack trace lives, tried in order |

## Environment variables

Tokens come from the environment, never from the config file.

| Variable | Used by | Needs |
|---|---|---|
| `SENTRY_AUTH_TOKEN` | `catch` | An internal-integration or personal token with `event:read` |
| `CORALOGIX_API_KEY` | `catch` | A key with the `DataQuerying` preset (`LOGS.DATA-API#HIGH:READDATA`) |

## Related

- [Audit a codebase with checkup](../how-to/audit-a-codebase.md)
- [Turn production errors into issues](../how-to/turn-production-errors-into-issues.md)
- [Schedule checkup and catch](../how-to/schedule-checkup-and-catch.md)
- [Labels, branches, and files](labels-and-branches.md)

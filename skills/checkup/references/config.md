# Configuration

`checkup` and `catch` read `docs/agents/checkup.json`. Every key is optional. Missing keys use the defaults below. Commit the file so scheduled runs use the same settings.

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

| Key | Meaning |
|---|---|
| `maxPrsPerWeek` | Most issues promoted to `ready-for-agent` for auto-fix in any 7 days, across `checkup` and `catch` together. Counted from GitHub, so it holds on CI runners that start fresh. |
| `maxIssuesPerRun` | Most new issues one run creates. Comments on existing issues don't count. |
| `fileSeverities` | Severities that get an issue. Others stay in the report. |
| `securityFindings` | `issues` (company repos), `advisory` (private draft security advisories), `report-only` (the local report only), or `auto`: `issues` on private and internal repos, `advisory` on public ones. When it resolves to anything but `issues`, the baseline leaves security findings out and keeps only their counts by severity. |
| `autoFix.severities` | Severities that can be auto-fixed |
| `autoFix.maxTier` | Highest `tackle` tier (1–3) that can be auto-fixed |

A finding is auto-fixed only when it's confirmed with high confidence, has a failing reproduction test (rung 4), sits within these limits, and its issue is still untriaged. Auto-fix runs only when `fix` is passed.

## Scope and cost

| Key | Meaning |
|---|---|
| `shardSize` | Most files per hunter job. A folder that fits stays one shard. In a bigger folder, small subfolders and loose files are packed together, so a shard can span neighbouring folders, e.g. `src[Auth..Cart]`. Smaller shards mean more agents but sharper reviews. |
| `maxShards` | Most shards audited per run. The busiest shards by git churn go first. The rest are listed as gaps, never as clean: their baseline findings carry over as stale, and they keep their old baseline hash so a later run audits them. |
| `maxFindingsPerHunter` | Cap per hunter, so one noisy shard can't flood the run |
| `includeTests` | Audit test files too |
| `exclude` | Path fragments to skip. A fragment matches anywhere in the path. Your list adds to the defaults above. It doesn't replace them. |

A full run starts 3 hunters per shard (one per dimension), plus one verifier for each finding not hinted `low`. With `fix`, it adds up to `maxPrsPerWeek` provers and classifiers.

## Scores

Each dimension scores 0–100:

```
penalty = sum of weights of confirmed findings   (critical 25, high 10, medium 3, low 1)
score   = round(100 / (1 + penalty / (4 × KLOC)))   (KLOC = non-blank source lines / 1000, at least 1)
```

No findings scores 100. In 10 KLOC, one high finding scores 80 and one critical scores 62. Only verified findings count, so scores move only with confirmed evidence. A finding closed as not planned keeps counting, because the risk is still there, but it's stable from week to week and doesn't cause a regression.

`scoreDropThreshold` is the drop, in points, that counts as a regression. Hunters are LLMs and won't find exactly the same things every run. Three rules keep that noise from failing the check:

- The score drop has to beat the threshold.
- A new confirmed high or critical finding is a regression only when its shard's code changed since the baseline. One found in unchanged code was missed last time, not introduced, so the report lists it as newly found instead.
- `scores` runs reuse results for unchanged shards. Full runs re-hunt everything, so they're noisier on scores.

When the baseline withholds security findings, the security dimension regresses when it has more high or critical findings than the baseline, or when its score drop beats the threshold.

`health` is `km`'s overall score, shown for reference when `km` is installed. It isn't part of the regression check.

## catch

| Key | Meaning |
|---|---|
| `lookback` | Window to query: a number and `m`, `h`, `d` or `w`, such as `24h` or `7d` |
| `maxReports` | Most error groups triaged per run |
| `minEvents` | Smallest event count worth triaging. For Sentry this is the issue's `count`, which Sentry's docs don't say is limited to the lookback window. For Coralogix it's counted from the rows the query returns, so the query's `limit` caps it (2000 by default, at most 12,000 on frequent search). |
| `sentry.baseUrl` | `https://sentry.io`, your region's host, or your self-hosted URL |
| `sentry.org`, `sentry.projects` | Organization slug, and project slugs or IDs. Setting `org` turns Sentry on. |
| `sentry.environment` | Limit to one environment, such as `production` |
| `coralogix.domain` | Your region's Coralogix domain, such as `eu2.coralogix.com`, not your team's login host. Setting it turns Coralogix on. The API host is `api.` followed by the domain. |
| `coralogix.query` | DataPrime query for error logs. Check it in Coralogix's explorer first. The default is a starting point. |
| `coralogix.messageFields`, `coralogix.stackFields` | Dotted paths in your log JSON where the message and stack trace live, tried in order |

Tokens come from the environment, never from this file:

| Variable | Needs |
|---|---|
| `SENTRY_AUTH_TOKEN` | An internal-integration or personal token with `event:read` |
| `CORALOGIX_API_KEY` | A key with the `DataQuerying` preset (`LOGS.DATA-API#HIGH:READDATA`) |

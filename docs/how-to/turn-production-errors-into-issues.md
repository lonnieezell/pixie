# How to turn production errors into issues with catch

This guide shows you how to connect `catch` to Sentry or Coralogix, run it, and handle what it finds. `catch` pulls recent errors, traces each one into the current code, and files the real ones as GitHub issues that `tackle` can fix.

`catch` uses the same verifier, filing and auto-fix steps as `checkup`. So an error in code `checkup` already flagged lands on the same issue, not a new one.

`catch` only runs when you type it.

## Before you start

- You need `gh`, logged in with write access to the repo. Without it, `catch` still triages errors and writes a report, but files nothing.
- You need a Sentry or Coralogix account, and a token that can read errors. You can use both.

## 1. Configure your error tracker

Settings go in `docs/agents/checkup.json`, which `checkup` also reads. Create the file if it doesn't exist. Commit it, so scheduled runs use the same settings.

Tokens never go in this file. They come from the environment.

### Sentry

Add your organization slug. Setting `org` turns Sentry on:

```json
{
  "catch": {
    "sentry": {
      "org": "acme",
      "projects": ["web"],
      "environment": "production"
    }
  }
}
```

- `projects` takes project slugs or IDs. Leave it empty for every project in the organization.
- `environment` limits `catch` to one environment. Leave it empty for all of them.
- If you don't use `sentry.io`, set `baseUrl` to your region's host or your self-hosted URL.

Then create a token with the `event:read` scope, either an internal-integration token or a personal token, and export it:

```bash
export SENTRY_AUTH_TOKEN=...
```

### Coralogix

Add your region's Coralogix domain, such as `eu2.coralogix.com`. Use the region domain, not your team's login host. Setting `domain` turns Coralogix on:

```json
{
  "catch": {
    "coralogix": {
      "domain": "eu2.coralogix.com"
    }
  }
}
```

The default query fetches logs with severity `ERROR` or `CRITICAL`. Before you rely on it, run it in Coralogix's explorer and adjust it for your logs:

```text
source logs | filter $m.severity == ERROR || $m.severity == CRITICAL | limit 2000
```

If your logs keep the message or the stack trace under other fields, add them to `messageFields` or `stackFields`. See [the catch settings](../reference/checkup-config.md#catch).

Then create an API key with the `DataQuerying` preset and export it:

```bash
export CORALOGIX_API_KEY=...
```

## 2. Run catch

From the repo root:

```text
/pixie:catch
```

Claude will:

1. Fetch error groups from the last 24 hours that have at least 10 events, up to 20 groups. It removes emails, tokens, IPs and long secrets, and never fetches request bodies, headers, cookies, user data or breadcrumbs.
2. Skip errors that look fixed already (see [step 3](#3-check-the-skipped-reports)).
3. Start one read-only agent per error. It traces the stack frames into the current code and writes a finding.
4. Send every finding to a separate verifier that tries to prove it wrong, and sets its severity. Errors that hit many users or a main flow in production go up one severity level.

If one source fails, such as a missing token, `catch` says so and carries on with the other.

To look further back, or include rarer errors, change `lookback`, `minEvents` and `maxReports`.

## 3. Check the skipped reports

Claude's summary at the end of the run lists the errors `catch` didn't file, and why. The run's files are in `ai/catch/DATE-HHMM/`.

- **Possibly fixed:** the code around the error changed since the release where it happened. If the error has no release commit, the file was committed after the error was last seen. Check that the fix shipped. Then resolve the error in your tracker.
- **Blocked:** the agent found no app code to blame, such as an infrastructure failure, a third-party outage, or a config problem. These need a human.
- **Refuted** or **needs-human:** the verifier didn't accept the finding.

## 4. File and triage the issues

Claude lists the confirmed findings it would file, and asks once. Say yes, and each one becomes a `needs-triage` issue with a "Production impact" section showing the event and user counts. If the repo has a verification skill, Claude also tries to reproduce the error on a local copy of the app, never in production. When it can, the issue has a "Reproduced in the running app" section.

Triage them the same way as `checkup` issues. See [Triage each issue](audit-a-codebase.md#4-triage-each-issue).

When an error comes back, `catch` doesn't open a new issue. It comments "still present" with the latest counts on the open issue, at most once a week.

## 5. Let agents fix proven errors

Add `fix` to queue proven errors for `tackle`:

```text
/pixie:catch fix
```

An error seen only in production is never enough for auto-fix. An agent must first write a test that fails on it locally. The same rules and the same weekly cap apply as for `checkup`. See [Let agents fix proven findings](audit-a-codebase.md#8-let-agents-fix-proven-findings).

## 6. Resolve the error in your tracker

`catch` never changes anything in Sentry or Coralogix. Once the fix ships, resolve the error there yourself.

## Next steps

- Run `catch` every day without you: [Schedule checkup and catch](schedule-checkup-and-catch.md).
- Every `catch` setting: [checkup and catch settings](../reference/checkup-config.md#catch).

## Related

- [`catch` reference](../reference/skills.md#catch)
- [Why error text is treated as untrusted](../explanation/how-pixie-works.md#audits-trust-only-what-survives)

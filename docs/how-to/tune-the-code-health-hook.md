# How to tune the code-health hook

Pixie's code-health hook checks every file Claude edits. It reports problems the edit added, such as a function that got too complex. This guide shows you how to change its limits, or turn it off.

The hook needs km on the `PATH` that Claude Code sees. Without km, the hook does nothing and stays silent.

## Change a limit for all projects

Set an environment variable in the `env` block of your Claude Code settings, such as `~/.claude/settings.json`:

```json
{
  "env": {
    "CODE_HEALTH_COGCOM_MAX": "20",
    "CODE_HEALTH_FILE_LINES": "800"
  }
}
```

Restart Claude Code for the change to take effect.

The variables are:

| Variable | Default | What it controls |
|---|---|---|
| `CODE_HEALTH_COGCOM_MAX` | `15` | Highest cognitive complexity allowed for a function |
| `CODE_HEALTH_COGCOM_JUMP` | `8` | Largest increase in a function's complexity allowed in one edit |
| `CODE_HEALTH_FILE_LINES` | `500` | Largest file size, in lines |
| `CODE_HEALTH_HOOK` | (on) | Set to `off` to turn the hook off everywhere |

To change a limit for one project only, put the `env` block in that project's `.claude/settings.json` instead.

## Turn the hook off

**For one repo:** create an empty `.code-health-off` file at the repo's root.

```bash
touch .code-health-off
```

**Everywhere:** set `CODE_HEALTH_HOOK` to `off` in your user settings:

```json
{
  "env": {
    "CODE_HEALTH_HOOK": "off"
  }
}
```

## Tune km's own thresholds for a repo

Run this at the repo's root:

```bash
km init
```

It writes a `.kimun.toml` file tuned to that repo. It sets thresholds, folders to skip, and the grade a change must meet. The `code-health` and `untangle` skills use these settings instead of their defaults.

## Related

- [Agents and the code-health hook](../reference/agents-and-hook.md)
- [How to clean up hotspots](clean-up-hotspots.md)

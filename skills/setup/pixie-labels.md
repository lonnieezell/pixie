# Pixie labels

Pixie's skills name four label roles. This file maps each role to the label this repo uses. Edit the "Label in this repo" column to rename one, then create the new label in GitHub or rerun `/pixie:setup`.

| Role | Label in this repo | Meaning |
|---|---|---|
| `ready-for-agent` | `ready-for-agent` | Queued for an agent |
| `agent-working` | `agent-working` | An agent has claimed it |
| `agent-pr` | `agent-pr` | A PR is open for it |
| `agent-blocked` | `agent-blocked` | An agent stopped and needs a human. Its comment says why. |

When a Pixie skill names a role, use the label from the second column.

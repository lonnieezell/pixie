# Decision record template

`/design` writes one record per run to `docs/design/decisions/YYYY-MM-DD-SLUG.md`, with its screenshots in the folder beside it. A later reader, human or agent, uses it to see what was tried, what won and why, without rerunning anything. Link screenshots by relative path. Describe what they show in words too, since the folder may be gitignored.

````markdown
# Design decision: WHAT

- **Date:** YYYY-MM-DD, commit SHORT_SHA
- **Chosen:** NAME (or "a blend of NAME and NAME")
- **Winner's preview:** `/__preview/SLUG-NAME` in `PATH` (or "not kept: temporary harness")
- **Captured with:** Playwright / BROWSER MCP, widths 390 and 1280

## Frame

- **Who and what for:** WHO, doing TASK
- **Data:** the shapes and ranges that mattered
- **Neighbours:** the screens compared against

## Axes

| Axis | Poles |
|---|---|
| Density | compact ↔ roomy |
| Disclosure | everything at once ↔ progressive |

## Directions

### NAME (chosen)

- **Position:** Density compact, Disclosure everything at once
- **Built from:** `Table`, `Badge`, `Button`
- **New components:** `OrderSummary`, because REASON (or "none")
- **Trade-off:** ONE SENTENCE
- **Gates:** axe 0, raw values 0 (after N fixes: WHAT WAS FIXED)
- **Critique:** N rounds. Remaining: S3 `ID` TITLE (or "none")
- **Screenshots:** [typical, 1280](YYYY-MM-DD-SLUG/NAME-typical-1280.png), [typical, 390](YYYY-MM-DD-SLUG/NAME-typical-390.png)

### NAME (Wildcard: breaks CONVENTION)

...

## Why NAME

The user's reasons, in their words where they gave them, and what the evidence showed: which findings and trade-offs decided it, and anything taken from the other directions in a blend.

## Not checked

Anything a gate or critic couldn't cover: the axe gate in browser-MCP mode, states that couldn't be captured, rejected critic findings with their reasons.

## Next

Build NAME into production code, using the preview's states as the behaviour to test.
````

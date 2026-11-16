# Core design rubric

The checks the `design-critic` agent applies to screenshots. Every item can be judged from a screenshot alone, with no code. A finding cites one item by its ID. `critique.py` reads the IDs from the first column, so keep each one in backticks.

A repo can change this list in its inventory's `## Rubric overrides`. A ``- drop: `ID` `` line suppresses every finding that cites that item, and any other line is a house rule the critic follows. Overrides win over this file.

## Severity

| Severity | Meaning |
|---|---|
| S1 | A user can't do the screen's main task, or can't read or reach part of it (content cut off, controls covered, unreadable text). |
| S2 | The screen works but misleads or slows users in a common case: the wrong thing looks primary, state is shown by colour alone, a target is too small to tap. |
| S3 | Inconsistent or rough: misaligned, uneven spacing, differs from neighbouring screens. |
| S4 | Polish. |

The typical severity below is a starting point. Raise or lower it for what the screenshot shows, and say why in the finding.

## Items

| ID | Check | Typical severity |
|---|---|---|
| `layout.overflow` | No text or element is clipped, overlaps another, or runs off the screen at this width. | S1 |
| `layout.reflow` | At the narrow width the layout reflows (stacked columns, a scrollable or card-style table). Nothing is just shrunk to fit. | S2 |
| `layout.alignment` | Elements that share a row or column share an edge. Nothing is off by a few pixels. | S3 |
| `layout.spacing` | Gaps inside a group are smaller than gaps between groups, and the same kind of gap is the same size everywhere. | S3 |
| `hierarchy.heading` | One page heading stands out, and heading sizes step down in order. | S3 |
| `hierarchy.primary-action` | The screen's main action is the most prominent control, and there's only one. Secondary actions look quieter. | S2 |
| `hierarchy.scan` | The most important information (status, totals, names) is the easiest to find, not buried in the same weight as everything else. | S3 |
| `type.readability` | Body text looks at least 16px at the narrow width and 14px at the wide one. Lines run no longer than about 80 characters. | S3 |
| `type.scale` | The screen uses a few text sizes and weights from one scale, not many near-identical ones. | S4 |
| `color.contrast` | Text and icons stand out from what's behind them, including text over images and on coloured buttons. | S2 |
| `color.meaning` | Colour is never the only signal for state (error, selected, status). An icon, text or shape says it too. | S2 |
| `color.palette` | Colours look drawn from one small palette that matches the neighbouring screens. | S4 |
| `consistency.neighbours` | Shared parts (header, buttons, cards, form fields, spacing) look the same as on the neighbouring screens. | S3 |
| `consistency.repeats` | Repeated elements on this screen (rows, cards, buttons of the same kind) look identical. | S3 |
| `states.feedback` | The captured state shows clear feedback: errors next to the field they're about, a visible loading indicator, a confirmation after an action. | S2 |
| `states.empty` | An empty state says what's missing and offers the next step. It isn't a blank area. | S3 |
| `interaction.targets` | At the narrow width, tap targets look at least 44px high and aren't crowded together. | S2 |
| `interaction.affordance` | Things you can click look clickable (links stand out from text, buttons look like buttons), and things you can't, don't. | S3 |
| `interaction.focus` | In a state with keyboard focus, the focused control has a visible focus ring. | S2 |
| `content.labels` | Every input has a visible label, and every icon-only control has a recognisable icon. | S2 |
| `content.truncation` | Long values wrap or truncate cleanly, with a way to see the full value. Numbers in columns line up. | S3 |

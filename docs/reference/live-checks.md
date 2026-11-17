# Live checks

When a repo has a verification skill in `.claude/skills/verify-<app>/` (made by `create-verifier`), several skills use it to drive the running app, so they don't rely on tests alone. This page lists which skills do that, and how to turn it on or off for each one.

## Which skills use it

| Skill | What it drives | When |
|---|---|---|
| `tackle` | Every journey in the feature map for the features the branch changed | After the reviews, before the final check |
| `diagnose` | The user's path to the bug, as its feedback loop | Building the loop, and the final re-check |
| `tdd` | The behavior, when a test isn't practical | As the fallback check |
| `untangle` | Every mapped feature whose source the run changed | After the refactor loop |
| `checkup` | Confirmed findings that will be filed and that a user can reach, to reach evidence rung 5. Off by default. | After verification |
| `catch` | The user path behind a confirmed production error, on a local instance | After verification |
| `poke` | Every mapped entry point for the section | During the live pass |
| `design-critique`, `design` | Launch, Doctor, sign-in and Cleanup only, to get the app running for screenshots | Before capture |

With no verification skill, these skills skip the live check. `tackle` and `untangle` say so in their PR or report. `poke` falls back to the next way to drive the app on its list. `design-critique` and `design` recommend `create-verifier`, then start the app with the launch fallback recorded in the design inventory, or a command you confirm.

`design-critique` and `design` use the verification skill only to run the app. It doesn't follow the skill's evidence rules, which prefer text over images, because screenshots are what it critiques.

## Settings

`docs/agents/pixie.json`, key `liveVerify`: one boolean per skill.

| Key | Default | Off means |
|---|---|---|
| `tackle` | `true` | No live check before the PR. The PR says it was turned off. |
| `diagnose` | `true` | The feedback loop is built without the verification skill. |
| `tdd` | `true` | The fallback check is built without the verification skill. |
| `untangle` | `true` | No live check after the refactor loop. |
| `checkup` | `false` | No live reproduction. Findings top out at evidence rung 4. Set it to `true` to reproduce filed findings in the app. Each drive costs many tokens and adds only a text note to the issue. |
| `catch` | `true` | No live reproduction of production errors. |
| `poke` | `true` | It skips the verification skill and uses the next way to drive the app on its list. |
| `design` | `true` | `design-critique` and `design` don't launch the app through the verification skill. It uses the launch fallback in the design inventory, or asks for a launch command. |

A missing file or a missing key means the default. Live checks prove things with text where they can, and view a screenshot only when the proof is visual. For how to set it, see [Choose which skills use it](../how-to/find-ux-bugs.md#5-choose-which-skills-use-it).

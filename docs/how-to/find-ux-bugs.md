# How to find bugs and UX gaps in a running app

This guide shows you how to have Claude use your app like a real user, report what breaks, and turn the findings into fixes. You use four skills:

- `create-verifier` teaches Claude to start and drive your app. You run it once per project.
- `poke` tests one section of the app and writes a ranked report.
- `tackle` fixes the findings you file as issues.
- `maintain-verifier` keeps the verifier up to date as the app changes.

All four only run when you type them.

## 1. Set up a verification skill (once)

```text
/pixie:create-verifier
```

Claude studies the repo to learn how the app starts and how to drive it. It asks you only what it can't find in the code, such as a test login. Then it writes a skill to `.claude/skills/verify-<app>/` with:

- Steps to launch the app, check it's healthy, drive it, capture evidence, and clean up.
- A feature map with one file for each of the top three to five user-facing features.

Claude then runs the new skill once from start to finish on one feature, and fixes what fails.

Commit the `.claude/skills/verify-<app>/` folder so your team and future runs can use it.

Once the skill is committed, other skills use it too. `tackle` and `untangle` drive the features they changed, `diagnose` and `tdd` use it to reproduce bugs, and `checkup` and `catch` use it to reproduce findings. See [Live checks](../reference/live-checks.md) for what each one does.

You can skip this step. `poke` still works without it, but it falls back to weaker ways of driving the app. With no way to drive the app, it reviews the code only. The other skills skip their live checks.

## 2. Poke at one section

Pick **one** section of the app, such as a screen, a feature, or a group of components:

```text
/pixie:poke the file tree in the sidebar
```

You can name apps to compare against:

```text
/pixie:poke the settings panel, compare with VS Code and macOS System Settings
```

Claude will:

1. Find the section's code and build a checklist of what users expect, based on similar apps.
2. Pick the best way to drive the app. It prefers the verification skill from step 1.
3. Check the code and the checklist in the background, while it uses the live app in your conversation.
4. Rank each finding from S1 (data loss, crash, or blocked task) to S4 (polish).
5. Stop any app or dev server it started.

If it needs to change data, it asks you for a test workspace. It doesn't touch real user data.

The report goes to `ai/poke/<date>-<section>.md`, with screenshots in a folder beside it. Claude adds `ai/` to `.gitignore` if it's not already there.

## 3. Turn findings into fixes

At the end, Claude offers to file findings as GitHub issues. By default it suggests the S1 and S2 findings. You can pick others. It also asks whether to label them `ready-for-agent`.

Screenshots don't go into the issues, because `ai/` is gitignored. Claude describes the evidence in words instead.

Fix each labeled issue with `tackle`:

```text
/pixie:tackle 57
```

Then run `/pixie:babysit` to get the PRs green. See the [tutorial](../tutorial/first-issue-to-pr.md) for what those two skills do.

## 4. Keep the verifier current

Apps change, and the feature map goes stale. Run this from time to time, such as after a big release:

```text
/pixie:maintain-verifier
```

Claude checks every feature in the map against the source, then drives each one in the live app. It fixes the verification skill when the map or the harness is wrong. It reports, but never fixes, bugs in the app itself.

It ends with one of three results:

- **Clean:** nothing needed fixing.
- **Changed:** it opened one PR with tested fixes to the verification skill.
- **Blocked:** it couldn't finish, and it says why.

## 5. Choose which skills use it

Every skill that can use the verification skill does so by default. To stop one, for example because the app is slow to start and `untangle` runs often, create `docs/agents/pixie.json` and set that skill to `false`:

```json
{
  "liveVerify": {
    "untangle": false
  }
}
```

Commit the file so your team and scheduled runs use the same settings. The skills you leave out keep their live checks. For every key, see [Live checks](../reference/live-checks.md).

## Related

- [`create-verifier` reference](../reference/skills.md#create-verifier)
- [`poke` reference](../reference/skills.md#poke)
- [`maintain-verifier` reference](../reference/skills.md#maintain-verifier)
- [Live checks](../reference/live-checks.md)

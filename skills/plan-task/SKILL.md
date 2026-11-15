---
name: plan-task
description: Turn a pasted PM task description (often sparse) into a tight implementation plan for the current codebase, and post it as a new GitHub issue once approved. Use for "plan this task", "plan this ticket", "turn this into an issue", or when the user pastes a PM request and wants it planned.
allowed-tools: Bash(gh repo view:*), Bash(gh auth status), Bash(gh issue list:*), Bash(gh pr list:*), Bash(gh label list:*), Bash(git status:*), Bash(git diff:*), Bash(git log:*)
---

# PM Task → Implementation Plan

You are a senior engineer who knows this codebase well. A PM has written a task, often a thin one. Your job is to do the planning the team would normally do by questioning the PM: work through every decision the spec leaves open, make the call a strong engineer on this team would make, and write a **short** GitHub issue that does two things:

1. Lets the user review the plan in about two minutes: what we're doing, the calls you made, and what we're not doing.
2. Gives a coding agent enough to build it without asking anything.

The user agrees with the PM's direction most of the time. Don't second-guess the *what*; work out the *how*. Think thoroughly, but write briefly: the issue reports your conclusions, not your reasoning.

The issue is the spec for `pixie:tackle`. Its classifier reads only the issue text to pick a route (`implement` or `diagnose`), and `pixie:tdd` builds from it until every **Done when** item has a green test. Write for that reader.

**Don't implement anything.** This skill ends when the issue is created.

## Step 1: Intake

1. The PM text arrives pasted, either with the command or in the next message. Keep it exactly as written; it goes into the issue unchanged (collapsed).
2. Look for a ticket reference: a Jira key (e.g. `ABC-123`) or an ID from the in-house tracker. If there isn't one, ask **once** with AskUserQuestion: "What's the ticket ID?", with a "No ticket" option (the user types the ID through "Other"). Don't ask anything else at this point.
3. Before reading any code, write a one-sentence statement of the user-facing outcome for yourself: who gets what, and why.
4. Decide the **shape**:
   - **Feature:** new or changed behavior. Use the feature template.
   - **Bug, cause known:** the PM or the code names what's wrong. Use the feature template; the fix is the plan.
   - **Bug, cause unknown:** something is broken, wrong or slow and nobody knows why. Use the bug template in Step 4 and **don't plan a fix**. A guessed fix would send `tackle` down the `implement` route and skip diagnosis. If the user wants the cause found before filing, suggest `/pixie:diagnose mode=diagnose-only` instead, and stop.

## Step 2: Learn the relevant code

Explore fresh every time. Don't rely on what you assume about the stack.

- Read `CLAUDE.md`, `AGENTS.md`, `README`, and any docs on architecture or conventions.
- Read `GLOSSARY.md` (if present) and the ADRs in the area you'll touch, so the issue uses the same terms `tdd` will use for tests.
- Find the code the task will touch: routes/controllers, services, models, migrations/schema, UI components, jobs, config, permissions/auth, tests.
- **Find the closest existing feature** and study how it was built. The plan should copy its patterns. Following this codebase's existing patterns beats following general best practice.
- Check `git log` on the touched areas for recent related work.
- **Check for duplicates and in-flight work.** Search open issues and PRs for the same feature or area:
  ```bash
  gh issue list --state open --search "<key terms>" --json number,title,labels --limit 20
  gh pr list --state open --search "<key terms>" --json number,title,headRefName --limit 20
  ```
  If an issue already covers the task, stop and ask whether to continue. If one is labeled `agent-working` or `agent-pr` (or the labels `docs/agents/pixie-labels.md` maps those roles to), or an open PR touches the same files, note the conflict as a one-line risk (see Notes on sections).
- For large repos, run parallel Explore subagents over separate areas, then combine what they find.

## Step 3: Walk the decision tree (privately)

Skip this step for a **bug, cause unknown**.

Work out every question the spec doesn't answer (data shape, where logic lives, API shape, UX states, permissions, edge cases, migration/backfill, rollout, performance). Decisions branch, so keep going until the tree is fully resolved.

Choose using this order of priority: **matches existing codebase patterns** → **smallest change that fully meets the PM's intent** → **easy to change later**.

Then **sort the decisions before writing anything**:
- **Surface it** only if a reasonable reviewer might choose differently, or if it changes scope, data, the API, or UX. Aim for 3–6. Never more than 8.
- **Drop it from the issue** if it just follows an obvious existing pattern. The build steps will show it.
- **Open question** only if it depends on business knowledge the code can't give you (pricing, legal, copy). Always state the default you're assuming. Step 5 resolves these with the user before posting.

Anything you'd like to build but the PM didn't ask for goes under **Not doing**.

**Size check.** `tackle` builds one issue as one PR. If the plan needs more than about 5 build steps, or crosses separate features, propose splitting it into several issues, each a working slice that can ship alone. Let the user choose in Step 5.

## Step 4: Write the issue

### Length and style rules

- **Target 250–450 words**, not counting the collapsed PM text and the build steps. If you're over, cut. Don't compress into terse fragments.
- One line per bullet. No sub-bullets except in build steps.
- Never say the same thing twice. Summary, Decisions, and Build steps each have their own job.
- No preamble, no "This issue describes…", no closing summary, no hedging.
- Use the codebase's names for things. Write file paths in backticks.
- Leave out any section that would be empty.

### Template

````markdown
**Source:** <TICKET-ID or "no ticket">

## Plan
2–3 plain sentences: what we're building and the core of the approach.

```mermaid
<diagram of the approach; see Diagrams>
```

## Decisions
| Decision | Chose | Over | Why |
|---|---|---|---|
| … | … | … | one short clause |

## Not doing
- One line each: scope deliberately left out, and anything the PM might assume is included but isn't.

## Assumed defaults
- **Question?** Build with: <default>.

## Build steps
1. **<Step name>**: `path/to/file` (new|edit), `path/to/other` (edit)
   - What to do in 1–2 lines, naming the existing pattern to copy (`path/to/example`).
   - Tests: the behaviors to cover, named the way a test would be ("rejects export when list is empty"), and the existing test file to extend.
2. …

## Done when
- [ ] 3–6 observable behaviors from the user's point of view, one per item, including the key edge cases.

<details>
<summary>Original PM request</summary>

<verbatim PM text>

</details>
````

### Bug template (cause unknown)

````markdown
**Source:** <TICKET-ID or "no ticket">

## Symptom
1–2 sentences: what goes wrong, for whom, and since when if known.

## Reproduce
1. Steps, data or request that trigger it.

## Expected vs actual
- **Expected:** …
- **Actual:** … (error text, wrong value, timing)

## Where to look
- `path/to/file`: why it's relevant. Facts from the code only; no suspected cause.

## Done when
- [ ] The reported symptom no longer occurs, covered by a regression test.

<details>
<summary>Original PM request</summary>

<verbatim PM text>

</details>
````

### Notes on sections

- **Build steps** are written for a coding agent. Each step names its files, the pattern to copy, and its tests, and leaves the app working. Usually 3–5 steps (see the size check in Step 3). Don't paste implementations; a schema line or function signature is fine when it removes ambiguity.
- **Done when** is the requirement list `tdd` checks itself against. Each item is one behavior a test can assert. No implementation details ("uses a service class") and no compound items.
- **Assumed defaults** holds only what the user left to your default in Step 5. `tackle` builds with them as written. Nothing in a posted issue should read as an unanswered question, or `tackle` may stop and mark it `agent-blocked`.
- **Risks**: there's no separate section. If a real risk exists (data migration, conflict with in-flight work), put one line in the relevant build step, or in Plan if it affects the whole approach.

### Diagrams

Include a Mermaid diagram right under the Plan sentences **by default**. GitHub renders it inline, and it's often the fastest way to see the approach. It doesn't count toward the word budget. Pick the type that fits:

- `sequenceDiagram` for requests that pass through several components, or for async/queued flows
- `flowchart` for branching logic, or for how the new pieces connect to existing ones
- `erDiagram` for new tables or changed relationships
- `stateDiagram-v2` for anything with a status lifecycle

Use one diagram, or two only if the change has both a meaningful flow and a schema change. Keep each to about 15 nodes or fewer, mark new pieces clearly (e.g. a `(new)` label or a styled class), and quote labels that contain parentheses, colons, or special characters. Skip the diagram only for trivial changes, like a copy tweak or a single-field addition. The bug template has no diagram.

## Step 5: Review, then create

1. Make a temporary file with `mktemp "${TMPDIR:-/tmp}/plan.XXXXXX"`, save the draft to the path it prints, and show the user the full title and body. **Title:** short and imperative, e.g. `Add CSV export to the invoices list`. For a bug, describe the symptom, e.g. `Invoice totals are wrong after a refund`.
2. Resolve open questions. Ask each one with AskUserQuestion, your default as the first, recommended option. Move answered ones into **Decisions** (or drop them if they follow an existing pattern). Ones the user leaves to you stay under **Assumed defaults**. If Step 3 proposed a split, ask about it here too.
3. Ask: "Want any changes, or should I create the issue?" Revise until they approve.
4. Find the queue label. If `docs/agents/pixie-labels.md` exists, use its label for the `ready-for-agent` role. Otherwise use `ready-for-agent`. Every mention of `ready-for-agent` below means this label. Quote it in commands. Ask with AskUserQuestion whether to label it `ready-for-agent`, so `/pixie:tackle` can pick it up. Default to **no**: queuing it is the user's go-ahead, not yours.
5. Before posting, confirm the target repo with `gh repo view --json nameWithOwner -q .nameWithOwner` and check `gh auth status`. If the repo looks wrong, ask. If the user wants the label, check it exists with `gh label list --json name --limit 200`, and create it with `gh label create "ready-for-agent"` if it doesn't.
6. Create it, adding `--label ready-for-agent` only if the user said yes:
   ```bash
   gh issue create --title "<title>" --body-file <draft-path>
   ```
   Don't add other labels, assignees, or milestones unless the user asks for them. For a split, create the issues in build order, and add `Depends on #X` under **Source** in each one after the first, naming the issue it builds on.
7. Delete the draft file.
8. Reply with the issue URL and one next step: `/pixie:tackle N` if it's labeled, otherwise "Label it `ready-for-agent`, then run `/pixie:tackle N`."

## Final check before showing the draft

- Can someone read everything above Build steps in under two minutes and know the plan, the calls you made, and what's excluded?
- Could an agent finish every build step without asking a question?
- Does every file path exist, or is it marked **new**?
- Is every decision row something a reviewer might actually push back on? If not, cut it.
- Is every **Done when** item a single behavior a test could check?
- For a bug with an unknown cause: is the issue free of any guessed cause or fix?
- Is anything said twice? Cut the repeat.

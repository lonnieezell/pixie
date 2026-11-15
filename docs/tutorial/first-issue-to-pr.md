# Tutorial: Ship your first change with Pixie

In this tutorial you take one small feature from a written task to a green pull request (PR). You won't write any code yourself. Pixie plans the work, builds it test-first, opens the PR, and gets CI green. You make the decisions and do the merge.

It takes about 20 minutes. Most of that is waiting for Claude and CI.

You will use four skills, in the order you'd use them on a real project:

1. `how` to learn the code.
2. `plan-task` to turn a task into a GitHub issue.
3. `tackle` to build the issue and open a PR.
4. `babysit` to get the PR ready to merge.

You'll work in a small throwaway repo, so nothing you do here can touch real work.

## Before you start

You need:

- Claude Code with Pixie installed. Type `/pixie:` in a session and check that the skills appear. If they don't, see [Install the plugin](../../README.md#install-the-plugin).
- The GitHub CLI, signed in. `gh auth status` should say you're logged in.
- Node.js 20 or later. `node --version` should print `v20` or higher.

You don't need km for this tutorial.

## Step 1: Create the sandbox repo

The sandbox is a tiny Node project. It has one function that totals a shopping cart, two tests, and a CI workflow that runs the tests.

Run these commands in a terminal, outside any other git repo:

```bash
mkdir pixie-sandbox && cd pixie-sandbox
git init -b main
mkdir -p src test .github/workflows
```

Create `package.json`:

```bash
cat > package.json <<'EOF'
{
  "name": "pixie-sandbox",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "node --test"
  }
}
EOF
```

Create the code and its tests:

```bash
cat > src/cart.js <<'EOF'
// Returns the cart total in cents.
export function cartTotal(items) {
  return items.reduce((sum, item) => sum + item.priceCents * item.quantity, 0);
}
EOF

cat > test/cart.test.js <<'EOF'
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cartTotal } from '../src/cart.js';

test('an empty cart totals zero', () => {
  assert.equal(cartTotal([]), 0);
});

test('adds price times quantity for each item', () => {
  const items = [
    { priceCents: 500, quantity: 2 },
    { priceCents: 250, quantity: 1 },
  ];
  assert.equal(cartTotal(items), 1250);
});
EOF
```

Create the CI workflow:

```bash
cat > .github/workflows/test.yml <<'EOF'
name: test
on:
  pull_request:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: npm test
EOF
```

Check that the tests pass:

```bash
npm test
```

You should see `pass 2` and `fail 0`.

Commit, then create a private GitHub repo and push to it:

```bash
git add -A
git commit -m "Initial sandbox"
gh repo create pixie-sandbox --private --source=. --push
```

You now have a repo on GitHub with a passing test suite and CI.

## Step 2: Learn the code with `how`

Start Claude Code in the sandbox folder:

```bash
claude
```

Ask how the cart works:

```text
/pixie:how how is the cart total calculated
```

Claude reads the code and explains it. It covers the moving parts, how a call flows through them, and which files to read first. On a repo this small, the answer is short. On a real project, this is how you get your bearings before you plan a change.

## Step 3: Plan the work with `plan-task`

Now give Pixie a task, written the way a product manager might write it. Run:

```text
/pixie:plan-task
Carts over $100 should get 10% off. Customers keep asking for a bulk discount.
```

Claude asks once for a ticket ID. Pick **No ticket**.

Claude then studies the code and shows you a draft GitHub issue. The draft has:

- A short plan, often with a diagram.
- A table of the decisions it made, such as whether "over $100" includes exactly $100.
- What it won't do.
- Build steps a coding agent can follow.
- A "Done when" checklist.

Read the decisions table. This is where you catch a wrong guess. If you disagree with one, say so, for example:

```text
Exactly $100 should not get the discount. Otherwise looks good.
```

If the draft has open questions, Claude asks each one, with its own default as the recommended answer. When you're happy, approve it:

```text
Create the issue.
```

## Step 4: Queue the issue for an agent

`tackle` works from a queue. An issue joins the queue when it has the `ready-for-agent` label. Before posting, Claude asks whether to add it. The default is no, because you decide when a plan is ready to build. This plan is ready, so pick **Yes**.

Claude creates the label if the repo doesn't have it, then creates the issue. It replies with the issue URL and the command to run next. Note the issue number. It's `1` in a new repo.

If you pick **No**, you can queue the issue later yourself:

```bash
gh label create ready-for-agent
gh issue edit 1 --add-label ready-for-agent
```

You only need to create the label once per repo. `tackle` creates its other labels itself.

## Step 5: Build it with `tackle`

In Claude Code, run:

```text
/pixie:tackle 1
```

This is the longest step. Watch for these moments:

1. **Claim.** Claude creates a branch named `agent/1-<short-slug>`. On the issue, it swaps `ready-for-agent` for `agent-working` and posts a claim comment. Then it runs the full test suite once to record a baseline.
2. **Classify.** A small subagent rates the issue's difficulty and picks a route. It posts a comment like `Tier 1 (small), route implement: ...`. A feature takes the `implement` route, which means test-driven development.
3. **Build.** Claude uses the `tdd` skill. For each slice, it writes a test, predicts how it will fail, and watches it fail that way. Then it writes just enough code to pass. Each slice becomes its own commit, such as `feat(#1): ...`.
4. **Review.** Claude runs linters if the project has any, then Claude Code's `/simplify` and `/code-review` on the branch. The sandbox has no verification skill, so Claude skips the live check, where it would drive the changed feature in the running app, and says so in the PR.
5. **Open the PR.** Claude pushes the branch and opens the PR. On the issue, it swaps `agent-working` for `agent-pr`.

Claude ends with the PR link and its tier. It also tells you that CI hasn't been checked yet.

Open the PR in your browser. Look at the commits. Each commit body includes the failing test output from before the fix. That's the proof the test failed first.

## Step 6: Get the PR green with `babysit`

`tackle` doesn't wait for CI. `babysit` does. Run:

```text
/pixie:babysit
```

`babysit` works through every open PR in the repo, oldest first. Here there's only one. For each PR, it:

1. Fixes merge conflicts, if any.
2. Answers comments from review bots, if any.
3. Waits for CI and fixes failures caused by the PR's code.

The sandbox has no review bots and no conflicts. So `babysit` waits for the `test` workflow to finish. It ends with a table that gives each PR a final state. You should see **Ready**.

## Step 7: Merge it yourself

Pixie never merges, approves, or closes a PR. That's always your call.

Review the PR on GitHub. If you're happy with it, merge it. Because the PR body says `Closes #1`, GitHub closes the issue when the PR merges.

## What you did

You took a vague, one-line request all the way to a merged change:

- `plan-task` turned the request into a plan with explicit decisions you could check.
- The `ready-for-agent` label was your go-ahead.
- `tackle` built it test-first, reviewed it, and opened a PR, tracking its progress with labels.
- `babysit` got the PR to a mergeable state.
- You made the two human calls: approving the plan and merging the code.

That's the core Pixie loop. The other skills plug into it. For example, `poke` and `code-health` find work to feed into it, and `diagnose` handles bugs with an unknown cause.

## Clean up

To delete the sandbox repo from GitHub, give `gh` permission to delete repos, then delete it:

```bash
gh auth refresh -s delete_repo
gh repo delete pixie-sandbox --yes
```

Then delete the local `pixie-sandbox` folder.

## Next steps

- To fix a bug, see [Fix a bug](../how-to/fix-a-bug.md).
- To find and clean up messy code, see [Clean up hotspots](../how-to/clean-up-hotspots.md).
- To understand why Pixie works this way, read [How Pixie works](../explanation/how-pixie-works.md).
- To look up any skill, see the [Skills reference](../reference/skills.md).

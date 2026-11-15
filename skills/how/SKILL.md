---
name: how
description: Explore the codebase to answer "how does X work?" with an architectural explanation pitched at a senior engineer onboarding onto that subsystem.
allowed-tools: Bash(git log:*), Bash(git blame:*), Bash(git show:*), Bash(git diff:*)
---
# How

Answer "how does X work?" by exploring the code and explaining it the way a good teammate would to a senior engineer joining that part of the system. The goal is a **working mental model**: what the pieces are, how data and control move between them, and why it's built that way. The reader should be able to reason about a change or a bug in X afterwards.

Aim for an architecture explanation, not a tour of the source. If it reads like a line-by-line walkthrough with comments, it has gone too deep.

## Arguments

The question itself, e.g. `/how does authentication work`, `/how are background jobs retried`, `/how does the docs build pick up versions`.

## Process

### 1. Pin down the question

Work out what X is and how far it reaches before searching. "How does auth work" could mean login, session handling, permission checks, or all three. If the scope is genuinely ambiguous and a wrong guess would waste the exploration, ask one short question. Otherwise pick the most likely reading and say which one you took in the first line of the answer.

### 2. Find the entry points

Find where X starts: routes, CLI commands, event listeners, job handlers, config keys, public API methods, framework hooks (service providers, filters, middleware). Use searches that find structure, not just keywords:

- grep for the domain term *and* its likely class/function/config names
- read config files, DI/service registration, and route files. They're a map of the wiring.
- skim the directory layout around the hits
- check tests. Their names and setup often describe the intended behavior better than the code does.

If the search needs to cover a large area (many directories, unclear naming), hand the broad search to an exploration subagent and keep reading the key files yourself.

### 3. Trace the main path

Follow one representative request or event from the entry point to the end: what it calls, what state it reads or writes, and where it leaves the subsystem (DB, queue, HTTP, filesystem, another module). Read the actual code at each hop; don't infer behavior from names.

Then note the important branches off the main path (error handling, caching, retries, feature flags, alternate drivers), but don't trace every one.

### 4. Find the shape

Step back from the trace and identify:

- **Core abstractions.** The 3–8 classes, modules, or concepts everything else hangs off.
- **Boundaries.** What X owns versus what it delegates, and the interfaces or contracts at those boundaries.
- **State and data flow.** Where the source of truth lives and how it changes over time.
- **Extension points.** How you'd add a new driver, handler, or case.
- **The why.** Design choices that aren't obvious. Use commit messages, comments, docs, or ADRs where they exist; if you're inferring intent, say so.

### 5. Verify before writing

Check each claim you plan to make against code you have actually read. Mark anything you couldn't confirm ("likely", "appears to") instead of stating it as fact. If the code contradicts the docs or comments, say so; that's valuable.

## Output

Write in prose with light structure. Typical length is 400–900 words; go shorter for small subsystems. Don't pad to fill the shape.

1. **The short version** (2–4 sentences). What X does and the one idea that makes it make sense.
2. **The moving parts.** The core abstractions, one or two sentences each, with the file path they live in.
3. **How a request/event flows.** A numbered walk through the main path, one line per hop. If there are more than about four hops or several components, add a small diagram (Mermaid or ASCII).
4. **Why it's built this way.** Key design decisions and trade-offs.
5. **Non-Obvious Things.** Anything surprising, historically motivated, or easy to get wrong. Things that look like they should work one way but work another.
6. **Where to start reading.** The 3–5 files to open first, in order, each with a short note on why.

### Calibration rules

- **Explain responsibilities, not lines.** "`TokenGuard` resolves the user from the bearer token and caches it per request" is right. A paraphrase of its method body is too deep.
- **Code snippets only when the shape matters**, such as a key interface, a config block, or a registration call. Keep each under about 8 lines, and include no more than a few.
- **Reference files with `path:line`** for the important locations, not for every claim.
- **Use the codebase's own vocabulary.** Name things what the code names them, and define project-specific terms once.
- **Assume senior-level general knowledge.** Don't explain what middleware, a queue, or dependency injection is. Do explain how *this* codebase uses them, especially where it departs from the framework's conventions.
- **Say what you didn't cover** in one line if you skipped meaningful branches, so the reader knows where the map ends.
- **Offer one follow-up**, such as going deeper on a component or tracing a specific edge case, rather than adding it unasked.
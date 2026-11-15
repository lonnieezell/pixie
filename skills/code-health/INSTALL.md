# Code Health for Claude Code with km

## Overview

Claude Code now checks the health of every file it edits and fixes problems it introduced before moving on. It uses [km (Kimün)](https://docs.rs/kimun/latest/km/), a free, local code-metrics tool, and works the same way for PHP (CodeIgniter, Laravel), TypeScript/React and Rust.

The setup has three parts:

- **A hook** that runs after every edit, compares the file with its last committed version, and tells Claude about new problems along with how to fix them in that language.
- **A `code-health` skill** for project-level questions: the health grade, whether a branch made things worse, and which files are worth refactoring first.
- **km's own `km-analyze` skill**, a reference for every km command and its output.

The key design choice: only regressions are reported. Existing debt is ignored by the hook, so Claude fixes what it just wrote instead of drifting into refactoring code nobody asked it to touch. Older debt is handled on purpose, through the skill's hotspot and refactor modes.

## How it works

&#91;embedded content: the edit loop · one check after every edit\]

After each Edit or Write, a Claude Code PostToolUse hook runs a small Python script, `check.py`. It takes two copies of the edited file, as it is now and as it was at the last commit, and runs km on both. It then compares function by function.

It reports four kinds of regression:

| Check | Flagged when | Default |
| --- | --- | --- |
| Cognitive complexity | a function goes over the limit, or one edit adds a lot to it | over 15, or +8 in one edit |
| Long function | a function newly exceeds the length limit | 50 lines |
| Long parameter list | a function newly takes too many parameters | more than 4 |
| File size | a file grows past the limit | 500 lines |

When something is flagged, the script exits with code 2. Claude Code passes its message back to Claude, which then fixes the code. Each message names the function and line and gives a fix for that language, for example guard clauses or a DTO in PHP, a custom hook in React, `let … else` in Rust.

Three details keep it from getting in the way:

- **Once per session.** A problem is reported once. If Claude explains the complexity is warranted, it isn't nagged again on later edits to that file.
- **Fails open.** If km is missing, the file isn't in git, or anything errors, the hook stays silent and never blocks work.
- **Fast.** About 60 ms per edit, because it analyzes only the one file.

The `code-health` skill handles everything bigger than one file. It picks a mode from the request:

1. **Score:** the project's grade (A++ to F--) and its weakest files.
2. **Diff:** whether a branch or uncommitted work made things worse than `main`. Only files that were touched are judged.
3. **Hotspots:** complex files that also change often, ranked as refactoring targets.
4. **Refactor:** measure, make sure tests cover the code, refactor in small steps, re-measure.

## Day-to-day use and tuning

The hook needs nothing from you. You'll see its warnings in Claude's transcript when it fires. For everything else, ask Claude in plain words and the skill takes over:

- “What's the code health of this project?”
- “Did this branch make the code worse than main?”
- “What should we refactor first?”
- “Refactor `OrderService` to bring its complexity down.”

Good habits: get a baseline grade for each project before relying on the hook, and run the diff check before opening a PR.

**Tuning.** Set these as environment variables, for example in the `env` block of Claude Code's `settings.json`:

| Variable | Default | Effect |
| --- | --- | --- |
| `CODE_HEALTH_COGCOM_MAX` | 15 | cognitive complexity limit per function |
| `CODE_HEALTH_COGCOM_JUMP` | 8 | flag one edit that adds this much to a function |
| `CODE_HEALTH_FILE_LINES` | 500 | flag files growing past this |
| `CODE_HEALTH_HOOK` | on | set to `off` to disable everywhere |

To turn the hook off for one repository, add an empty `.code-health-off` file at its root. Running `km init` in a repo writes a `.kimun.toml` with thresholds calibrated to that codebase, which the skill's project-level checks use.

The hook skips `vendor`, `node_modules`, `target`, `dist`, `build`, `.next`, `writable` and `storage`, plus `.d.ts` and `.min.js` files.

## Setting it up on another computer

It takes about ten minutes on macOS or Linux, most of it compiling km. The steps assume Claude Code's default config folder, `~/.claude`. If you use a different one (set by `CLAUDE_CONFIG_DIR`), substitute it throughout.

1. **Check the prerequisites.** You need `git`, `python3` (3.8 or later) and Rust. If `cargo --version` fails, install Rust from [rustup.rs](https://rustup.rs).
2. **Install km.**

   ```bash
   cargo install kimun
   km --version
   ```

   If `km` isn't found afterwards, add `~/.cargo/bin` to your PATH. The hook also looks there on its own.
3. **Add the hook script.** Create the folder and save the script from the appendix as `check.py`:

   ```bash
   mkdir -p ~/.claude/hooks/code-health
   # paste the appendix script into this file
   nano ~/.claude/hooks/code-health/check.py
   ```
4. **Add km's reference skill.** Install it at user level (choose option 2 when asked). The `code-health` skill itself comes with the Pixie plugin, as `pixie:code-health`, so don't copy it in by hand.

   ```bash
   km ai skill claude
   ```
5. **Register the hook.** Add this to `~/.claude/settings.json`. If the file already has a `hooks` section, add the `PostToolUse` entry inside it, not a second `hooks` key.

   ```json
   {
     "hooks": {
       "PostToolUse": [
         {
           "matcher": "Edit|Write|MultiEdit",
           "hooks": [
             {
               "type": "command",
               "command": "python3 \"$HOME/.claude/hooks/code-health/check.py\"",
               "timeout": 30
             }
           ]
         }
       ]
     }
   }
   ```
6. **Restart Claude Code.** Hooks are read when a session starts, so a session that was already open won't run the new one. In an open session you can use `/hooks` instead.
7. **Test it.** In any git repository, ask Claude to add a function with five or six nested `if` statements. A “Code health regression” message should come back right after the edit, and Claude should refactor. Then ask “what's the code health of this project?” to check the skill.

**Two config folders on one machine.** If you run Claude Code with more than one config folder (for example `~/.claude` and `~/.claude-work`), keep one copy of the script and skills. Link the skill folders into the second config with `ln -s`, and add the same hook entry to its `settings.json`, still pointing at the one `check.py`.

**If the hook never fires,** check that `python3` and `km` are on the PATH Claude Code sees, and that the repository has at least one commit. Without a commit, there is nothing to compare against.

## Appendix A: the hook script

Save as `~/.claude/hooks/code-health/check.py`. Tested with km 0.46.

```python
#!/usr/bin/env python3
"""Claude Code PostToolUse hook: flag code-health regressions in the edited file.

Compares the file as it is now against its version at git HEAD, using km
(kimun). Only *new or worsened* problems are reported, never pre-existing debt,
so Claude fixes what it just did instead of wandering off to refactor.

Exit 0 = fine (silent). Exit 2 = regression; stderr is fed back to Claude.
Fails open: any error, missing km, non-git file, etc. -> exit 0.

Tuning (environment variables, e.g. in settings.json "env"):
  CODE_HEALTH_HOOK=off        disable entirely
  CODE_HEALTH_COGCOM_MAX=15   function cognitive complexity limit (Sonar default)
  CODE_HEALTH_COGCOM_JUMP=8   flag any single edit that adds this much to a function
  CODE_HEALTH_FILE_LINES=500  flag files that grow past this many lines
A repo can opt out by adding a `.code-health-off` file at its root.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

EXTS = {".php", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".rs"}
SKIP_DIRS = {"vendor", "node_modules", "target", "dist", "build", ".next", "writable", "storage"}

COGCOM_MAX = int(os.environ.get("CODE_HEALTH_COGCOM_MAX", "15"))
COGCOM_JUMP = int(os.environ.get("CODE_HEALTH_COGCOM_JUMP", "8"))
FILE_LINES = int(os.environ.get("CODE_HEALTH_FILE_LINES", "500"))

HINTS = {
    "complexity": {
        ".php": "use guard clauses/early returns, extract the loop body into a private method, "
                "replace if/else chains with a match expression or a strategy/lookup array",
        ".rs": "flatten with `let ... else` / `?`, pull match arms into helper fns, "
               "replace nested `if let` with combinators (`and_then`, `filter_map`)",
        "js": "use early returns, extract the nested branch into a named function; in React move "
              "logic out of the component into a custom hook or a pure helper",
    },
    "long_function": {
        ".php": "split into well-named private methods (or a dedicated service/action class in Laravel)",
        ".rs": "split into smaller fns or an impl block on a small struct holding the shared state",
        "js": "split into smaller functions; for components, extract subcomponents or a custom hook",
    },
    "long_parameter_list": {
        ".php": "introduce a parameter object / DTO, or pass an entity instead of its fields",
        ".rs": "group related params into a struct (or a builder for optional ones)",
        "js": "take a single typed options object instead of positional params",
    },
    "file_size": {
        ".php": "the class is taking on too much: extract a cohesive group of methods into a new class",
        ".rs": "split into submodules by responsibility",
        "js": "split the module; move helpers/types/subcomponents into their own files",
    },
}


def hint(kind, ext):
    table = HINTS[kind]
    return table.get(ext) or table["js"]


def find_km():
    km = shutil.which("km")
    if km:
        return km
    cand = Path.home() / ".cargo" / "bin" / "km"
    return str(cand) if cand.exists() else None


def run_json(km, args, cwd):
    out = subprocess.run([km, *args, "--format", "json", "--include-tests", "."],
                         cwd=cwd, capture_output=True, text=True, timeout=20)
    if out.returncode != 0 or not out.stdout.strip():
        return []
    return json.loads(out.stdout)


def analyze(km, source, ext):
    """Return (functions{key: complexity}, smells{key: detail}, lines) for one file's text."""
    if source is None:
        return {}, {}, 0
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / f"subject{ext}").write_text(source)
        funcs = {}
        for f in run_json(km, ["cogcom", "--per-function"], d):
            seen = {}
            for fn in f.get("functions", []):
                name = fn["name"]
                seen[name] = seen.get(name, 0) + 1
                key = name if seen[name] == 1 else f"{name}#{seen[name]}"
                funcs[key] = (fn["complexity"], fn["start_line"])
        smells = {}
        for f in run_json(km, ["smells"], d):
            for s in f.get("smells", []):
                if s["kind"] in ("long_function", "long_parameter_list"):
                    # detail names the function, so it is stable across line shifts
                    smells[(s["kind"], s["detail"])] = s["line"]
    lines = source.count("\n") + 1
    return funcs, smells, lines


def main():
    if os.environ.get("CODE_HEALTH_HOOK", "").lower() in ("off", "0", "false"):
        return 0
    data = json.load(sys.stdin)
    path = (data.get("tool_input") or {}).get("file_path")
    if not path:
        return 0
    p = Path(path)
    ext = p.suffix.lower()
    if ext not in EXTS or not p.exists() or SKIP_DIRS & set(p.parts):
        return 0
    if p.name.endswith((".d.ts", ".min.js")):
        return 0
    km = find_km()
    if not km:
        return 0

    top = subprocess.run(["git", "-C", str(p.parent), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    if top.returncode != 0:
        return 0
    root = Path(top.stdout.strip())
    if (root / ".code-health-off").exists():
        return 0
    rel = p.resolve().relative_to(root.resolve()).as_posix()
    old = subprocess.run(["git", "-C", str(root), "show", f"HEAD:{rel}"],
                         capture_output=True, text=True)
    before_src = old.stdout if old.returncode == 0 else None

    b_funcs, b_smells, b_lines = analyze(km, before_src, ext)
    a_funcs, a_smells, a_lines = analyze(km, p.read_text(errors="replace"), ext)

    problems = []
    for name, (cc, line) in a_funcs.items():
        prev = b_funcs.get(name, (0, 0))[0]
        if cc <= prev:
            continue
        if cc > COGCOM_MAX or cc - prev >= COGCOM_JUMP:
            change = f"{prev} -> {cc}" if prev else f"new, {cc}"
            problems.append(f"- `{name}` (line {line}): cognitive complexity {change} "
                            f"(limit {COGCOM_MAX}). Fix: {hint('complexity', ext)}.")
    for (kind, detail), line in a_smells.items():
        if (kind, detail) not in b_smells:
            problems.append(f"- line {line}: {detail}. Fix: {hint(kind, ext)}.")
    if a_lines > FILE_LINES and a_lines > b_lines + 20 and (b_lines <= FILE_LINES or before_src is None):
        problems.append(f"- file grew to {a_lines} lines (limit {FILE_LINES}). Fix: {hint('file_size', ext)}.")

    # Report each problem once per session, so an accepted trade-off isn't nagged on every edit.
    session = "".join(c for c in str(data.get("session_id", "nosession")) if c.isalnum() or c in "-_")
    cache = Path(tempfile.gettempdir()) / "claude-code-health" / f"{session}.json"
    try:
        seen = set(json.loads(cache.read_text()))
    except Exception:
        seen = set()
    fresh = [pr for pr in problems if f"{rel}|{pr.split(' Fix:')[0]}" not in seen]
    if not fresh:
        return 0
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(sorted(seen | {f"{rel}|{pr.split(' Fix:')[0]}" for pr in fresh})))
    problems = fresh
    print(f"Code health regression in {rel} (compared with git HEAD):\n" + "\n".join(problems) +
          "\nRefactor these before moving on, keeping behaviour identical. If the complexity is "
          "genuinely warranted, say so briefly and continue.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # never block Claude because the checker itself broke
```

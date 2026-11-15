# Instrumentation

Every probe maps to a prediction from Phase 3. Change one variable at a time.

## Order of preference

1. **Debugger or REPL.** One breakpoint beats ten logs.
2. **Targeted logs** at the boundaries that distinguish hypotheses (where data enters, crosses a module, or is persisted).
3. Never "log everything and grep".

## Tag every debug line

Pick one unique prefix per session, such as `[DEBUG-a4f2]`, and put it on every temporary log line, assertion, dump, or injected sleep. Cleanup is then a single search:

```bash
git grep -n --untracked 'DEBUG-a4f2'    # must return nothing before the fix starts
```

Keep `--untracked`. Plain `git grep` searches only tracked files, so it misses debug lines in new files.

Untagged debug lines survive into commits. Tagged ones get removed.

## Runtime artifacts for live symptoms

For leaks, spinning CPU, hangs, or visual glitches, capture a real artifact instead of theorising from source:

- **CPU profile** for a spinning or slow process: find the function on the hot path.
- **Heap snapshot** for a leak: follow the retainer chain from the leaked object to a GC root.
- **Trace or recording** for a glitch: find the loop or event firing without input.

Reduce the artifact to the smoking gun, prove the mechanism with a cheap targeted probe, then map it back to a file, symbol, and line. When an artifact is large, have a subagent parse it and return only the reduced finding.

## Performance branch

Logs are usually the wrong tool for performance. Measure first, fix second:

1. Capture a **baseline** with a timing harness, profiler, or query plan, and run it several times to see the variance.
2. Bisect (commits, data size, config) against that baseline.
3. Report before and after numbers from the same harness, with the variance.

## By stack

**PHP: CodeIgniter 4 and Laravel**
- Step debugging: Xdebug with `XDEBUG_MODE=debug` and your IDE listening. For CLI runs, `XDEBUG_TRIGGER=1 php spark …` or `XDEBUG_TRIGGER=1 php artisan …`.
- CodeIgniter 4: the Debug Toolbar (development environment) shows queries, timeline, and variables per request. Use `log_message('debug', '[DEBUG-a4f2] …')` for tagged logs in `writable/logs`.
- Laravel: `DB::listen(fn ($q) => logger('[DEBUG-a4f2] '.$q->sql, $q->bindings));` for query tracing, Telescope if the project has it, and `Log::debug('[DEBUG-a4f2] …')` for tagged logs.
- Slow queries: run `EXPLAIN` (or `EXPLAIN ANALYZE` on PostgreSQL and MySQL 8+) on the captured SQL.
- Stale state after a deploy: clear caches before trusting a result (`php spark cache:clear`, `php artisan optimize:clear`) and check opcache.

**TypeScript and React**
- Node: `node --inspect-brk` and attach a debugger. Tests: `npx vitest --inspect-brk --no-file-parallelism <file>`.
- Browser: DevTools breakpoints, the Performance panel for jank, the Memory panel for heap snapshots, the Network panel for request evidence (export a HAR, then redact it).
- React: React DevTools Profiler for unexpected re-renders. Tag `console.log` calls with the prefix.

**Rust**
- `RUST_BACKTRACE=1` (or `full`) for panics.
- `dbg!(expr)` for quick probes (it prints to stderr with file and line), and still tag with the prefix in a comment or message so it is easy to find.
- `RUST_LOG=debug` with `tracing` or `env_logger` if the project uses them.
- Debugger: `rust-lldb` or `rust-gdb` on the test binary.
- Performance: `cargo flamegraph` (from the `flamegraph` crate) or `perf`, plus `cargo bench` or Criterion for before and after numbers.

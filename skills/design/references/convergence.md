# Converging a design into production code

How a design becomes production code, test-first. `/design` follows all of it to build the direction the user picked. `/design-critique` follows it for fixes that change behaviour, with one test per fix, for the state its finding cites, in place of the state matrix.

**No visual snapshot tests**, ever: no `toMatchSnapshot`, `toMatchInlineSnapshot`, `toHaveScreenshot` or stored HTML to compare against. The screenshots and the critic check how it looks. The tests check how it behaves.

## 1. The test list is the state matrix

Write one test per state in the preview's matrix: the six required states, any extra states (`disabled`, `read-only`), and each interaction state. Each test renders the production component with **that state's fixtures from the preview**, so the tests and the screenshots show the same data.

| Stack | Tests |
|---|---|
| React | Vitest and Testing Library. If the repo runs Jest instead, use Jest. With no JS test runner, ask before adding one: it changes the repo's dependencies. |
| Laravel Blade | View tests (`$this->blade()`, `$this->component()`, `$this->view()`), or a feature test (`$this->get()`) for a page |
| CodeIgniter 4 | Feature tests with `FeatureTestTrait` for a page. For a view cell or partial, render it (`view_cell()`, `view()`) in a test and check the output. |

Put them where the repo keeps its tests for that kind of file, named for the outcome. Each test asserts what the user gets in that state, not how the markup is built:

| State | Asserts, for example |
|---|---|
| `empty` | The empty message is shown, with its call to action |
| `single` | The one item is shown, with nothing implying a list of many |
| `typical` | Each item's key values are shown, in order |
| `overflow` | A long name is truncated with its full text in a `title` (or the catalogued tooltip); a large count is formatted |
| `error` | The error message is shown, with a way to retry, and no stale data |
| `loading` | A busy indicator is announced (`role="status"`, `aria-busy`), and no data or empty message |
| an interaction | The outcome of the steps: the menu's items are shown, the field's error is announced |

Find elements the way a user does: by role, label or text (`getByRole`, `assertSee`). Never by class name, element nesting or test IDs added only for the test.

## 2. Red, then green

**With Pixie's `tdd` skill** (`pixie:tdd` is in the available skills): load it with the Skill tool in feature mode, with the test list from step 1, one slice per state. Tell it the caller owns commits: it doesn't commit, and the user commits at the end.

**Without it**, run this loop yourself, one state at a time:
1. Write the state's test. Write down the failure you expect.
2. Run just that test. It must fail on the state's own assertion. The very first test may fail because the component doesn't exist yet: stub it so the run fails on the assertion instead. Any other failure (an import, a fixture, a typo) is a broken test: fix the test and run it again.
3. Write the least production code that makes it pass. Run it, then every test written so far.
4. Keep the failing and the passing line of each run for the report.

A state's test that passes the first time it runs doesn't prove anything. Make it assert what's particular to that state (the empty state's call to action, not only "renders"), and run it again. Each state ends with one test that failed before its code was written and passes after. Run the repo's whole test suite once at the end.

## 3. Platform behaviour: inventory first

Overlays, tooltips, popovers, menus, forms and validation, transitions and responsive containers:

1. **A catalogued component wins.** If the inventory has a `preferred` component for it (a Radix `Dialog`, a Bootstrap modal, an `<x-tooltip>`), use it, even where a platform feature could do the job (`<dialog>`, `popover`, `:user-invalid`, container queries).
2. **Modern Web Guidance**, if it's installed as a skill or plugin, then informs new components and the inside of components being built: which platform feature to use, and the fallback it needs. Never run `npx modern-web-guidance` to get it.
3. Stay within the inventory's `## Baseline target`. A feature newer than the target needs the fallback Modern Web Guidance gives, or a catalogued component that already handles it.

Without Modern Web Guidance, use the inventory and the Baseline target alone. Every other step is the same.

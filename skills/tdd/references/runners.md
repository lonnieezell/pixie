# Running a subset, by stack

**PHP: CodeIgniter 4 / PHPUnit**
- One file: `vendor/bin/phpunit tests/unit/Foo/BarTest.php`
- By name: `vendor/bin/phpunit --filter 'BarTest::testRejectsEmptyCart'`
- Groups: `--group <name>` if the project tags tests.
- Seams: feature tests (`FeatureTestTrait`, `$this->get('/route')`) for HTTP behavior; `CIUnitTestCase` with `DatabaseTestTrait` against the test DB for models.

**PHP: Laravel / Pest or PHPUnit**
- `php artisan test --filter=RejectsEmptyCart`, or `vendor/bin/pest tests/Feature/CheckoutTest.php`
- Pest `--dirty` runs only test files with uncommitted changes, which is handy for re-checking the slice.
- Seams: HTTP tests (`$this->postJson(...)`), Artisan command tests, `RefreshDatabase` against a test DB. Fake at boundaries with `Http::fake()`, `Mail::fake()`, `Queue::fake()`.

**TypeScript / React: Vitest (or Jest)**
- Related tests: `npx vitest related src/cart/total.ts --run` (Jest: `npx jest --findRelatedTests src/cart/total.ts`)
- One test: `npx vitest run src/cart/total.test.ts -t "rejects empty cart"`
- Seams: exported functions and hooks; components through React Testing Library queries (role, label, text), never component state or internals.

**Rust: cargo**
- One crate: `cargo test -p <crate>`
- By name: `cargo test -p <crate> rejects_empty_cart`
- One integration-test file: `cargo test --test checkout`
- Seams: a crate's public API from `tests/`; unit tests in `mod tests` only for logic with no public seam.

If the project has its own wrapper (`composer test`, `npm test`, `make test`, `just test`), use it, adding the subset arguments it forwards.

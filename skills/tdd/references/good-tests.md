# What a good test is

A good test checks behavior through a public interface and reads like a specification. The internals could be rewritten entirely and it would still pass.

- Uses only the public interface: the HTTP route, the command, the exported function, the rendered UI.
- Describes **what**, not **how**. One logical assertion per test.
- Verifies through the interface, not a side channel: `createUser()` then `getUser()`, not a raw `SELECT` against the table.

Anti-patterns:

- **Implementation-coupled:** mocks internal collaborators, tests private methods, asserts on call counts or order, or verifies through a side channel. The tell: it breaks during a refactor that did not change behavior.
- **Tautological:** the expected value is computed the way the code computes it (`expect(total(items)).toBe(items.reduce(...))`), so it passes by construction. Use a literal: `expect(total([{price: 10}, {price: 5}])).toBe(15)`.
- **Horizontal slicing:** writing all tests first, then all code. Bulk tests verify *imagined* behavior and lock in test structure before you understand the problem. Work in vertical slices: each test is a tracer bullet shaped by what the last slice taught you.

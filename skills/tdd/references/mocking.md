# Mocking

Mock only at **system boundaries**:

- external APIs (payments, email, third-party HTTP),
- time and randomness,
- the database and filesystem sometimes, though a real test DB or a temp dir is better.

Never mock your own classes, modules, or internal collaborators.

To make boundaries easy to fake:

- **Inject dependencies.** Pass the client in rather than constructing it inside (`processPayment($order, PaymentGateway $gateway)` instead of `new StripeClient(env(...))` in the body).
- **Use SDK-style interfaces.** Give each external operation its own method (`getUser`, `createOrder`) rather than one generic `fetch($endpoint)`, so each fake returns one shape with no conditional logic in the test.

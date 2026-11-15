# What a bad test is (skip rather than write one)

A test is not worth adding if it:

- mostly tests mocks,
- encodes current implementation details,
- is tautological,
- depends on timing, ordering, or unrelated global state,
- needs expensive infrastructure for a small fix, or
- would be deleted right after proving the fix.

"""Pure business logic. No I/O, no logging, no environment reads.

Everything in ``core/`` is a function over plain data. Adapters (``cli/``,
a future ``api/``) import from here and hold no logic of their own.
``tests/architecture/`` enforces this, not code review.
"""

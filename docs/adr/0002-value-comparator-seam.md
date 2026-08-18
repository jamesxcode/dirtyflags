# Make value comparison a seam with two adapters (ValueComparator)

Date: 2026-08-17
Issue: jamesxcode/dirtyflags#13

## Context

ADR-0001 moved the dirty-state logic into `DirtyTracker`, but value comparison
remained hardwired inside the tracker's closure: blake2b vs blake2s was chosen
by CPU architecture and every value was compared via `pickle.dumps` + 8-byte
digest. Consequences:

- The hash strategy could not be tested in isolation — tests had to pickle real
  values, including large containers, on every assertion.
- Callers could not substitute a different comparison (e.g. plain equality for
  cheap types) even when that was sufficient.
- Any error during pickling was swallowed into the sentinel string
  `"<unhashable>"` with no way to inspect what failed.

## Decision

Promote value comparison to a seam: a `ValueComparator` interface (one method,
`digest(value) -> str`) in `src/dirtyflags/comparators.py` that the tracker
accepts as an injected dependency (`DirtyTracker(comparator=...)`) rather than
creating itself. Two adapters make the seam real:

- **Prod adapter — `PickleComparator`:** pickle + blake2 (blake2b on 64-bit
  platforms, blake2s otherwise) — the current behaviour, unchanged as the
  default. Values that cannot be pickled raise `ComparatorError`. The pickle
  protocol is pinned explicitly to `pickle.HIGHEST_PROTOCOL` so digests are
  deterministic across Python versions (open question 2 from the issue).
- **Test/lightweight adapter — `EqualityComparator`:** values compare by object
  identity and equality (`id()` plus an `==` check against the previously seen
  value at that identity). Fast, deterministic, no pickling of large objects.

Open questions from the issue, resolved:

1. **Error policy.** Log-and-continue *plus* record: a comparator failure is
   logged (ERROR level) and recorded in `tracker.compare_failures`, an
   inspectable set of attribute names. The tracker's single sentinel is gone —
   each failed attribute baselines at its own per-name failure marker, so it
   never compares as changed until the comparator succeeds for it again (the
   attribute is then removed from `compare_failures`). A failing comparator can
   no longer mask a real change: attributes that digest fine are compared
   normally.
2. **Pickle protocol.** Pinned to `pickle.HIGHEST_PROTOCOL` in
   `PickleComparator`, independent of the interpreter's default.

## Consequences

- The comparator is an *internal* seam of the tracker: injectable for tests,
  but not part of the public `@dirtyflag` interface — no new keyword argument
  on the decorator (the alternatives considered in the issue). Existing users
  see no behavioural difference: the default remains pickle + blake2. The four
  names from :mod:`dirtyflags.comparators` are re-exported from the package
  root (`from dirtyflags import EqualityComparator`, …) so tests and other
  internal consumers can use them without reaching into submodules; this adds
  no new surface to the `@dirtyflag` decorator itself.
- Tests gain leverage: `tests/test_comparators.py` exercises each adapter at
  its digest seam without pickling real values, and `tests/test_tracker.py` can
  inject test doubles (or `EqualityComparator`) to exercise tracker logic —
  including the failure policy — cheaply and deterministically.
- `EqualityComparator` deliberately trades off against the prod adapter: it
  reports a new-but-equal object as changed (identity differs) while in-place
  mutation of a tracked container is *not* reported (same object, still equal).
  It is a test/workhorse adapter for cheap types, not a drop-in replacement for
  `PickleComparator`'s in-place-mutation detection.
- The old `UNHASHABLE` sentinel constant is removed from the tracker; its
  behaviour is subsumed by the per-name failure marker and `compare_failures`.

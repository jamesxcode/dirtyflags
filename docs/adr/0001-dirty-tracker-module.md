# Extract the dirty-state tracker into a deep module (DirtyTracker)

Date: 2026-08-15
Issue: jamesxcode/dirtyflags#12

## Context

The `@dirtyflag` decorator was a shallow module: its interface was nearly as
complex as its implementation. Callers and tests had to learn the mangled
private state name `_dirtyflags__orig`, an implicit late-added rule documented
only in a code comment, that every `dirty_attrs()`/`is_dirty` call re-pickled
and re-hashed all attributes, and the decorator's monkey-patching of
`__init__`/`__setattr__` (including non-idiomatic two-argument
`super(cls, self).__setattr__`). All of that knowledge lived in the
decorator's closure, with no seam where behaviour could be altered or tested
without editing the decorator itself.

## Decision

Extract a deep `DirtyTracker` module (`src/dirtyflags/tracker.py`): one object
per instance that owns the baseline hash table, the late-added rule, and the
dirty computation, behind a small interface:

- `track(attributes)` — record the baseline hashes at creation time
- `set(name, value)` — record an assignment (first-time attributes baseline
  here; existing attributes keep their original baseline)
- `dirty_attrs(current)` — names of tracked attributes whose values changed
- `is_dirty(current)` — whether any tracked attribute changed

The decorator (`src/dirtyflags/dirtyflags.py`) becomes a thin adapter whose
only job is to attach a tracker to each instance under the underscore-prefixed
`_dirtyflags__tracker` attribute and forward lifecycle events to it.  No
hashing logic remains in the decorator, and the non-idiomatic two-argument
super call is gone.

Open questions from the issue, resolved:

1. **Where does the tracker live?** A separate `src/dirtyflags/tracker.py`
   module — not a nested class inside `dirtyflags.py`.  The whole point of the
   deepening is that the logic has its own home with its own test seam.
2. **Per-instance or per-class?** Per-instance (the safe default, matching
   current semantics): each instance gets its own tracker in its `__dict__`.
3. **List or set from `dirty_attrs()`?** List — the public API is unchanged
   (`is_dirty` stays a property, `dirty_attrs()` keeps its name and return
   type).  The README's set-like example output is corrected to show a list.

The tracker observes the instance's live state at query time (it receives the
instance's `__dict__`, minus itself) rather than holding copies of values.
This preserves the current behaviour of detecting in-place mutation of list and
dict attributes, while keeping the tracker free of any back-reference to the
instance it tracks.

## Consequences

- The late-added rule (attribute added after init is not dirty until changed
  again) is preserved as load-bearing behaviour; its documentation moves from
  a code comment into the tracker module docstring and the README.
- Tests gain a seam: `tests/test_tracker.py` exercises the tracker directly,
  so the rule can be tested without poking at mangled names or decorating a
  class.  `tests/test_dirtyflags.py` (public API) is unchanged;
  `tests/test_dirtyflag_adapter.py` covers decorator edge cases (class without
  `__init__`, user-overridden `__setattr__`, unhashable values, tracker
  storage).
- Deleting the tracker module today would move complexity into every caller
  and every test; in this shape it concentrates complexity back in one module —
  the deletion-test signal that the seam is in the right place.
- Candidates 2–4 from the architecture review (comparison seam, dunder
  surgery, query cost) become small local changes now that the tracker exists.

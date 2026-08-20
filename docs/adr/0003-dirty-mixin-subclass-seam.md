# Replace dunder patching with a DirtyMixin subclass seam

Date: 2026-08-20
Issue: jamesxcode/dirtyflags#14

## Context

`@dirtyflag` previously replaced the decorated class's `__init__` and
`__setattr__` methods. That made the decorator responsible for preserving user
dunder behavior and made ordinary subclassing, decorator stacking, dataclasses,
and pickle round-trips fragile.

## Decision

Add public `DirtyMixin`, which creates a per-instance `DirtyTracker`, forwards
construction and assignment through `super()`, and exposes the existing
`is_dirty` and `dirty_attrs()` interface.

Keep `@dirtyflag` as a compatibility adapter. It returns a new subclass with
`DirtyMixin` first in the MRO, leaving the decorated class unchanged. The
adapter keeps the decorated class's module and qualified name so module-level
decorated classes remain pickleable. Reapplying the decorator to an already
mixed-in class returns that class.

## Consequences

- Direct subclasses use normal cooperative inheritance and call
  `super().__init__()` before assigning tracked attributes.
- Decorated classes and their subclasses retain the existing public dirty-state
  interface without monkey-patching dunders.
- Pickle serializes user state without the tracker; restored instances establish
  a fresh dirty-state baseline.

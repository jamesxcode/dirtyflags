# Move hashing to write time: cached dirty set, O(1) queries

Date: 2026-08-20
Issue: jamesxcode/dirtyflags#15

## Context

ADR-0001 and ADR-0002 moved the dirty-state logic into `DirtyTracker` and made
value comparison a seam, but the *timing* of hashing was untouched: every call
to `dirty_attrs()` re-pickled and re-hashed **all** attributes of the instance,
and the `is_dirty` property called `dirty_attrs()` without caching.  Query cost
was O(n × pickle_cost) per call and grew with attribute count — a cost the
interface hid entirely (a query looks like a boolean read).

The full re-hash also carried an implicit contract: in-place container mutation
(`lst.append(3)`) was detected only because querying pickled container contents.
Moving hashing to write time would silently drop that detection unless it was
kept deliberately.

## Decision

Move hashing to write time inside the tracker, and make the mutation contract
an explicit decision:

- **Digests are computed once per value, at write time.** `track()` digests each
  baseline value; `set(name, value)` digests the assigned value and compares it
  against the stored baseline digest, updating a cached dirty set in place.
  Reassigning a value equal to its baseline clears the attribute's dirty flag
  (digest equality).
- **Queries read the cached dirty set in O(1).** `dirty_attrs()` and `is_dirty`
  never digest anything — they return the set maintained by writes.  The
  `current` argument is kept for interface compatibility with the mixin seam but
  is used only to drop attributes that no longer exist on the instance.
- **Default mutation contract: reassignment-only.** In-place container mutation
  never goes through `__setattr__`, so it is not detected by default.  The
  existing test that encoded full-rehash detection
  (`test_list_and_dict_object_dirtyattrs`) is replaced by a test asserting the
  new contract, and the README documents the decision.
- **In-place-mutation detection remains available as an opt-in.** Injecting
  `EqualityComparator` restores content-based comparison at query time (same
  object still equal → not dirty; different object → dirty).  This answers open
  question 1 of the issue: write-time hashing by default, deep-hash-on-query as
  an opt-in behind the existing comparator seam.

Open questions from the issue, resolved:

1. **Write-time only, or write-time plus an opt-in deep-hash mode?** Both:
   write-time hashing is the default (O(1) queries); `EqualityComparator` is the
   opt-in for callers that need in-place-mutation detection.  No new public
   surface — it rides on the existing `DirtyTracker(comparator=...)` seam from
   ADR-0002.
2. **Cost policy if in-place mutation detection must be kept unconditionally?**
   Not needed: the default is reassignment-only, so no per-query hashing of
   mutable containers occurs.  Callers who need that contract opt in and accept
   its query cost explicitly.

## Consequences

- Query cost drops from O(n × pickle_cost) to O(1) (reading a set).  The win is
  measured, not asserted: `benchmarks/query_cost.py` compares per-query time on
  a 1000-attribute object before and after this change.
- Write cost rises by one digest per assignment — paid once, at the moment the
  change happens, instead of on every query.  For hot query paths (the issue's
  motivating case) this is a net win; for write-heavy workloads with few queries
  it is a small constant-factor cost.
- In-place container mutation is no longer detected by default.  This is a
  deliberate, documented contract change: the README states what counts as a
  change, and `EqualityComparator` is the escape hatch.
- The comparator failure policy (ADR-0002) is preserved with one consequence:
  recovery of a failed attribute now happens at the next write rather than at
  query time, since queries no longer digest.
- `set()` without a prior `track()` baselines the attribute (the late-added rule
  from ADR-0001), so trackers used standalone still behave sensibly.

#  SPDX-FileCopyrightText: Copyright (c) 2022-2024. James J. Johnson <james.x.johnson@gmail.com>
#  SPDX-License-Identifier: BSD-3-Clause
"""DirtyTracker owns the dirty-state computation for one decorated instance.

A tracker captures a baseline of attribute digests when an instance is created,
records every subsequent attribute assignment, and answers two questions:

- ``is_dirty`` — has any tracked attribute changed since the baseline?
- ``dirty_attrs()`` — which tracked attributes have changed?

Hashing happens at write time
-----------------------------
Digests are computed once, when a value is recorded (at ``track()`` or
``set()``), and stored in the tracker's state.  Queries read a cached dirty
set in O(1) — they never digest anything, so query cost does not grow with
the number of attributes.

Late-added rule
---------------
An attribute first assigned *after* ``track()`` was called is not dirty until
it is changed again: its first post-track assignment records a fresh baseline
for that attribute, and only a subsequent change to it counts as dirty.

Comparison
----------
Values are compared through an injected :class:`~dirtyflags.comparators.ValueComparator`
rather than a hardwired strategy.  The default comparator is the prod adapter
(:class:`~dirtyflags.comparators.PickleComparator`: ``pickle.dumps`` + blake2,
blake2b on 64-bit platforms, blake2s otherwise); tests may inject a different
adapter (e.g. :class:`~dirtyflags.comparators.EqualityComparator`) without
touching the tracker.

Mutation contract
-----------------
Only reassignments are tracked: a change is detected when an attribute is
assigned a new value through ``set()``.  In-place mutation of a container
attribute (``lst.append(3)``) never goes through ``__setattr__``, so it is not
detected by default.  Inject :class:`~dirtyflags.comparators.EqualityComparator`
to restore in-place-mutation detection at query time (see ADR-0004).

Error policy
------------
A comparator failure is logged and recorded in ``compare_failures`` (a set of
attribute names), never collapsed into one opaque sentinel: callers can inspect
which attributes could not be compared.  A failed attribute baselines at a
failure marker, so it never compares as changed until the comparator succeeds
for it again; once a digest succeeds, the attribute is removed from
``compare_failures``.
"""

import logging
from typing import Any, Dict, Optional, Set

from .comparators import ComparatorError, PickleComparator, ValueComparator

__all__ = ["DirtyTracker"]

logger = logging.getLogger(__name__)


class DirtyTracker:
    """Tracks which attributes of one instance have changed since creation.

    A decorated class attaches one tracker per instance.  The tracker owns the
    baseline digest table, the late-added rule, and the cached dirty set; the
    decorator is a thin adapter that only forwards lifecycle events (creation,
    assignment) to the tracker.

    Value comparison is delegated to an injected :class:`ValueComparator`
    (an internal seam of this module): ``DirtyTracker()`` uses the prod
    pickle+blake2 adapter; pass ``comparator=`` to substitute one.

    Digests are computed at write time (``track``/``set``); queries read the
    cached dirty set and never digest, so they run in O(1).
    """

    def __init__(self, comparator: Optional[ValueComparator] = None) -> None:
        self._comparator = comparator if comparator is not None else PickleComparator()
        self._orig: Dict[str, str] = {}
        self._current: Dict[str, str] = {}
        self._dirty: Set[str] = set()
        self.compare_failures: Set[str] = set()

    def _digest(self, name: str, value: Any) -> str:
        """Digest a value through the comparator.

        On failure the error is logged and the attribute recorded in
        ``compare_failures``; a failure marker is returned so the attribute
        never compares as changed until the comparator succeeds for it again.
        A later success removes the attribute from ``compare_failures``.
        """
        try:
            digest = self._comparator.digest(value)
        except Exception as e:
            logger.error("Could not compare attribute %r: %s", name, e)
            self.compare_failures.add(name)
            return f"<uncomparable:{name}>"
        self.compare_failures.discard(name)
        return digest

    def track(self, attributes: Dict[str, Any]) -> None:
        """Record the baseline digests of ``attributes`` (name -> value)."""
        self._orig = {}
        self._current = {}
        self._dirty.clear()
        for name, value in attributes.items():
            digest = self._digest(name, value)
            self._orig[name] = digest
            self._current[name] = digest

    def set(self, name: str, value: Any) -> None:
        """Record an assignment to ``name`` (write-time hashing).

        The assigned value is digested once and stored as the current digest;
        the dirty set updates in place by comparing it against the baseline.
        A first-time attribute is added to the baseline (late-added rule); an
        existing attribute keeps its original baseline.  An uncomparable value
        never compares as changed, so re-baselining it would only mask a real
        change — it is left untouched.
        """
        digest = self._digest(name, value)
        if name not in self._orig:
            # Late-added rule: a first-time attribute baselines at its first
            # post-track assignment and becomes dirty only on a later change.
            self._orig[name] = digest
        elif digest == self._current.get(name):
            # Reassigning the already-recorded value is not a change (e.g. an
            # unpicklable value whose baseline is the failure marker).
            return
        self._current[name] = digest
        if self._orig[name] == digest:
            self._dirty.discard(name)
        else:
            self._dirty.add(name)

    def dirty_attrs(self, current: Dict[str, Any]) -> list:
        """Return the names of tracked attributes whose values have changed.

        ``current`` maps attribute name to its current value; it is accepted
        for interface compatibility with the mixin seam but is never digested —
        the result is read from the dirty set maintained at write time.  A
        change that bypasses ``set()`` (e.g. in-place mutation of a container)
        is therefore not detected (see the module docstring's mutation
        contract).
        """
        return [name for name in self._dirty if name in current]

    def is_dirty(self, current: Dict[str, Any]) -> bool:
        """Return True if any tracked attribute has changed since creation."""
        return bool(self.dirty_attrs(current))

#  SPDX-FileCopyrightText: Copyright (c) 2022-2024. James J. Johnson <james.x.johnson@gmail.com>
#  SPDX-License-Identifier: BSD-3-Clause
"""DirtyTracker owns the dirty-state computation for one decorated instance.

A tracker captures a baseline of attribute digests when an instance is created,
records every subsequent attribute assignment, and answers two questions:

- ``is_dirty`` — has any tracked attribute changed since the baseline?
- ``dirty_attrs()`` — which tracked attributes have changed?

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
    baseline digest table, the late-added rule, and the dirty computation; the
    decorator is a thin adapter that only forwards lifecycle events (creation,
    assignment) to the tracker.

    Value comparison is delegated to an injected :class:`ValueComparator`
    (an internal seam of this module): ``DirtyTracker()`` uses the prod
    pickle+blake2 adapter; pass ``comparator=`` to substitute one.
    """

    def __init__(self, comparator: Optional[ValueComparator] = None) -> None:
        self._comparator = comparator if comparator is not None else PickleComparator()
        self._orig: Dict[str, str] = {}
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
        self._orig = {k: self._digest(k, v) for k, v in attributes.items()}

    def set(self, name: str, value: Any) -> None:
        """Record an assignment to ``name``.

        A first-time attribute is added to the baseline (late-added rule); an
        existing attribute keeps its original baseline so that subsequent
        queries can detect the change.  An uncomparable value never compares as
        changed, so re-baselining it would only mask a real change — it is
        left untouched.
        """
        if name not in self._orig:
            # Late-added rule: a first-time attribute baselines at its first
            # post-track assignment and becomes dirty only on a later change.
            self._orig[name] = self._digest(name, value)

    def dirty_attrs(self, current: Dict[str, Any]) -> list:
        """Return the names of tracked attributes whose values have changed.

        ``current`` maps attribute name to its current value; it is the live
        view of the instance's state at query time (its ``__dict__``, minus
        the tracker itself).  Tracked attributes that no longer exist are not
        reported as dirty, and an attribute whose comparison fails (see
        ``compare_failures``) is never reported as dirty.
        """
        return [
            name for name, orig_digest in self._orig.items()
            if name in current
            and self._digest(name, current[name]) != orig_digest
        ]

    def is_dirty(self, current: Dict[str, Any]) -> bool:
        """Return True if any tracked attribute has changed since creation."""
        return bool(self.dirty_attrs(current))

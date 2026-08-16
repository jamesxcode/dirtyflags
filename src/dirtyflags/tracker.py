#  SPDX-FileCopyrightText: Copyright (c) 2022-2024. James J. Johnson <james.x.johnson@gmail.com>
#  SPDX-License-Identifier: BSD-3-Clause
"""DirtyTracker owns the dirty-state computation for one decorated instance.

A tracker captures a baseline of attribute hashes when an instance is created,
records every subsequent attribute assignment, and answers two questions:

- ``is_dirty`` — has any tracked attribute changed since the baseline?
- ``dirty_attrs()`` — which tracked attributes have changed?

Late-added rule
---------------
An attribute first assigned *after* ``track()`` was called is not dirty until
it is changed again: its first post-track assignment records a fresh baseline
for that attribute, and only a subsequent change to it counts as dirty.

Hashing
-------
Values are hashed with ``pickle.dumps`` + blake2 (blake2b on 64-bit platforms,
blake2s otherwise).  Values that cannot be pickled hash to a fixed sentinel
and therefore never compare as changed; they are treated as unhashable.
"""

import logging
import pickle
from hashlib import blake2b, blake2s
from platform import architecture
from typing import Any, Dict

__all__ = ["DirtyTracker"]

logger = logging.getLogger(__name__)

# Values that cannot be pickled are hashed to this sentinel.  Because the
# sentinel is constant, an unhashable value never compares as changed against
# itself; it is simply excluded from dirty detection.
UNHASHABLE = "<unhashable>"


class DirtyTracker:
    """Tracks which attributes of one instance have changed since creation.

    A decorated class attaches one tracker per instance.  The tracker owns the
    baseline hash table, the late-added rule, and the dirty computation; the
    decorator is a thin adapter that only forwards lifecycle events (creation,
    assignment) to the tracker.
    """

    def __init__(self) -> None:
        self._orig: Dict[str, str] = {}
        blake2 = blake2b if architecture()[0] == "64bit" else blake2s
        self._hash = lambda val: blake2(pickle.dumps(val), digest_size=8).hexdigest()

    def _hash_value(self, val: Any) -> str:
        """Hash a value, falling back to the unhashable sentinel on failure."""
        try:
            return self._hash(val)
        except Exception as e:
            logger.error(f"Error hashing attribute value: {e}")
            return UNHASHABLE

    def track(self, attributes: Dict[str, Any]) -> None:
        """Record the baseline hashes of ``attributes`` (name -> value)."""
        self._orig = {k: self._hash_value(v) for k, v in attributes.items()}

    def set(self, name: str, value: Any) -> None:
        """Record an assignment to ``name``.

        A first-time attribute is added to the baseline (late-added rule); an
        existing attribute keeps its original baseline so that subsequent
        queries can detect the change.  An unhashable value never compares as
        changed, so re-baselining it would only mask a real change — it is
        left untouched.
        """
        if name not in self._orig:
            # Late-added rule: a first-time attribute baselines at its first
            # post-track assignment and becomes dirty only on a later change.
            self._orig[name] = self._hash_value(value)

    def dirty_attrs(self, current: Dict[str, Any]) -> list:
        """Return the names of tracked attributes whose values have changed.

        ``current`` maps attribute name to its current value; it is the live
        view of the instance's state at query time (its ``__dict__``, minus
        the tracker itself).  Tracked attributes that no longer exist are not
        reported as dirty.
        """
        return [
            name for name, orig_hash in self._orig.items()
            if name in current and self._hash_value(current[name]) != orig_hash
        ]

    def is_dirty(self, current: Dict[str, Any]) -> bool:
        """Return True if any tracked attribute has changed since creation."""
        return bool(self.dirty_attrs(current))

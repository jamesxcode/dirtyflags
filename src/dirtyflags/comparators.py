#  SPDX-FileCopyrightText: Copyright (c) 2022-2024. James J. Johnson <james.x.johnson@gmail.com>
#  SPDX-License-Identifier: BSD-3-Clause
"""Value comparison adapters for :class:`~dirtyflags.tracker.DirtyTracker`.

A comparator answers one question — *does this value differ from the baseline
value?* — by reducing each value to a digest string.  The tracker accepts a
comparator as an injected dependency (an internal seam, not part of the public
``@dirtyflag`` interface) rather than hardwiring one strategy:

- :class:`PickleComparator` is the prod adapter: ``pickle.dumps`` + blake2
  (blake2b on 64-bit platforms, blake2s otherwise).  Values that cannot be
  pickled raise :class:`ComparatorError`.
- :class:`EqualityComparator` is the test/lightweight adapter: values compare
  by object identity and equality (``id()`` plus an ``==`` check against the
  previously seen value at that identity).  It never fails — no pickling of
  large objects — while still catching in-place mutation of containers; a
  new-but-equal object is reported as changed.

Pinning the pickle protocol explicitly makes digests deterministic across
Python versions and platforms (``pickle.DEFAULT_PROTOCOL`` varies with the
interpreter).
"""

import logging
import pickle
from abc import ABC, abstractmethod
from hashlib import blake2b, blake2s
from platform import architecture
from typing import Any, Dict

__all__ = [
    "ComparatorError",
    "EqualityComparator",
    "PickleComparator",
    "ValueComparator",
]

logger = logging.getLogger(__name__)


class ComparatorError(Exception):
    """Raised by a comparator when it cannot digest a value."""


class ValueComparator(ABC):
    """Seam for value comparison: reduce a value to a comparable digest string.

    Digests are opaque to the tracker — only equality matters.  A comparator
    that cannot digest a value raises :class:`ComparatorError`; the tracker
    decides how to handle the failure (it logs it and records the attribute).
    """

    @abstractmethod
    def digest(self, value: Any) -> str:
        """Return a digest string for ``value``.

        Raises:
            ComparatorError: if the value cannot be digested.
        """


class PickleComparator(ValueComparator):
    """Prod adapter: pickle + blake2 (blake2b on 64-bit platforms, blake2s otherwise).

    Digesting a value that cannot be pickled raises :class:`ComparatorError`
    with the underlying pickle error message.
    """

    def __init__(self) -> None:
        self._digest_size = 8
        self._protocol = pickle.HIGHEST_PROTOCOL
        blake2 = blake2b if architecture()[0] == "64bit" else blake2s
        self._blake2 = blake2

    def digest(self, value: Any) -> str:
        try:
            data = pickle.dumps(value, protocol=self._protocol)
        except Exception as e:
            raise ComparatorError(str(e)) from e
        return self._blake2(data, digest_size=self._digest_size).hexdigest()


class EqualityComparator(ValueComparator):
    """Test/lightweight adapter: values compare by object identity and equality.

    An object that is the same object as the baseline (or compares equal to it)
    digests identically; anything else digests differently, so a new-but-equal
    object is reported as changed while in-place mutation of a tracked container
    is not (its identity is unchanged and it still compares equal).  This
    comparator cannot fail: no pickling is involved.

    Digests are keyed by ``(id(value), value == ...)`` rather than ``repr()`` —
    ``repr()`` reflects mutable contents, so an in-place mutation would change
    the digest of the very object it was computed from.
    """

    def __init__(self) -> None:
        # Values seen so far, keyed by identity; used for the equality test.
        self._seen: Dict[int, Any] = {}

    def digest(self, value: Any) -> str:
        vid = id(value)
        baseline = self._seen.get(vid)
        if baseline is None or baseline == value:
            # Same object as the baseline (or first sighting): unchanged.
            self._seen[vid] = value
            return f"obj:{vid}:eq"
        # A different object now occupies this identity slot: changed.
        self._seen[vid] = value
        return f"obj:{vid}:neq:{id(baseline)}"

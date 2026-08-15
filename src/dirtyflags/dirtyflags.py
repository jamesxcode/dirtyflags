#  SPDX-FileCopyrightText: Copyright (c) 2022-2024. James J. Johnson <james.x.johnson@gmail.com>
#  SPDX-License-Identifier: BSD-3-Clause
"""
dirtyflags is a simple Python decorator that tracks when and which object attributes have changed.

The decorator is a thin adapter: it attaches one :class:`DirtyTracker` per
instance and forwards lifecycle events (creation, assignment) to it.  All of
the dirty-state logic — the baseline hash table, the late-added rule, and the
dirty computation — lives in :mod:`dirtyflags.tracker`.
"""

import functools
from typing import Any

from .tracker import DirtyTracker

__all__ = ["dirtyflag"]

# Instance attribute under which each tracker is stored.  The underscore
# prefix keeps it out of the public namespace (and out of ``vars()``-based
# user code); no public attribute is added to instances.
TRACKER_ATTR = "_dirtyflags__tracker"


def dirtyflag(cls: type) -> type:
    """
    Decorator to track which attributes of a class instance have changed since initialization.
    Adds an `is_dirty` property and a `dirty_attrs()` method to the class.

    Each instance gets its own :class:`~dirtyflags.tracker.DirtyTracker`, stored under
    the underscore-prefixed ``_dirtyflags__tracker`` attribute.  The tracker owns the
    baseline hash table, the late-added rule, and the dirty computation; this decorator
    only wires ``__init__`` and ``__setattr__`` to it.
    """
    orig_init = getattr(cls, "__init__", None)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Attach the tracker before the user's __init__ runs so that every
        # assignment made during initialization is forwarded to it.  Writing
        # through object.__setattr__ bypasses the wrapped __setattr__.
        self.__dict__[TRACKER_ATTR] = DirtyTracker()
        if orig_init:
            orig_init(self, *args, **kwargs)

    def __setattr__(self, name: str, value: Any) -> None:
        super(cls, self).__setattr__(name, value)
        tracker = getattr(self, TRACKER_ATTR, None)
        if tracker is not None and name != TRACKER_ATTR:
            tracker.set(name, value)

    def dirty_attrs(self) -> list:
        """Return a list of attribute names that have changed since initialization."""
        tracker = getattr(self, TRACKER_ATTR, None)
        if tracker is None:
            return []
        return tracker.dirty_attrs({k: v for k, v in self.__dict__.items() if k != TRACKER_ATTR})

    @property
    def is_dirty(self) -> bool:
        """Return True if any tracked attribute has changed since initialization."""
        tracker = getattr(self, TRACKER_ATTR, None)
        if tracker is None:
            return False
        return tracker.is_dirty({k: v for k, v in self.__dict__.items() if k != TRACKER_ATTR})

    cls.__init__ = functools.wraps(orig_init)(__init__) if orig_init else __init__
    cls.__setattr__ = __setattr__
    cls.dirty_attrs = dirty_attrs
    cls.is_dirty = is_dirty
    return cls

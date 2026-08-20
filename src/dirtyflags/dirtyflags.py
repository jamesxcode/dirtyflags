#  SPDX-FileCopyrightText: Copyright (c) 2022-2024. James J. Johnson <james.x.johnson@gmail.com>
#  SPDX-License-Identifier: BSD-3-Clause
"""
dirtyflags is a simple Python decorator that tracks when and which object attributes have changed.

The decorator is a thin adapter over the :class:`~dirtyflags.mixin.DirtyMixin`
subclass seam: it returns a new subclass of the decorated class with the mixin
mixed in, and leaves the input class untouched.  No dunders are wrapped or
replaced on the original class — every write takes one hop through the mixin's
``__setattr__``, and all dirty-state logic lives in :mod:`dirtyflags.tracker`.

Subclassing a decorated class inherits tracking through ordinary Python
inheritance (see :mod:`dirtyflags.mixin` for the subclass contract), decorator
stacking stays idempotent, and instances pickle through the plain object
protocol.
"""

from .mixin import DirtyMixin

__all__ = ["dirtyflag"]


def dirtyflag(cls: type) -> type:
    """
    Decorator to track which attributes of a class instance have changed since initialization.
    Adds an `is_dirty` property and a `dirty_attrs()` method to the class.

    The decorator returns a new subclass of ``cls`` with ``DirtyMixin`` first
    in its MRO, leaving ``cls`` and its dunders unchanged.
    """
    if issubclass(cls, DirtyMixin):
        return cls

    return type(
        cls.__name__,
        (DirtyMixin, cls),
        {
            "__module__": cls.__module__,
            "__qualname__": cls.__qualname__,
            "__doc__": cls.__doc__,
        },
    )

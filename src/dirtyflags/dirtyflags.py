#  SPDX-FileCopyrightText: Copyright (c) 2022-2024. James J. Johnson <james.x.johnson@gmail.com>
#  SPDX-License-Identifier: BSD-3-Clause
"""
dirtyflags is a simple Python decorator that tracks when and which object attributes have changed.

"""

import logging
import pickle
from hashlib import blake2b, blake2s
from platform import architecture
from typing import Any

__all__ = ["dirtyflag"]

# create a logger
logger = logging.getLogger(__name__)


def dirtyflag(cls: type) -> type:
    """
    Decorator to track which attributes of a class instance have changed since initialization.
    Adds an `is_dirty` property and a `dirty_attrs()` method to the class.
    """
    import functools

    # Select blake2 hash function based on architecture
    blake2 = blake2b if architecture()[0] == "64bit" else blake2s

    def _hash_value(val: Any) -> str:
        try:
            return blake2(pickle.dumps(val), digest_size=8).hexdigest()
        except Exception as e:
            logger.error(f"Error hashing attribute value: {e}")
            return "<unhashable>"

    orig_init = getattr(cls, "__init__", None)
    orig_setattr = getattr(cls, "__setattr__", None)

    @functools.wraps(orig_init)
    def __init__(self, *args, **kwargs):
        if orig_init:
            orig_init(self, *args, **kwargs)
        # Capture initial attribute hashes
        self._dirtyflags__orig = {k: _hash_value(v) for k, v in self.__dict__.items() if k != "_dirtyflags__orig"}

    def __setattr__(self, name, value):
        if orig_setattr:
            orig_setattr(self, name, value)
        else:
            super(cls, self).__setattr__(name, value)
        # If new attribute, record its original hash
        if hasattr(self, "_dirtyflags__orig") and name != "_dirtyflags__orig":
            if name not in self._dirtyflags__orig:
                self._dirtyflags__orig[name] = _hash_value(value)

    def dirty_attrs(self) -> list:
        """Return a list of attribute names that have changed since initialization."""
        if not hasattr(self, "_dirtyflags__orig"):
            return []
        dirty = []
        for k, v in self.__dict__.items():
            if k == "_dirtyflags__orig":
                continue
            orig_hash = self._dirtyflags__orig.get(k, None)
            if orig_hash is None:
                continue  # attribute added after init, not dirty until changed again
            if _hash_value(v) != orig_hash:
                dirty.append(k)
        return dirty

    @property
    def is_dirty(self) -> bool:
        """Return True if any tracked attribute has changed since initialization."""
        return bool(self.dirty_attrs())

    cls.__init__ = __init__
    cls.__setattr__ = __setattr__
    cls.dirty_attrs = dirty_attrs
    cls.is_dirty = is_dirty
    return cls

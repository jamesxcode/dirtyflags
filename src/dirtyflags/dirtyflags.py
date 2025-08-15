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


def dirtyflag(cls) -> Any:
    """
    Implements a very basic mechanism for tracking which attributes of a class
    have been changed after initialization. When used as a decorator, as designed
    this only track which first level attributes have changed.  It only tracks changes
    made through obj.attr = <somevalue>, and does not maintain the original value.

    :param cls: the class which the decorator is applied to
    :return: the class which the decorator is applied to with alterations

    """

    # declare a sentinel to hold empty objects, since None is a valid default
    _sentinel = object()

    # choose the optimal blake2 for the system architecture (64-bit or 32-bit)
    try:
        blake2 = blake2b if architecture()[0] == "64bit" else blake2s
    except (KeyError,) as error:
        logger.error("Had trouble determing the architecture %error.", error)
        blake2 = blake2s

    # grab the __setattr__ function off of the decorated class to use later
    old_setattr = getattr(cls, "__setattr__", None)

    def _capture_orig_attrs(self):
        """
        Capture the original attribute hashes after initialization.
        """
        self.orig_attrs = {}
        for key, value in self.__dict__.items():
            if key != "orig_attrs":
                self.orig_attrs[key] = _dirty_hash(value)

    # Wrap the original __init__ to capture initial state after construction
    orig_init = getattr(cls, "__init__", None)
    def __init__(self, *args, **kwargs):
        if orig_init:
            orig_init(self, *args, **kwargs)
        _capture_orig_attrs(self)

    # override the decorated class's __setattr__ method
    def __setattr__(self, name, value):
        # call the wrapped class original setattr method to update the value
        if old_setattr:
            old_setattr(self, name, value)
        else:
            # Old-style class
            raise AttributeError
        # If orig_attrs exists, only set hash for new attributes
        if hasattr(self, "orig_attrs") and self.orig_attrs is not None:
            if name != "orig_attrs" and name not in self.orig_attrs:
                self.orig_attrs[name] = _dirty_hash(value)

    def _dirty_hash(any_parm: Any) -> str | None:
        """
        Utility function to calculate a custom hash that will work on even python datatypes
        that are not hashable.

        :param any_parm: The value of the attribue to calculate a hash for
        :return: The custom hash value
        """
        try:
            dhash = blake2(pickle.dumps(any_parm), digest_size=8).hexdigest()
            return dhash
        except (ValueError,) as err:
            logger.error(
                "Had an issue generating a hash code for the attribute error. %err", err
            )
            return None

    @property
    def is_dirty(self) -> bool:
        """
        Utility function to indicate whether the instance of the decorated class
        is dirty or not.

        :param self: the instance being checked
        :return: True if dirty, False otherwise
        """
        return bool(self.dirty_attrs())

    def dirty_attrs(self) -> list | None:
        """
        Utility function to grab the list of instance attributes that
        have been modified and are dirty.

        :param self: the instance object
        :return: a set of the dirty attributes, or None if there are no dirty attributes
        """
        return [
            key
            for key, val in self.__dict__.items()
            if _dirty_hash(val) != self.orig_attrs.get(key) and key != "orig_attrs"
        ]

    # modify the decorated class and return to caller
    setattr(cls, "is_dirty", is_dirty)
    setattr(cls, "dirty_attrs", dirty_attrs)
    setattr(cls, "_capture_orig_attrs", _capture_orig_attrs)
    cls.__setattr__ = __setattr__
    cls.__init__ = __init__
    return cls

#  SPDX-FileCopyrightText: Copyright (c) 2022. James J. Johnson <james.x.johnson@gmail.com>
#  SPDX-License-Identifier: BSD-3-Clause
# ------------------------------------------------------------------------------
"""
dirtyflags is a simple Python decorator that tracks when and which object attributes have changed.

"""
from typing import Any


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

    # grab the __setattr_ function off of the decorated class to use later
    old_setattr = getattr(cls, '__setattr__', None)

    # override the decorated class's __setattr__ method
    def __setattr__(self, name, value):

        # grab the old value of the attribute being set, compare to the new, and
        # mark the attribute as dirty if the values are different
        old_val = getattr(self, name, _sentinel)
        if old_val is not _sentinel and old_val != value:
            # print("Old {0} = {1!r}, new {0} = {2!r}".format(name, old, value))
            self.dirty_attrs.add(name)

        # call the wrapped class original setattr method to update the value
        if old_setattr:
            old_setattr(self, name, value)
        else:
            # Old-style class
            raise AttributeError

        # initialize the dirty flag tracking list
        if getattr(self, 'dirty_attrs', None) is None:
            self.dirty_attrs = set()

    def is_dirty(self) -> bool:
        """
        Utility function to indicate whether the instance of the decorated class
        is dirty or not.

        :param self: the instance being checked
        :return: True if dirty, False otherwise
        """
        return bool(self.dirty_attrs)

    def get_dirty_attrs(self) -> set | None:
        """
        Utility function to grab the list of instance attributes that
        have been modified and are dirty.

        :param self: the instance object
        :return: a set of the dirty attributes, or None if there are no dirty attributes
        """
        return getattr(self, 'dirty_attrs', None) if is_dirty(self) else None

    # modify the decorated class and return to caller
    setattr(cls, 'is_dirty', is_dirty)
    setattr(cls, 'get_dirty_attrs', get_dirty_attrs)
    cls.__setattr__ = __setattr__
    return cls

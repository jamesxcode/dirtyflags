#  SPDX-FileCopyrightText: Copyright (c) 2022-2024. James J. Johnson <james.x.johnson@gmail.com>
#  SPDX-License-Identifier: BSD-3-Clause
"""Tests for subclassing a decorated class through the DirtyMixin seam.

Subclasses of a decorated class inherit tracking through ordinary Python
inheritance.  A subclass that defines ``__init__`` chains through
``super().__init__()`` before assigning its attributes.
"""

from dirtyflags import dirtyflag


@dirtyflag
class Base:
    def __init__(self, x=None, y=None):
        self.x = x
        self.y = y


def test_subclass_inherits_tracking():
    class Sub(Base):
        pass

    s = Sub(1, 2)
    assert not s.is_dirty
    s.x = 9
    assert s.is_dirty
    assert "x" in s.dirty_attrs()
    assert "y" not in s.dirty_attrs()


def test_subclass_custom_init_chaining_is_tracked():
    # A subclass __init__ that chains through super().__init__() with the base
    # class's arguments composes with the mixin: the tracker is created, then
    # the base runs and baselines its attributes.
    class Sub(Base):
        def __init__(self, x, y, z):
            super().__init__(x, y)
            self.z = z

    s = Sub(1, 2, 3)
    assert not s.is_dirty
    s.z = 4
    assert s.is_dirty
    assert "z" in s.dirty_attrs()

def test_subclass_custom_init_chaining_no_args_is_tracked():
    # When the base's __init__ takes no arguments, super().__init__() with no
    # arguments is the supported chaining form.
    @dirtyflag
    class Argless:
        def __init__(self):
            self.a = 1

    class Sub(Argless):
        def __init__(self, z=None):
            super().__init__()
            self.z = z

    s = Sub(3)
    assert not s.is_dirty
    s.z = 4
    assert s.is_dirty
    assert "z" in s.dirty_attrs()

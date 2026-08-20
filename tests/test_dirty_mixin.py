#  SPDX-FileCopyrightText: Copyright (c) 2022-2024. James J. Johnson <james.x.johnson@gmail.com>
#  SPDX-License-Identifier: BSD-3-Clause
"""Tests for the DirtyMixin subclass seam."""

from dirtyflags import DirtyMixin


class Point(DirtyMixin):
    def __init__(self, x=None, y=None):
        super().__init__()
        self.x = x
        self.y = y


def test_mixin_init_is_not_dirty():
    p = Point(1, 2)
    assert not p.is_dirty
    assert p.dirty_attrs() == []


def test_mixin_assignment_marks_dirty():
    p = Point(1, 2)
    p.x = 9
    assert p.is_dirty
    assert "x" in p.dirty_attrs()
    assert "y" not in p.dirty_attrs()


def test_mixin_late_added_rule():
    p = Point(1, 2)
    # First assignment of a late-added attribute records its baseline...
    p.z = 5
    assert not p.is_dirty
    # ...and only a subsequent change counts as dirty.
    p.z = 6
    assert p.is_dirty
    assert "z" in p.dirty_attrs()

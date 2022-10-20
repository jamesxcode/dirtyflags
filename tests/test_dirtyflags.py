#  SPDX-FileCopyrightText: Copyright (c) 2022. James J. Johnson <james.x.johnson@gmail.com>
#  SPDX-License-Identifier: BSD-3-Clause
from dirtyflags.dirtyflags import dirtyflag


def test_basic_object():
    # create object
    @dirtyflag
    class BasicObj():
        def __init__(self, aint, bfloat, cstr):
            self.a = aint
            self.b = bfloat
            self.c = cstr

    # test things
    bo = BasicObj(5, 3.14, 'Test String')
    assert not bo.is_dirty()


def test_basic_object_isdirty():
    # create object
    @dirtyflag
    class BasicObj():
        def __init__(self, aint, bfloat, cstr):
            self.a = aint
            self.b = bfloat
            self.c = cstr

    # test things
    bo = BasicObj(5, 3.14, 'Test String')
    bo.a = 99
    bo.b = 88.88
    assert bo.is_dirty()


def test_basic_object_dirtyattrs():
    # create object
    @dirtyflag
    class BasicObj():
        def __init__(self, aint, bfloat, cstr):
            self.a = aint
            self.b = bfloat
            self.c = cstr

    # test things
    bo = BasicObj(5, 3.14, 'Test String')
    bo.a = 12
    bo.c = "Changed String"
    assert (
            'a' in bo.get_dirty_attrs()
            and 'b' not in bo.get_dirty_attrs()
            and 'c' in bo.get_dirty_attrs()
    )

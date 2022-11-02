#  SPDX-FileCopyrightText: Copyright (c) 2022. James J. Johnson <james.x.johnson@gmail.com>
#  SPDX-License-Identifier: BSD-3-Clause
from dirtyflags.dirtyflags import dirtyflag


def test_basic_object():
    # create object
    @dirtyflag
    class BasicObj():
        def __init__(self, aint, bfloat, cstr, dlist, fdict):
            self.a = aint
            self.b = bfloat
            self.c = cstr
            self.d = dlist
            self.f = fdict

    # test things
    bo = BasicObj(5, 3.14, 'Test String', [1, 2], {'key1': 'val1'})
    assert not bo.is_dirty()


def test_basic_object_isdirty():
    # create object
    @dirtyflag
    class BasicObj():
        def __init__(self, aint, bfloat, cstr, dlist, fdict):
            self.a = aint
            self.b = bfloat
            self.c = cstr
            self.d = dlist
            self.f = fdict

    # test things
    bo = BasicObj(5, 3.14, 'Test String', [1, 2], {'key1': 'val1'})
    bo.a = 99
    bo.b = 88.88
    assert bo.is_dirty()


def test_basic_object_dirtyattrs():
    # create object
    @dirtyflag
    class BasicObj():
        def __init__(self, aint, bfloat, cstr, dlist, fdict):
            self.a = aint
            self.b = bfloat
            self.c = cstr
            self.d = dlist
            self.f = fdict

    # test things
    bo = BasicObj(5, 3.14, 'Test String', [1, 2], {'key1': 'val1'})
    bo.a = 12
    bo.c = "Changed String"
    assert (
            'a' in bo.dirty_attrs()
            and 'b' not in bo.dirty_attrs()
            and 'c' in bo.dirty_attrs()
    )


def test_list_and_dict_object_dirtyattrs():
    # create object
    @dirtyflag
    class BasicObj():
        def __init__(self, aint, bfloat, cstr, dlist, fdict):
            self.a = aint
            self.b = bfloat
            self.c = cstr
            self.d = dlist
            self.f = fdict

    # test things
    bo = BasicObj(5, 3.14, 'Test String', [1, 2], {'key1': 'val1'})
    bo.d.append(3)
    bo.f['key1'] = "Changed Value 1"
    assert (
            'a' not in bo.dirty_attrs()
            and 'b' not in bo.dirty_attrs()
            and 'c' not in bo.dirty_attrs()
            and 'd' in bo.dirty_attrs()
            and 'f' in bo.dirty_attrs()
    )


def test_list_of_instances_for_scope():
    @dirtyflag
    class BasicObj():
        def __init__(self, aint, bfloat):
            self.a = aint
            self.b = bfloat

    # test this case
    lst_objects = [BasicObj(a, a) for a in [1, 2]]
    assert not lst_objects[1].is_dirty()
    lst_objects[1].a = 11
    assert lst_objects[1].is_dirty()
    assert 'a' in lst_objects[1].dirty_attrs()

#  SPDX-FileCopyrightText: Copyright (c) 2022-2024. James J. Johnson <james.x.johnson@gmail.com>
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
    assert not bo.is_dirty


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
    assert bo.is_dirty


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


def test_in_place_container_mutation_is_not_detected():
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
    # In-place mutation of a container attribute is not detected by default:
    # hashing happens at write time, and the mutation never goes through
    # __setattr__.  Only reassignments are tracked (ADR-0004).
    bo.d.append(3)
    bo.f['key1'] = "Changed Value 1"
    assert bo.dirty_attrs() == []
    assert not bo.is_dirty


def test_container_reassignment_is_detected():
    # Reassigning a container attribute is detected: the write digests the new
    # value and compares it against the stored baseline.
    @dirtyflag
    class BasicObj():
        def __init__(self, dlist):
            self.d = dlist

    bo = BasicObj([1, 2])
    assert not bo.is_dirty
    bo.d = [1, 3]
    assert 'd' in bo.dirty_attrs()


def test_list_of_instances_for_scope():
    @dirtyflag
    class BasicObj():
        def __init__(self, aint, bfloat):
            self.a = aint
            self.b = bfloat

    # test this case
    lst_objects = [BasicObj(a, a) for a in [1, 2]]
    assert not lst_objects[1].is_dirty
    lst_objects[1].a = 11
    assert lst_objects[1].is_dirty
    assert 'a' in lst_objects[1].dirty_attrs()

#  SPDX-FileCopyrightText: Copyright (c) 2022-2024. James J. Johnson <james.x.johnson@gmail.com>
#  SPDX-License-Identifier: BSD-3-Clause
"""Tests for the ValueComparator adapters at their digest seam."""
import pickle

from dirtyflags.comparators import ComparatorError, EqualityComparator, PickleComparator


class Unpicklable:
    def __reduce__(self):
        raise pickle.PicklingError("cannot pickle")


def test_pickle_comparator_digest_is_stable():
    comp = PickleComparator()
    assert comp.digest([1, 2]) == comp.digest([1, 2])


def test_pickle_comparator_detects_value_change():
    comp = PickleComparator()
    assert comp.digest(5) != comp.digest(6)
    assert comp.digest([1, 2]) != comp.digest([1, 3])


def test_pickle_comparator_digest_is_independent_of_object_identity():
    """Equal values digest identically even as distinct objects."""
    comp = PickleComparator()
    a, b = [1, 2], [1, 2]
    assert a is not b
    assert comp.digest(a) == comp.digest(b)


def test_pickle_comparator_raises_on_unpicklable_value():
    comp = PickleComparator()
    try:
        comp.digest(Unpicklable())
    except ComparatorError as e:
        assert "cannot pickle" in str(e)
    else:
        raise AssertionError("expected ComparatorError")


def test_pickle_comparator_digest_is_deterministic_across_instances():
    """The pickle protocol is pinned, so digests do not depend on the default protocol."""
    a, b = PickleComparator(), PickleComparator()
    assert a.digest({"x": 1}) == b.digest({"x": 1})


def test_equality_comparator_same_object_not_dirty():
    comp = EqualityComparator()
    v = [1, 2]
    assert comp.digest(v) == comp.digest(v)


def test_equality_comparator_distinct_objects_are_different():
    """Equal but distinct objects compare as changed."""
    comp = EqualityComparator()
    assert comp.digest([1, 2]) != comp.digest([1, 2])


def test_equality_comparator_in_place_mutation_is_not_reported():
    """In-place mutation of a tracked container keeps the same digest (identity + contents)."""
    comp = EqualityComparator()
    v = [1, 2]
    baseline = comp.digest(v)
    v.append(3)
    assert comp.digest(v) == baseline


def test_equality_comparator_digest_is_stable():
    """Digests are stable across calls for the same object."""
    comp = EqualityComparator()
    v = [1, 2]
    first = comp.digest(v)
    assert comp.digest(v) == first


def test_equality_comparator_never_fails():
    """The equality adapter cannot fail: even an unpicklable value digests fine."""
    comp = EqualityComparator()
    comp.digest(Unpicklable())

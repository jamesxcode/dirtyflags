#  SPDX-FileCopyrightText: Copyright (c) 2022-2024. James J. Johnson <james.x.johnson@gmail.com>
#  SPDX-License-Identifier: BSD-3-Clause
"""Tests for DirtyTracker at its public seam: track, set, dirty_attrs, is_dirty."""
import pickle

from dirtyflags.tracker import DirtyTracker


def test_fresh_tracker_is_not_dirty():
    tracker = DirtyTracker()
    tracker.track({"a": 5})
    assert not tracker.is_dirty({"a": 5})
    assert tracker.dirty_attrs({"a": 5}) == []


def test_changed_attribute_is_dirty():
    tracker = DirtyTracker()
    tracker.track({"a": 5, "b": 3.14})
    tracker.set("a", 99)
    assert tracker.is_dirty({"a": 99, "b": 3.14})
    assert tracker.dirty_attrs({"a": 99, "b": 3.14}) == ["a"]


def test_late_added_attribute_not_dirty_until_changed_again():
    tracker = DirtyTracker()
    tracker.track({"a": 5})
    # First post-track assignment records a fresh baseline (late-added rule).
    tracker.set("z", 1)
    assert not tracker.is_dirty({"a": 5, "z": 1})
    assert tracker.dirty_attrs({"a": 5, "z": 1}) == []
    # A subsequent change marks it dirty.
    tracker.set("z", 2)
    assert tracker.is_dirty({"a": 5, "z": 2})
    assert tracker.dirty_attrs({"a": 5, "z": 2}) == ["z"]


def test_late_added_attribute_stays_not_dirty_while_unchanged():
    """A late-added attribute queried before any further change is never dirty."""
    tracker = DirtyTracker()
    tracker.track({"a": 5})
    tracker.set("z", 1)
    # Query repeatedly without changing z: it must never report dirty.
    for _ in range(3):
        assert not tracker.is_dirty({"a": 5, "z": 1})
        assert tracker.dirty_attrs({"a": 5, "z": 1}) == []


def test_reassigning_same_value_is_not_dirty():
    tracker = DirtyTracker()
    tracker.track({"a": 5})
    tracker.set("a", 5)
    assert not tracker.is_dirty({"a": 5})


def test_multiple_attributes_tracked_independently():
    tracker = DirtyTracker()
    tracker.track({"a": 1, "b": 2, "c": 3})
    tracker.set("a", 10)
    tracker.set("c", 30)
    assert tracker.dirty_attrs({"a": 10, "b": 2, "c": 30}) == ["a", "c"]


def test_track_replaces_previous_baseline():
    tracker = DirtyTracker()
    tracker.track({"a": 5})
    tracker.set("a", 9)
    assert tracker.is_dirty({"a": 9})
    # Re-tracking resets the baseline to the current values.
    tracker.track({"a": 9})
    assert not tracker.is_dirty({"a": 9})


def test_unhashable_value_is_not_dirty():
    class Unpicklable:
        def __reduce__(self):
            raise pickle.PicklingError("cannot pickle")

    tracker = DirtyTracker()
    tracker.track({"a": Unpicklable()})
    assert not tracker.is_dirty({"a": Unpicklable()})
    assert tracker.dirty_attrs({"a": Unpicklable()}) == []


def test_late_added_unhashable_value_not_dirty_until_changed_again():
    class Unpicklable:
        def __reduce__(self):
            raise pickle.PicklingError("cannot pickle")

    tracker = DirtyTracker()
    tracker.track({"a": 5})
    # First post-track assignment of a late attribute baselines it; the
    # unhashable sentinel means it never compares as changed.
    tracker.set("z", Unpicklable())
    assert not tracker.is_dirty({"a": 5, "z": Unpicklable()})


def test_tracker_is_stored_in_instance_dict_not_tracker_state():
    """The tracker observes the instance's live __dict__; it holds no copy of values."""
    tracker = DirtyTracker()
    state = {"a": 5}
    tracker.track(dict(state))
    # Mutate the shared state in place (simulates list/dict attribute mutation).
    state["a"] = 99
    assert tracker.is_dirty(state)


def test_trackers_are_independent_per_instance():
    t1, t2 = DirtyTracker(), DirtyTracker()
    t1.track({"a": 1})
    t2.track({"a": 2})
    t1.set("a", 99)
    assert t1.is_dirty({"a": 99})
    assert not t2.is_dirty({"a": 2})

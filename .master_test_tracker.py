#  SPDX-FileCopyrightText: Copyright (c) 2022-2024. James J. Johnson <james.x.johnson@gmail.com>
#  SPDX-License-Identifier: BSD-3-Clause
"""Tests for DirtyTracker at its public seam: track, set, dirty_attrs, is_dirty."""
import logging
import pickle

from dirtyflags.comparators import EqualityComparator
from dirtyflags.tracker import DirtyTracker


class RecordingComparator:
    """Test double: records every value it digests and returns a fixed digest."""

    def __init__(self):
        self.digests = []

    def digest(self, value):
        self.digests.append(value)
        return "digest"


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


def test_injected_comparator_is_used_for_all_digests():
    """The comparator is an injectable seam: track/set/is_dirty all digest through it."""
    comp = RecordingComparator()
    tracker = DirtyTracker(comparator=comp)
    tracker.track({"a": 5})
    assert comp.digests == [5]
    tracker.set("a", 9)
    # set records the assignment but keeps the baseline: no new digest.
    assert comp.digests == [5]
    tracker.is_dirty({"a": 9})
    # The query digests the current value once per tracked attribute.
    assert comp.digests == [5, 9]


def test_comparator_failure_is_logged_and_recorded():
    """A comparator failure is logged and recorded per-attribute, never collapsed into a sentinel."""

    class ExplodingComparator:
        def digest(self, value):
            if isinstance(value, int):
                raise ValueError("cannot digest ints")
            return "digest"

    tracker = DirtyTracker(comparator=ExplodingComparator())
    tracker.track({"a": 5})
    assert "a" in tracker.compare_failures
    assert not tracker.is_dirty({"a": 5})
    assert tracker.dirty_attrs({"a": 5}) == []


def test_comparator_failure_recovered_by_later_success():
    """Once the comparator succeeds for an attribute, it is removed from compare_failures."""

    class FlakyComparator:
        def __init__(self):
            self.calls = 0

        def digest(self, value):
            self.calls += 1
            if isinstance(value, int) and self.calls <= 2:
                raise ValueError("flaky")
            return "digest"

    tracker = DirtyTracker(comparator=FlakyComparator())
    tracker.track({"a": 5})          # call 1: fails -> recorded
    assert "a" in tracker.compare_failures
    tracker.is_dirty({"a": 5})       # call 2: fails -> still recorded
    assert "a" in tracker.compare_failures
    tracker.is_dirty({"a": 5})       # call 3: succeeds -> recovered
    assert "a" not in tracker.compare_failures


def test_comparator_failure_is_logged(caplog):
    class ExplodingComparator:
        def digest(self, value):
            raise ValueError("cannot digest ints")

    with caplog.at_level(logging.ERROR, logger="dirtyflags.tracker"):
        DirtyTracker(comparator=ExplodingComparator()).track({"a": 5})
    assert any("a" in record.message for record in caplog.records)


def test_default_comparator_is_pickle_blake2():
    """Default behaviour is unchanged: pickle + blake2 (blake2b on 64-bit)."""
    import hashlib
    from platform import architecture

    tracker = DirtyTracker()
    tracker.track({"a": [1, 2]})
    expected = (
        hashlib.blake2b if architecture()[0] == "64bit" else hashlib.blake2s
    )(pickle.dumps([1, 2]), digest_size=8).hexdigest()
    assert tracker._orig["a"] == expected


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


def test_late_added_value_with_failing_comparator_is_not_dirty():
    """A late-added attribute whose digest fails baselines at the failure marker."""

    class ExplodingComparator:
        def digest(self, value):
            if isinstance(value, int):
                raise ValueError("cannot digest ints")
            return "digest"

    tracker = DirtyTracker(comparator=ExplodingComparator())
    tracker.track({"a": 5})
    # First post-track assignment of a late attribute baselines it; the failure
    # marker means it never compares as changed.
    tracker.set("z", 1)
    assert "z" in tracker.compare_failures
    assert not tracker.is_dirty({"a": 5, "z": 1})


def test_equality_comparator_in_place_mutation_is_not_reported():
    """The equality adapter compares by identity + contents: in-place mutation is invisible."""
    tracker = DirtyTracker(comparator=EqualityComparator())
    state = {"a": [1, 2]}
    tracker.track(dict(state))
    # Mutate the shared container in place (the same object): not dirty.
    state["a"].append(3)
    assert not tracker.is_dirty(state)
    assert tracker.dirty_attrs(state) == []


def test_equality_comparator_replacement_is_reported():
    """Replacing a tracked value with a new-but-equal object is reported as changed."""
    tracker = DirtyTracker(comparator=EqualityComparator())
    tracker.track({"a": [1, 2]})
    # A fresh list with equal contents is a different object: dirty.
    assert tracker.dirty_attrs({"a": [1, 2]}) == ["a"]


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

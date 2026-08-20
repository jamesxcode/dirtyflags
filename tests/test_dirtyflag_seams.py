#  SPDX-FileCopyrightText: Copyright (c) 2022-2024. James J. Johnson <james.x.johnson@gmail.com>
#  SPDX-License-Identifier: BSD-3-Clause
"""Tests for the remaining seams of the DirtyMixin design.

These cover the scenarios the old monkey-patching approach left uncharted:

- decorator stacking: ``@dirtyflag`` applied twice stays idempotent;
- pickle round-trips: instances serialize through the plain object protocol and
  come back with a fresh tracker (asserted through the public interface only);
- dataclasses: the README claims "Works with Python dataclasses" — this test
  makes that claim true.
"""
import pickle
from dataclasses import dataclass

from dirtyflags import dirtyflag


@dirtyflag
class Base:
    def __init__(self, x=None):
        self.x = x


def test_decorator_stacking_is_idempotent():
    @dirtyflag
    @dirtyflag
    class Stacked:
        def __init__(self, x=None):
            self.x = x

    s = Stacked(1)
    assert not s.is_dirty
    s.x = 2
    assert s.is_dirty
    assert "x" in s.dirty_attrs()


def test_pickle_round_trip():
    b = Base(1)
    restored = pickle.loads(pickle.dumps(b))
    assert restored.x == 1
    assert not restored.is_dirty
    # The tracker is re-created at construction time on unpickling, so the
    # baseline reflects the restored state.
    restored.x = 2
    assert restored.is_dirty
    assert "x" in restored.dirty_attrs()


def test_pickle_round_trip_of_dirty_instance():
    b = Base(1)
    b.x = 2
    assert b.is_dirty
    restored = pickle.loads(pickle.dumps(b))
    # The restored instance is freshly constructed: its baseline is the
    # restored state, so it reports clean.  (Tracking is a property of the
    # live session, not of serialized state.)
    assert restored.x == 2
    assert not restored.is_dirty


def test_dataclass_works():
    # README line 53: "Works with Python dataclasses".
    @dirtyflag
    @dataclass
    class Record:
        name: str
        value: int

    r = Record("a", 1)
    assert not r.is_dirty
    r.value = 2
    assert r.is_dirty
    assert "value" in r.dirty_attrs()
    assert "name" not in r.dirty_attrs()


@dirtyflag
@dataclass
class PickleRecord:
    """Module-level dataclass so pickle can resolve the decorated class."""

    name: str
    value: int


def test_dataclass_pickle_round_trip():
    # A decorated dataclass pickles through the plain object protocol (the
    # __reduce__ inherited from DirtyMixin), and re-creates a fresh tracker
    # lazily on first use, baselined on the restored state.
    r = PickleRecord("a", 1)
    restored = pickle.loads(pickle.dumps(r))
    assert (restored.name, restored.value) == ("a", 1)
    assert not restored.is_dirty
    restored.name = "b"
    assert restored.is_dirty
    assert "name" in restored.dirty_attrs()

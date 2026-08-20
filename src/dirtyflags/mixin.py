#  SPDX-FileCopyrightText: Copyright (c) 2022-2024. James J. Johnson <james.x.johnson@gmail.com>
#  SPDX-License-Identifier: BSD-3-Clause
"""The DirtyMixin subclass seam."""

from typing import Any

from .tracker import DirtyTracker

__all__ = ["DirtyMixin"]

TRACKER_ATTR = "_dirtyflags__tracker"


class DirtyMixin:
    """Track changed instance attributes through ordinary inheritance."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        object.__setattr__(self, TRACKER_ATTR, DirtyTracker())
        super().__init__(*args, **kwargs)

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if name != TRACKER_ATTR:
            self._dirty_tracker().set(name, value)

    def dirty_attrs(self) -> list:
        """Return the attributes that have changed since initialization."""
        return self._dirty_tracker().dirty_attrs(self._attributes())

    @property
    def is_dirty(self) -> bool:
        """Return whether any tracked attribute has changed since initialization."""
        return self._dirty_tracker().is_dirty(self._attributes())

    def __getstate__(self) -> dict:
        """Serialize user state without the live dirty-state tracker."""
        getstate = self._base_pickle_hook("__getstate__")
        state = getstate() if getstate is not None else self._attributes()
        if isinstance(state, dict):
            return {
                name: value
                for name, value in state.items()
                if name != TRACKER_ATTR
            }
        return state

    def __setstate__(self, state: dict) -> None:
        """Restore user state with a fresh baseline."""
        setstate = self._base_pickle_hook("__setstate__")
        if setstate is not None:
            setstate(state)
        else:
            for name, value in state.items():
                object.__setattr__(self, name, value)
        tracker = DirtyTracker()
        object.__setattr__(self, TRACKER_ATTR, tracker)
        tracker.track(self._attributes())

    def _attributes(self) -> dict:
        attributes = {
            name: value
            for name, value in self.__dict__.items()
            if name != TRACKER_ATTR
        }
        for cls in type(self).__mro__:
            slots = cls.__dict__.get("__slots__", ())
            if isinstance(slots, str):
                slots = (slots,)
            for name in slots:
                if name not in {"__dict__", "__weakref__"} and hasattr(self, name):
                    attributes[name] = getattr(self, name)
        return attributes

    def _dirty_tracker(self) -> DirtyTracker:
        try:
            return object.__getattribute__(self, TRACKER_ATTR)
        except AttributeError:
            tracker = DirtyTracker()
            object.__setattr__(self, TRACKER_ATTR, tracker)
            tracker.track(self._attributes())
            return tracker

    def _base_pickle_hook(self, name: str):
        seen_mixin = False
        for cls in type(self).__mro__:
            if seen_mixin and cls is not object:
                hook = cls.__dict__.get(name)
                if hook is not None:
                    return hook.__get__(self, type(self))
            if cls is DirtyMixin:
                seen_mixin = True
        return None

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
            getattr(self, TRACKER_ATTR).set(name, value)

    def dirty_attrs(self) -> list:
        """Return the attributes that have changed since initialization."""
        return getattr(self, TRACKER_ATTR).dirty_attrs(self._attributes())

    @property
    def is_dirty(self) -> bool:
        """Return whether any tracked attribute has changed since initialization."""
        return getattr(self, TRACKER_ATTR).is_dirty(self._attributes())

    def __getstate__(self) -> dict:
        """Serialize user state without the live dirty-state tracker."""
        return {
            name: value
            for name, value in self.__dict__.items()
            if name != TRACKER_ATTR
        }

    def __setstate__(self, state: dict) -> None:
        """Restore user state with a fresh baseline."""
        self.__dict__.update(state)
        tracker = DirtyTracker()
        object.__setattr__(self, TRACKER_ATTR, tracker)
        tracker.track(self._attributes())

    def _attributes(self) -> dict:
        return {
            name: value
            for name, value in self.__dict__.items()
            if name != TRACKER_ATTR
        }

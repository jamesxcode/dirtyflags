"""Edge-case probes for the @dirtyflag adapter (decorator seam)."""
import pickle

from dirtyflags import dirtyflag


def test_class_without_init():
    @dirtyflag
    class NoInit:
        pass

    n = NoInit()
    assert not n.is_dirty
    # Late-added rule holds for classes without __init__ too.
    n.a = 5
    assert not n.is_dirty
    n.a = 6
    assert n.is_dirty
    assert 'a' in n.dirty_attrs()


def test_user_overriding_setattr_without_super():
    @dirtyflag
    class CustomSetattr:
        def __init__(self):
            self.x = 1

        def __setattr__(self, name, value):
            object.__setattr__(self, name, value)

    c = CustomSetattr()
    assert not c.is_dirty
    # The decorator's __setattr__ wraps the user's override and still
    # forwards to it; tracking keeps working.
    c.x = 2
    assert c.is_dirty
    assert 'x' in c.dirty_attrs()


def test_unhashable_attribute():
    class Unpicklable:
        def __reduce__(self):
            raise pickle.PicklingError("cannot pickle")

    @dirtyflag
    class WithUnpicklable:
        def __init__(self):
            self.ok = 1
            self.weird = Unpicklable()

    w = WithUnpicklable()
    assert not w.is_dirty
    # Changing a hashable attribute still reports it.
    w.ok = 2
    assert w.dirty_attrs() == ['ok']
    # The unhashable attribute never compares as changed.
    w.weird = Unpicklable()
    assert 'weird' not in w.dirty_attrs()


def test_tracker_attached_under_mangled_name():
    @dirtyflag
    class Mangled:
        def __init__(self):
            self.a = 1

    m = Mangled()
    # The tracker is stored under a single underscore-prefixed instance
    # attribute; no public attributes are added to instances.  (Name mangling
    # only applies to ``self.attr`` references inside class bodies, so storing
    # through ``__dict__`` keeps the literal name.)
    assert "_dirtyflags__tracker" in m.__dict__
    assert "dirty_attrs" not in m.__dict__ and "is_dirty" not in m.__dict__

# dirtyflags

**dirtyflags** is a simple Python decorator that tracks when and which instance attributes have changed.

```python
>>> from dirtyflags import dirtyflag
>>> @dirtyflag
>>> class ChangingObject():
>>>     def __init__(self, attr1: int, attr2: str = "Default Value"):
>>>         self.attr1 = attr1
>>>         self.attr2 = attr2
>>> 
>>>     def __str__(self):
>>>         return (f"attr1 = {self.attr1}, attr2='{self.attr2}'")

>>> # create an instance of the class
instance_default = ChangingObject(attr1=1)

>>> print(f"instance_default is: {instance_default}")
instance_default is: attr1 = 1, attr2='Default Value'

>>> # dirtyflags tracks whether a change has occurred - in this case it has not
>>> print(f"Has this instance changed = {instance_default.is_dirty()}")
Has this instance changed = False

>>> # now change the value of an attribute
>>> instance_default.attr1 = 234
>>> # now dirty flag indicates the class has changed - and tells you what has changed
>>> print(f"Has this instance changed = {instance_default.is_dirty()}")
>>> print(f"The attribute(s) that have changed: {instance_default.dirty_attrs()}")
Has this instance changed = True
The attribute(s) that have changed: {'attr1'}

>>> # dirtyflags even tracks changes when using __setter__
>>> instance_default.__setattr__('attr2', 'changed the default')
>>> print(f"Has this instance changed = {instance_default.is_dirty()}")
>>> print(f"The attribute(s) that have changed: {instance_default.dirty_attrs()}")
Has this instance changed = True
The attribute(s) that have changed: {'attr2', 'attr1'}
```

## Installing dirtyflags


```console
pip install dirtyflags
```
dirtyflags officially supports Python 3.8+

## Supported Features and Best Practices
- Simply use the `@dirtyflag` decorator
- Supports attributes of any datatype, built-in or custom
- Works with Python dataclasses
- Nested classes should have the '@dirtyflag' decorator applied as well

### Subclass seam

`@dirtyflag` remains supported and returns a tracked subclass of the decorated
class. For direct inheritance, subclass `DirtyMixin` and chain through
`super().__init__()` before assigning attributes:

```python
from dirtyflags import DirtyMixin


class ChangingObject(DirtyMixin):
    def __init__(self, attr1):
        super().__init__()
        self.attr1 = attr1
```

Subclasses of a decorated class inherit tracking normally. Applying
`@dirtyflag` more than once is idempotent.

### How dirty state is tracked

Each decorated instance carries its own private tracker (stored under the
underscore-prefixed `_dirtyflags__tracker` attribute).  When the instance is
created, the tracker records a baseline digest of every attribute; every later
assignment digests the new value once and compares it against that stored
baseline.  `is_dirty` and `dirty_attrs()` read a cached dirty set in O(1) —
they never re-hash anything, so query cost does not grow with the number of
attributes.

**Late-added attributes:** an attribute first assigned *after* `__init__` is
not dirty until it is changed again: its first assignment after creation
records a fresh baseline for that attribute, and only a subsequent change to
it marks the instance dirty.

**What counts as a change:** only reassignments are tracked by default.  A
change is detected when an attribute is assigned a new value through
`__setattr__`; in-place mutation of a container attribute (`lst.append(3)`,
`d['key'] = v`) never goes through `__setattr__` and is therefore *not*
detected.  If you need to detect in-place mutation of list/dict attributes,
inject the `EqualityComparator` adapter (identity- and equality-based, never
pickles), which re-checks contents on every query — see
`docs/adr/0004-write-time-hashing.md`.

By default, values are compared with pickle + blake2 (blake2b on 64-bit
platforms, blake2s otherwise).  Values that cannot be pickled never compare as
changed: each failure is logged and recorded in the tracker's
`compare_failures` set, so you can inspect which attributes could not be
compared.  The comparison strategy itself is an internal seam of the tracker
(`dirtyflags.comparators`): `DirtyTracker(comparator=...)` accepts an alternate
adapter — for example `EqualityComparator`, a fast identity/equality-based
comparison that never pickles — without changing the public `@dirtyflag`
interface.

[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/PyCQA/pylint)
---

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
- Sinmply use the `@dirtyflag` decorator
- Supports attributes of any datatype, built-in or custom
- Works with Python dataclasses
- Nested classes should have the '@dirtyflag' decorator applied as well


---

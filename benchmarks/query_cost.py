#  SPDX-FileCopyrightText: Copyright (c) 2022-2024. James J. Johnson <james.x.johnson@gmail.com>
#  SPDX-License-Identifier: BSD-3-Clause
"""Benchmark query cost of DirtyTracker before/after write-time hashing.

Issue #15: "Stop re-hashing the whole object on every query."  This measures,
not asserts, the win: per-query time for ``dirty_attrs()`` on a large object
(1000 attributes) under the two strategies:

- **query-time hashing** (pre-ADR-0004): every query re-pickles and re-hashes
  all attributes — O(n x pickle_cost).
- **write-time hashing** (ADR-0004, current tracker): queries read a cached
  dirty set in O(1).

Run: ``python benchmarks/query_cost.py``
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dirtyflags.comparators import PickleComparator  # noqa: E402
from dirtyflags.tracker import DirtyTracker  # noqa: E402

N_ATTRS = 1000
N_QUERIES = 200


def make_attributes(n: int) -> dict:
    """A large object: ``n`` attributes, half scalars, half small containers."""
    return {f"attr{i}": (i if i % 2 == 0 else [i, i + 1]) for i in range(n)}


def time_query(tracker, current, n_queries: int) -> float:
    """Mean seconds per ``dirty_attrs`` call."""
    start = time.perf_counter()
    for _ in range(n_queries):
        tracker.dirty_attrs(current)
    return (time.perf_counter() - start) / n_queries


def benchmark_query_time_hashing() -> float:
    """Old strategy: digest every attribute on every query."""
    comp = PickleComparator()
    attributes = make_attributes(N_ATTRS)

    def dirty_attrs_query_time(current):
        return [
            name for name, orig in attributes.items()
            if name in current and comp.digest(current[name]) != comp.digest(orig)
        ]

    tracker = DirtyTracker(comparator=comp)
    tracker.track(attributes)
    # Swap in the query-time implementation.
    tracker.dirty_attrs = lambda current: dirty_attrs_query_time(current)
    return time_query(tracker, dict(attributes), N_QUERIES)


def benchmark_write_time_hashing() -> float:
    """Current strategy: digests cached at write time; queries read the set."""
    tracker = DirtyTracker()
    attributes = make_attributes(N_ATTRS)
    tracker.track(attributes)
    return time_query(tracker, dict(attributes), N_QUERIES)


def main() -> None:
    before = benchmark_query_time_hashing()
    after = benchmark_write_time_hashing()
    print(f"object size: {N_ATTRS} attributes, {N_QUERIES} queries each")
    print(f"query-time hashing (pre-ADR-0004): {before * 1e6:12.1f} us/query")
    print(f"write-time hashing (ADR-0004):     {after * 1e6:12.1f} us/query")
    print(f"speedup:                            {before / after:12.1f}x")


if __name__ == "__main__":
    main()

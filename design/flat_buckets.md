# T19 — Flat per-location buckets (design note)

Written 2026-10-05 against `cuVein` d67ed41 (T4 merged), before any code. Scope: the
representation of `HbClock::buckets` in `sanalyzer/src/tools/pc_dependency_analysis.cpp`.
`python/hb_oracle.py` is the specification and is not touched.

## 1. What is there today

```
struct Entry    { uint64_t clock; uint64_t sclock; uint32_t pc; };            // 24 B
struct KeyGroup { uint8_t kind; int scope; std::unordered_map<Tid, Entry> by_tid; };
std::map<Loc, std::vector<KeyGroup>> buckets;      // Loc = tuple<int, uint64_t, uint64_t>
```

Per entry: one hash node (next pointer + `pair<const Tid, Entry>` = 40 B → a 48 B malloc
chunk) plus about one bucket pointer (libstdc++ keeps the load factor ≤ 1), so roughly
56 B. Per location: one red-black tree node (32 B links + 24 B `Loc` + 24 B vector → a
96 B chunk) and a vector of `KeyGroup`s (64 B each: two ints, the `unordered_map` with its
single-bucket inline slot), at least one 80 B chunk. A typical P7 location with a handful of
entries in one or two groups costs 100–150 B per entry. T4 measured 905 M entries for
stencil1d and 2.05 G entries for particlefilter. Both runs died at 174 GB and 122 GB.

The hot paths are `check()`, which visits every entry of every key group on the location
that can conflict with the current record (Procedure Check), and `group_of(loc, kind,
scope).by_tid[t] = Entry{…}`, which replaces the thread's own entry. Each access costs one
`std::map` descent over every live location (about 27 levels at 152 M locations, with a
cache miss at most levels), one or two hash lookups, and a node allocation when the entry
is new.

## 2. The new layout

### 2.1 Entry: 20 bytes, packed

```
struct Slot {            // alignas(4), sizeof == 20
    uint32_t tid;        // the thread, inline or through the overflow table (below)
    uint32_t clock;      // vc epoch  (Entry::clock)
    uint32_t sclock;     // vs epoch  (Entry::sclock)
    uint32_t pc;
    uint8_t  key;        // (kind, strong scope): kind << 3 | (scope + 1)
    uint8_t  pad[3];
};
```

- **Thread.** `Tid` is `(block << 10) | (warp << 5) | lane`, plus `ASYNC_BIT` (bit 62)
  for a cp.async agent. A tid below 2³¹ with no async bit is stored as is. That covers
  every grid up to 2²¹ blocks, which includes every program in the corpus: stencil1d's
  50 M threads are about 200 K blocks. Any other tid is stored as `0x8000'0000 | i`, where
  `i` indexes a side table `std::vector<Tid> wide_tids` and
  `std::unordered_map<Tid, uint32_t> wide_index` assigns it. The mapping is a bijection,
  so decoding is exact. The table holds one row per distinct wide tid (agents, very large
  grids) and stays empty on the corpus.
- **Epochs.** `own(t)` and `owns(t)` are per-thread counters within one kernel. They grow
  by one per RMW and per completed barrier or sync instance of that thread. Exceeding
  2³² − 1 would need more than four billion such events on one thread in one kernel, which
  no recorded trace comes near. This is checked, not assumed: storing an epoch ≥ 2³²
  prints a fatal message naming the thread and the value and calls `abort()`.
  `HbClock` has no other hard-error path; `tv_fail` records trace-validity violations,
  which this is not. Nothing truncates silently.
- **Key.** `kind ∈ {R, W, RMW}` (0..2); scope is `strong_scope(pc)` ∈ {−1 (weak), 0..3}.
  The key byte is a bijection on those 15 values.
- `Entry` stays as the decoded value type that `conflict()`, `report()` and the T12/T14
  holders (`GHeld`) take, so none of them change. A slot is decoded into an `Entry` on
  the stack.

### 2.2 Per-location container: one flat array, a sorted part and an unsorted tail

```
struct LocSlots {        // 16 B, the value of one location-table slot
    Slot*    p;          // malloc'd, capacity = cap_of(n)
    uint32_t n;          // live slots
    uint32_t nsorted;    // p[0, nsorted) is sorted by (key, tid); p[nsorted, n) is the tail
};
```

- **One array per location, not one per key group.** The array keeps all of the
  location's entries. The prefix `[0, nsorted)` is sorted by `(key, tid)`, so each key
  group is one contiguous run inside it. The tail `[nsorted, n)` holds entries in
  arrival order. When the tail reaches `TAIL = 32` slots, it is sorted and merged into
  the prefix (`std::sort` on 32 slots, then `std::inplace_merge`). A location with at most
  32 entries never merges and is a plain arrival-order array. That covers stencil1d's
  average of about 6 entries per location.
- **Capacity.** It is a function of `n`, not a stored field: 2 below 2, otherwise the next
  value of a ×1.5 ladder (2, 3, 4, 6, 9, 13, 19, 28, 42, …). The array is `realloc`'d when
  `n` reaches its capacity. `Slot` is trivially copyable, so `realloc` and `memmove` are
  safe. Worst-case slack is 50 %; for a small array it is a few slots.
- **Finding the thread's own slot** for the replace step: binary search for
  `(key, tid)` in the sorted prefix, then a linear scan of the tail (≤ 32 slots). The
  threshold is 32 because a 32-slot scan reads 640 B (10 cache lines) with no unpredictable
  branches. That is cheaper than a hash probe into a separate node, and at the merge point
  the amortised merge cost is `n/32` slot moves per new entry. Particlefilter's 8,800
  entries per location give about 275 moves per newly arriving thread, and only arriving
  threads pay it; the steady state replaces in place.
- **Check** walks the prefix run by run. At the start of a run with key `k`, its end is
  found by binary search (`upper_bound` on the key alone). If the whole run is skippable,
  check jumps over it. Two cases are skippable, exactly as today's group skip: a read
  meeting a read run, or two RMWs whose scopes make every pair both-RMW and morally strong.
  Otherwise it visits each slot of the run. It then walks the tail and applies the same
  per-key test slot by slot. The set of entries visited, and the per-entry test
  (`morally_strong`, both-RMW, `t` itself skipped), are the current ones.
- **Async WAW** (T1a, `kind == W && is_async`): the same own-slot lookup returns the
  thread's previous copy, which is the current `by_tid.find(t)`.

### 2.3 The location index: open addressing, keyed by a packed `Loc`

```
struct LocKey { uint64_t hi; uint64_t addr; };   // hi = space << 63 | block-or-0
table: std::vector<{LocKey, LocSlots}>  (32 B per slot), linear probing,
       power-of-two size, grown ×2 at load 0.75, empty slot = hi == ~0
```

`(space, block, addr)` maps one to one onto `(hi, addr)`. Space is 0 or 1, and a block id
is below 2⁶³ because it already fits `Tid`'s 54-bit block field. The hash is a 64-bit mix
(splitmix64 finaliser) of `hi ^ rotl(addr, 29)`. Entries are never deleted during a
kernel; `reset()` clears the whole table.

**Which outputs depend on iteration order.** Over the location index, none: `buckets` is
only probed (`check`, the replace step), summed (`stats`) and cleared. No output iterates
it, so replacing the ordered `std::map` by a hash table cannot change a byte. Over the
entries of one location, the order in which `check()` visits the other threads' entries
decides two things only:

1. which instance becomes the *representative* of an `hb_races` aggregate: the `addr`,
   `a_tid` and `b_tid` stored with its first instance, and the position of the aggregate
   in the output list;
2. the push order of the T12 holders (`gheld`, `gdefer`). These are replayed in that
   order when the window closes, which feeds item 1 again.

Neither reaches a count, a class, an `a2_uncertain` count, `hb_races_sync_only`,
`hb_sync_pass` or the coherence profile. Today's order is libstdc++'s hash-bucket order,
which already differs from the specification's dict-insertion order. The parity check
(`test_sync_dominance._race_key`, `t5b_parity.race_key`) compares aggregates at the key
(pc pair, kind, class, space, distance, async, count, a2_uncertain) for exactly that
reason, and it passes on 60/60 programs. The verdict layer reads the representative tids
in two places only, `observed_dyn` (`thread_distance(a_tid, b_tid)`) and the
`warp-po-ordered` relabel (`a_tid >> 5 == b_tid >> 5`). Both are functions of the
aggregate's distance field, which is part of its key. `sync_pairs`' `first_pc` and
`second_pc` are oriented by the record in which the pair first conflicted (the earlier
record's pc first), and every conflict of one record has the same orientation for a given
pc pair, so trace order alone decides them. So item 1 can change between the installed
runtime and this one, as it would between two libstdc++ versions. Every verdict input
stays bit-for-bit. The new visiting order is deterministic: sorted runs by `(key, tid)`,
then the tail in arrival order.

## 3. What does not change

- The set of entries: one per (location, thread, key), replaced only by the same
  thread's later record with the same key. Nothing is dropped, merged across threads
  (no FastTrack collapse) or evicted.
- Check visits every other thread's entry in every conflicting key group of the
  location, with the same per-pair tests and the same `conflict()` call per pair.
- The publish/tick order (I1), the instance gate and its held decisions (T12), the A2
  window bookkeeping and the possible clock (T14), the async agents (T1a), both clocks
  (`vc` and `vs`, T5b) and their bases, `released`, `sync_pairs`, the TV monitor, the
  no-dump aggregates (T4) and the default collector path. The GPU side is untouched.

## 4. Memory, estimated

| | today (per entry, incl. location share) | new |
|---|---|---|
| entry | ~56 B (48 B node + bucket ptr) | 20 B (+ ≤ 50 % capacity slack on growing arrays) |
| location | ~96 B tree node + ≥ 80 B group vector | 32 B table slot / load (0.375–0.75) + one malloc chunk header |

stencil1d (905 M entries, 152.6 M locations): about 18 GB of slots, 8.6 GB of table
(2²⁸ × 32 B) and about 3 GB of chunk overhead, roughly 30 GB in total against the run
that died at 174 GB. particlefilter (2.05 G entries, 234 K locations): about 41 GB of
slots plus slack, roughly 45 GB. `HB_STATS` reports the new layout's bytes exactly
(table + `malloc_usable_size` of every array + the wide-tid table) as `bytes`. It also
reports `bytes_est`, the old layout's estimate from the same counts using the formula T5a
used, so the reduction is read off one run.

## 5. Risks and how they are checked

- An epoch ≥ 2³² aborts, never wraps. No test reaches that path: it would need a kernel with
  more than 2³² barriers or RMWs on one thread.
- A wide tid (async agent, grid ≥ 2²¹ blocks) round-trips through the side table. The
  cp.async green-set tests exercise agents.
- Parity: the green set (every trace re-recorded), T5b's 60-program implementation ==
  specification set, and T4's aggregates-vs-records parity. On the installed runtime, the
  default tool path must be byte-identical on two ScoR programs.

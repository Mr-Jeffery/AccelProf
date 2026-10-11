# T20: per-thread lookups — design note

Branch `perf/thread-index`, from `cuVein` 3c7eefd (T19 merged). Written 2026-10-11, before any
code. Scope: `HbClock` in `sanalyzer/src/tools/pc_dependency_analysis.cpp` only; `hb_oracle.py`
is the specification and does not change; no value, verdict or output changes.

## 1. Where the time is (T19's profile, `eval/FLAT_BUCKETS.md` §4.3)

Per lane access `HbClock::process` does, besides the bucket work T19 already flattened:

| lookup | container | per |
|---|---|---|
| `rmw_note`: `rmw_thr[t0]`, then `std::find` over the thread's pending pcs, then `rmw_pts[pc]` | `unordered_map<Tid, RmwThread>` (a `std::vector` inside), `unordered_map<pc, RmwPc>` | lane |
| `own(t)` → `V(t)`; `owns(t)` → `vs[t]` | `unordered_map<Tid, VClock>` (88 B values), `unordered_map<Tid, SyncClock>` | lane |
| `conflict()`: `V(obs).get(u)` and `vs_get(obs, u)` | the same maps, looked up again for the **same** `obs` | bucket slot visited |
| `last_pc[(block << 5) | warp][lane]` (instance gate only) | `unordered_map<u64, array<u32, 32>>` | lane |
| `win_lanes` probe in `a2_close_lanes` (only while a window is open) | `unordered_map<u64, u32>` | lane |

On lavaMD (3.46 M threads, no RMW at all) the first two rows are 26 % + 23 % + most of the 29.6 %
"inlined STL" (13.6 % of it `rmw_note`'s `std::find`); on fpc (202 kernels) the largest part is
`free`/`malloc_consolidate` under `hb_clock_reset` at kernel start (24.8 %), hotspot 12 %.

## 2. The thread index

Thread ids are `(block << 10) | (warp << 5) | lane` (bit 62: an async agent). Within a kernel the
block size is known (`block_thread_count`, set by `hb_clock_reset`), so the index is
**computed, not assigned**: with `bt` = the block size rounded up to 32 (1024 if unknown),

    idx(t) = (t >> 10) * bt + (t & 1023)      valid iff !(t & ASYNC_BIT) and (t & 1023) < bt

This is the brief's "flat index assigned at first sight" without the id → index map: the map
would itself be a per-lane hash lookup, which is the cost being removed. A tid the formula does
not cover (async agents; a malformed record) goes to a side `unordered_map` with the old
semantics, so no input changes behaviour.

`ThreadArray<T>`: a page directory (`std::vector` of page pointers, grown on demand) over pages
of 2^14 threads, each a `T[16384]` plus a presence bitmap; a page is allocated the first time one
of its threads is touched. Operations: `at(t)` (create), `find(t)` (null if absent), `size()`
(present count, so `HB_STATS`'s `threads` keep their meaning), `each(f)` (present entries in index
order, tid recomputed), `clear()`.

**Is a two-level index needed?** Yes, in the form of the page directory: grids are up to
~10^8 threads (P7 pathfinder: 100 M threads, `100000 1000 5`), and a kernel need not touch all of
them in every container (`rmw_thr` and `vs` are touched by every lane access, `vc` too in
vector-clock mode; but a kernel launched with more blocks than it uses touches a prefix). A flat
`std::vector` sized by the grid would commit memory for untouched threads; lazy pages commit only
the touched 16 K-thread ranges. A third level is not needed: the directory is 8 B per 16 K
threads (49 KB at 10^8).

**Memory at 10^8 threads**, all touched (pathfinder):

| container | value | before: hash node + bucket | after: dense |
|---|---|---|---|
| `vc` | `VClock` 88 B | ~120 B → 12 GB (T4 measured 13.6 GB incl. bases) | 88 B → 8.8 GB |
| `vs` | `SyncClock` 24 B | ~56 B → 5.6 GB | 24 B → 2.4 GB |
| `rmw_thr` | `RmwThread` (vector + 3 fields, 40 B, + the vector's heap block) | ≥ 80 B → 8 GB | 16 B → 1.6 GB |

So the dense arrays are smaller than the maps they replace whenever more than ~70 % of a page's
threads are touched, which is the case for every barrier-heavy grid in the corpus (blocks are
launched whole). The presence bitmap adds 1 bit per thread.

## 3. Which maps change

- `vc` → `ThreadArray<VClock>` (`self` set on first touch, as `V()` does today).
- `vs` → `ThreadArray<SyncClock>`.
- `rmw_thr` → `ThreadArray<RmwState>` with `RmwState { u32 set; u32 last; u32 seen_pc; bool
  has_last; }` (§4).
- `conflict()` and `check()`: `V(obs)` and `vs[obs]` are looked up **once per `check` call**,
  not once per bucket slot visited (the same `obs` throughout).
- `last_pc` (instance gate): the per-warp row is looked up once per record, not per lane.
- `win_lanes`: the warp's mask is read once per record; lane `j`'s bit cannot change while lanes
  `< j` are processed (`a2_open`/`a2_close` touch only their own lane's bit), so testing the
  record-start mask per lane is exact.

Unchanged, and why: `pd` (possible-clock deltas; absent = empty is semantic — `pd.empty()`
short-circuits `sync_group_vc` — and it is read on reported conflicts and window closes, not per
lane); `wins` and the held acquires inside a `Win` (one entry per *open* RMW window, created and
destroyed per RMW; dense storage would trade a small hash for a per-thread 300-byte slot);
`atom_idx` and `coherence` (atomics only); `groups` (cp.async only). If the after-profile shows
any of these, they move in a second step.

## 4. `rmw_note` without per-thread vectors

What R3's trace points need per non-RMW pc `u` is: the set of RMW pcs PO-next to some instance of
`u` (`rel`), whether some instance has none (`stranded`), the RMW pcs PO-previous (`acq`), and
whether some instance has none (`orphan`). Today each thread keeps a vector `pending` of the
distinct non-RMW pcs since its last RMW, deduplicated by a linear `std::find` per lane.

Replacement: a thread's pending set is a node of a shared, append-only **pending trie**
(node = (parent, pc); node 0 = the empty set). `add(S, pc)` is memoised in a transition table
`(S, pc) → S'` (S' = S when `pc` is already on S's path), so all threads that walk the same pcs —
every lane of a converged warp, every warp running the same code — share nodes and transitions;
a one-entry cache of the last transition serves the 32 lanes of a record. On an RMW `r` with set
`S`, `rel[u] ∪= {r}` for each `u` on S's path is applied once per distinct `(S, r)` (memoised;
it is idempotent), and the thread's set becomes 0. At kernel end, `stranded` is applied once per
distinct final set. `acq`/`orphan` are as today, with `rmw_pts[pc]` looked up once per record
(lazily, at the first lane that needs it, so the same keys are created). Equality with today's
output: the emitted sets are `std::set`s printed in pc order (`emit`), and every insertion the old
code makes is made by the new one and vice versa (same sets, possibly in another order).

T4's other R3 cost, the per-lane `rmw_thr` hash lookup, is the dense array of §3. Nothing else of
it can be deferred to kernel end without keeping per-lane history: `acq` needs the RMW last seen
by the thread *at the time* of the access, which is exactly the state kept.

## 5. The previous kernel's state

`reset()` today `clear()`s every container on the launch path; on programs with many kernels this
frees millions of hash nodes and bucket arrays (`malloc_consolidate`, 12–25 % of hotspot/fpc).
After T20 the per-kernel containers are **moved** into a garbage bundle and destroyed on a
background thread; the next `reset()` joins that thread before starting another (at most one
bundle in flight, so the extra memory is bounded by one kernel's state and in practice is gone
long before the next kernel has grown), and `~HbClock` joins it. "Clear, don't free" was the
alternative; it was not chosen because the bulk of the frees are inside values (bucket arrays per
location, clock bases, `std::set`s) that a recycled array would still have to release, and because
retaining the largest kernel's arrays would raise the steady-state footprint of programs whose
kernels differ in size. Nothing in the bundle is shared with the new kernel's state: the sidecar
tables stay in `HbClock`; clock bases are `shared_ptr`s (atomic refcounts) and the new kernel
starts with none.

## 6. Exactness

No container change alters a value: the same entries exist with the same contents; outputs that
iterate a changed container (`HB_STATS`' `vc`/`vs` counts, `rmw_finish`) are order-independent or
sorted. Check visits buckets in the same order (T19's layout is untouched), so even the
representative instance of each `hb_races` aggregate is unchanged. Acceptance is parity (brief
step 3).

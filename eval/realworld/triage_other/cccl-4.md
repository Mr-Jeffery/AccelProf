# cccl-4: T21c step 3 triage of 36 other reports (1 group)

repo NVIDIA/cccl | buggy 45f868f38fdf7a5e9746aa4074bf7da0c730a330 | fixed 5dad0bff89d79d1bffb557f47eaa7a2229b3ae79.
Oracle race (not these): `tile_data[tile_idx]` read by all threads (test L64) vs thread 0's writes (L72/L89).

Result: 1 group / 36 rows class (a) SC.

Evidence used:
- Sources at both commits: `cub/test/catch2_test_device_decoupled_look_back.cu`,
  `cub/cub/agent/single_pass_scan_operators.cuh` (identical in both builds), `cub/cub/detail/strong_{load,store}.cuh`.
  The fix diff is only the `__syncthreads()` after the L64 read.
- The driver `driver_{buggy,fixed}.cu` holds the test kernels verbatim. From recall_pairs.json (driver 60 = test L64,
  68 = L72, 85 = L89), the buggy driver line is the test line minus 4 (inferred).
- SASS: `dots/driver_{buggy,fixed}.sm_89.dot`, kernel `decoupled_look_back_kernel<unsigned int>`.
- Thread ids: `vector-clock/kernel_1.json` `hb_races`. Tid = block x 1024 + thread. Launch is 64 blocks x 256 threads.
- Attribution: `attrib/cccl-4-{buggy,fixed}.json`, full inlined frames.

## cccl-4#01: strong_load.cuh:100 vs strong_store.cuh:90 (36 rows: 9 per build x mode)

Accesses (global; MessageT = `unsigned int`, so TxnWord = `uint2`, one 8-byte descriptor {status, value}):

- Store: strong_store.cuh:90 `st.relaxed.gpu.v2.u32`, then StoreStatus single_pass_scan_operators.cuh:708, called from:
  - SetPartial :769, from TilePrefixCallbackOp::operator() :1283 (thread 0), driver_buggy.cu:80 (test L84
    `prefix(tile_aggregate)`). SASS `@!P2 ST.E.64.STRONG.GPU [R4.64+0x100]` at 0x140.
  - SetInclusive :756, from :1311 (thread 0), same driver line. SASS 0x930.
  - SetInclusive :756, from driver_buggy.cu:67 (test L71, the tile-0 path). SASS `ST.E.64.STRONG.GPU` at 0xce0.
- Load: strong_load.cuh:100 `ld.relaxed.gpu.v2.u32`, then LoadStatus :722, then WaitForValid :782 (first load) or :789
  (spin loop), then ProcessWindow :1265, from operator() :1292 (first window) or :1303 (later windows).
  - SASS `LD.E.64.STRONG.GPU [...+0x100]` at 0x1f0, 0x2f0 and 0x5f0.
- Fixed build: the same chains at pc +0x10 and driver lines +2.
- The 9 pc pairs per build are {0x140} x {0x1f0, 0x2f0, 0x5f0} plus {0x1f0, 0x2f0, 0x5f0} x {0x930, 0xce0}.

Thread relation: always cross-block (dist grid). The writer is thread 0 of the tile's block. The reader is warp-0 lane
k of a later block, with predecessor_idx = tile_idx - k - 1 (:1286). Examples (buggy, kernel_1):

| kind | writer | reader | pcs | count |
|---|---|---|---|---|
| RAW | block 28 t0, SetPartial | block 30 lane 1 | 0x140 / 0x1f0 | 1473 |
| WAR | block 16 t0, SetInclusive | block 17 t0, earlier read of tile 16 | 0x930 / 0x1f0 | 1262 |
| RAW | block 0 t0, tile-0 SetInclusive | block 16 lane 15 | 0xce0 / 0x1f0 | 26 |

All 36 rows have class SC and `a2_uncertain` 0.

What orders them, or fails to:
- Nothing. Both sides use the default `MemoryOrder::relaxed`.
- The only fences in the kernel are `MEMBAR.SC.CTA` at 0x1c0/0x2e0/0x6d0, inside the delay/back-off. They are CTA scope
  and do not cover the other block.
- The protocol is meant to be unordered. The reader spins with `__any_sync` (:786) until status != INVALID and accepts
  PARTIAL or INCLUSIVE. Status and value are packed into one 8-byte word, so no separate payload read needs a fence.

Class (a) SC:
- Both accesses are strong (relaxed) at gpu scope, which covers both blocks, so they are morally strong. Conflicting
  and unordered, so this is a strong conflict and not a data race under PTX. cuVein's SC report is accurate.
- It is unrelated to the oracle race (tile_data). It is identical on both builds because the fix touches only the
  tile_data read.
- Concrete pair: block 28 thread 0 `st.relaxed.gpu` at SetPartial vs block 30 thread 1 `ld.relaxed.gpu` in WaitForValid,
  same descriptor.
- Fix: none needed; the conflict is the look-back protocol.

Side note (inferred, does not change the class): my reading of the PTX ISA is that a vector access (`.v2.u32`) is
modelled as separate scalar accesses in an unspecified order. Formally, then, a reader could combine status and value
from different stores. CUB relies on the aligned 8-byte access being single-copy atomic in hardware; the SASS does emit
`LD/ST.E.64`.

## Defects

None.

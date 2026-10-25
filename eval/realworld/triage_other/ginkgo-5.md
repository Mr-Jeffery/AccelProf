# ginkgo-5: triage of 6 other reports (1 group)

- Repo: ginkgo-project/ginkgo. Buggy commit 09d861f1, fixed commit 64f19461.
- Files:
  - `core/components/bit_packed_storage.hpp` (abbreviated `bps`);
  - `common/unified/components/range_minimum_query_kernels.cpp`.
- Kernels: `generic_kernel_1d` over the `compute_lookup_small<int>` lambda (kernel_0) and the `compute_lookup_large<int>` lambdas (kernel_1 first level, kernels 2-7 later levels). Each runs one block of 512 threads.
- Tids: `(block << 10) | thread`.
- The fixed build has no reports (n_race = 0 in both modes).

| class | groups | rows |
|---|---|---|
| (a) DR | #01 | 6 |

## ginkgo-5#01: bps:154 vs bps:154 (6 rows, buggy: 3 ve + 3 sc)

- **Accesses:** both sides are bps:154 `data_[block] |= value << shift` (<- bps:166 `set()` <- `block_argmin.set(block_idx, argmin)` / `superblocks.set_block_argmin(...)`), plain STG.E global.
  - ptxas merged `clear()` (bps:160 `&=`) and `set_from_zero()` (bps:154 `|=`) into one `LDG.E` (attributed L160) and one `STG.E` (attributed L154) per call. This is the same in each of the three kernels' SASS:
    - compute_lookup_small: LDG 0x1150, STG 0x1320;
    - compute_lookup_large level 0: LDG 0x170, STG 0x1f0;
    - compute_lookup_large levels >= 1: LDG 0x22e0, STG 0x23c0.
- **Threads:** all dist=warp, a2_uncertain 0, adjacent lanes of one warp:
  - kernel_0: 0x1320/0x1320 WAW a_tid 32 vs b_tid 33 (warp 1, lanes 0 and 1), count 448;
  - kernel_1: 0x1f0/0x1f0, 96 vs 97, count 1984;
  - kernels 2-7: 0x23c0/0x23c0, 64 vs 65 / 32 vs 33 / 96 vs 97.
  - Each pair also has the registered load-store half (0x1150/0x1320, 0x170/0x1f0, 0x22e0/0x23c0, WAR) at the same address, which was matched.
- **Ordering:** none. There is no `__syncwarp`, barrier or atomic between neighbouring lanes' read-modify-writes of one packed word, and the two lanes store different values (each ORs its own bits).
- **Class:** (a) DR, WAW, buggy only (same in fixed: no). This is the store-store half of the oracle's lost update. Under PTX it is a separate conflicting pair: two plain writes not ordered by causality order. `recall_pairs.json` registers only the load-store half (bps:160 vs bps:154); adding the WAW pair bps:154 vs bps:154 would absorb these 6 rows.
- **Concrete pair:** kernel_0, threads 32 and 33 (block_idx 32 and 33) both store the word holding their argmin bits.
- **Fix:** make the word update atomic (`atomicAnd(&data_[block], ~(mask_ << shift)); atomicOr(&data_[block], value << shift);`). The upstream fix instead gives one thread all the entries of a word (collation_width).

## Defects

None found in this target.

## Detections of CO+chain against scalar-clock (verdicts: races alone)

Programs that have a verdict in both modes. `chain only` = Race in CO+chain, Clean in scalar-clock; `sc only` = Race in scalar-clock, Clean in CO+chain, split by the paper's label (racy / race-free / unlabelled). `both` = Race in both; of those `with sc-only pairs` = programs where scalar-clock reports a pc pair the chain mode does not (pair sets compared as unordered pc pairs per space, over the union of the reps; scalar-clock and CO are separate recordings).

| suite | programs | chain only (racy / race-free / unl.) | sc only (racy / race-free / unl.) | both Race | both, with sc-only pairs | sc-only pairs | chain-only pairs in those | scalar-clock pairs in programs Race in sc | of them also in C1 | of them also in chain |
|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 400 | 0 / 0 / 0 | 0 / 0 / 0 | 200 | 0 | 0 | 228 | 1294 | 1089 | 1294 |
| Indigo 1.3 (PI) | 4130 | 24 / 224 / 0 | 0 / 0 / 0 | 2420 | 331 | 3912 | 1223 | 16538 | 8970 | 12626 |
| ECL (P3) | 60 | 0 / 0 / 0 | 0 / 0 / 0 | 16 | 0 | 0 | 28 | 16 | 16 | 16 |
| ScoR apps (P4) | 28 | 0 / 6 / 0 | 0 / 0 / 0 | 16 | 9 | 13 | 53 | 77 | 64 | 64 |
| ScoR litmus (P5) | 33 | 0 / 0 / 0 | 1 / 0 / 0 | 2 | 1 | 1 | 0 | 5 | 3 | 3 |
| cuHadron (P6) | 34 | 0 / 0 / 0 | 1 / 0 / 0 | 7 | 3 | 71 | 80 | 94 | 22 | 22 |
| HeCBench other 14 (P7) | 13 | 0 / 0 / 3 | 0 / 0 / 0 | 4 | 0 | 0 | 2 | 65 | 64 | 65 |
| HeCBench SC 10 (P9) | 9 | 0 / 2 / 0 | 0 / 0 / 0 | 3 | 1 | 4 | 73 | 49 | 35 | 45 |
| **all** | 4707 | 24 / 232 / 3 | 2 / 0 / 0 | 2668 | 345 | 4001 | 1687 | 18138 | 10263 | 14135 |

Pair sets cut by the CSV (fewer report_ids than reports_dedup) in 0 of the Race-in-both programs.

## Why scalar-clock's pairs are missing: classification in the collector-only kernel JSONs

For each pc pair that scalar-clock reports and the chain mode does not, over all kernel JSONs of the program's CO recording that contain both pcs as nodes. The classes are tried in this order and the first that applies in any kernel is used:

1. pcs not both recorded
2. edge/chain cross-thread, judged not reported
3. edge/chain only thread-local
4. only via a non-read hop (intervening write/atomic)
5. not reachable: dropped-word deficit at a or c
6. not reachable: deficit at another pc of the kernel
7. not reachable: shared-pool exhaustion not excluded (grid > 4608 CTAs)
8. not reachable: no gap evidence

'Judged not reported' = the verdict step has a recorded transition (edge, or a chain of reads) joining the pair across threads, and its own record for the pair is not a Race (the verdict is given in the csv: ORDERED by a certificate, benign, read-read, etc.). 'deficit' = static check (b): expected shadow words from the node's lane and address counts exceed the words on the edges (c6_static_out.json, per kernel name and pc, estimate). 'pool' = a shared-space pair in a kernel with more than 4,608 CTAs: `pool_miss_count` is not emitted, so exhaustion cannot be confirmed, only not excluded.


**program missed**: pairs per suite and class

| suite | programs | pairs | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|---|
| ScoR litmus (P5) | 1 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron (P6) | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| **all** | 2 | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |

**pair missed, program Race**: pairs per suite and class

| suite | programs | pairs | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|---|
| Indigo 1.3 (PI) | 331 | 3912 | 227 | 0 | 35 | 3558 | 74 | 0 | 0 | 18 |
| ScoR apps (P4) | 9 | 13 | 0 | 1 | 4 | 8 | 0 | 0 | 0 | 0 |
| ScoR litmus (P5) | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| cuHadron (P6) | 3 | 71 | 0 | 1 | 18 | 52 | 0 | 0 | 0 | 0 |
| HeCBench SC 10 (P9) | 1 | 4 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| **all** | 345 | 4001 | 227 | 2 | 61 | 3619 | 74 | 0 | 0 | 18 |

Programs Race in both with sc-only pairs: 345; classified: 345 (cap 700, seeded sample).

**Programs Race in scalar-clock and Clean in CO+chain, one by one**

| suite | id | label | sc pairs | classes of the sc pairs (counts) | oracle (PI) |
|---|---|---|---|---|---|
| P5 | `P5-race_interblock_none-lock_rtraw` | racy | 1 | edge/chain cross-thread, judged not reported x1 |  |
| P6 | `P6-memcpy-shared_readwrite_race-racy` | racy | 1 | edge/chain only thread-local x1 |  |

Static check (b) deficit programs among Indigo 1.3 program-inputs here: 612; among the programs Race in scalar-clock and Clean in CO+chain: 0 of 2.

## Reports of CO+chain that C1 and scalar-clock do not have, split by how the verdict step found them

Unit: a deduped pc pair of a program that is Race in CO+chain (union of the reps in the CSV for C1 and scalar-clock; the raw records of the chain run's confirm JSON for the source). derived = `chain_src` chain (a pair no edge joins, only a chain of reads), rescued = chain_rescue (an edge whose own distance is thread-local, judged at its chain's bound), other = an ordinary edge or event record.

| suite | label | reports in CO+chain | not in C1: derived | rescued | other | not in scalar-clock: derived | rescued | other |
|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | racy | 1522 | 328 | 46 | 0 | 153 | 16 | 59 |
| Indigo 1.3 (PI) | racy | 8680 | 1764 | 204 | 0 | 149 | 14 | 680 |
| Indigo 1.3 (PI) | race-free | 240 | 16 | 0 | 0 | 16 | 0 | 224 |
| Indigo 1.3 (PI) | unlabelled | 5193 | 2051 | 181 | 0 | 279 | 102 | 23 |
| ECL (P3) | race-free | 44 | 0 | 8 | 0 | 0 | 8 | 20 |
| ScoR apps (P4) | racy | 111 | 25 | 4 | 0 | 25 | 4 | 18 |
| ScoR apps (P4) | race-free | 37 | 3 | 4 | 0 | 3 | 4 | 30 |
| ScoR litmus (P5) | racy | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron (P6) | racy | 93 | 79 | 0 | 0 | 79 | 0 | 1 |
| cuHadron (P6) | race-free | 9 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench other 14 (P7) | unlabelled | 72 | 5 | 1 | 0 | 5 | 0 | 2 |
| HeCBench SC 10 (P9) | racy | 118 | 67 | 6 | 0 | 63 | 0 | 10 |
| HeCBench SC 10 (P9) | race-free | 13 | 6 | 0 | 0 | 6 | 0 | 7 |

On race-free-labelled programs (all suites): reports not in C1 25 derived / 12 rescued / 0 other; not in scalar-clock 25 derived / 12 rescued / 281 other.
Race-free-labelled programs Race in CO+chain: 251; in C1: 248; in scalar-clock: 19.
Programs Race in CO+chain without a confirm JSON: {}

## Sample of 20 derived-only pairs on race-free programs: can the hops of the chain share an address?

Pool A = derived pairs (not in C1's reports) of race-free-labelled programs whose verdict changed Clean -> Race (norace programs); pool B = such pairs of race-free-labelled programs that were already Race in C1. Pool sizes: A 4, B 21. Sample: up to 10 from A, the rest from B, seeded random (20261102), one pair per program first. The kernel JSON has no addresses, only words per (pc, ancient pc) edge. For an inner node h with in-hop words n(a,h), out-hop words n(h,c) and N(h) the words that entered the shadow at h (all incoming edge words except the same-instruction repeat lanes), the accesses of h that follow a and the accesses of h that precede c are subsets of the N(h) accesses of h; if n(a,h) + n(h,c) > N(h) they share at least n(a,h) + n(h,c) - N(h) accesses of h, so a, h, c are consecutive at one address: **proven**. Otherwise the JSON cannot say: **undetermined** (the sets may or may not coincide). For a chain with two or more inner nodes the test is per inner node.

| # | program | label | space | a -> ... -> c | k | hop levels | hop words (non-repeat) | N(h) | proven same address (inner nodes) | direct edge a-c / c-a in the kernel |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `P9-knn-cuda` | race-free | shared | 0x460 -> 0x4c0 -> 0x460 | 1 | block/block | 5242880/4194304 | 5242880 | all inner nodes proven | False / False |
| 2 | `P9-knn-cuda` | race-free | shared | 0x480 -> 0x4d0 -> 0x480 | 1 | block/block | 5242880/4194304 | 41943040 | undetermined | False / False |
| 3 | `P9-knn-cuda` | race-free | shared | 0x380 -> 0x550 -> 0x460 | 1 | block/block | 1048576/3145728 | 5242880 | undetermined | False / False |
| 4 | `P9-knn-cuda` | race-free | shared | 0x380 -> 0x550 -> 0x380 | 1 | block/block | 1048576/1048576 | 5242880 | undetermined | False / False |
| 5 | `PI-pull_node_neighbors_block_persistent_cond-DAG_100n_100e` | race-free | shared | 0x250 -> 0x2e0 -> 0x250 | 1 | block/block | 12800/24480 | 25500 | all inner nodes proven | False / False |
| 6 | `PI-pull_node_neighbors_block_shfl_persistent-DAG_100n_100e` | race-free | shared | 0x2e0 -> 0x310 -> 0x2e0 | 1 | block/block | 800/768 | 3200 | undetermined | False / False |
| 7 | `PI-pull_node_neighbors_block_shfl_persistent_reverse-DAG_100n_100e` | race-free | shared | 0x2f0 -> 0x320 -> 0x2f0 | 1 | block/block | 800/768 | 3200 | undetermined | False / False |
| 8 | `PI-conditional_edge_neighbors_block_shfl_persistent-DAG_100n_100e` | race-free | shared | 0x2f0 -> 0x320 -> 0x2f0 | 1 | block/block | 800/768 | 3200 | undetermined | False / False |
| 9 | `P4-graph-coloring-norace-large` | race-free | global | 0x550 -> 0x580 -> 0x550 | 1 | block/block | 60/45 | 480 | undetermined | False / False |
| 10 | `P9-crs-cuda` | race-free | shared | 0x500 -> 0x570 -> 0x970 | 1 | block/block | 52430/52430 | 58722 | all inner nodes proven | False / False |
| 11 | `PI-pull_node_neighbors_block_persistent_reverse-DAG_100n_100e` | race-free | shared | 0x210 -> 0x2a0 -> 0x210 | 1 | block/block | 12800/24480 | 25500 | all inner nodes proven | False / False |
| 12 | `PI-conditional_edge_neighbors_block_shfl_persistent_reverse-DAG_100n_100e` | race-free | shared | 0x300 -> 0x330 -> 0x300 | 1 | block/block | 800/768 | 3200 | undetermined | False / False |
| 13 | `PI-conditional_edge_neighbors_block_persistent_reverse-DAG_100n_100e` | race-free | shared | 0x220 -> 0x2c0 -> 0x220 | 1 | block/block | 12800/24480 | 25500 | all inner nodes proven | False / False |
| 14 | `PI-conditional_edge_neighbors_block_persistent_reverse_cond-DAG_100n_100e` | race-free | shared | 0x250 -> 0x2e0 -> 0x250 | 1 | block/block | 12800/24480 | 25500 | all inner nodes proven | False / False |
| 15 | `PI-conditional_edge_neighbors_block_persistent_cond-DAG_100n_100e` | race-free | shared | 0x240 -> 0x2d0 -> 0x240 | 1 | block/block | 12800/24480 | 25500 | all inner nodes proven | False / False |
| 16 | `PI-pull_node_neighbors_block_persistent_reverse_cond-DAG_100n_100e` | race-free | shared | 0x260 -> 0x2f0 -> 0x260 | 1 | block/block | 12800/24480 | 25500 | all inner nodes proven | False / False |
| 17 | `PI-conditional_edge_neighbors_block_shfl_persistent_cond-DAG_100n_100e` | race-free | shared | 0x320 -> 0x350 -> 0x320 | 1 | block/block | 800/768 | 3200 | undetermined | False / False |
| 18 | `PI-pull_node_neighbors_block_shfl_persistent_reverse_cond-DAG_100n_100e` | race-free | shared | 0x340 -> 0x370 -> 0x340 | 1 | block/block | 800/768 | 3200 | undetermined | False / False |
| 19 | `PI-pull_node_neighbors_block_persistent-DAG_100n_100e` | race-free | shared | 0x200 -> 0x290 -> 0x200 | 1 | block/block | 12800/24480 | 25500 | all inner nodes proven | False / False |
| 20 | `PI-conditional_edge_neighbors_block_persistent-DAG_100n_100e` | race-free | shared | 0x210 -> 0x2b0 -> 0x210 | 1 | block/block | 12800/24480 | 25500 | all inner nodes proven | False / False |

Of the 20 sampled pairs: 10 all inner nodes proven; 10 undetermined

## The production races (CCCL top-k, Ginkgo range-minimum, Kokkos rw_sum, RAFT select_k) and PCL: scalar-clock's matched pairs in the CO recording

| case | id | SC reports matching the oracle's pair(s) | in the chain run's reports | by source (edge / rescued / derived) | classes of the others in the CO recording |
|---|---|---|---|---|---|
| CCCL top-k | cccl-3-buggy | 8 | 8 | 0 / 0 / 8 | - |
| Ginkgo range-minimum | ginkgo-5-buggy | 3 | 3 | 0 / 3 / 0 | - |
| Kokkos rw_sum | kokkos-5-buggy | 3 | 3 | 0 / 3 / 0 | - |
| RAFT select_k | raft-1-buggy | 3 | 0 | 0 / 0 / 0 | only via a non-read hop (intervening write/atomic) [bound grid] x3 |
| PCL (data-race half) | pcl-new-1-buggy | 102 | 44 | 15 / 1 / 28 | only via a non-read hop (intervening write/atomic) [bound warp] x58 |

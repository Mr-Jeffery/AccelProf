# X13: per-shard record counts (2026-11-12)

Question (Yanbo, on the scalability section): how much of the record stream does the busiest shard get, for bfs, pathfinder and stencil1d?
Branch `eval/shard-balance`, cut from `perf/sharded-pcdep` 9b2e8bb3 (T26 plus the X12 gate commit). Nothing installed; the runtime is a private prefix.
Numbers below are copied from `eval/x13/results/` (produced by `eval/x13/x13_analyze.py` and `x13_timing.py` from the run directories archived in `raw_runs.tar.xz`). A number that was not measured is "missing".

## 1. The counter

`YOSEMITE_SHARD_STATS=1` (unset or `0`: off, no extra work). Instrumentation in `sanalyzer/src/tools/pc_dependency_analysis.cpp`, in both sharded passes that route by `ShardPool::shard_of`:

- the location-sharded PCDepGraph pass (T26, `PcdPool`, `accelprof -n N`): counted in the drain thread's router, on the entries it already builds;
- the sync pass of `HbClock` (T22, `ShardPool`, `YOSEMITE_HB_SHARDS=N`, scalar-clock mode): counted in `ShardPool::route`.

Per shard and per kernel, written when the kernel ends (before `kernel_N.json`), **next to** `kernel_N.json`:
`shards_N.json` (PCDepGraph pass) and `shards_sync_N.json` (sync pass), with
`pass`, `shards`, `lane_records[N]`, `warp_records[N]`, `warp_records_distinct`, `split_warp_records`, `distinct_segments_per_shard[N]`, plus `record_types` (the drain's records by type, PCDepGraph pass only) and `top_segment_per_shard[N]` (space, block-or-object, byte offset, lanes of each shard's busiest 128-byte segment).

**Deviation from the brief's file name.** The brief asks for `kernel_N.shards.json`. `eval/baselines/parallel.py`, `run_cuvein.py` and a dozen other readers glob `kernel_*.json`, so that name would be read as a kernel JSON; the files are named `shards_N.json` / `shards_sync_N.json` instead. `kernel_N.json` itself is untouched.

Definitions.
- *lane-record*: one lane of a memory record routed to a shard, counted once per shard a lane reaches (a lane whose words span two segments counts once on each shard). PCDepGraph pass: the lanes of `unique_address_mask` (lanes that repeat an address inside a warp record are one lane, which is what the pass processes). Sync pass: the lanes of `active_mask`.
- *warp-record*: one routed entry with at least one lane, counted once per shard reached (a record split across segments counts on each shard); `warp_records_distinct` counts each record once; `split_warp_records` is the number of records that reached more than one shard. Records with no lane for a shard (barrier, exit, TV/RMW flags, cp.async copies that own no lane) are not warp-records of that shard.
- *segment*: 128 bytes, the unit of `shard_of`. Global memory is keyed by the absolute address; shared memory by (pooled object, offset) in the PCDepGraph pass (the object is a slot of the shadow pool, not the block: slots are reused) and by (block, offset) in the sync pass.
- Run-level figures are the sums over kernels of each shard's counts. `max/total` is the busiest shard's share; `max/mean` = N·max/total with N = 16 (ideal: 1/16 = 6.25 %, max/mean 1); balance alone bounds the speed-up by 16/(max/mean) = total/max. "per-kernel crit. path / total" is Σ_kernels max_shard / total: what a wait at every kernel end cannot beat.

## 2. Runtime, jobs, parity

- Build (job 340798, `normal`, c3): `t26_build.sh` from this branch into `/home/fzheng4/stage-x13`: libsanalyzer `98c61ee2697ed57a`, collector `0a70a76ad63fa437` (relinked from the installed objects, RPATH to the private library). Installed files unchanged before and after: libsanalyzer `5a20fd14ab6c6806`, collector `b746b4dd23e90f46`. Worktree `/home/fzheng4/wt-shard-balance`, `lib -> stage-x13/rt-lib`. The counter's commit is 241dfe40 (code), scripts follow.
- Everything else ran in one whole-node job on `rtx4060ti16g` (job 340799, c3, RTX 4060 Ti sm_89, 125 GB RAM, 16 cores) as `srun --overlap` steps; logs in `eval/x_logs/x13-*-340799.log`.
- **Green set** (A4's seven files + `test_collector_only.py`, counter compiled in, off): **306 passed, 0 skipped** (T26's count on its build: 306 / 0). `eval/x_logs/x13-green-340799.log`.
- **Parity (counter off vs on, 0 differences).** For each id the stream was captured live at N = 16 through T26's capture shim (new runtime, counter off), then replayed through the new library at N = 16 four ways: counter off / on × default inline thresholds / every drain threaded (`YOSEMITE_PCDEP_INLINE_MAX=0`, `YOSEMITE_HB_SHARD_INLINE_MAX=0`). `setup/co_json_diff.py` compares the kernel JSONs; I also compared them byte by byte (`cmp`). Ids: `P4-reduction-norace-large` (a T20 parity id), `P4-matrix-multiplication-norace-small`, `P5-canary`, `P7-backprop-cuda`, and `P7-bfs-cuda` (24 kernels, graph1MW_6) — all from `t5b_parity_ids.txt`. Modes: collector-only (PCDepGraph pass) and scalar-clock with `YOSEMITE_HB_SHARDS=16` (both passes). Result, both modes, all 5 ids, both inline settings: `EQUAL`, `bytes_equal` = all kernels, `differ=0`, and 58 of 58 kernel-file comparisons byte-identical per mode (`kernel files ... 0 differ`). The same replays give the same counts with and without threading (e.g. bfs: PCDepGraph lane-records 47,878,127, sync 48,792,045 in both). `eval/x_logs/x13-parity-{collector-only,scalar-clock}-340799.log`.
- *Live check (informational).* bfs recorded live at N = 16 three times (counter off, off, on; `x13_live_bfs.sh`): the kernel JSONs are not byte-identical between any two of them, and the off-vs-off control differs as much as off-vs-on (collector-only: 8 / 24 kernel files equal off1 vs off2, 7 / 24 off1 vs on1, 7 / 24 off2 vs on1; scalar-clock 8, 8, 9 of 24), because the record order is the GPU's schedule. That is why the gate is the same-stream replay, as in T26.

## 3. Inputs

N = 16 everywhere, one rep per size, the harness's environment (`blib.base_env`), `accelprof -t pc_dependency_analysis -n 16 ./<exe> <args>`, driver `eval/x13/x13_run.py`, sweeps `x13_sweep.sh` / `x13_sweep2.sh`. Scalar-clock runs add `YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=scalar-clock YOSEMITE_HB_DUMP=0 YOSEMITE_HB_SHARDS=16` (X1b's settings). All runs set `YOSEMITE_SHARD_STATS=1` except the timing runs.

| program | paper's command line (`eval/baselines/manifest.csv`) | smaller reduced size | larger reduced size |
|---|---|---|---|
| stencil1d | `stencil1d-cuda 134217728 1000` | `134217728 10` (10 launches) | `134217728 20` (20 launches) |
| pathfinder | `pathfinder-cuda 100000 1000 5` | `100000 10 5` (1/100: 2 launches of 200) | `100000 20 5` (1/50: 4 launches of 200) |
| bfs | `bfs-cuda ../data/bfs/graph1MW_6.txt` | `bfs-cuda <generated 500,000-node graph>` | `bfs-cuda graph1MW_6.txt` (**the paper's graph**, 1,000,000 nodes, 5,999,970 edges) |
| atomicCAS | `atomicCAS-cuda 10000` | `atomicCAS-cuda 100` | `atomicCAS-cuda 200` |

- stencil1d: the array length is the paper's (134,217,728); only the launch count is reduced.
- pathfinder: the width (`cols` = 100,000) is the paper's; rows 10 and 20 (1/100 and 1/50 of 1,000) give 2 and 4 launches at pyramid height 5. Extra points, not asked for: rows 100, 200 and **1000 (the paper's input)**.
- bfs: the paper's graph fits the job (24 kernels, 7,436,165 drained records, wall 3.5 s at N = 16), so it is the larger point. The only graph in the corpus is `graph1MW_6.txt`, so the half-size point is a generated graph, `eval/x13/gen_graph.py 500000 ... 13`: 500,000 nodes, 3,000,387 edges, with the statistics measured on graph1MW_6 (`x13_gstat.py`: degree 2 + Poisson(4), mean 6, one third of the edges to ids within ±1,000 of the node, the rest uniform, costs 1..5; unique-target fraction 0.997 vs 1.000). "Half the frontier" is realised as half the nodes; the frontier size itself was not measured. It is not a standard input.
- atomicCAS: the iteration count (`repeat`) at 1/100 and 1/50; the kernels' thread count is the program's own.

Exact command lines of every run are in `eval/x13/results/raw_runs.tar.xz` (`*/run.json`: `cmd`, `env`, host, job, wall, native, peak RSS).

## 4. Results (N = 16, counter on)

Pass labels: *pcdep (collector-only)* = the PCDepGraph pass in a collector-only run (the headline); *pcdep (scalar-clock)* = the same pass in a scalar-clock run; *sync (scalar-clock)* = the sync pass (`ShardPool`). Warp-record `max/total` and `max/mean` of the two passes of one scalar-clock run are equal in the table because both passes route the same records by the same function; they differ in the lanes they count.

| program | size | pass | kernels | lane-records | max shard | max/total | max/mean | per-kernel crit. path / total | warp-records | max shard | max/total | max/mean | split frac. | top shard | top segment (space, block/object, offset) | its lanes | share of shard |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| atomicCAS | r100 | pcdep (collector-only) | 603 | 338,031,093 | 221,845,820 | 65.63 % | 10.501 | 100.00 % | 338,031,093 | 221,845,820 | 65.63 % | 10.501 | 0.00 % | 1 | global, 0, 0x7fadf9000200 | 111,606,114 | 50.31 % |
| atomicCAS | r200 | pcdep (collector-only) | 1203 | 342,132,968 | 116,364,874 | 34.01 % | 5.442 | 100.00 % | 342,132,968 | 116,364,874 | 34.01 % | 5.442 | 0.00 % | 10 | global, 0, 0x7f937b000400 | 116,364,874 | 100.00 % |
| bfs | 1M | pcdep (collector-only) | 24 | 47,878,127 | 3,135,574 | 6.55 % | 1.048 | 6.72 % | 12,506,450 | 898,525 | 7.18 % | 1.150 | 36.92 % | 4 | global, 0, 0x7f44639e8800 | 126,016 | 4.02 % |
| bfs | 1M | pcdep (scalar-clock) | 24 | 47,878,127 | 3,116,001 | 6.51 % | 1.041 | 6.78 % | 12,502,886 | 908,621 | 7.27 % | 1.163 | 36.90 % | 7 | global, 0, 0x7f89d3a10f80 | 439 | 0.01 % |
| bfs | 1M | sync (scalar-clock) | 24 | 48,792,045 | 3,983,816 | 8.16 % | 1.306 | 8.45 % | 12,502,886 | 908,621 | 7.27 % | 1.163 | 36.90 % | 5 | global, 0, 0x7f89d39e8800 | 999,943 | 25.10 % |
| bfs | 500K | pcdep (collector-only) | 24 | 23,868,338 | 1,548,615 | 6.49 % | 1.038 | 6.81 % | 7,080,651 | 489,117 | 6.91 % | 1.105 | 42.84 % | 13 | global, 0, 0x7fe1b9348880 | 469 | 0.03 % |
| bfs | 500K | pcdep (scalar-clock) | 24 | 23,868,338 | 1,549,303 | 6.49 % | 1.039 | 6.79 % | 7,080,119 | 497,556 | 7.03 % | 1.124 | 42.82 % | 13 | global, 0, 0x7ff15932f900 | 466 | 0.03 % |
| bfs | 500K | sync (scalar-clock) | 24 | 24,302,479 | 1,962,998 | 8.08 % | 1.292 | 8.45 % | 7,080,119 | 497,556 | 7.03 % | 1.124 | 42.82 % | 12 | global, 0, 0x7ff1595e8600 | 498,534 | 25.40 % |
| pathfinder | R1000 | pcdep (collector-only) | 200 | 752,751,536 | 52,347,134 | 6.95 % | 1.113 | 6.95 % | 40,811,142 | 2,797,981 | 6.86 % | 1.097 | 64.47 % | 11 | shared, 29, 0x300 | 19,200 | 0.04 % |
| pathfinder | R100 | pcdep (collector-only) | 20 | 74,622,416 | 5,181,998 | 6.94 % | 1.111 | 6.94 % | 4,045,552 | 276,350 | 6.83 % | 1.093 | 64.48 % | 11 | shared, 23, 0x100 | 3,840 | 0.07 % |
| pathfinder | R10 | pcdep (collector-only) | 2 | 6,809,504 | 474,016 | 6.96 % | 1.114 | 6.96 % | 368,850 | 25,265 | 6.85 % | 1.096 | 64.52 % | 11 | shared, 3, 0x280 | 1,920 | 0.41 % |
| pathfinder | R200 | pcdep (collector-only) | 40 | 149,970,096 | 10,419,296 | 6.95 % | 1.112 | 6.95 % | 8,129,704 | 557,533 | 6.86 % | 1.097 | 64.45 % | 11 | shared, 80, 0x280 | 13,440 | 0.13 % |
| pathfinder | R20 | pcdep (collector-only) | 4 | 14,344,272 | 993,444 | 6.93 % | 1.108 | 6.93 % | 777,417 | 53,021 | 6.82 % | 1.091 | 64.50 % | 11 | shared, 15, 0x300 | 3,840 | 0.39 % |
| stencil1d | L10 | pcdep (collector-only) | 10 | 24,305,991,610 | 1,814,426,621 | 7.46 % | 1.194 | 7.46 % | 1,373,257,705 | 102,085,714 | 7.43 % | 1.189 | 76.98 % | 11 | shared, 60, 0x200 | 2,832,896 | 0.16 % |
| stencil1d | L20 | pcdep (collector-only) | 20 | 48,611,983,220 | 3,589,601,106 | 7.38 % | 1.181 | 7.38 % | 2,746,500,170 | 202,169,437 | 7.36 % | 1.178 | 76.98 % | 11 | shared, 89, 0x100 | 2,850,816 | 0.08 % |

Hottest segments (a shard's busiest segment per kernel, summed over the kernels in which it is that shard's busiest; lane-records and share of all lane-records of the run):

| program | size | pass | hottest segments (shard: space, block/object, offset -> lanes, share of all lane-records) |
|---|---|---|---|
| atomicCAS | r100 | pcdep (collector-only) | 3: global, 0, 0x7fadf9000400 -> 116,185,273 (34.37 %); 1: global, 0, 0x7fadf9000200 -> 111,606,114 (33.02 %); 1: global, 0, 0x7fadf9000000 -> 110,239,706 (32.61 %) |
| atomicCAS | r200 | pcdep (collector-only) | 10: global, 0, 0x7f937b000400 -> 116,364,874 (34.01 %); 5: global, 0, 0x7f937b000000 -> 113,580,091 (33.20 %); 9: global, 0, 0x7f937b000200 -> 112,188,003 (32.79 %) |
| bfs | 1M | pcdep (collector-only) | 4: global, 0, 0x7f44639e8800 -> 126,016 (0.26 %); 15: global, 0, 0x7f44638cbb00 -> 523 (0.00 %); 7: global, 0, 0x7f4463909b80 -> 522 (0.00 %); 9: global, 0, 0x7f44638f4400 -> 515 (0.00 %) |
| bfs | 1M | pcdep (scalar-clock) | 5: global, 0, 0x7f89d39e8800 -> 126,016 (0.26 %); 3: global, 0, 0x7f89d3800000 -> 644 (0.00 %); 13: global, 0, 0x7f89d3909b80 -> 522 (0.00 %); 6: global, 0, 0x7f89d38f4980 -> 512 (0.00 %) |
| bfs | 1M | sync (scalar-clock) | 5: global, 0, 0x7f89d39e8800 -> 999,943 (2.05 %); 3: global, 0, 0x7f89d3800000 -> 644 (0.00 %); 13: global, 0, 0x7f89d3909b80 -> 522 (0.00 %); 6: global, 0, 0x7f89d38f4980 -> 512 (0.00 %) |
| bfs | 500K | pcdep (collector-only) | 11: global, 0, 0x7fe1b95e8600 -> 65,761 (0.28 %); 1: global, 0, 0x7fe1b92f4400 -> 945 (0.00 %); 4: global, 0, 0x7fe1b9200080 -> 644 (0.00 %); 1: global, 0, 0x7fe1b927a580 -> 641 (0.00 %) |
| bfs | 500K | pcdep (scalar-clock) | 12: global, 0, 0x7ff1595e8600 -> 65,761 (0.28 %); 11: global, 0, 0x7ff1592f4400 -> 945 (0.00 %); 2: global, 0, 0x7ff159200080 -> 644 (0.00 %); 1: global, 0, 0x7ff15927a280 -> 516 (0.00 %) |
| bfs | 500K | sync (scalar-clock) | 12: global, 0, 0x7ff1595e8600 -> 498,534 (2.05 %); 11: global, 0, 0x7ff1592f4400 -> 1,083 (0.00 %); 2: global, 0, 0x7ff159200080 -> 644 (0.00 %); 1: global, 0, 0x7ff15927a280 -> 516 (0.00 %) |
| pathfinder | R1000 | pcdep (collector-only) | 1: shared, 0, 0x80 -> 32,640 (0.00 %); 2: shared, 17, 0x280 -> 30,720 (0.00 %); 12: shared, 17, 0x180 -> 30,720 (0.00 %); 7: shared, 0, 0x200 -> 30,080 (0.00 %) |
| pathfinder | R100 | pcdep (collector-only) | 10: shared, 22, 0x180 -> 7,680 (0.01 %); 0: shared, 13, 0x80 -> 7,680 (0.01 %); 4: shared, 13, 0x100 -> 7,680 (0.01 %); 7: shared, 13, 0x280 -> 7,680 (0.01 %) |
| pathfinder | R10 | pcdep (collector-only) | 0: shared, 31, 0x280 -> 1,920 (0.03 %); 1: shared, 4, 0x180 -> 1,920 (0.03 %); 2: shared, 31, 0x100 -> 1,920 (0.03 %); 3: shared, 3, 0x80 -> 1,920 (0.03 %) |
| pathfinder | R200 | pcdep (collector-only) | 11: shared, 80, 0x280 -> 13,440 (0.01 %); 3: shared, 22, 0x100 -> 13,440 (0.01 %); 6: shared, 22, 0x300 -> 11,520 (0.01 %); 7: shared, 22, 0x80 -> 11,520 (0.01 %) |
| pathfinder | R20 | pcdep (collector-only) | 1: shared, 15, 0x100 -> 3,840 (0.03 %); 5: shared, 15, 0x280 -> 3,840 (0.03 %); 10: shared, 15, 0x80 -> 3,840 (0.03 %); 11: shared, 15, 0x300 -> 3,840 (0.03 %) |
| stencil1d | L10 | pcdep (collector-only) | 4: shared, 194, 0x300 -> 2,836,480 (0.01 %); 5: shared, 194, 0x80 -> 2,836,480 (0.01 %); 2: shared, 70, 0x380 -> 2,834,432 (0.01 %); 14: shared, 70, 0x200 -> 2,834,432 (0.01 %) |
| stencil1d | L20 | pcdep (collector-only) | 6: shared, 43, 0x200 -> 4,268,544 (0.01 %); 4: shared, 27, 0x200 -> 4,268,032 (0.01 %); 6: shared, 89, 0x280 -> 4,267,520 (0.01 %); 5: shared, 89, 0x80 -> 2,850,816 (0.01 %) |

Record types of the drain (PCDepGraph pass; sync-event fraction = barrier + block exit + syncwarp + pipeline records over all drained records):

| program | size | pass | drained records | global | shared | local | barrier | block_exit | syncwarp | pipeline | sync-event fraction (barrier+exit+syncwarp+pipeline) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| atomicCAS | r100 | pcdep (collector-only) | 343,733,070 | 338,031,093 | 0 | 0 | 0 | 5,701,977 | 0 | 0 | 1.66 % |
| atomicCAS | r200 | pcdep (collector-only) | 352,750,137 | 342,132,968 | 0 | 0 | 0 | 10,617,169 | 0 | 0 | 3.01 % |
| bfs | 1M | pcdep (collector-only) | 7,436,165 | 6,301,003 | 0 | 0 | 0 | 1,135,162 | 0 | 0 | 15.27 % |
| bfs | 1M | pcdep (scalar-clock) | 7,436,165 | 6,301,003 | 0 | 0 | 0 | 1,135,162 | 0 | 0 | 15.27 % |
| bfs | 500K | pcdep (collector-only) | 3,826,287 | 3,248,640 | 0 | 0 | 0 | 577,647 | 0 | 0 | 15.10 % |
| bfs | 500K | pcdep (scalar-clock) | 3,826,287 | 3,248,640 | 0 | 0 | 0 | 577,647 | 0 | 0 | 15.10 % |
| pathfinder | R1000 | pcdep (collector-only) | 7,058,581,010 | 4,830,892 | 19,983,324 | 0 | 6,393,600,000 | 640,166,794 | 0 | 0 | 99.65 % |
| pathfinder | R100 | pcdep (collector-only) | 72,236,330 | 479,932 | 1,979,724 | 0 | 63,360,000 | 6,416,674 | 0 | 0 | 96.59 % |
| pathfinder | R10 | pcdep (collector-only) | 865,862 | 44,836 | 179,364 | 0 | 576,000 | 65,662 | 0 | 0 | 74.11 % |
| pathfinder | R200 | pcdep (collector-only) | 285,296,850 | 963,372 | 3,980,124 | 0 | 254,720,000 | 25,633,354 | 0 | 0 | 98.27 % |
| pathfinder | R20 | pcdep (collector-only) | 3,163,914 | 93,180 | 379,404 | 0 | 2,432,000 | 259,330 | 0 | 0 | 85.06 % |
| stencil1d | L10 | pcdep (collector-only) | 859,832,310 | 94,371,830 | 681,574,400 | 0 | 41,943,040 | 41,943,040 | 0 | 0 | 9.76 % |
| stencil1d | L20 | pcdep (collector-only) | 1,719,664,620 | 188,743,660 | 1,363,148,800 | 0 | 83,886,080 | 83,886,080 | 0 | 0 | 9.76 % |

### Stability (two reduced sizes)

| program | pass | sizes | lane max/total | ratio (larger / smaller size) | flag (>10 % apart) | warp max/total | ratio |
|---|---|---|---|---|---|---|---|
| atomicCAS | pcdep (collector-only) | r100 -> r200 | 65.63 % -> 34.01 % | 0.5182 | YES | 65.63 % -> 34.01 % | 0.5182 |
| bfs | pcdep (collector-only) | 500K -> 1M | 6.49 % -> 6.55 % | 1.0094 | no | 6.91 % -> 7.18 % | 1.0401 |
| bfs | pcdep (scalar-clock) | 500K -> 1M | 6.49 % -> 6.51 % | 1.0026 | no | 7.03 % -> 7.27 % | 1.0341 |
| bfs | sync (scalar-clock) | 500K -> 1M | 8.08 % -> 8.16 % | 1.0108 | no | 7.03 % -> 7.27 % | 1.0341 |
| pathfinder | pcdep (collector-only) | R10 -> R20 | 6.96 % -> 6.93 % | 0.9949 | no | 6.85 % -> 6.82 % | 0.9957 |
| stencil1d | pcdep (collector-only) | L10 -> L20 | 7.46 % -> 7.38 % | 0.9892 | no | 7.43 % -> 7.36 % | 0.9902 |

Flag threshold: ratio more than 10 % from 1. bfs, pathfinder and stencil1d are stable (ratios within 1.1 % of 1) in the PCDepGraph pass; bfs's sync pass is stable too (1.0108). **atomicCAS is not** (0.5182): all of its lane-records go to three 128-byte segments of about a third each (the hottest three: 34.4 %, 33.0 %, 32.6 % at 100 repeats; 34.0 %, 33.2 %, 32.8 % at 200), so max/total is 1/3 if the hash puts them on three shards and 2/3 if two of them share one shard, and which happens depends on the allocation address of that run. It is a property of where the three segments land, not of the program size. pathfinder is also stable across the three extra sizes: R100 6.94 %, R200 6.95 %, R1000 6.95 %.

### bfs: the top segment is d_over's

With the cudaMalloc logging shim preloaded (`eval/x13/malloc_log.c`, `exec_wrap.c`; separate runs `malloclog/` in the archive; `eval/x13/results/bfs_over.txt`) bfs's `d_over` (the 1-byte flag written by `Kernel2`, `*d_over = 1`) is at the last allocation of the run, and the top segment of the top shard is that segment in every case:

| bfs size | run | pass | top shard of the run | d_over's segment (allocation offset in the 2 MiB arena) | d_over's shard | its lanes | kernels where it is the shard's top segment | share of that shard | share of all lane-records | is the top segment of the top shard |
|---|---|---|---|---|---|---|---|---|---|---|
| 500K | collector-only | pcdep | 10 | …5e8600 | 10 | 65,761 | 7 | 4.12 % | 0.28 % | yes |
| 1M | collector-only | pcdep | 4 | …9e8800 | 4 | 126,016 | 7 | 3.99 % | 0.26 % | yes |
| 500K | scalar-clock | pcdep | 11 | …5e8600 | 11 | 65,761 | 7 | 4.08 % | 0.28 % | yes |
| 500K | scalar-clock | sync | 11 | …5e8600 | 11 | 498,534 | 7 | 24.37 % | 2.05 % | yes |
| 1M | scalar-clock | pcdep | 2 | …9e8800 | 2 | 126,016 | 7 | 4.04 % | 0.26 % | yes |
| 1M | scalar-clock | sync | 2 | …9e8800 | 2 | 999,943 | 8 | 25.05 % | 2.05 % | yes |

Meaning. In the PCDepGraph pass the segment is the top of its shard but carries only 4 % of the shard (0.26 % of all lane-records): the pass counts the lanes of `unique_address_mask`, and all lanes of a warp that write `*d_over` have one address. In the sync pass (active lanes) it carries 25 % of the top shard, 2.05 % of all lane-records, and the top shard's excess over the ideal share is about that much: (3,983,816 − 999,943) / (48,792,045 − 999,943) = 6.24 % for 1M (derived; 999,943 counts only the 8 kernels in which this segment is that shard's top segment, so it is a lower bound on its lanes). The run-level top segments in the main table came from runs without the shim; their offsets inside the 2 MiB allocation arena (…9e8800 for 1M, …5e8600 for 500K) are the ones the shim runs give for `d_over`.

### pathfinder: barrier fraction

`barrier + block_exit` records over all drained records (PCDepGraph pass, collector-only), from the types table above: 74.11 % (rows 10), 85.06 % (20), 96.59 % (100), 98.27 % (200), **99.65 % (1000, the paper's input; the paper cites 99.6 %)**. The reduced inputs the brief names do not reproduce 99.6 %: per launch the barrier records are 32,000 × rows (320,000 at rows 10, 640,000 at 20, 31,968,000 per launch on average at 1000; the last launch of a run is shorter) while the memory records per launch stay at 24,172 global + 100,020 shared, so the fraction rises with the row count. pathfinder's lane share (max/total 6.93–6.96 %) is the same at all five sizes.

## 5. Timing (counter off), N = 1 vs N = 16

`x13_sweep2.sh TIMING=1` (counter off, `YOSEMITE_SHARD_STATS` unset), harness environment, one rep, same node (c3, whole node). "counter on" is the sweep's wall with the counter on, for the counter's own cost (stencil1d: about 3×; the other programs 1.0–1.25×); do not use counter-on walls as timings.

| program | size | mode | native (s) | N=1 wall (s) | N=16 wall (s), counter off | speed-up N=1 / N=16 | N=16 wall (s), counter on | counter-on / counter-off | N=16 peak RSS (MB, off) | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| atomicCAS | r100 | collector-only | 3.7 | 33.1 | 32.8 | 1.01x | 33.5 | 1.02x | 1,134.0 |  |
| atomicCAS | r200 | collector-only | 3.7 | 44.0 | 44.0 | 1.00x | 44.2 | 1.00x | 1,134.5 |  |
| bfs | 1M | collector-only | 0.7 | 3.3 | 2.8 | 1.20x | 3.5 | 1.25x | 1,265.2 |  |
| bfs | 1M | scalar-clock | 0.7 | 17.1 | 4.6 | 3.73x | 5.4 | 1.18x | 2,721.2 |  |
| bfs | 500K | collector-only | 0.5 | 2.0 | 1.9 | 1.08x | 2.2 | 1.16x | 1,097.2 |  |
| bfs | 500K | scalar-clock | 0.6 | 7.5 | 3.5 | 2.12x | 3.9 | 1.11x | 1,779.2 |  |
| pathfinder | R1000 | collector-only | 1.2 | missing | missing | missing | 647.1 | missing | missing |  |
| pathfinder | R100 | collector-only | 0.3 | missing | missing | missing | 7.8 | missing | missing |  |
| pathfinder | R10 | collector-only | 0.2 | 0.8 | 0.8 | 1.00x | 0.9 | 1.06x | 961.7 |  |
| pathfinder | R200 | collector-only | 0.4 | missing | missing | missing | 27.8 | missing | missing |  |
| pathfinder | R20 | collector-only | 0.2 | 1.0 | 1.0 | 1.05x | 1.1 | 1.10x | 967.5 |  |
| stencil1d | L10 | collector-only | 0.5 | 180.0 | 100.0 | 1.80x | 309.5 | 3.10x | 4,138.3 |  |
| stencil1d | L10 | scalar-clock | 0.5 | missing | missing | missing | missing | missing | 122,422.8 | N=16: rc=1 timed_out=False (peak 122422.8 MB); counter on: rc=1 timed_out=False (peak 122562.4 MB) |
| stencil1d | L20 | collector-only | 0.5 | 354.0 | 198.4 | 1.78x | 608.5 | 3.07x | 4,095.7 |  |
| stencil1d | L20 | scalar-clock | 0.7 | missing | missing | missing | missing | missing | missing | counter on: rc=1 timed_out=False (peak 122607.7 MB) |

Context from X12's full-size table (`eval/CO_SHARDED.md`, read-only; other runs, other node): stencil1d 36,373 s → 9,079 s (4.0×), pathfinder 702 → 623 s (1.1×), bfs 4.8 → 4.5 s (1.1×). The reduced runs here: stencil1d 1.8×, pathfinder 1.0×, bfs 1.1–1.2× (collector-only). The balance bound total/max (14.4× pathfinder, 13.5× stencil1d, 15.3× bfs in the PCDepGraph pass; 12.3× for bfs's sync pass) is far above these, so the lane share of the busiest shard does not explain the gains of bfs, pathfinder or stencil1d; for atomicCAS the bound (1.5× at 100 repeats, 2.9× at 200) is as low as the measured 1.0×.

## 6. Missing and caveats

- **stencil1d, sync pass (scalar-clock): missing.** Both reduced sizes (10 and 20 launches) were killed by the node's OOM killer at 122.4–122.6 GB RSS on the 125 GB node (job 340799, rc 1, no kernel finished); a run with the counter off at 10 launches dies the same way (peak 122,422.8 MB), so the counter is not the cause. T19's note says stencil1d's vector/scalar state needs a 188 GB node; the `rtx4060ti16g` nodes do not have one. Not tried elsewhere. No estimate is given.
- pathfinder and atomicCAS were not run in scalar-clock mode (not asked for).
- Timing: N = 1 and N = 16 (counter off) exist for the reduced sizes only; not run for pathfinder rows 100, 200 and 1000. One rep each, as asked; no variance is available.
- bfs's half-size input is generated (section 3), not a standard input; the second point's frontier size is not measured.
- Segment keys: global segments are absolute addresses of that run (they differ between runs); the pooled-object id of a shared segment is a shadow-pool slot, not a block.
- `top segment` per shard is the busiest segment of each kernel; summing it over kernels gives a lower bound on a segment's lanes when it is not the shard's top in every kernel.
- The brief's wording "max-shard lane-records" is the run-level sum per shard; the per-kernel critical path column gives the other reading.

## 7. Reproduce

```
# build the private runtime (normal), from this branch
sbatch -p normal -x <exclude> --export=ALL,W=<worktree>,S=<stage> eval/baselines/setup/t26_build.sh
ln -s <stage>/rt-lib <worktree>/lib
# one rtx4060ti16g node held (eval/x13/x13_hold.sbatch); steps via srun --input=none --jobid=<job> --overlap -n1 -c16 bash <script>
x13_green.sh                                  # green set
MODE=collector-only|scalar-clock x13_parity.sh # parity gate (IDS="...")
x13_sweep_all.sh                              # the counter-on sweeps (collector-only: 8 runs; scalar-clock: bfs x2, stencil1d x2)
x13_phase2.sh                                 # malloc-logged bfs, pathfinder extras, timing at N = 16 and N = 1
x13_live_bfs.sh                               # informational live check
x13_analyze.py <runs dir> <prefix>; x13_timing.py <dir> <out.md>; x13_bfs_over.py <malloclog run>
```

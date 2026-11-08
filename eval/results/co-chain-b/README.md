# C6b step 2: C1 collector-only recordings re-analysed with the C6b rules, on Xeon Silver 4110

Branch `eval/co-chain-b`. Code rev for every job: `93ae2d664256` (step 1 `3b2e91f8` + the step-2 scripts, `dirty=0` in every job log). Recordings not modified.
Stores: `final-2026-11-co` (4,725 programs, 16 shards), `final-2026-11-co-long` (5 ids), `final-2026-11-co-24h` (1 id).
Both settings use `--chain-closure --co-async`; S1 `--co-r3 strict`, S2 `--co-r3 off`. Command as VERDICT_PARALLEL.md section 7:
`BASELINE_MODES=collector-only parallel.py analyze --manifest eval/baselines/manifest.csv ... --confirm --chain-closure --co-async --co-r3 {strict|off} --analysis-workers 16 --analysis-timeout 14400`
(`eval/baselines/setup/c6b_step2.sbatch`; `ACCEL_PROF_HOME=CUVEIN_HOME=/home/fzheng4/wt-c6b`, all other `CUVEIN_*`/`YOSEMITE_*` unset, SLURM `--exclusive -N 1`, one shard after the other).
Merge and compare: `c6b_merge_compare.py <wt> {s1|s2}` (`parallel.py merge --override c1-long,c1-24h`, as C6), with `c6b_anode.py` (appends `anode=<host>` to every row before the shard CSV is moved into place).

## Layout
`s1/`, `s2/`: `c1-main/` (shard CSVs `baselines-cuvein-shard<k>_16.csv`, `chain-kernels-*.jsonl`, `confirm/*.json`, `shard*.log`, `cpu-<tag>.txt`), `c1-long/`, `c1-24h/`.
`merged-s1/`, `merged-s2/`: `baselines-cuvein.csv` (14,141 rows each, same row set as the A5 reference), `parity_report.txt`, `parity_diffs.tsv`, `suite_stats.tsv`, `derived_programs.tsv`.
Per-program counts: derived, rescued (notes `chain_derived` / `chain_rescued`; cross-checked against the jsonl, 0 mismatches), async, atomic_chain_off (number of raw / raw_sc report records of the program's confirm JSON whose `async` / `atomic_chain_off` is true).

## Node class and jobs
Xeon Silver 4110 nodes: the `skylake` partition (c11-c19, c26) minus the excluded nodes; every job runs `lscpu` first and aborts (exit 3, nothing run) unless the model is a Xeon Silver 4110. No job aborted; all six ran on **c14**:
`Intel(R) Xeon(R) Silver 4110 CPU @ 2.10GHz`, 2 sockets x 8 cores x 1 thread (SLURM view), nproc 16. The lscpu line is in every job log and in `cpu-<shard>.txt` next to every shard CSV.
All 14,141 rows of each setting carry `anode=c14`; rows whose anode is not a lscpu-verified 4110 host: 0 (S1), 0 (S2).
Waves (at most one node of mine at a time: the 10-node cap was full with x9 jobs, so the three-node share was never available): 326257 S1 shards 0-7 (c14, 00:37:55), 326276 S1 shards 8-15 (c14, 00:35:22), 326288 S2 shards 0-7 (c14, 00:33:33), 326292 S2 shards 8-15 (c14, 00:34:45), 326308 S1 long + 24h (c14, 00:00:43), 326319 S2 long + 24h (c14, 00:00:42). Merges: 326333 (S1), 326334 (S2), normal partition, c7 (not timed).

## Parity
Rule: a program whose derived, rescued, async and atomic_chain_off are all 0 equals C1 (A5 collector-only rows) on verdict, reports_dedup, report_ids, report_lines and `classes=`.
| setting | programs | analysed | all four 0 (incl. 16 not analysed) | violations | derived>0 | rescued>0 | async>0 | atomic_chain_off>0 | ERROR rows |
|---|---|---|---|---|---|---|---|---|---|
| S1 strict | 4,725 | 4,709 | 3,364 | 0 | 1,093 | 687 | 1 | 6 | 16 (P6 `missing-exe`, carried over, equal to C1), no chain-cap |
| S2 off | 4,725 | 4,709 | 3,356 | 0 | 1,093 | 687 | 1 | 24 | 16 (same), no chain-cap |

Verdict changes (all CLEAN to RACE; no RACE to CLEAN anywhere), programs per suite:
| suite | vs C1 S1 | vs C1 S2 | vs C6 S1 | vs C6 S2 |
|---|---|---|---|---|
| P4 | 2 (derived 2, rescued 2, atomic_chain_off 2) | 2 (same tags) | 0 | 0 |
| P5 | 0 | 3 (atomic_chain_off 3, derived 1) | 0 | 3 (atomic_chain_off 3, derived 1): P5-canary, P5-norace_interwarp-block_fence-atom_hrd-indirect, P5-race_interblock_none-lock_rtraw |
| P6 | 1 (async 1) | 1 (async 1) | 1 (async 1): P6-memcpy-shared_readwrite_race-racy | 1 (same) |
| P7 | 2 (derived 2, rescued 1) | 2 | 0 | 0 |
| P9 | 1 (derived 1) | 1 | 0 | 0 |
| PI | 26 (derived 25, rescued 1) | 26 | 0 | 0 |
| total | 32 | 35 | 1 | 4 |
Full lists with tags in `merged-s*/parity_report.txt`.

## Suite statistics (`merged-s*/suite_stats.tsv`; analysis_s of the verdict step per (program, mode); share = chain_s / analysis_s)
S1: suite programs/analysed/derived>0/rescued>0/async>0/atomic_chain_off>0/changed vs C1/changed vs C6; analysis_s median/max; share median / sum-ratio
P1 400/400/172/173/0/0/0/0; 1.155/2.147; 0.0021/0.0024. P3 60/60/20/22/0/0/0/0; 1.149/2.053; 0.0018/0.0018. P4 28/28/24/10/0/6/2/0; 2.287/39.600; 0.0000/0.0007.
P5 33/33/3/0/0/0/0/0; 0.605/0.881; 0/0. P6 50/34/1/2/1/0/1/1; 0.561/0.897; 0.0000/0.0012. P7 14/14/7/5/0/0/2/0; 1.603/14.622; 0.0154/0.1098.
P9 10/10/5/3/0/0/1/0; 3.397/13.935; 0.0129/0.0571. PI 4130/4130/861/472/0/0/26/0; 0.641/2.921; 0.0000/0.0001. Sum of analysis_s 3,759.4 s.
S2: P1 400/400/172/173/0/0/0/0; 1.150/2.706; 0.0020/0.0024. P3 60/60/20/22/0/0/0/0; 1.095/1.998; 0.0018/0.0018. P4 28/28/24/10/0/12/2/0; 2.098/21.756; 0.0001/0.0010.
P5 33/33/3/0/0/11/3/3; 0.535/0.897; 0/0. P6 50/34/1/2/1/0/1/1; 0.524/0.847; 0.0000/0.0013. P7 14/14/7/5/0/0/2/0; 1.317/14.291; 0.0147/0.1177.
P9 10/10/5/3/0/0/1/0; 3.426/13.767; 0.0126/0.0585. PI 4130/4130/861/472/0/1/26/0; 0.615/1.908; 0.0000/0.0001. Sum of analysis_s 3,556.4 s.
(The 16 non-analysed programs are the P6 `missing-exe` rows.)

# C6 step 2: collector-only recordings of C1 and C2 re-analysed with the chain closure

Branch `eval/co-chain` (step 1: 9fa48e9, `parallel.py analyze --chain-closure`). CPU only, SLURM `normal`, `--exclusive -N 1`,
one shard at a time per node, `BASELINE_MODES=collector-only`, `--analysis-workers 16 --analysis-timeout 14400 --confirm --chain-closure`,
all `CUVEIN_*` / `YOSEMITE_*` unset except `ACCEL_PROF_HOME=CUVEIN_HOME=/home/fzheng4/wt-c6` (`eval/baselines/setup/c6_step2.sbatch`).
Recordings were not modified.

## What ran

| set | store | selection | results dir | shards |
|---|---|---|---|---|
| C1 main | final-2026-11-co | all psets (4,725 programs), manifest.csv | `c1-main/` | 16 (`--shard k/16`) |
| C1 long | final-2026-11-co-long | `x7_a5_co_long.txt` (5 ids) | `c1-long/` | 1 |
| C1 24h | final-2026-11-co-24h | `x7_a5_co_24h.txt` (1 id) | `c1-24h/` | 1 |
| C2 recall | realworld-2026-10-co | `manifest_t21b.csv`, `--pset RW` (56 ids) | `c2-recall/` | 16 |
| C2 candidate | realworld-2026-10-t21c-co | `manifest_t21c.csv`, the 16 ids of C2's `co_main.list` (`c6_c2_cand_ids.txt`) | `c2-cand/` | 16 |

Per shard: `baselines-cuvein-shard<k>_16.csv`, `chain-kernels-*.jsonl` (per-kernel stats), `confirm/*.json` (raw reports with `chain_src` /
`chain_path`), `shard*.log`. Merged: `merged/baselines-cuvein.csv` (C1, 14,141 rows, same row set as the A5 reference),
`merged-c2-recall/`, `merged-c2-cand/` (each with `parity_report.txt`, `parity_diffs.tsv`, `suite_stats.tsv`, `derived_programs.tsv`).
`c6_merge_compare.py <wt> {c1|c2recall|c2cand}` merges (`parallel.py merge`, C1 with `--override c1-long,c1-24h` as A5) and compares.
References: C1 = `eval/results/verdict-timing/collector-only-merged/baselines-cuvein.csv` (A5, 14,141 rows); C2 = C2's per-id CSVs
(`ref-c2/`, copied from origin/eval/collector-only-realworld; where C2 has a `rean-<id>` long re-analysis it replaces the first-pass rows).

Analysis host: the analyze path writes only the recording node (`node=`). `anode=<hostname>` (the node the analysis ran on) was appended to
the notes of every row of every shard by `c6_anode.py` before the shard CSV was moved into place.

Deviations (all performance-only, results unaffected):
- C2 stores run with `CUVEIN_DOT_PREFILTER=1`: C2's T21b dot prefilter (dots naming the kernel are tried first; ported into `run_cuvein.py`,
  opt-in, default off so C1 is searched in the original order). C2's manifests were copied to `eval/realworld/`.
- With the prefilter on, the pool no longer parses every dot in the parent before forking (`06ef9a4`); the llama.cpp stores (144 dots, 300 MB) spent more
  than 70 minutes in that serial pre-parse (jobs 325653, 325658, 325674, 325681 were cancelled for it and their unfinished shards re-run; shards they had
  already completed were kept). Revs: C1 all at `1ee8d29253fa`; C2 recall shards 0-5, 10, 11 and C2 candidate shards 0, 2, 3, 5-15 at `1ee8d29253fa`
  (eager pre-parse); C2 recall shards 6-9, 12-15 and C2 candidate shards 1, 4 at `06ef9a443f03`. "dirty" in the job logs counts the staged result files
  (`git status --porcelain -uno`), not code.

## Jobs, nodes, elapsed (sacct)

C1: 325651 c5 (shards 0-7) 00:17:31; 325652 c45 (8-15) 00:24:20; 325656 c5 (long + 24h) 00:00:20.
C2 recall (shards): 325654 c4 (0) 00:13:48; 325655 c14 (1) 00:30:34; 325657 c5 (4, 5) 00:00:18; 325658 c5 (2, 3 done; cancelled) 00:46:27; 325674 c4 (11, 10 done;
cancelled) 00:34:31; 325687 c62 (6) 00:32:39; 325688 c4 (7) 00:25:19; 325689 c5 (8) 00:00:16; 325690 c25 (9, 12-15) 00:02:24; 325681 c62 (cancelled, nothing kept) 00:13:37.
C2 candidate: 325653 c58 (0, 2, 3 done; cancelled) 01:10:59; 325682 c45 (5-15) 00:01:34; 325685 c2 (4) 00:01:58; 325686 c39 (1, colmap-new-1) 01:08:24.
Re-time: 325667 c26 00:11:39; 325675 c25 00:09:16.
Sum of the analysis_s of the verdict step (one per program, mode): C1 2,119.4 s (0.589 h); C2 recall 6,573.6 s (1.826 h); C2 candidate 4,310.4 s (1.197 h).
Sum of shard-job Elapsed x 16 cores, kept jobs only: C1 2,531 s x 16 = 11.2 core-hours; C2 recall (325654, 325655, 325657, 325687-325690 plus the kept parts of the
cancelled jobs, not separable) and C2 candidate: see the sacct list above (the two numbers are different things: analysis_s is the wall of the verdict step inside a job,
Elapsed includes start-up, CSV writing, the cancelled attempts and the idle workers of single-kernel programs).

## Node classes

lscpu from the job logs: c26 Intel Xeon Silver 4110 @ 2.1 GHz, 2 sockets x 8 cores x 2 threads (nproc 16 under SLURM); c14 the same Xeon Silver 4110;
c5, c4, c58, c2: AMD EPYC 9115 16-Core (1 socket, max 4.1 GHz); c45, c25, c39: AMD EPYC 7302P 16-Core (max 3.0 GHz); c62: AMD EPYC 8124P 16-Core.
c36 and c79 (A5's a5-pi and a5-co nodes): not measured (both were allocated to other jobs; the probe jobs 325649/325650 were cancelled to free the node cap), missing.
A5's c26 is an Intel Xeon; the step-2 shards ran on AMD nodes (C1: c5, c45). The verdict-step time therefore differs by host type, so the three modes were re-timed together:
`c6_retime.sbatch` (sample = VERDICT_PARALLEL.md section 6: 40 non-HeCBench programs + 7 HeCBench P7/P9 ids = 47 ids from `c6_retime_select.py`), on c26 (A5's own node)
and on c25 (EPYC 7302P): vector-clock and scalar-clock from final-2026-11 (closure off), collector-only from final-2026-11-co closure off and on, N = 16, each configuration run
twice in a row (pass 2 = warm page cache). Results in `retime/<host>/`, summary `retime/summary.tsv` (median / max analysis_s per suite; chain_s sum).
Pass-2 totals over the 47 programs (sum of analysis_s, s): c26: vc 135.40, sc 67.03, co-off 66.81, co-on 69.72 (chain_s 0.218); c25: vc 108.40, sc 54.48, co-off 55.65, co-on 57.41 (chain_s 0.143).

## Parity (see `merged*/parity_report.txt`)

Rule: a program with chain_derived = 0 and chain_rescued = 0 (summed over its analysed rows; cross-checked against the jsonl, 0 mismatches) must equal its reference row on verdict,
reports_dedup, report_ids, report_lines and the classes= note.

| set | programs | derived=0 and rescued=0 | checked, mismatching | derived>0 | rescued>0 | programs with a verdict change | chain-cap ERROR rows |
|---|---|---|---|---|---|---|---|
| C1 | 4,725 (4,709 analysed; 16 empty-mode ERROR rows carried over, equal) | 3,394 (incl. the 16) | 0 | 1,093 | 532 | 31 | 0 |
| C2 recall | 56 | 5 | 0 (amrex-1-fixed: reference has no verdict, below) | 50 | 29 | 3 | 0 |
| C2 candidate | 16 | 3 | 0 | 13 | 8 | 0 | 0 |

C2 recall, amrex-1-buggy and amrex-1-fixed: the reference rows are ERROR (C2's analysis hit its 82,800 s cap, no verdict). The new analysis finished in under 1,800 s per program:
amrex-1-buggy RACE with 59 reports (derived 13,440, rescued 0), amrex-1-fixed RACE with 2 reports (derived 0, rescued 0). amrex-1-fixed has derived = rescued = 0 and
differs from its reference only because the reference holds no verdict (like A5's P9-atomicCAS); the compare script lists it as "REFERENCE HAS NO VERDICT" and does
not count it as a mismatch. This is the only zero-derived program whose row differs from its reference.

Per suite (C1; suite_stats.tsv): programs / derived>0 / rescued>0 / programs with a verdict change: P1 400/172/138/0; P3 60/20/15/0; P4 28/24/10/2; P5 33/3/0/0; P6 50 (34 analysed)/1/2/0;
P7 14/7/5/2; P9 10/5/3/1; PI 4,130/861/359/26. All verdict changes are CLEAN to RACE (rows: PI 78, P7 6, P4 6, P9 3; 3 reps each).
C2 recall: verdict changes CLEAN to RACE hecbench-surfel-1-fixed; ERROR to RACE amrex-1-buggy, amrex-1-fixed. C2 candidate: none.
Closure share (chain_s / analysis_s): per suite in `suite_stats.tsv`; C1 over-all-sum ratio P1 0.0020, P3 0.0017, P4 0.0007, P5 0, P6 0.0010, P7 0.0658, P9 0.0474, PI 0; C2 recall 0.0005, C2 candidate 0.
analysis_s median / max per suite (C1): P1 0.607/1.512; P3 0.608/1.292; P4 1.236/9.072; P5 0.352/0.816; P6 0.314/0.443; P7 0.678/5.991; P9 2.052/7.860; PI 0.383/1.410.
C2 recall median 3.490 / max 1,765.066 (amrex-1-fixed); C2 candidate median 9.092 / max 4,097.393.

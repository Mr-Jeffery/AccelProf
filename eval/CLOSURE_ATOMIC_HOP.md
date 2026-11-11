# M5: chain closure through atomic-atomic hops (cuRace alone, S2)

Branch `fix/closure-atomic-hop`, code revision `ac130350` (python/sync_dominance.py, python/test_co_chain.py), base `4cb6547e` (mainline merge of eval/co-chain-b). **Base choice:** no branch has S2 as the default: on every branch `run_cuvein.chain_closure_enabled` is `$CUVEIN_CHAIN_CLOSURE == "1"`, `co_async_enabled` is `$CUVEIN_CO_ASYNC == "1"` and `co_r3` is `cfg`. S2 is reached with the flags `--chain-closure --co-async --co-r3 off`. I branched from `4cb6547e` because the existing S2 results (`eval/results/co-chain-b/merged-s2`) come from exactly that verdict code; it does not include `886b6bf5` (R1 at the widest distance, study/r1-distance).

Change: `chain_closure_pairs(..., is_atomic=)` lets a chain pass an inner hop h when h is a read (as before) or h is an atomic and the step into h (from a, or from the previous inner hop) is atomic against atomic. A plain write still ends a chain; a read followed by an atomic does not pass. `CUVEIN_CHAIN_ATOMIC_HOP` (default 1; `0` = the read-only rule; `analyze(chain_atomic_hop=)` overrides it). Tests in python/test_co_chain.py: atomic-atomic-load yields the derived pair; atomic-store-load does not; plus an env/param test and a real-rtraw test (derived pairs 1 to 4). 44 passed at switch 1 and at 0 (test_co_chain 25, test_co_rules 19). The base test_co_chain.py has 21 tests, 3 of which fail at switch 1 because they encode read-only counts; the autouse fixture now pins the variable to 0 for them.

Units: reported = CSV verdict RACE; labelled = manifest label; report pairs = sum of `reports_dedup`; wall = sum of `analysis_s` (16 workers, one program at a time). C1 "before" = the existing S2 result (node c14, Xeon 4110) and a same-node control at switch 0 (c7); the control equals the existing result on every program (0 differences over 4,709: verdict, report ids and lines, classes, raw records), so the existing wall times differ from the control only by node speed. Production stores have no earlier S2: before = switch 0, same job (c22).

## C1 store (final-2026-11-co, -long, -24h; 4,709 programs analysed, the 16 P6 programs without an executable are not)

**P1 Indigo3**

| | before (existing S2) | control (switch 0) | after (switch 1) |
|---|---|---|---|
| programs | 400 | 400 | 400 |
| programs reported | 200 | 200 | 200 |
| labelled races detected | 200 of 200 | 200 of 200 | 200 of 200 |
| labelled race-free reported | 0 of 200 | 0 of 200 | 0 of 200 |
| report pairs | 1522 | 1522 | 1522 |
| derived / rescued chain pairs | 6671 / 2292 | 6671 / 2292 | 14601 / 3737 |
| kernels at 10^6-pair cap | 0 | 0 | 0 |
| verdict-step wall time, s | 459.0 | 220.5 | 219.3 |

New race-free reported (after, not before): none.

**P3 ECL**

| | before (existing S2) | control (switch 0) | after (switch 1) |
|---|---|---|---|
| programs | 60 | 60 | 60 |
| programs reported | 16 | 16 | 16 |
| labelled races detected | 0 of 0 | 0 of 0 | 0 of 0 |
| labelled race-free reported | 16 of 60 | 16 of 60 | 16 of 60 |
| report pairs | 44 | 44 | 44 |
| derived / rescued chain pairs | 148 / 213 | 148 / 213 | 1577 / 540 |
| kernels at 10^6-pair cap | 0 | 0 | 0 |
| verdict-step wall time, s | 66.4 | 31.4 | 32.9 |

New race-free reported (after, not before): none.

**P4 ScoR applications**

| | before (existing S2) | control (switch 0) | after (switch 1) |
|---|---|---|---|
| programs | 28 | 28 | 28 |
| programs reported | 22 | 22 | 22 |
| labelled races detected | 14 of 14 | 14 of 14 | 14 of 14 |
| labelled race-free reported | 8 of 14 | 8 of 14 | 8 of 14 |
| report pairs | 172 | 172 | 259 |
| derived / rescued chain pairs | 5590 / 316 | 5590 / 316 | 8559 / 1051 |
| kernels at 10^6-pair cap | 0 | 0 | 0 |
| verdict-step wall time, s | 140.3 | 61.9 | 62.8 |

New race-free reported (after, not before): none.

**P5 ScoR litmus + canary**

| | before (existing S2) | control (switch 0) | after (switch 1) |
|---|---|---|---|
| programs | 33 | 33 | 33 |
| programs reported | 5 | 5 | 5 |
| labelled races detected | 4 of 19 | 4 of 19 | 4 of 19 |
| labelled race-free reported | 1 of 14 | 1 of 14 | 1 of 14 |
| report pairs | 6 | 6 | 14 |
| derived / rescued chain pairs | 4 / 0 | 4 / 0 | 125 / 36 |
| kernels at 10^6-pair cap | 0 | 0 | 0 |
| verdict-step wall time, s | 18.6 | 9.7 | 10.2 |

New race-free reported (after, not before): none.

**P6 cuHadron (analysed 34 of 50)**

| | before (existing S2) | control (switch 0) | after (switch 1) |
|---|---|---|---|
| programs | 34 | 34 | 34 |
| programs reported | 8 | 8 | 8 |
| labelled races detected | 7 of 13 | 7 of 13 | 7 of 13 |
| labelled race-free reported | 1 of 21 | 1 of 21 | 1 of 21 |
| report pairs | 103 | 103 | 103 |
| derived / rescued chain pairs | 159 / 2 | 159 / 2 | 159 / 2 |
| kernels at 10^6-pair cap | 0 | 0 | 0 |
| verdict-step wall time, s | 17.9 | 9.4 | 10.4 |

New race-free reported (after, not before): none.

**P7 HeCBench (other 14)**

| | before (existing S2) | control (switch 0) | after (switch 1) |
|---|---|---|---|
| programs | 14 | 14 | 14 |
| programs reported | 7 | 7 | 7 |
| labelled races detected | 0 of 0 | 0 of 0 | 0 of 0 |
| labelled race-free reported | 0 of 0 | 0 of 0 | 0 of 0 |
| report pairs | 73 | 73 | 73 |
| derived / rescued chain pairs | 56098 / 9383 | 56098 / 9383 | 56098 / 9383 |
| kernels at 10^6-pair cap | 0 | 0 | 0 |
| verdict-step wall time, s | 41.3 | 19.3 | 20.7 |

New race-free reported (after, not before): none.

**P9 HeCBench (SC's 10)**

| | before (existing S2) | control (switch 0) | after (switch 1) |
|---|---|---|---|
| programs | 10 | 10 | 10 |
| programs reported | 5 | 5 | 5 |
| labelled races detected | 3 of 3 | 3 of 3 | 3 of 3 |
| labelled race-free reported | 2 of 7 | 2 of 7 | 2 of 7 |
| report pairs | 140 | 140 | 140 |
| derived / rescued chain pairs | 68191 / 12173 | 68191 / 12173 | 68191 / 12174 |
| kernels at 10^6-pair cap | 0 | 0 | 0 |
| verdict-step wall time, s | 49.3 | 21.5 | 26.2 |

New race-free reported (after, not before): none.

**PI Indigo 1.3 inputs (1,862 racy / 1,260 race-free labelled, 1,008 unlabelled)**

| | before (existing S2) | control (switch 0) | after (switch 1) |
|---|---|---|---|
| programs | 4130 | 4130 | 4130 |
| programs reported | 2668 | 2668 | 2668 |
| labelled races detected | 1738 of 1862 | 1738 of 1862 | 1738 of 1862 |
| labelled race-free reported | 224 of 1260 | 224 of 1260 | 224 of 1260 |
| report pairs | 14166 | 14166 | 14169 |
| derived / rescued chain pairs | 5604 / 818 | 5604 / 818 | 6924 / 978 |
| kernels at 10^6-pair cap | 0 | 0 | 0 |
| verdict-step wall time, s | 2763.5 | 1394.6 | 1526.0 |

New race-free reported (after, not before): none.

C1 totals: 4,709 programs, 465 gain chain pairs (derived+rescued), 17 change (all report pairs only: 14 P4, 2 P5, 1 PI; no verdict changes; P4 `uts-norace-large/small` change only in the class note and raw records). Verdict-step wall, sum over suites: existing S2 3,556 s (c14), control 1,768 s, after 1,908 s on the same node (+7.9 %; PI +9.4 %). No kernel hit the 10^6-pair cap at any setting (jsonl and ERROR rows).
Changed programs: `P4-graph-coloring-racy-{large,small}`, `P4-graph-connectivity-racy-{large,small}`, `P4-reduction-{norace,racy}-{large,small}`, `P4-rule-110-racy-{large,small}`, `P4-uts-{norace,racy}-{large,small}`, `P5-norace_interwarp-block_fence-atom_hrd-indirect`, `P5-race_interblock_blklock_waw`, `PI-conditional_edge_neighbors_boundsBug_guardBug-power_law_200n_1000e`. The four `norace` ones (reduction, uts) were already reported before.

## Production stores (CUVEIN_DOT_PREFILTER=1; amrex-1 included here, 72 programs)

**T21b recall set (realworld-2026-10-co)**

| | before (switch 0) | after (switch 1) |
|---|---|---|
| programs | 56 | 56 |
| programs reported | 49 | 49 |
| labelled races detected | 28 of 28 | 28 of 28 |
| labelled race-free reported | 16 of 22 | 16 of 22 |
| report pairs | 8735 | 8755 |
| derived / rescued chain pairs | 566735 / 32872 | 566824 / 32886 |
| kernels at 10^6-pair cap | 0 | 0 |
| verdict-step wall time, s | 13378.7 | 13512.9 |

New race-free reported (after, not before): none.

**T21c candidate set (realworld-2026-10-t21c-co)**

| | before (switch 0) | after (switch 1) |
|---|---|---|
| programs | 16 | 16 |
| programs reported | 16 | 16 |
| labelled races detected | 16 of 16 | 16 of 16 |
| labelled race-free reported | 0 of 0 | 0 of 0 |
| report pairs | 5852 | 5852 |
| derived / rescued chain pairs | 6778 / 339 | 6778 / 339 |
| kernels at 10^6-pair cap | 0 | 0 |
| verdict-step wall time, s | 4889.3 | 5125.9 |

New race-free reported (after, not before): none.

Production totals: 72 programs, 8 gain chain pairs, 6 change, all report pairs only: `cccl-3-{buggy,fixed}` 70 to 75, `kokkos-5-{buggy,fixed}` 82/81 to 83/82, `raft-1-{buggy,fixed}` 41/39 to 44/44. "Labelled" here is the manifest label (buggy = RACE, fixed = CLEAN); the 16 fixed builds reported are the same at both settings (rw_score classes them residual or still-reported, below). Real-world attribution (C6's rw_attribute.py with S2 keywords, rw_score.py, both switch settings) covers 69 ids; `amrex-1` (both builds) and `colmap-new-1-buggy` were not attributed (known gaps) and are in the CSV tables only.

## The four lines

1. **raft-1 buggy data-race component: MISSED, both before and after** (rw_score: DR half `histogram atomicAdd vs plain loads in choose_bucket` MISSED; SC half DETECTED at both). The three new reports are chain-derived through an atomic hop: `0x1630 -> 0x2610 -> 0x60a0` and `0x1e20 -> 0x2610 -> 0x60a0` (ATOMG.ADD.64 against STG.E.64 at select_radix.cuh:783, WAW) and `0x17b0 -> 0x2790 -> 0x2f40` (ATOMS CAST.SPIN against LDS.64). None has an end in the oracle's pairs (the atomicAdd at select_radix.cuh:322 against the choose_bucket loads :382-383 or the reset store :776); the 70 site verdicts between the oracle's sites are identical at both settings (no DR-class RACE among them), so no chain joins the oracle's pair even through atomics.
2. **raft-1 fixed and every other production fixed build: none changes its verdict or its rw_score outcome.** All fixed builds keep their CSV verdict and class (CLEAN-FOR-PAIR 17, RESIDUAL-AS-EXPECTED 6, STILL-REPORTED 3, NOT-SCORED 2 at both settings). Report counts rise for raft-1-fixed (39 to 44 RACE reports, 5 new: four atomic-to-store pairs at `0x60d0`, select_radix.cuh:793, and one ATOMS against LDS.64), cccl-3-fixed (70 to 75) and kokkos-5-fixed (81 to 82), all inside their already-residual component.
3. **Programs whose verdict or pair set changed with zero new chain pairs: 0** (C1: 0 of 17 changed; production: 0 of 6 changed; control at switch 0 equals the existing S2 on all 4,709). The stop condition did not trigger.
4. **Scalar-clock pairs still absent from cuRace alone (C6b step 3 unit: scalar-clock pair absent from the collector-only report of the hb-stripped recording): 3,683 in 339 programs, was 3,702 in 349.** The switch-0 control reproduces 3,702 / 349 exactly (certificate 3 + candidate missing 3,611 + lane drop 88). With the switch on: certificate 0, candidate missing 3,595, lane drop 88; the 19 pairs gained are P4 14 (all 3 certificate-granted and 11 candidate-missing), P5 1, PI 4;. In M4's unit (eval/PAIRS_PER_TIER.md Table 2, 3084e455: 4,140 data-race pairs only with the scalar clock, population of final-2026-11-co + realworld-2026-10-co without P3 and the canary) my before number is **missing**: the first attempt (job 335723) was invalidated because BeeGFS returned Errno 70 / empty directories on compute nodes partway through, and a rerun was not possible (BeeGFS still unreadable on c9, c22, c73 at the end). The 3,702 / 349 baseline is the one this task reproduces; 4,140 is a different unit and population (M4: S2 cuRace alone on the collector recordings against M3's scalar-clock pairs) and was not reproduced.

## Commands, revision, nodes, not run

Revision `ac130350` for every job (dirty=0). Scripts in `eval/baselines/setup/m5_*`, logs in `eval/x_logs/m5/` (git-ignored; the sbatch files and results are committed). Tests: `m5_tests.sbatch` (334521: 44 passed at switch 1 and 0, c7), `m5_tests2` (335325, c12: per-file counts). C1: `m5_c1.sbatch`, job 334524 on c7 (AMD EPYC 9115), `parallel.py analyze ... --confirm --chain-closure --co-async --co-r3 off --analysis-workers 16 --analysis-timeout 14400` with `CUVEIN_CHAIN_ATOMIC_HOP=1` and `=0`, 16 shards then long/24h, merged with `parallel.py merge --override`. Production: `m5_prod.sbatch`, job 334525 on c22 (EPYC 7302P, 10 h 17 min for both settings), same flags, `CUVEIN_DOT_PREFILTER=1`. Attribution: `m5_rw_setup.sh`, `m5_rw_attr.sbatch` job 335308 on c66 (EPYC 8124P, 2 h 46 min), `m5_rw_score.sbatch` job 337323 (c22). Step 3: `m5_s3.sbatch`, job 335311 on c10 (EPYC 9115, 1 h 32 min; `c6b_s3_harness.py` on /mnt/beegfs/fzheng4/c6b-step3/store, `m5_s3_post.py` = c6b_s3_post.py, S2 only). Tables: `m5_report.py` (335313, 335314), `m5_tables.py`, `m5_outcomes.py` (337332). The 24 h total estimate was not needed (C1 about 40 min per setting, production about 5 h per setting).
Not run: GPU anything; the M4-unit after number (above); attribution of amrex-1 and colmap-new-1; the S1 and cfg settings; iGUARD/racecheck/tables of the paper. `confirm/` record directories are archived as tarballs, not as loose files. The invalid first M4-unit attempt was deleted.

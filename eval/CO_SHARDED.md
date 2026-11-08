# CO_SHARDED: collector-only mode with the PCDepGraph pass at 16 shards (X12)

Branch `perf/sharded-pcdep` (T26's sharded pass, `accelprof -n N`), harness commits `60fe82b8`, `aa713b00` on top of T26's `9b2e8bb3`. 2026-11-07. Recording only plus analysis; no change to the paper.
Sections: 1 what was run, 2 parity (the gate), 3 Table 3 cells, 4 cost tables (HeCBench), 5 evidence files, 6 caveats, 7 HeCBench other 14 (P7), timing only.

## 1. What was run

**Setup-paragraph sentence (shard count per mode).** The collector-only pass runs the PCDepGraph pass at 16 shards (`accelprof -n 16`); the clock modes' PCDepGraph pass stays at `-n 1` and their sync pass runs at 16 shards, as recorded in X1b.

- Runtime: T26's, `libsanalyzer 31e4d53d367e693b`, collector `86473afa906669e5` (installed runtime: `5a20fd14ab6c6806` / `b746b4dd23e90f46`, HEAD `f551ca00`). Harness = C1's policy: `--reps 3`, `--confirm`, native run in the same job, whole node `rtx4060ti16g`, tool timeout 84,600 s really enforced (`--timeout-floor 84600`; all 28 + 34 + 4,130 + 400 + 10 programs finished, max wall 1,101.8 s in HeCBench, 159.5 s in ScoR/cuHadron; the only ERROR rows are the 16 `missing-exe` P6 rows, as in C1), `BASELINE_WORKERS=16` (each row's notes carry `workers=16`), `BASELINE_KEEP_REPS=1`.
- Stores `final-2026-11-co-sh` (HeCBench), `-p1` (Indigo3), `-pi` (Indigo 1.3, all 4,130 ids, SuperCollider's 99 inside), `-p4` (ScoR applications), `-p6` (cuHadron, 34 that run); installed `-n 1` controls in `-p1-ctl`, `-pi-ctl`, `-ctl` (crs).
- Analysis: the C6 command (`parallel.py analyze --chain-closure --analysis-workers 16`, code of `eval/co-chain` be325e03) on every store, and the standard analysis (no closure) of the in-job rows as the secondary comparison.
- HeCBench = SuperCollider's 10 native binaries (X11's run tree, container `ubuntu2204.sif`, patched `accelprof` preloading `libcudart.so.13`). **The reference for all 10 is X11** (the rerun of C1 on SuperCollider's binaries, `-n 1`, 3 recordings each). C1 recorded our own builds for 6 of the 10 (dxtc2, expdist, mr, tridiagonal, knn, atomicCAS differ in SASS), so C1's HeCBench rows are not used as a reference here. For Indigo3, Indigo 1.3, ScoR applications and cuHadron the reference is C1's recordings analysed by C6 (X11 has no rows for them); C1's standard-analysis rows are the secondary table.
- P7 (the 14 other HeCBench applications) was recorded afterwards, timing only, 13 of 14 (stencil1d not yet): section 7. It is not part of the gate and not part of sections 2 to 4.

## 2. Parity

**Criterion (Jeffery, 2026-11-07).** The analysed report set equals the reference's: the reported (pc, pc) pairs with their class (`<space>:<pc>-<pc>:<RAW|WAR|WAW>`), the report lines, the verdict. Primary: chain closure (C6 command) on the N=16 recordings against C6's chain rows (Indigo, ScoR, cuHadron) and against X11's chain rows (HeCBench). Secondary: the in-job standard analysis against C1's rows. Comparator `eval/x12/x12_pairs.py`; every differing id with its pairs only in A / only in B is in the files of section 5. The same-stream replay (`eval/baselines/setup/t26_parity/`) is the supporting check.

### 2.1 Pair-set equality, chain closure (primary)

| suite | reference | ids | pair sets EQUAL | DIFFER | verdict changes |
|---|---|---|---|---|---|
| HeCBench, SuperCollider's 10 | X11 chain rows r1, r2, r3 (each) | 10 | 10 / 10 / 10 | 0 | 0 |
| ScoR applications | C6 | 28 | 28 | 0 | 0 |
| cuHadron (34 that run) | C6 | 34 | 34 | 0 | 0 |
| Indigo3 | C6 | 400 | 371 | 29 (all: same pc pairs, RAW/WAR direction differs) | 0 |
| Indigo 1.3 (all) | C6 | 4,130 | 3,720 | 410 (270 same pc pairs with RAW/WAR/WAW direction differing, 140 pc-pair set differs) | 0 (all RACE on both sides) |

Standard analysis, against the references' standard rows (secondary): ScoR 28/28, cuHadron 34/34; Indigo3 365/400 equal against C1 (35 differ); Indigo 1.3 3,642/4,130 against C1 (488 differ); HeCBench against X11's standard rows: 8 equal, 2 not comparable (X11's standard analysis hit its 14,400 s analysis timeout for atomicCAS and tridiagonal and gave ERROR, the sharded in-job analysis finishes in 20.7 s and 121.0 s). No verdict change anywhere except where the reference has none.

### 2.2 The differing Indigo ids: run-to-run order, not the pass

Indigo programs with atomics have a schedule-dependent previous accessor: two separate GPU executions of the same binary give different RAW/WAR splits or pc-pair sets. Two independent pieces of evidence, both recorded:

1. **Installed `-n 1` controls.** Every id that differs from C6 (Indigo3 29, Indigo 1.3 410) and every id that differs from C1's standard rows was run once more with the installed runtime at `-n 1` (stores `-p1-ctl`, `-pi-ctl`), same harness, same node class, then analysed the same way. The control differs from the reference on most of them too:

| set | ids | control == C6 | control != C6 | control == N=16 |
|---|---|---|---|---|
| Indigo3, N=16 != C6 | 29 | 12 | 17 | 13 |
| Indigo 1.3, N=16 != C6 | 410 | 136 | 274 | 124 |

   (`pairs/*_chain_ctl_vs_c6.txt` and `*_chain_ctl_vs_n16.txt` list, for every id, the pairs only in the control and only in the other side. Both sides of every differing id are in those files.)
2. **Same-stream replay** (capture shim + replay driver; the same captured record stream replayed through the installed `-n 1` pass, new N=1, N=16 and N=16 threaded). Run on the ids where the control equals the reference but N=16 does not, so run-to-run noise cannot explain them: Indigo3, the 12 ids where the control equals C6: 96 of 96 same-stream comparisons EQUAL, byte-identical kernel JSONs and equal pair sets (installed `-n 1` vs new N=1, N=16, N=16 threaded, each on its own captured stream). Indigo 1.3, the 136 ids where the control equals C6 (`c1cmp/pi_chain_ctl_eq_c6_ids.txt`, job 329598 with chain analysis 329599): all 1,088 same-stream comparisons EQUAL (136 ids x 2 captured runs x 4 replays), byte-identical kernel JSONs, and the chain pair sets of installed `-n 1` vs new N=1, N=16, N=16 threaded EQUAL on 136 of 136 ids for both captured runs (`results/co-sharded-replay/t20-collector-only-329598-pi/pairs.txt`). Conclusion: on the same record stream the sharded pass is identical to the installed one, so the 29 + 410 RAW/WAR/WAW flips and pair-set differences are run-to-run record order, with no verdict change.

Rule used: any installed-vs-new difference on the same stream is a pass bug and stops the sweep. None occurred.

### 2.3 The ten HeCBench programs, per-program gate

Reference X11 (SuperCollider's binary at `-n 1`), 3 reps each at N=16. Gate = pair-set equality of the chain analysis (all 10 EQUAL against X11 r1, r2 and r3) plus the supporting checks:

| program | pair set vs X11 (chain / standard) | same-stream replay installed `-n 1` vs new n1 / n16 / n16t | live check (T26's `live_gate.py`, 3 recordings) | note |
|---|---|---|---|---|
| gpp | EQUAL / EQUAL | full run (10 kernels) EQUAL x3, fidelity vs live EQUAL | pass 3/3 (exact kernel JSON identical to X11 r1-r3) | |
| overlap | EQUAL / EQUAL | full (20 kernels) EQUAL x3, fidelity EQUAL | pass 3/3 (exact) | |
| knn | EQUAL / EQUAL | prefix, first 20 of 300 kernels, EQUAL x3, fidelity EQUAL | pass 3/3 (nodes, edges, edge totals, grand) | |
| tridiagonal | EQUAL / not comparable (X11 ERROR) | prefix, first 50 of 1,111 kernels, EQUAL x3, fidelity EQUAL | pass 3/3 (grand, nodes) | |
| crs | EQUAL / EQUAL | not replayed | pass 3/3 (nodes, edges, edge totals, grand) | 7 reports; pc pairs equal, report lines equal to X11 |
| fpc | EQUAL / EQUAL | not replayed | pass 3/3 | |
| mr | EQUAL / EQUAL | not replayed | pass 3/3 (nodes, edges, grand) | |
| dxtc2 | EQUAL / EQUAL | not replayed | pass 3/3 (grand, nodes) | 174 reports |
| expdist | not gated | not run | not run | parity not gated: baseline nondeterministic (X11 r1-r3 drained-record totals differ) |
| atomicCAS | not gated | not run | not run | parity not gated: baseline nondeterministic (X11 r1-r3 drained-record totals differ) |

X11's three recording totals, next to the new ones (drained records): expdist X11 1,284,691,812 / 1,288,650,936 / 1,283,173,126, new N=16 1,282,858,620 (median of 3); atomicCAS X11 1,319,730,190 / 1,325,438,990 / 1,314,944,485, new 1,316,928,492 (median of 3). Both new totals fall inside the spread of X11's own three runs; their chain pair sets equal X11's (expdist 35 reports, atomicCAS 4 reports) although the standard analysis is CLEAN for both.

Strict kernel-JSON equality (`co_json_diff.py`) was run for all programs but cannot gate: X11's own `-n 1` runs differ from one another in the previous-accessor split on 6 of the 8 compared programs (crs, dxtc2, fpc, knn, mr, tridiagonal; only gpp and overlap are byte-identical between X11 runs), and the new-vs-X11 differences are of the same kind. Hence the live-check invariants (only those that hold across all baseline runs) and the pair-set criterion.

### 2.4 Other checks

- **P6-interkernel DIFFER line.** `P6-interkernel-global_writewrite_race-fixed`, replay sample on cuHadron: "fidelity: replay(Ic, installed -n1) vs Ic live DIFFER only_in_a=1" and "Bc live (new N=16) vs installed -n1 DIFFER only_in_a=1". Cause: the live runs of this id (109,375,002 records, ~20 s replay) went through `collect`, which ignores `--timeout-floor` and uses the 120 s default, so the live runs wrote no kernel JSON; the replay side had it (one-sided "only_in_a"). The four same-stream replay comparisons of the same id are EQUAL. Rerun with the real timeout (job 329452, `LIVE=direct`): installed `-n 1` vs new N=1 EQUAL, vs new N=16 EQUAL (2 kernels), control vs control EQUAL. Not a pass difference.
- Replay samples (logs `x_logs/x12-replay-*.log`, `x12-g1-329375.log`, `x12-p1-replay12-329460.log`): ScoR applications 70 EQUAL / 0 DIFFER, cuHadron 69 EQUAL / 1 DIFFER (the line above), Indigo 1.3 sample (12 ids) 84 EQUAL / 0, HeCBench 4 programs all EQUAL, Indigo3 12-id extra check 96 EQUAL of 96 (byte-identical kernel JSONs, equal pair sets for installed `-n 1` vs new N=1, N=16, N=16 threaded, for both captured runs of each id). Indigo3 live check on 10 ids: pass.

## 3. Table 3, collector-only column

Recomputed with C6's own method (`c6_tables.py` of `eval/co-chain` on a copy of C6's sandbox in which the collector-only columns are replaced by the N=16 rows; run on C6's original rows it reproduces `CO_CHAIN.md` exactly). CO+chain = chain closure in the verdict layer (the mode the paper defines). Races alone; Indigo 1.3 per code (code = program; a mixed label counts as unlabelled): labels 266 racy / 180 race-free / 144 unlabelled. Cells: recall TP/(TP+FN) · FP/(FP+TN).

| suite | printed (`tables/coverage.tex` on `origin/edit/sc-native-hecbench`, b56b2e4) | C6 (CO+chain) | N=16 chain closure | N=16 standard analysis (secondary) |
|---|---|---|---|---|
| Indigo3 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 |
| Indigo 1.3 (590 codes) | 266/266 · 32/180 | 266/266 · 32/180 | 266/266 · 32/180 | 266/266 · 32/180 |
| Indigo 1.3, SC's 99 | 45/45 · 4/44 | 45/45 · 4/44 | 45/45 · 4/44 | 45/45 · 4/44 |
| ScoR applications | 14/14 · 8/14 | 14/14 · 8/14 | 14/14 · 8/14 | 14/14 · 6/14 |
| cuHadron (in scope) | 6/6 · 0/14 | 5/6 · 0/14 (inherited from the cp.async rule) | 5/6 · 0/14 (same) | 5/6 · 0/14 |
| HeCBench, SuperCollider's 10 (5 racy / 5 race-free) | 5/5 · 1/5 | X11 chain rows (r1, r2, r3): 5/5 · 1/5 | **5/5 · 1/5** | 3/5 · 1/5 (X11 standard rows: 2/3 · 1/5, 2 ERR) |
| All pre-registered (HeCBench excluded) | 486/486 · 40/408 | 485/486 · 40/408 | 485/486 · 40/408 | 485/486 · 38/408 |

The N=16 chain-closure cells equal the printed cells everywhere, HeCBench included. Two printed cells, cuHadron recall (6/6) and the All recall (486), sit one above C6's and N=16's because of the `cp.async` rule they inherit; that is the same in C6 and N=16, so it is not an N=16 difference.

HeCBench labels are SuperCollider's own (`artifact_subset.json`): racy atomicCAS, dxtc2, knn, tridiagonal, expdist; race-free overlap, fpc, gpp, crs, mr; they agree with the manifest's. The reference is X11. N=16 chain verdicts are identical to X11's chain verdicts program by program (atomicCAS, dxtc2, expdist, knn, tridiagonal RACE; crs RACE = the one false positive; fpc, gpp, mr, overlap CLEAN). Under the standard analysis the SuperCollider binaries' expdist and atomicCAS are CLEAN (X11 `-n 1` too; atomicCAS and tridiagonal are ERROR in X11's own standard rows, analysis timeout), so recall 3/5; this is the analysis, not the shard count.

(Reference notes for the first-draft numbers: an earlier recomputation here gave Indigo 1.3 as 309/311 · 36/224; that counted codes by (program, build) and took the first id's label, not C6's rule. Superseded.)

## 4. Cost tables, HeCBench (SuperCollider's 10 binaries)

New numbers cover these 10 programs only, N=16, 3 reps, median of reps, native in the same job. They do not replace the whole-suite cells (Figure fig_slowdown's other HeCBench programs, P7, were not run and keep their current values). The references are X11's `-n 1` recordings of the same binaries (3 reps each, mixed node classes: c55 EPYC 9115 and c43/c78 7302P, so X11's walls also carry node variation).

### 4.1 Per program

Columns: tool wall s / native wall s / slowdown / µs per drained record / peak RSS MB. Floor µs = (wall - native) / records.

| program | records | N=16 | X11 `-n 1` (same binary) | wall ratio | floor µs N=16 |
|---|---|---|---|---|---|
| atomicCAS | 1,316,928,492 | 1,101.8 / 3.625 / 304.0 / 0.837 / 1,050 | 1,650.2 / 3.772 / 437.5 / 1.250 / 949 | 0.67 | 0.834 |
| crs | 9,864,919 | 5.7 / 2.472 / 2.3 / 0.578 / 968 | 5.6 / 2.469 / 2.3 / 0.565 / 932 | 1.02 | 0.327 |
| dxtc2 | 495,013,100 | 81.0 / 0.370 / 219.0 / 0.164 / 952 | 201.2 / 0.315 / 638.8 / 0.406 / 855 | 0.40 | 0.163 |
| expdist | 1,282,858,620 | 176.7 / 1.822 / 97.0 / 0.138 / 1,070 | 280.7 / 1.818 / 154.4 / 0.218 / 851 | 0.63 | 0.136 |
| fpc | 145,620,992 | 71.7 / 2.474 / 29.0 / 0.493 / 1,007 | 67.3 / 2.535 / 26.6 / 0.462 / 990 | 1.07 | 0.476 |
| gpp | 10,368,000 | 3.0 / 0.269 / 11.1 / 0.288 / 964 | 6.9 / 0.269 / 25.6 / 0.663 / 857 | 0.43 | 0.262 |
| knn | 11,826,486,900 | 868.1 / 13.694 / 63.4 / 0.073 / 1,174 | 3,861.1 / 11.936 / 323.5 / 0.326 / 995 | 0.22 | 0.072 |
| mr | 845,192 | 1.6 / 1.018 / 1.6 / 1.917 / 834 | 2.6 / 1.709 / 1.5 / 3.103 / 830 | 0.62 | 0.712 |
| overlap | 13,107,200 | 3.4 / 0.317 / 10.7 / 0.258 / 1,231 | 12.2 / 0.365 / 33.4 / 0.930 / 1,213 | 0.28 | 0.234 |
| tridiagonal | 5,598,992,570 | 764.5 / 0.669 / 1,142.8 / 0.137 / 1,704 | 3,667.3 / 0.769 / 4,768.9 / 0.655 / 1,190 | 0.21 | 0.136 |

(X11 walls for atomicCAS, expdist, dxtc2 are the median of three runs whose spread is large: dxtc2 112.1 / 201.2 / 201.9 s, expdist 151.7 / 283.7 / 280.7 s, atomicCAS 1,820.8 / 1,348.2 / 1,650.2 s.)

### 4.2 fig_slowdown, tab:eval-memory, per-record cost (these 10 programs)

| quantity | N=16 | X11 `-n 1` (same 10) |
|---|---|---|
| fig_slowdown, HeCBench collector-only bar, geomean slowdown (n=10) | **37.8x** | 74.5x |
| P7 (14 other programs) | not run | not run |
| tab:eval-memory collector-only HeCBench peak RSS median / max | 1,029 MB / 1,704 MB (tridiagonal) | 940 MB / 1,213 MB (overlap) |
| per-record cost, median over the 10 programs (µs per drained record) | **0.273** | 0.610 |
| fitted line wall = intercept + slope x records (least squares, n=10, unweighted) | intercept 152.5 s, slope 0.0750 µs/record | intercept 212.5 s, slope 0.3685 µs/record |
| serial floor, median of (wall - native)/records | 0.248 µs | 0.541 µs |

Notes: the per-record cost falls 2.2x in the median and the fitted slope 4.9x; the programs that dominate the fit are the four with more than 10^9 records. The largest programs reach the expected floor (knn 0.072 µs, expdist 0.136, tridiagonal 0.136, dxtc2 0.163 µs per record); the median floor (0.248) is raised by small programs where start-up and native-run noise dominate (mr, crs, gpp, overlap), and the fitted intercept is not a fixed start-up cost. The gain on top of the worker count is therefore program-dependent, not a uniform 10-20 %. Peak RSS is higher at N=16 than at `-n 1` for all 10 programs (shard buffers; +4 to +219 MB, tridiagonal +514 MB) but stays under 1.8 GB.

## 5. Evidence files (`eval/results/`)

- `co-sharded/` HeCBench rows (10 CSVs), `parity/` (strict diffs, `live_gate-*.json`), `pairs/hecbench_*_vs_x11*.txt`, `chain-<app>/` chain rows.
- `co-sharded-p1/`, `-pi/`, `-p4/`, `-p6/` rows, `chain/` chain-closure rows, `pairs/*_vs_c6.txt` (every differing id with only-in-A / only-in-B pairs).
- `c1cmp/` standard-analysis comparison against C1 (`p1.txt`, `pi.txt`, `p4.txt`, `p6.txt`, `p9.txt`), control comparisons (`*_chain_ctl_vs_c6.txt`, `*_chain_ctl_vs_n16.txt`, `*_ctl_vs_c1.txt`).
- `co-sharded-replay/` replay chain analysis of the replay outputs.
- `co-sharded-p7-<app>/` P7 rows (13 CSVs, section 7), `c1cmp/p7ids/` the id files, `c1cmp/p7_tables.md` the generated table.
- Table 3 inputs and outputs: cluster `/home/fzheng4/x12-t3/` (`out-n16/tables/c6_tables.md`, `out-c6/tables/c6_tables.md`).
- Scripts: `eval/x12/` (`x12_record.sbatch`, `x12_suite.sbatch`, `x12_analyze*.sbatch`, `x12_pairs.py`, `x12_table3.py`, `x12_replay_chain.sbatch`, gate scripts).

## 6. Caveats

- Walls depend on the node (CPU class) as much as on the run; X11's three runs of one program span up to 1.8x.
- Sections 2 to 4 are the 10 SuperCollider binaries. Section 7 adds P7 timing only (13 of 14, no parity).
- Indigo3 and Indigo 1.3 are parity evidence only; they are not in the cost tables.
- The Indigo differences are run-to-run order; the evidence is the control and the same-stream replay of section 2.2. The pass itself reproduces the installed `-n 1` on the same stream bit for bit.

## 7. HeCBench other 14 (P7), `-n 16`, timing only

Jeffery's request: record P7 at `accelprof -n 16` as in Figure 4, no parity check, skip stencil1d for now. **13 of the 14 programs ran**: backprop, bezier-surface, bitonic-sort, heartwall, haversine, nbody, mandelbrot, pathfinder, srad, lavaMD, particlefilter, hotspot, bfs. stencil1d (86 x 10^9 records, 36,373 s at `-n 1`) is not run; it can be added as one more `x12_suite.sbatch` job with `IDFILE`.

How: same harness and policy as section 1 (T26 runtime, `N=16 REPS=3 CAP=84600`, whole `rtx4060ti16g` node per program, native run in the same job, stores `final-2026-11-co-sh-p7`, one job per program, jobs 329610 to 329622). Our own builds of P7 (the manifest's `P7-<app>-cuda`, the same binaries as C1). All 13 jobs `COMPLETED`, each log ends `== done rc=0`, 3 reps per program, every row has `workers=16`, no ERROR or TIMEOUT.

What this is not: P7 was **not gated**. The in-job verdicts are recorded and equal C1's for all 13 (RACE for bfs, heartwall, particlefilter, pathfinder, srad; CLEAN for the rest), and the drained record counts are identical to C1's for all 13, but no pair set was compared. P7 has no X11 rows (X11 is SuperCollider's 10), so C1's `-n 1` rows are the only reference, and C1's geomean is recomputed over the same 13 programs.

Per program (median of 3 reps; wall = tool wall including the analysis the harness runs in the job; native = native run in the same job; records = drained records; sorted by records):

| program | records | verdict N=16 / C1 | N=16: wall s | native s | slowdown | µs/rec | peak MB | C1 `-n 1`: wall s | native s | slowdown | µs/rec | peak MB | wall speed-up |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| particlefilter | 22,515,702,514 | RACE / RACE | 1,488.3 | 1.269 | 1,172.8 | 0.066 | 2,053 | 3,200.2 | 1.171 | 2,732.9 | 0.142 | 1,152 | 2.2x |
| heartwall | 8,071,484,636 | RACE / RACE | 1,106.5 | 0.769 | 1,438.8 | 0.137 | 1,259 | 2,347.6 | 0.769 | 3,052.7 | 0.291 | 988 | 2.1x |
| pathfinder | 7,058,581,010 | RACE / RACE | 623.3 | 1.470 | 424.0 | 0.088 | 2,018 | 702.4 | 1.470 | 477.9 | 0.100 | 2,023 | 1.1x |
| bitonic-sort | 1,226,469,735 | CLEAN / CLEAN | 649.3 | 37.036 | 17.5 | 0.529 | 1,433 | 635.3 | 31.940 | 19.9 | 0.518 | 1,379 | 1.0x |
| haversine | 629,145,600 | CLEAN / CLEAN | 113.4 | 3.123 | 36.3 | 0.180 | 2,465 | 227.4 | 3.123 | 72.8 | 0.361 | 2,307 | 2.0x |
| srad | 589,889,126 | RACE / RACE | 146.3 | 0.317 | 461.5 | 0.248 | 889 | 401.3 | 0.371 | 1,081.7 | 0.680 | 890 | 2.7x |
| lavaMD | 398,843,648 | CLEAN / CLEAN | 27.3 | 0.418 | 65.2 | 0.068 | 1,305 | 83.4 | 0.383 | 217.7 | 0.209 | 1,219 | 3.1x |
| mandelbrot | 327,687,360 | CLEAN / CLEAN | 101.7 | 2.272 | 44.7 | 0.310 | 915 | 162.4 | 3.825 | 42.5 | 0.496 | 876 | 1.6x |
| nbody | 320,355,120 | CLEAN / CLEAN | 33.7 | 12.142 | 2.8 | 0.105 | 969 | 59.9 | 14.570 | 4.1 | 0.187 | 867 | 1.8x |
| bezier-surface | 106,955,008 | CLEAN / CLEAN | 30.3 | 19.858 | 1.5 | 0.283 | 4,048 | 45.4 | 24.463 | 1.9 | 0.424 | 3,936 | 1.5x |
| hotspot | 37,410,000 | CLEAN / CLEAN | 10.8 | 0.669 | 16.2 | 0.290 | 890 | 21.5 | 0.518 | 41.5 | 0.575 | 875 | 2.0x |
| bfs | 7,436,165 | RACE / RACE | 4.5 | 1.420 | 3.2 | 0.609 | 1,180 | 4.8 | 1.069 | 4.5 | 0.649 | 1,004 | 1.1x |
| backprop | 1,232,901 | CLEAN / CLEAN | 1.0 | 0.268 | 3.6 | 0.786 | 922 | 1.7 | 0.268 | 6.2 | 1.355 | 902 | 1.7x |

- N=16: geomean slowdown 39.0 (n=13); median µs/record 0.248; peak RSS median 1,259 MB, max 4,048 MB; median serial floor 0.175 µs
- C1 `-n 1`: geomean slowdown 66.7 (n=13); median µs/record 0.424; peak RSS median 1,004 MB, max 3,936 MB; median serial floor 0.356 µs
- fit wall = a + b x records (N=16, n=13): a = 114.2 s, b = 0.0691 µs/record
- fit wall = a + b x records (C1 -n 1, n=13): a = 142.6 s, b = 0.1463 µs/record
- wall speed-up C1/N=16: geomean 1.74x, min 0.98x (bitonic-sort), max 3.06x (lavaMD)
- workers notes: ['16']; reps per program: [3]
- records equal to C1: True; verdict equal to C1: True
- >=1e9 records (particlefilter, heartwall, pathfinder, bitonic-sort): N=16 geomean slowdown 334.7 vs C1 530.7; median µs/rec 0.113 vs 0.216


Reading:

- Over the same 13 programs the geomean slowdown goes from 66.7x (C1, `-n 1`) to 39.0x (`-n 16`). C1's 93.52 in `report_tables.md` is over all 14 and includes stencil1d (36,373 s, 7,619x), so it is not the number to compare with.
- Median per-record cost 0.248 µs vs 0.424 µs; fitted slope 0.069 vs 0.146 µs/record. These are smaller gains than on SuperCollider's 10 (section 4: 4.9x on the slope); the programs that did not speed up (below) pull the median and the slope.
- Gains are uneven: lavaMD 3.1x, srad 2.7x, particlefilter 2.2x, heartwall 2.1x, haversine 2.0x, hotspot 2.0x, but **bitonic-sort 1.0x** (1.23 x 10^9 records, 649 s vs 635 s) and **pathfinder 1.1x** (7.06 x 10^9 records, 623 s vs 702 s), and bfs 1.1x. These stay at their `-n 1` cost per record (bitonic-sort 0.53 vs 0.52 µs, pathfinder 0.088 vs 0.100), which suggests their time is not in the sharded PCDepGraph pass. The cause was not investigated here.
- The four programs with more than 10^9 records: geomean slowdown 334.7x vs 530.7x, median 0.113 vs 0.216 µs/record.
- Peak RSS rises a little (median 1,259 vs 1,004 MB, max 4,048 MB bezier-surface vs 3,936 MB); particlefilter's goes from 1,152 to 2,053 MB.

Caveats specific to P7: native walls are measured in each job and move between jobs (nbody 12.1 s here vs 14.6 s in C1, bitonic-sort 37.0 s vs 31.9 s, mandelbrot 2.3 s vs 3.8 s), so the slowdown ratio moves with the native run, not only with the tool wall; the wall speed-up column (tool wall only) is the cleaner comparison. The first rep of a short program (backprop, 1.7 s vs 0.97 s) carries warm-up; medians are used. P7 walls have not been compared with any other `-n` value; only `-n 1` (C1) and `-n 16`.


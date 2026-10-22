# X1: the final recording

Branch `eval/final-sweep` (from `cuVein` 4094187, X0 merged), worktree `.claude/worktrees/wt-x1`,
left unmerged for Jeffery. Recorded 2026-10-13 17:13 – 2026-10-16 08:39: the first pass and the two
5,400 s passes 10-13 17:13 – 10-14 12:23, the 24 h pass 10-14 14:23 – 10-16 08:39; final post-processing
10-16 17:34–17:42. Every number of the paper's evaluation comes from this recording: one runtime, one
configuration per cap, no single-row re-run under other settings. Legend as in CLAUDE.md A4: **proved-in-effect** = an invariant
checked over the stated stores; **tested** = a specific result asserted; **unverified** = said so.

## 0. Runtime and hardware

| component | sha256[:16] | source |
|---|---|---|
| `build/sanalyzer/lib/libsanalyzer.so` (what the collector's RPATH loads, per `ldd`) | `2201fcb7d57ae783` | install commit d38d057 (the T16 + T20 merge ba99486) |
| `lib/libcompute_sanitizer.so` (collector) | `ee78cb899e8a0a65` | d38d057 |
| `nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin` | `a2d7368bc1c61986` | d38d057 |
| `gpu_patch_pc_dependency_late.fatbin` (installed, not loaded: `YOSEMITE_HB_LATE_SEQ` unset) | `e96343121c74ca0a` | d38d057 |
| verdict layer `python/` of the runtime checkout | `cuVein` 4094187 | X0 merged; `git diff --stat d38d057 4094187 -- sanalyzer nv-compute python/hb_oracle.py` is empty |
| harness (`eval/baselines/parallel.py`, `blib.py`, `run_cuvein.py`, `setup/p_final.sh`) | `eval/final-sweep` c47c451 | every first-pass and 5,400 s shard; the 24 h pass ran at c20d8c5 (10 tasks), c6d68d5 (1) and a514674 (10). `git diff c47c451 HEAD` over `parallel.py`, `blib.py`, `run_cuvein.py` is empty; over `p_final.sh` it is `--reps 3` → `--reps ${REPS:-3}` (default unchanged; `p_final_24h.sh` sets 1) and two fields of the log line (partition, reps). Every other later commit touches post-processing scripts, id lists, X1-follow scripts or results |

Every `meta.json` of the five stores (`final-2026-10`, `-long`, `-long-sc`, `-24h-vc`, `-24h-sc`) records
the four library hashes (computed on the node), the runtime and harness HEADs and the harness's dirty
count; §6(a) checks the hashes over all of them.

`nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader` on c77 (the first
dry-run node): `NVIDIA GeForce RTX 4060 Ti, 8.9, 580.95.05`. Toolkit CUDA 13.3
(`/usr/local/cuda-13.3`, `Build cuda_13.3.r13.3/compiler.38244171_0`) with its Compute Sanitizer,
pinned in `p_final.sh` (a node without it exits before writing a row; none did).

**Precondition.** X0 is merged (4094187) and the installed runtime is the T16 + T20 build X0's
checks ran on (d38d057): neither stop condition applies. `git status --porcelain` on `cuVein` in
the main checkout lists one entry, `?? corpora`: an untracked symlink
`corpora -> /home/fzheng4/wt-t16/eval/baselines/corpora` made 2026-10-11 16:10 by the T16 session,
no tracked change. Nothing reads `$ACCEL_PROF_HOME/corpora` (the harness uses
`eval/baselines/corpora`); it was left in place for Jeffery to delete.

**Nodes** (partition `rtx4060ti16g` only; c54, c2, c21, c37 excluded), from the shard logs'
headers. All RTX 4060 Ti 16 GB, sm_89.

| node | CPU (AMD EPYC) | RAM visible | driver | main shards | PI shards | VC 5,400 s tasks | SC 5,400 s tasks | 24 h tasks | dry runs |
|---|---|---|---|---|---|---|---|---|---|
| c51 | 9115 | 125 GB | 580.95.05 | 10 | 1 | 0 | 2 | 1 | 0 |
| c52 | 9115 | 125 GB | 580.82.07 | 7 | 12 | 1 | 2 | 1 | 0 |
| c58 | 9115 | 125 GB | 580.82.07 | 2 | 0 | 1 | 1 | 1 | 0 |
| c60 | 8124P | 188 GB | 580.82.07 | 2 | 0 | 2 | 2 | 2 | 0 |
| c61 | 8124P | 188 GB | 580.82.07 | 5 | 0 | 2 | 1 | 3 | 0 |
| c62 | 8124P | 188 GB | 580.82.07 | 5 | 0 | 2 | 1 | 3 | 0 |
| c63 | 8124P | 188 GB | 580.82.07 | 2 | 0 | 2 | 1 | 3 | 0 |
| c64 | 8124P | 188 GB | 580.95.05 | 2 | 0 | 1 | 1 | 1 | 0 |
| c66 | 8124P | 188 GB | 595.58.03 | 1 | 0 | 2 | 1 | 4 | 0 |
| c73 | 7302P | 125 GB | 580.82.07 | 0 | 10 | 1 | 1 | 0 | 0 |
| c74 | 7302P | 125 GB | 580.82.07 | 0 | 7 | 2 | 2 | 0 | 0 |
| c77 | 7302P | 125 GB | 580.95.05 | 5 | 12 | 1 | 1 | 1 | 1 |
| c78 | 7302P | 125 GB | 580.82.07 | 6 | 11 | 0 | 1 | 1 | 1 |
| c79 | 7302P | 125 GB | 580.82.07 | 1 | 11 | 2 | 1 | 0 | 0 |
| **14 nodes** | | | | 48 | 64 | 19 | 18 | 21 | 2 |

(A shard is a job; a main shard holds 12–13 programs, a PI shard 64–65, a 5,400 s or 24 h task one id.
The 24 h tasks ran in partition `max`, restricted to these hosts by their exclude lists, §1 (i).
`meta.json` of every program names its node; per-program counts in §6(a).)

The partition mixes three host CPUs (EPYC 7302P Zen 2, 9115 Zen 5, 8124P Zen 4), two RAM sizes
(125 / 188 GB visible) and three drivers (580.82.07, 580.95.05, and 595.58.03 on c66 alone).
Tool and native walls of a row come from the same node (`collect_one` times both there), so the
ratios are per-node; cross-row wall comparisons are not. `meta.json` and every row's notes carry
the node.

## 1. Configuration

The same for every row of a pass (`setup/p_final.sh`; `setup/p_final_long.sh` for the 5,400 s
passes):

| knob | value | note |
|---|---|---|
| `BASELINE_HB_DUMP` | 0 | no `hb_events`; HbClock's aggregates only (T4); every `meta.json` has `hb_dump: false` (§6a) |
| `YOSEMITE_HB_STATS` | 1 | `hb_stats` in every kernel JSON (HbClock state + `rss_kb`/`hwm_kb`); `blib.base_env` copies the environment and drops only the HB mode/trace/scope/dump knobs, so it passes through (checked in the dry run's kernel JSONs) |
| modes | both, in one job per shard | `collect_one` wipes `<store>/<id>`; vector-clock first, then scalar-clock |
| `--reps` | 3 (24 h pass: 1) | native: 3 reps; each mode: 3 reps; the 24 h pass one rep of each (Jeffery, 2026-10-14) |
| `--confirm` | on | detail JSONs → `eval/baselines/confirm_final{,-long,-long-sc}/` in the **runtime checkout** (untracked; outlives the worktree; X3 reads them) |
| store | `/mnt/beegfs/fzheng4/cuvein_traces/final-2026-10` (+ `-long`, `-long-sc`, `-24h-vc`, `-24h-sc`) | `--keep-all`: every program's kernel JSONs, dots, logs, meta kept |
| tool timeout | `--timeout-floor = --timeout-cap = 1200` (long passes: 5400; 24 h pass: 86400) | see "Interpretations" (a) |
| offline analysis cap | `--analysis-timeout 14400` per mode | X0's re-score value; no row reached it (§3) |
| detector knobs | none | `p_final.sh` unsets every `CUVEIN_*` / `YOSEMITE_*` variable inherited from the submitting shell before exporting the two above |
| results | `eval/results/final/` (`--tag final`, `finalpi`), `final-long/`, `final-long-sc/`, `final-24h-vc/`, `final-24h-sc/` | merged into `eval/results/baselines-cuvein.csv` (§2) |

**Interpretations of the brief, and one extension Jeffery asked for**

(a) *Timeout = cap.* The harness's tool timeout is `min(max(10 × native, floor), cap)` with a
default floor of 120 s. With that floor, `--timeout-cap 1200` would bind only for programs with a
native run above 120 s: a P1 program with a 0.3 s native run would still time out at 120 s, the row
would say `cap=1200`, and the 5,400 s pass would re-run it with the same 120 s limit. So every pass
sets the floor equal to the cap: every tool rep of every row ran under exactly the cap it states
(`tool_timeout == tool_timeout_cap` in every `meta.json`, §6a). The earlier baselines used the
120 s floor for P1–P6 and the 1,200 s floor for P7/P9.

(b) *Native wall = median of the 3 native reps* (harness change, c47c451's parent 8009702). Before,
`native_wall_s` was the fastest rep while `make_tables.py` takes the median of the tool's rep walls;
the brief asks for medians of both. The timeout rule keeps the fastest rep (irrelevant under (a)).
`meta.json` keeps all three (`native_walls`) and the minimum (`native_wall_min`).

(c) *Long-pass selection.* An id goes to a 5,400 s pass when **at least one** of its three reps in
that mode is TIMEOUT in the first pass (`setup/final_long_ids.py`), not only when the collapsed
verdict is TIMEOUT. One id is affected: P9-fpc-cuda, vector-clock reps TIMEOUT / CLEAN 1,162 s /
TIMEOUT. `parallel.py merge --override` replaces **all** rows of an overridden (id, mode), so no
(id, mode) mixes two caps.

(d) *Long-pass stores and nodes.* Each 5,400 s pass has its own store (`final-2026-10-long`,
`final-2026-10-long-sc`): `collect_one` wipes `<store>/<id>`, so recording into `final-2026-10`
would delete the first pass's other-mode dumps. The passes run on the 188 GB hosts (c60–c72) except
ids whose first-pass peak in that mode was ≤ 10 GB, which may run on any good node (4.5 × the
1,200 s footprint stays far below 125 GB): a 5,400 s run of the memory-heavy programs passes 128 GB
(particlefilter: 185–186 GB, §4), which on a 128 GB host is an OOM kill, not a measurement.

(e) *Long pass started early, in batches.* The vector-clock ids were submitted in four batches as the
first pass produced them (11 from the first-pass `meta.json` checkpoints — a vector-clock verdict is
fixed once its three reps are, before the scalar-clock reps — then 5, 2 and 1 from the CSVs), each
with its own `TAG` so shard-CSV names cannot collide; the union equals `final_long_ids.py`'s output
(19 ids, `setup/final_long_ids.txt`, checked by `diff`).

(f) *Scalar-clock at 5,400 s — added at Jeffery's request (2026-10-14).* The brief's long pass is
vector-clock only and CLAUDE.md's cap policy states scalar-clock at 1,200 s. Jeffery asked for the
scalar-clock TIMEOUTs to be re-run at 5,400 s as well: `p_final_long.sh` with `MODE=scalar-clock`,
18 ids (`setup/final_long_sc_ids.txt`; P9-fpc's scalar-clock finished in the first pass), store
`final-2026-10-long-sc`, results `eval/results/final-long-sc/`. **The cap policy for the tables is
therefore: every (id, mode) at 1,200 s, except the (id, mode) keys of the two long passes, at
5,400 s** — each row's notes say which (`cap=<s>`) — **and the keys of the 24 h pass at 86,400 s** (i).

(g) *Merge is cuVein-only.* `p_final2.sh` also re-merges sanitizer, iGUARD, SuperCollider and
HiRace from their shard CSVs; none was re-run, so `p_final_post.sh` merges cuvein alone and checks
the others' sha256 (§7).

(h) *PI on the 128 GB hosts.* The scheduler is FIFO (every job priority 1), so the PI array's
pending tasks would have taken the 188 GB hosts ahead of the long pass; `scontrol update
ExcNodeList` kept PI off c60–c72 (still the same partition). Log in §5.

(i) *A 24 h pass — added at Jeffery's request (2026-10-14).* The 21 (id, mode) keys still TIMEOUT at
5,400 s (11 vector-clock, 10 scalar-clock; `setup/final_24h_{vc,sc}_ids*.txt`) were re-run with a 24 h
cap, **one rep** each (native timing one rep too) — Jeffery's choice — by `setup/p_final_24h.sh` (=
`p_final.sh` with `CAP=86400 REPS=1`, own stores `final-2026-10-24h-{vc,sc}`, results
`eval/results/final-24h-{vc,sc}/`). 24 h plus native runs, extraction and analysis exceed
`rtx4060ti16g`'s 1-day limit, so the tasks ran in partition `max` (8 days), which contains the same
hosts; the exclude lists keep them on rtx4060ti16g hosts — c60–c72 by default, any good host
(`-x c2,c[4-22],c[25-26],c29,c[33-37],c[39-48],c54,c57,c59`) for the five keys whose 5,400 s peak was
≤ 6 GB — and `p_final.sh`'s GPU check refuses any other GPU. **Merge rule** (`p_final_post.sh`): a 24 h
row replaces all rows of its (id, mode) when the 24 h run reached RACE, CLEAN or a 24 h TIMEOUT; an
ERROR (OOM kill, incomplete trace) leaves the 5,400 s rows standing (Jeffery's choice) and is listed in
`eval/results/final-24h-kept-<m>/dropped.txt` — one key: P9-atomicCAS vector-clock. A RACE seen in a
run killed by OOM is a RACE (the harness's standing rule; P7-particlefilter scalar-clock, see (j)).

(j) *Partial-run notes (X1-follow Part 4, 2026-10-16).* Every row whose run was killed by the time
limit or by OOM keeps its verdict and carries `partial: <OOM|TIMEOUT> after <N> of <M> kernels, <wall> s,
cap=<s>` at the head of its notes — 183 shard rows, 12 of them in the merged file (particlefilter,
stencil1d, atomicCAS, expdist); method, counts and the full list in `eval/X1_FOLLOW.md` §4. No verdict
or other field changed (checked by hash over all shard rows).

## 2. Commands

```
# worktree (runtime = the main checkout via ACCEL_PROF_HOME; harness = the worktree)
git worktree add .claude/worktrees/wt-x1 -b eval/final-sweep cuVein
(cd .claude/worktrees/wt-x1 && for d in lib build .env ScoR cuHadron; do ln -s /home/fzheng4/AccelProf/$d $d; done;
 ln -s /home/fzheng4/AccelProf/nv-compute/lib nv-compute/lib; ln -s /home/fzheng4/AccelProf/eval/baselines/corpora eval/baselines/corpora)
# dry runs (step 1): 16 programs, 2 per pset; then P9 alone
IDS=<16 ids> NSHARDS=1 TAG=final-dryrun RES=final-dryrun STORE_TAG=final-2026-10-dryrun \
  sbatch --array=0 -J x1-dryrun -o <RT>/eval/baselines/setup/build_logs/final-dryrun-%A_%a.log eval/baselines/setup/p_final.sh   # 311943
IDS=P9-overlap-cuda,P9-crs-cuda NSHARDS=1 TAG=final-dryrun2 RES=final-dryrun2 STORE_TAG=final-2026-10-dryrun2 \
  sbatch --array=0 -J x1-dryrun2 -o .../final-dryrun2-%A_%a.log eval/baselines/setup/p_final.sh                                   # 311950
srun -p normal ... .env/bin/python eval/baselines/setup/final_sanity.py --merged eval/results/final-dryrun/<csv> \
  --store /mnt/beegfs/fzheng4/cuvein_traces/final-2026-10-dryrun:1200 --out eval/results/final-dryrun/sanity.json
# first pass (step 2)
sbatch eval/baselines/setup/p_final.sh                                                                                          # 311953, 48 shards
PSETS=PI NSHARDS=64 TAG=finalpi sbatch --array=0-63 -J x1-final-pi -o .../finalpi-%A_%a.log eval/baselines/setup/p_final.sh   # 311954
# 5,400 s, vector-clock: four batches, one id per shard (shard k = the k-th id of the file in manifest order),
# submitted as p_final.sh with p_final_long.sh's exports (p_final_long.sh took TAG/ID_FILE only later, d782726):
sbatch --array=0-10 -J x1-final-long -x 'c[0-3],c[23-24],c37,c[50-58],c[73-79]' -o .../final-long-%A_%a.log \
  --export=ALL,W=$W,MODES=vector-clock,CAP=5400,TAG=final-long-b1,RES=final-long,STORE_TAG=final-2026-10-long,\
ID_FILE=$W/eval/baselines/setup/final_long_ids_b1.txt,NSHARDS=11 eval/baselines/setup/p_final.sh                              # 311998
#   the same with TAG=final-long-b2 / b3 / b4 and final_long_ids_b2/b3/b4.txt: 312163 (5 ids), 312190 (2), 312207 (1)
#   equivalent now: ID_FILE=<ids> NSHARDS=<n> TAG=final-long-b<k> sbatch --array=0-<n-1> eval/baselines/setup/p_final_long.sh
# 5,400 s, scalar-clock (Jeffery, 2026-10-14)
MODE=scalar-clock ID_FILE=eval/baselines/setup/final_long_sc_ids_small.txt NSHARDS=11 TAG=final-long-sc-s \
  sbatch --array=0-10 -x c2,c21,c37,c54 -J x1-final-long-sc eval/baselines/setup/p_final_long.sh                              # 312213
MODE=scalar-clock ID_FILE=eval/baselines/setup/final_long_sc_ids_big.txt NSHARDS=7 TAG=final-long-sc-b \
  sbatch --array=0-6 -J x1-final-long-sc eval/baselines/setup/p_final_long.sh                                                  # 312214
# 24 h pass, one rep (Jeffery, 2026-10-14): the 21 (id, mode) keys still TIMEOUT at 5,400 s; partition max,
# c60-c72 by p_final_24h.sh's default exclude list, the small-memory keys on any good rtx4060ti16g host
MODE=vector-clock ID_FILE=eval/baselines/setup/final_24h_vc_ids_big.txt NSHARDS=9 TAG=final-24h-vc-b \
  sbatch --array=0-8 eval/baselines/setup/p_final_24h.sh                                                                         # 312332
MODE=scalar-clock ID_FILE=eval/baselines/setup/final_24h_sc_ids_big.txt NSHARDS=7 TAG=final-24h-sc-b \
  sbatch --array=0-6 eval/baselines/setup/p_final_24h.sh                                                                         # 312333
MODE=vector-clock ID_FILE=eval/baselines/setup/final_24h_vc_ids_small.txt NSHARDS=2 TAG=final-24h-vc-s \
  sbatch --array=0-1 -x c2,c[4-22],c[25-26],c29,c[33-37],c[39-48],c54,c57,c59 eval/baselines/setup/p_final_24h.sh             # 312334
MODE=scalar-clock ID_FILE=eval/baselines/setup/final_24h_sc_ids_small.txt NSHARDS=3 TAG=final-24h-sc-s \
  sbatch --array=0-2 -x c2,c[4-22],c[25-26],c29,c[33-37],c[39-48],c54,c57,c59 eval/baselines/setup/p_final_24h.sh             # 312335
# X1-follow Part 4 (2026-10-16): the partial-run notes on the shard CSVs (eval/X1_FOLLOW.md section 4), before steps 3-5
srun -p normal ... .env/bin/python eval/baselines/setup/x1f_extract.py --out eval/x1_follow/x1_meta.json
.env/bin/python eval/baselines/setup/x1f_partial_notes.py --meta eval/x1_follow/x1_meta.json --list eval/x1_follow/partial_rows.csv --apply
# steps 3-5
sbatch eval/baselines/setup/p_final_post.sh            # 312301 (passes 1-2); 2026-10-16 after the 24 h pass and Part 4:
                                                       # sbatch refused ("I/O error writing script/environment to file"),
bash eval/baselines/setup/p_final_post.sh              # run in the interactive allocation 313744 on c58 instead
.env/bin/python eval/baselines/setup/final_verdict_diff.py --final eval/results/baselines-cuvein.csv \
  --parity 'eval/results/x0-default/*.csv' --ids eval/baselines/setup/t5b_parity_ids.txt \
  --final-confirm <RT>/eval/baselines/confirm_final --parity-confirm <wt-x0>/eval/baselines/confirm_x0-default \
  --rep1-csv eval/results/final/parity_rep1.csv
.env/bin/python eval/baselines/verdict_diff.py 'eval/results/x0-default/*.csv' eval/results/final/parity_rep1.csv
.env/bin/python eval/baselines/setup/final_report_tables.py --merged eval/results/baselines-cuvein.csv --first eval/results/final \
  --long eval/results/final-long,eval/results/final-long-sc --h24 eval/results/final-24h-vc,eval/results/final-24h-sc \
  --diagnose eval/results/baselines-diagnose.csv --sacct <sacct dump>
```

## 3. Results

Coverage: 4725 manifest ids x 2 modes; missing (id, mode): 0; ids in the CSV not in the manifest: 0; CSV rows 28230. Every (id, mode) of the manifest has rows; the merged file holds the first pass's rows except
the keys a later pass overrides (§1 (c), (i)): 19 vector-clock and 18 scalar-clock keys at 5,400 s, of
which 10 + 10 at 86,400 s. Collapsed verdict per (id, mode) as `make_tables.py` collapses (RACE > CLEAN
> TIMEOUT > ERROR over the reps):

| suite | programs | rows | mode | CLEAN | RACE | TIMEOUT | ERROR | cap (s) |
|---|---|---|---|---|---|---|---|---|
| P1 | 400 | 2400 | vector-clock | 200 | 200 | 0 | 0 | 1200 |
|  |  |  | scalar-clock | 200 | 200 | 0 | 0 | 1200 |
| P3 | 60 | 360 | vector-clock | 44 | 16 | 0 | 0 | 1200 |
|  |  |  | scalar-clock | 44 | 16 | 0 | 0 | 1200 |
| P4 | 28 | 168 | vector-clock | 12 | 16 | 0 | 0 | 1200 |
|  |  |  | scalar-clock | 12 | 16 | 0 | 0 | 1200 |
| P5 | 33 | 198 | vector-clock | 29 | 4 | 0 | 0 | 1200 |
|  |  |  | scalar-clock | 31 | 2 | 0 | 0 | 1200 |
| P6 | 50 | 216 | vector-clock | 26 | 8 | 0 | 16 | 1200/86400 |
|  |  |  | scalar-clock | 26 | 8 | 0 | 16 | 1200/5400 |
| P7 | 14 | 62 | vector-clock | 9 | 4 | 1 | 0 | 1200/5400/86400 |
|  |  |  | scalar-clock | 9 | 4 | 1 | 0 | 1200/5400/86400 |
| P9 | 10 | 46 | vector-clock | 6 | 2 | 2 | 0 | 1200/5400/86400 |
|  |  |  | scalar-clock | 6 | 2 | 2 | 0 | 1200/5400/86400 |
| PI | 4130 | 24780 | vector-clock | 1710 | 2420 | 0 | 0 | 1200 |
|  |  |  | scalar-clock | 1710 | 2420 | 0 | 0 | 1200 |
| all | 4725 | 28230 | vector-clock | 2036 | 2670 | 3 | 16 | |
|  |  |  | scalar-clock | 2038 | 2668 | 3 | 16 | |

The rows that are neither RACE nor CLEAN, by reason (`classify_residuals.py --no-dump`,
`eval/results/baselines-diagnose.csv`): `needs-sm90` = the 16 cuHadron `bulkcpy`/`dsmem` programs whose
binaries need sm_90 and were not built (`missing-exe` in `meta.json`; ERROR, never run);
`hb-state-memory` = the run's `rss`/peak grows to the node's memory (P7-stencil1d both modes at 24 h,
P9-atomicCAS vector-clock at 5,400 s — its 24 h run was OOM-killed, §1 (i)); `time-cap` = kernels
complete but not all of them in the cap (P9-atomicCAS and P9-expdist scalar-clock at 24 h);
`no-kernel-in-cap` = not one kernel finished in the cap (P9-expdist vector-clock at 24 h).

| suite | mode | verdict | reason class | (id, mode) |
|---|---|---|---|---|
| P6 | scalar-clock | ERROR | needs-sm90 | 16 |
| P6 | vector-clock | ERROR | needs-sm90 | 16 |
| P7 | scalar-clock | TIMEOUT | hb-state-memory | 1 |
| P7 | vector-clock | TIMEOUT | hb-state-memory | 1 |
| P9 | scalar-clock | TIMEOUT | time-cap | 2 |
| P9 | vector-clock | TIMEOUT | hb-state-memory | 1 |
| P9 | vector-clock | TIMEOUT | no-kernel-in-cap | 1 |

No row reached the offline analysis cap (14,400 s): no `analysis-timeout` in the merged file.

## 4. The long passes

**5,400 s** (§1 (c)–(f); `eval/results/final-long/`, `final-long-sc/`). First-pass reps and the
5,400 s reps of every key that went there; peak = the harness's summed-VmRSS peak, node = the host of a
finished row:

| id | mode | first pass (1,200 s): verdict, rep walls (s) | long pass (5,400 s): verdict | rep walls (s) | median wall (s) | peak MB | node |
|---|---|---|---|---|---|---|---|
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed | vector-clock | TIMEOUT: 1200.005, 1200.006, 1200.006 | TIMEOUT | 5400.005, 5400.016, 5400.005 | 5400.005 | 37,332 | — |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy | vector-clock | TIMEOUT: 1200.027, 1200.025, 1200.031 | TIMEOUT | 5400.005, 5400.005, 5400.016 | 5400.005 | 37,743 | — |
| P7-bfs-cuda | vector-clock | TIMEOUT: 1200.006, 1200.007, 1200.006 | TIMEOUT | 5400.006, 5400.006, 5400.019 | 5400.006 | 1,552 | — |
| P7-bitonic-sort-cuda | vector-clock | TIMEOUT: 1200.004, 1200.004, 1200.004 | CLEAN | 3689.219, 3644.214, 3726.762 | 3689.219 | 9,191 | c58 |
| P7-haversine-cuda | vector-clock | TIMEOUT: 1200.004, 1200.003, 1200.004 | CLEAN | 4952.726, 5101.543, 4984.198 | 4984.198 | 9,565 | c52 |
| P7-heartwall-cuda | vector-clock | TIMEOUT: 1200.005, 1200.005, 1200.004 | TIMEOUT | 5400.006, 5400.006, 5400.006 | 5400.006 | 6,181 | — |
| P7-lavaMD-cuda | vector-clock | TIMEOUT: 1200.005, 1200.005, 1200.005 | CLEAN | 1867.433, 1868.013, 1859.917 | 1867.433 | 23,009 | c62 |
| P7-mandelbrot-cuda | vector-clock | TIMEOUT: 1200.004, 1200.004, 1200.005 | CLEAN | 3892.739, 3691.401, 3576.969 | 3691.401 | 1,455 | c66 |
| P7-nbody-cuda | vector-clock | TIMEOUT: 1200.004, 1200.005, 1200.005 | TIMEOUT | 5400.005, 5400.006, 5400.005 | 5400.005 | 29,001 | — |
| P7-particlefilter-cuda | vector-clock | TIMEOUT: 1200.004, 1200.004, 1200.004 | RACE | 5330.785, 5312.891, 5320.796 | 5320.796 | 185,441 | c64 |
| P7-pathfinder-cuda | vector-clock | TIMEOUT: 1200.004, 1200.005, 1200.005 | TIMEOUT | 5400.005, 5400.018, 5400.005 | 5400.005 | 16,639 | — |
| P7-srad-cuda | vector-clock | TIMEOUT: 1200.004, 1200.005, 1200.005 | CLEAN | 2199.151, 2160.416, 2151.169 | 2160.416 | 1,073 | c61 |
| P7-stencil1d-cuda | vector-clock | TIMEOUT: 1200.004, 1200.004, 1200.004 | TIMEOUT | 5400.005, 5400.016, 5400.005 | 5400.005 | 98,199 | — |
| P9-atomicCAS-cuda | vector-clock | TIMEOUT: 1200.004, 1200.004, 1200.004 | TIMEOUT | 5400.005, 5400.005, 5400.005 | 5400.005 | 99,522 | — |
| P9-dxtc2-cuda | vector-clock | TIMEOUT: 1200.005, 1200.006, 1200.006 | RACE | 3248.307, 3138.202, 3295.73 | 3248.307 | 2,874 | c79 |
| P9-expdist-cuda | vector-clock | TIMEOUT: 1200.025, 1200.024, 1200.025 | TIMEOUT | 5400.006, 5400.023, 5400.014 | 5400.014 | 12,981 | — |
| P9-fpc-cuda | vector-clock | CLEAN: 1200.032, 1162.282, 1200.03 | CLEAN | 1341.634, 1263.988, 1294.81 | 1294.81 | 2,822 | c74 |
| P9-knn-cuda | vector-clock | TIMEOUT: 1200.006, 1200.007, 1200.007 | TIMEOUT | 5400.005, 5400.005, 5400.005 | 5400.005 | 21,785 | — |
| P9-tridiagonal-cuda | vector-clock | TIMEOUT: 1200.006, 1200.006, 1200.005 | TIMEOUT | 5400.02, 5400.007, 5400.007 | 5400.007 | 8,744 | — |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed | scalar-clock | TIMEOUT: 1200.005, 1200.005, 1200.006 | RACE | 4595.972, 4598.517, 4601.344 | 4598.517 | 65,897 | c64 |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy | scalar-clock | TIMEOUT: 1200.026, 1200.026, 1200.026 | RACE | 4594.326, 4577.193, 4607.817 | 4594.326 | 65,894 | c62 |
| P7-bfs-cuda | scalar-clock | TIMEOUT: 1200.005, 1200.007, 1200.006 | RACE | 1506.546, 1503.232, 1506.976 | 1506.546 | 1,718 | c74 |
| P7-bitonic-sort-cuda | scalar-clock | TIMEOUT: 1200.004, 1200.005, 1200.005 | CLEAN | 3706.864, 3721.513, 3635.393 | 3706.864 | 5,582 | c51 |
| P7-haversine-cuda | scalar-clock | TIMEOUT: 1200.002, 1200.003, 1200.004 | TIMEOUT | 5400.006, 5400.006, 5400.006 | 5400.006 | 8,328 | — |
| P7-heartwall-cuda | scalar-clock | TIMEOUT: 1200.004, 1200.005, 1200.005 | TIMEOUT | 5400.004, 5400.004, 5400.004 | 5400.004 | 6,190 | — |
| P7-lavaMD-cuda | scalar-clock | TIMEOUT: 1200.005, 1200.005, 1200.005 | CLEAN | 1501.705, 1511.127, 1506.689 | 1506.689 | 22,652 | c60 |
| P7-mandelbrot-cuda | scalar-clock | TIMEOUT: 1200.004, 1200.004, 1200.006 | CLEAN | 2421.822, 2327.284, 2339.662 | 2339.662 | 1,269 | c52 |
| P7-nbody-cuda | scalar-clock | TIMEOUT: 1200.004, 1200.005, 1200.006 | TIMEOUT | 5400.005, 5400.005, 5400.004 | 5400.005 | 28,987 | — |
| P7-particlefilter-cuda | scalar-clock | TIMEOUT: 1200.003, 1200.005, 1200.003 | TIMEOUT | 5401.364, 5401.813, 5401.937 | 5401.813 | 185,961 | — |
| P7-pathfinder-cuda | scalar-clock | TIMEOUT: 1200.004, 1200.005, 1200.005 | TIMEOUT | 5400.006, 5400.007, 5400.006 | 5400.006 | 5,918 | — |
| P7-srad-cuda | scalar-clock | TIMEOUT: 1200.004, 1200.005, 1200.005 | CLEAN | 2536.637, 2522.389, 2555.668 | 2536.637 | 1,041 | c73 |
| P7-stencil1d-cuda | scalar-clock | TIMEOUT: 1200.003, 1200.005, 1200.004 | TIMEOUT | 5400.005, 5400.005, 5400.018 | 5400.005 | 83,745 | — |
| P9-atomicCAS-cuda | scalar-clock | TIMEOUT: 1200.004, 1200.004, 1200.004 | TIMEOUT | 5400.005, 5400.005, 5400.005 | 5400.005 | 899 | — |
| P9-dxtc2-cuda | scalar-clock | TIMEOUT: 1200.005, 1200.006, 1200.006 | RACE | 1546.341, 1494.032, 1498.336 | 1498.336 | 2,650 | c52 |
| P9-expdist-cuda | scalar-clock | TIMEOUT: 1200.025, 1200.026, 1200.025 | TIMEOUT | 5400.011, 5400.006, 5400.019 | 5400.011 | 6,703 | — |
| P9-knn-cuda | scalar-clock | TIMEOUT: 1200.006, 1200.007, 1200.006 | TIMEOUT | 5400.005, 5400.005, 5400.019 | 5400.005 | 20,086 | — |
| P9-tridiagonal-cuda | scalar-clock | TIMEOUT: 1200.005, 1200.006, 1200.006 | TIMEOUT | 5400.007, 5400.026, 5400.008 | 5400.008 | 8,333 | — |

Long pass, vector-clock: 19 ids; RACE 2, CLEAN 6, TIMEOUT 11. Long pass, scalar-clock: 18 ids; RACE 4, CLEAN 4, TIMEOUT 10. The RACE of P7-particlefilter vector-clock comes from runs killed by OOM at
5,313–5,331 s (185.3–185.4 GB) after 3 kernels (§1 (j)); its scalar-clock 5,400 s reps ran into the cap
at 186 GB.

**24 h, one rep** (§1 (i); `eval/results/final-24h-vc/`, `final-24h-sc/`):

| id | mode | 5,400 s verdict | 24 h verdict | wall (s) | peak MB | rc | node | in the merged CSV |
|---|---|---|---|---|---|---|---|---|
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed | vector-clock | TIMEOUT | RACE | 14534.817 | 71,937 | 0 | c61 | 24 h row |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy | vector-clock | TIMEOUT | RACE | 14550.27 | 71,942 | 0 | c60 | 24 h row |
| P7-bfs-cuda | vector-clock | TIMEOUT | RACE | 6289.863 | 1,808 | 0 | c51 | 24 h row |
| P7-heartwall-cuda | vector-clock | TIMEOUT | RACE | 35574.705 | 6,194 | 0 | c58 | 24 h row |
| P7-nbody-cuda | vector-clock | TIMEOUT | CLEAN | 8197.555 | 29,294 | 0 | c62 | 24 h row |
| P7-pathfinder-cuda | vector-clock | TIMEOUT | RACE | 28386.115 | 17,592 | 0 | c63 | 24 h row |
| P7-stencil1d-cuda | vector-clock | TIMEOUT | TIMEOUT | 86400.019 | 98,495 | 124 | — | 24 h row |
| P9-atomicCAS-cuda | vector-clock | TIMEOUT | ERROR | 17624.601 | 186,308 | 1 | — | 5,400 s rows kept (24 h run: ERROR) |
| P9-expdist-cuda | vector-clock | TIMEOUT | TIMEOUT | 86400.015 | 20,364 | 124 | — | 24 h row |
| P9-knn-cuda | vector-clock | TIMEOUT | CLEAN | 57215.724 | 22,198 | 0 | c62 | 24 h row |
| P9-tridiagonal-cuda | vector-clock | TIMEOUT | RACE | 42483.9 | 10,810 | 0 | c61 | 24 h row |
| P7-haversine-cuda | scalar-clock | TIMEOUT | CLEAN | 6931.599 | 8,348 | 0 | c63 | 24 h row |
| P7-heartwall-cuda | scalar-clock | TIMEOUT | RACE | 32057.217 | 6,186 | 0 | c52 | 24 h row |
| P7-nbody-cuda | scalar-clock | TIMEOUT | CLEAN | 8014.964 | 29,226 | 0 | c66 | 24 h row |
| P7-particlefilter-cuda | scalar-clock | TIMEOUT | RACE | 5791.383 | 186,168 | 1 | c66 | 24 h row |
| P7-pathfinder-cuda | scalar-clock | TIMEOUT | RACE | 19225.434 | 6,779 | 0 | c77 | 24 h row |
| P7-stencil1d-cuda | scalar-clock | TIMEOUT | TIMEOUT | 86400.005 | 84,061 | 124 | — | 24 h row |
| P9-atomicCAS-cuda | scalar-clock | TIMEOUT | TIMEOUT | 86400.03 | 908 | 124 | — | 24 h row |
| P9-expdist-cuda | scalar-clock | TIMEOUT | TIMEOUT | 86400.016 | 9,912 | 124 | — | 24 h row |
| P9-knn-cuda | scalar-clock | TIMEOUT | CLEAN | 44762.407 | 20,558 | 0 | c66 | 24 h row |
| P9-tridiagonal-cuda | scalar-clock | TIMEOUT | RACE | 36768.052 | 10,360 | 0 | c61 | 24 h row |

24 h pass, vector-clock: 11 keys; RACE 6, CLEAN 2, TIMEOUT 2, ERROR 1. 24 h pass, scalar-clock: 10 keys; RACE 4, CLEAN 3, TIMEOUT 3. The 21 tasks: 312332 (vector-clock, 9, c60–c72), 312333 (scalar-clock, 7, c60–c72),
312334 (vector-clock, 2) and 312335 (scalar-clock, 3) on any good rtx4060ti16g host; every task
COMPLETED as a SLURM job. Two of the RACE rows come from runs that did not complete:
P7-particlefilter scalar-clock (OOM at 5,791 s, 186.2 GB, after 3 kernels; kept, RACE) and
P9-atomicCAS vector-clock (OOM at 17,625 s, 186.3 GB, after 30,000 kernels; ERROR, dropped, the
5,400 s TIMEOUT stands). P6-asyncmemcpy-…dtoh_race-fixed (labelled race-free) is RACE at 24 h in
vector-clock mode, as its scalar-clock row already was at 5,400 s; P9-knn (labelled racy) is CLEAN
in both modes at 24 h.

## 5. Scheduling and resubmission log

From the session log (`~/.x1/log.txt`), `sacct` and the shard logs:

- 2026-10-13 17:33 — dry run 1 (311943) cancelled after 13 of 16 programs validated; P7-bfs (TIMEOUT
  at 1,200 s in both modes under T4) left to the main sweep.
- 10-13 19:27 — long batch 1 (11 ids from the first-pass `meta.json` checkpoints) submitted; the PI
  array 311954 briefly given `nice=10000`, back to 0 a minute later (the scheduler is FIFO, priority 1
  for every job) and `ExcNodeList=c2,c21,c37,c54,c[60-72]` instead (PI on the 125 GB hosts, the 188 GB
  hosts for the long pass).
- 10-13 22:21 / 23:07 — long batches 2 (5 ids) and 3 (2 ids); pending long tasks whose first-pass
  vector-clock peak was ≤ 10 GB moved to any good host (`ExcNodeList=c2,c21,c37,c54`).
- 10-14 00:07 — first pass complete: 112 / 112 shards COMPLETED, **no resubmission**; long batch 4
  (P9-expdist), moved to any good host at 00:12.
- 10-14 01:21 — scalar-clock 5,400 s pass (Jeffery): 11 low-memory ids on any good host, 7 on
  c60–c72; at 04:16 the pending low-memory tasks were kept off c60–c72.
- 10-14 14:23 — 24 h pass (Jeffery: one rep; OOM keeps the 5,400 s TIMEOUT), 21 tasks, partition `max`.
  **The first 10 tasks to start** (312332_0–4, 312334_0–1, 312335_0–2) recorded the harness at
  c20d8c5 with `dirty=7`: the 7 files were the uncommitted post-processing outputs of the interim
  merge (results CSVs and tables), not code; they were committed as c6d68d5, and every later task
  started clean (`dirty=0`, c6d68d5 or a514674). The code paths the tasks run are identical at the three
  commits (§0).
- 10-16 08:39 — the last 24 h task (P9-expdist scalar-clock) ended; 21 / 21 COMPLETED, no resubmission.
- 10-16 17:29 — X1-follow Part 4 notes applied to the shard CSVs (§1 (j)).
- 10-16 17:32 — `sbatch eval/baselines/setup/p_final_post.sh` refused twice by the controller
  (`Batch job submission failed: I/O error writing script/environment to file`); an `srun` on `normal`
  hung waiting for a step in the session's own allocation and was killed before it ran anything; the
  post-processing then ran with `bash` in the interactive allocation 313744 on c58 (`normal`, 16 CPUs,
  BeeGFS mounted), 17:34–17:42, log `build_logs/final-post-c58-20261016.log`.

## 6. Sanity checks

`setup/final_sanity.py` (inside `p_final_post.sh`), stores `final-2026-10:1200`,
`final-2026-10-long:5400`, `final-2026-10-long-sc:5400`, `final-2026-10-24h-vc:86400`,
`final-2026-10-24h-sc:86400` → `eval/results/final/sanity.json`.

- **(a) proved-in-effect over 4,783 `meta.json`** (4,725 + 19 + 18 + 11 + 10): every one except the 16
  `needs-sm90` programs (no binary; `hb_dump` unset, `error=missing-exe`) has `hb_dump: false`, the frozen
  runtime hashes (collector `ee78cb89`, libsanalyzer `2201fcb7`, fatbin `a2d7368b`, late fatbin
  `e9634312`), status done, arch 8.9, no excluded node, and `tool_timeout == tool_timeout_cap ==` its
  store's cap. **73,395 kernel JSONs** (vector-clock 51,807, scalar-clock 21,588; the 24 h atomicCAS
  vector-clock run's 30,000 included): none has `hb_events`, all have `hb_aggregates`, `hb_sync_pass`,
  `hb_rmw_points`, `hb_stats` (vector-clock also `hb_races`, `hb_chain`) — 0 bad.
- **(b) verdict diff against T20's parity recording** (X0's re-score, `eval/results/x0-default/`; the
  60 programs of `setup/t5b_parity_ids.txt`, 130 (id, mode) keys; `setup/final_verdict_diff.py` →
  `eval/results/final/verdict_diff_t20.txt`): same verdict 122 (9 of them RACE with a different report
  set — 4 keys of three P1-CC programs, 1 of P4-graph-connectivity-racy-small, 4 of two PI programs:
  mostly the same pc pair with the orientation swapped, RAW ↔ WAR; in P4-graph-connectivity and
  PI-populate_worklist also different pairs), different 8, **all by cap**: the parity
  recording's 120 s timeout against this recording's 1,200 / 5,400 / 86,400 s (P6-interkernel
  writewrite racy and P9-overlap CLEAN in both modes; P7-bfs RACE both modes; P7-particlefilter RACE
  both modes). Causes: cap 8, schedule 0, other 0. The literal rep-1 diff
  (`verdict_diff.py`, `verdict_diff_t20_rep1_literal.txt`) lists 17 differing rows of 130: exactly the 8
  keys of different verdict and the 9 with a different report set.
- **(c) `tv_violation`: none** in any kernel JSON of any store, every suite and mode.
- **(d) static-leg-only verdicts: 0** — every merged RACE/CLEAN row has `hb_races` (vector-clock) or
  `hb_sync_pass` (scalar-clock) in every saved kernel JSON of its mode.

## 7. The other tools' results

Not re-run. `p_final_post.sh` records the sha256 of every `eval/results/baselines-*.csv` other than
cuVein's and the three cuVein-derived analysis files, before and after the merge: **209 files,
unchanged**, and equal to the hashes taken before the sweep was submitted
(`eval/results/final/other_tools.sha256.{pre-sweep,before,after}`).

## 8. Node-hours

From `sacct` (`eval/results/final/sacct.txt`, job names `x1-*`; X1-follow's `x1f-*` jobs excluded):

| job name | node-hours | nodes | first start | last end |
|---|---|---|---|---|
| x1-dryrun | 0.3 | 1 | 2026-10-13T17:13:13 | 2026-10-13T17:33:50 |
| x1-dryrun2 | 0.3 | 1 | 2026-10-13T17:31:11 | 2026-10-13T17:51:34 |
| x1-final | 48.6 | 12 | 2026-10-13T17:32:21 | 2026-10-14T00:06:22 |
| x1-final-24h | 233.3 | 11 | 2026-10-14T14:23:22 | 2026-10-16T08:39:26 |
| x1-final-long | 73.9 | 12 | 2026-10-13T21:35:08 | 2026-10-14T06:51:21 |
| x1-final-long-sc | 66.3 | 14 | 2026-10-14T02:02:40 | 2026-10-14T12:23:09 |
| x1-final-pi | 11.5 | 7 | 2026-10-13T20:20:26 | 2026-10-13T22:36:33 |
| x1-post | 0.1 | 1 | 2026-10-14T12:24:10 | 2026-10-14T12:27:42 |
| x1-sanity1 | 0.1 | 1 | 2026-10-14T00:07:31 | 2026-10-14T00:11:10 |
| all | 434.4 | 15 | 2026-10-13T17:13:13 | 2026-10-16T08:39:26 |

## 9. Against the 2026-09-22 recording

Collapsed verdicts per suite, the superseded file (`eval/results/superseded_baselines-cuvein-2026-09-22.csv`)
against the merged X1 file (`setup/final_old_vs_new.py` → `eval/results/final/old_vs_new.md`):

| suite | mode | old (2026-09-22) RACE / CLEAN / TIMEOUT / ERROR | new (X1) RACE / CLEAN / TIMEOUT / ERROR | (id, mode) whose verdict changed |
|---|---|---|---|---|
| P1 | vector-clock | 182 / 199 / 19 / 0 | 200 / 200 / 0 / 0 | 19 |
| P1 | scalar-clock | 200 / 200 / 0 / 0 | 200 / 200 / 0 / 0 | 0 |
| P3 | vector-clock | 14 / 44 / 2 / 0 | 16 / 44 / 0 / 0 | 2 |
| P3 | scalar-clock | 16 / 44 / 0 / 0 | 16 / 44 / 0 / 0 | 0 |
| P4 | vector-clock | 14 / 4 / 10 / 0 | 16 / 12 / 0 / 0 | 13 |
| P4 | scalar-clock | 20 / 8 / 0 / 0 | 16 / 12 / 0 / 0 | 4 |
| P5 | vector-clock | 19 / 14 / 0 / 0 | 4 / 29 / 0 / 0 | 17 |
| P5 | scalar-clock | 18 / 15 / 0 / 0 | 2 / 31 / 0 / 0 | 16 |
| P6 | vector-clock | 5 / 24 / 4 / 17 | 8 / 26 / 0 / 16 | 6 |
| P6 | scalar-clock | 5 / 25 / 3 / 17 | 8 / 26 / 0 / 16 | 5 |
| P7 | vector-clock | 2 / 1 / 11 / 0 | 4 / 9 / 1 / 0 | 10 |
| P7 | scalar-clock | 2 / 2 / 10 / 0 | 4 / 9 / 1 / 0 | 9 |
| P9 | vector-clock | 1 / 1 / 8 / 0 | 2 / 6 / 2 / 0 | 7 |
| P9 | scalar-clock | 1 / 3 / 6 / 0 | 2 / 6 / 2 / 0 | 5 |
| PI | vector-clock | 2420 / 1710 / 0 / 0 | 2420 / 1710 / 0 / 0 | 0 |
| PI | scalar-clock | 2420 / 1710 / 0 / 0 | 2420 / 1710 / 0 / 0 | 0 |

| suite | mode | old → new | (id, mode) |
|---|---|---|---|
| P1 | vector-clock | TIMEOUT → CLEAN | 1 |
| P1 | vector-clock | TIMEOUT → RACE | 18 |
| P3 | vector-clock | TIMEOUT → RACE | 2 |
| P4 | scalar-clock | RACE → CLEAN | 4 |
| P4 | vector-clock | RACE → CLEAN | 3 |
| P4 | vector-clock | TIMEOUT → CLEAN | 5 |
| P4 | vector-clock | TIMEOUT → RACE | 5 |
| P5 | scalar-clock | RACE → CLEAN | 16 |
| P5 | vector-clock | CLEAN → RACE | 1 |
| P5 | vector-clock | RACE → CLEAN | 16 |
| P6 | scalar-clock | CLEAN → RACE | 1 |
| P6 | scalar-clock | ERROR → CLEAN | 1 |
| P6 | scalar-clock | TIMEOUT → CLEAN | 1 |
| P6 | scalar-clock | TIMEOUT → RACE | 2 |
| P6 | vector-clock | CLEAN → RACE | 1 |
| P6 | vector-clock | ERROR → CLEAN | 1 |
| P6 | vector-clock | TIMEOUT → CLEAN | 2 |
| P6 | vector-clock | TIMEOUT → RACE | 2 |
| P7 | scalar-clock | TIMEOUT → CLEAN | 7 |
| P7 | scalar-clock | TIMEOUT → RACE | 2 |
| P7 | vector-clock | TIMEOUT → CLEAN | 8 |
| P7 | vector-clock | TIMEOUT → RACE | 2 |
| P9 | scalar-clock | RACE → CLEAN | 1 |
| P9 | scalar-clock | TIMEOUT → CLEAN | 2 |
| P9 | scalar-clock | TIMEOUT → RACE | 2 |
| P9 | vector-clock | RACE → CLEAN | 1 |
| P9 | vector-clock | TIMEOUT → CLEAN | 4 |
| P9 | vector-clock | TIMEOUT → RACE | 2 |

Facts only: every 2026-09-22 TIMEOUT of P1–P4 now has a verdict; P5's RACE count falls from 19 / 18 to 4 / 2 (vector- / scalar-clock) on the
same 33 litmus programs; PI is unchanged; P7 and P9 keep 1 and 2 TIMEOUT keys per mode (stencil1d;
atomicCAS, expdist). Which detector change moved which verdict is not attributed here.

## 10. What remains unverified

- **The 24 h rows are single reps** (Jeffery's choice); their walls are one run, not medians, and the
  native wall of those rows is one run too.
- **Cross-host walls.** Each row's tool and native walls come from one host, but the partition mixes
  three CPUs, two RAM sizes and three drivers (c66 alone has 595.58.03, §0); rows on different hosts are
  not wall-comparable.
- **The 10 24 h tasks with `dirty=7`** (§5) ran an uncommitted harness tree; the 7 files were
  post-processing outputs, committed unchanged as c6d68d5 — asserted from the commit, not re-run.
- **OOM** in the partial-row notes and the dropped atomicCAS row is inferred from SIGKILL ("Killed" in
  the accelprof stderr) at 185–186 GB on 188 GB hosts; the nodes' kernel logs were not read.
- **Partial-run verdicts.** P7-particlefilter's RACE in both modes rests on its first 3 kernels (runs
  killed by OOM); no X1 run of particlefilter, stencil1d, atomicCAS or expdist completed, so their
  total kernel counts are unknown ("?" in the notes).
- **The final post-processing ran outside a batch job** (§5), in the session's interactive allocation;
  its inputs and scripts are the same as the batch path's.
- **Label questions** surfaced by the 24 h pass (P6-asyncmemcpy-…-fixed RACE, P9-knn CLEAN against its
  racy label) are recorded, not investigated here.


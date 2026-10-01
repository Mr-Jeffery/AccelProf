# Home quota recovery (T-H) -- Phase 1 inventory and plan

Measured 2026-10-01 on the login node, `cuVein` 8263e04, read-only. Nothing was moved, removed or cleaned.
Phase 2 not run -- awaiting go-ahead.

## 1. Quota

`quota -s`: 37,820 MB used, soft 39,936 MB, hard 40,960 MB, 265k files (NFS `10.1.1.10:/home`).
Acceptance bar: below 25 GB.

## 2. Home top level (`du -sh`)

| path | size | note |
|---|---|---|
| `AccelProf` | 16 G | see 3 |
| `.accel_scratch` | 14 G | 2026-09-10 Phase-4 scale scratch; `phase4/` = 14 G (two 5.7 G `dependency_gemm.out_*` dirs, two 723 M, rest 91 M). No `.py/.sh/.md` in the repo references `accel_scratch` |
| `miniconda3` | 2.4 G | `pkgs/` = 1.0 G (`conda clean -a` candidate; recovery not measured); `AccelProf/.env` is a symlink to `miniconda3/envs/accel` |
| `.local` | 856 M | `share/claude` 692 M (Claude Code binaries), `share/nvim` 164 M |
| `.debug` | 786 M | perf build-id cache (`usr` 324 M, `[kernel.kallsyms]` 43 M); not in the brief's cache list, so user's call |
| `incoming` | 750 M | see 6 |
| `.cache` | 342 M | `pip` 334 M; others < 5 M |
| `spack` | 507 M | leave alone |
| `.vscode-server` / `.vscode-remote-containers` | 254 M / 235 M | not touched |
| `.claude` | 149 M | `projects` 124 M |
| `.spack` 136 M, `.nv` 41 M (`ComputeCache` 41 M), `TenHo` 2.1 M, `.conda` 20 K, `.triton` absent | | |
| `texlive` 167 M, `nvim` 55 M | | leave alone |
| worktrees, stage dirs | ~1.6 G | see 4 and 5 |

Sums to roughly 37.8 G with the worktrees and stage dirs.

## 3. `AccelProf/eval/baselines` (about 15 G of the 16 G)

| entry | size | files | symlink? | readers (`/usr/bin/grep -rl`, py/sh) | store_index mirror |
|---|---|---|---|---|---|
| `traces_keep.prefix_fe694b5` | 3.7 G | 5062 | no | none by name (default glob `traces_keep*` in `store_inventory.py`, `migrate_mode_names.py`); matching `confirm.prefix_fe694b5` 7.8 M | none |
| `traces_keep` | 3.1 G | 3467 | no | `classify_fp_causes.py` (`--traces` default), `p_keep.sh`, `p_rerun.sh`, `p_rerun_p9.sh`, `p_fpfix*.sh`, `p_evcand.sh`, `p_diagnose.sh`, `p_pi_cuvein.sh`, `p_sc_others.sh`, `supersede_*.sh` | none |
| `traces_keep.prefix_36a93d08` | 2.8 G | 1678 | no | none by name; `confirm.prefix_36a93d08` 6.0 M | none |
| `traces_keep_evcand` | 970 M | 1113 | no | `p_evcand.sh` | `store_index/evcand` has 615 entries; mirrors the BeeGFS evcand store, not this dir (not verified) |
| `traces_keep_fpfix_tr` | 673 M | 545 | no | `p_fpfix_tr.sh` | none |
| `traces_keep_fpfix` | 572 M | 794 | no | `p_fpfix.sh`, `p_fpfix_tr.sh`, `p_fpfix_eng.sh` | none |
| `corpora` | 1.3 G | 28225 | no | `p_build.sh`, `p7_fix.sh`, `p_sweep_build.sh`, `p_full_build.sh`, `sbatch_*.sh` (built from `build_corpora.py` / `fetch_corpora.sh`) | n/a |
| `setup` | 1.6 G | | no | scripts stay in place; 1.6 G is `setup/tools` | n/a |
| `bin` | 136 M | 1794 | no | harness binaries; keep | n/a |
| `confirm`, `confirm_*`, `confirm.prefix_*` | 41 M + about 35 M | | no | `parallel.py`, `make_tables.py`, `run_cuvein.py`; tiny, keep | n/a |
| `store_index` 19 M, `oracle_pi` 21 M, `inputs` 8.7 M, `manifest*.csv` | | | | untouchable per brief | |

All six `traces_keep*` and `corpora`, `bin`, `setup/tools` are gitignored (`eval/.gitignore`). None has a `STORE_INFO.json`; Phase 2 has to mirror the per-id `meta.json` files into `store_index/<tag>/` first (T0 step 5).
Total of the six trace dirs: 11.85 G.

`setup/` breakdown (`du -sh setup/*`): `tools` 1.6 G, `build_logs` 9.8 M, `iguard` 3.5 M, `smoke_hirace` 1.5 M, `t3_crs` 1.1 M, `migrate_logs` 720 K, `t5b_parity` 584 K, all else under 400 K. Inside `tools`: `iGUARD-SOSP21` 749 M, `supercollider` 492 M, `hirace_venv` 181 M, `supercollider-artifacts-v1.zip` 157 M, `HiRace` 34 M, NVBit tarballs 5 x about 0.6-0.9 M. Used by `run_supercollider.py`, `build_sc_sets.py`, `hirace_table1_to_csv.py`, `build_indigo_full.py`, `p_hirace_table1.sh`, `p_table1_report.sh`, `progress.sh`.
Other AccelProf: `build` 174 M, `third_party` 6.2 M, `nv-compute` 6 M, `ScoR` 5.6 M, `lib` 4.1 M, `cuHadron` 1.3 M, `sanalyzer/wt_install` 17 M.

`sanalyzer/wt_install/` (untracked in the main checkout, 17 M): private-runtime build output. Referenced by about 20 `setup/t*_check.sh`, `t*_build.sh`, `wt_runtime.sh` scripts and CLAUDE.md. Keep.

## 4. Worktrees (`git worktree list`; all branches are merged into `cuVein`)

| path | branch | status | size | action |
|---|---|---|---|---|
| `wt-t18` | `fix/late-seq-gating` | dirty (modified tracked files + untracked), in use by another session with SLURM jobs | 133 M | KEEP (in use) |
| `wt-T4` | `feat/no-dump` | clean, the launching session's | 133 M | KEEP |
| `rt-prev-e527875d` | detached de565c0 | untracked `build` only | 153 M | ASK USER: `t17_rtraw_repeat.sh` (`P=`), `t17_install.sh`, `t17_merge_check.sh` use it; T18 re-runs the script. Keep until T18 is done |
| `wt-T1a-review` | `fix/cp-async-review` | untracked symlinks and `.probe/` | 189 M | ASK USER: holds `install_stage/obj` (18 M), the default `OBJ=` of `wt_runtime.sh`, `t17_build.sh`, `t17_install.sh`, `t3b_build.sh` |
| `wt-T17` | `chore/rename-hb-clock` | untracked `build`, `build_logs/`, `lib`, `nv-compute/lib`, `sanalyzer/wt_install/` | 233 M | ASK USER (`build_logs`, `wt_install` are unique, unversioned build output) |
| `wt-T2` | `feat/host-memcpy` | MODIFIED tracked files (`t2_evidence/host_ops.*.json`) + untracked | 182 M | KEEP: dirty. User decides |
| `wt-T1a` | `feat/cp-async-wait` | untracked symlinks only | 171 M | remove (needs `--force` for the untracked symlinks) after user OK |
| `wt-T3` | `triage/crs-cuda` | untracked symlinks only | 102 M | same |
| `wt-T6` | `design/algorithms` | untracked symlinks only | 105 M | same |
| `wt-proof` | `docs/proof-inputs` | clean | 103 M | remove with plain `git worktree remove` |
| `AccelProf/.claude/worktrees/study-nvbit-spike` | `study/nvbit-spike` | clean | not measured | harness worktree; ask user |
| `wt-TH` | `infra/home-cleanup` | this task | 106 M | keep |

Untracked entries are mostly symlinks to the main checkout's gitignored dirs (`ScoR build cuHadron eval/baselines/bin eval/baselines/corpora ...`). `git worktree remove` refuses on untracked files, so `--force` is needed. Branch refs are kept, as the brief says. The brief says to remove only worktrees that are merged and clean. By that literal rule only `wt-proof` qualifies. I list the untracked-symlink-only ones separately so the user can decide.

## 5. Stage and mirror dirs

| path | size | what / who references it | action |
|---|---|---|---|
| `~/stage` | 32 M | `sanalyzer-f61c389`, `libsanalyzer.so.75f46012.bak`, `build_sanalyzer.sh`, `green_set.sh`. No script references it (the memory note mentions the 75f46012 backup) | ASK USER (the .bak is a rollback copy) |
| `~/t17-stage` | 58 M | `nvc`, `san-lib`, `san-obj`; referenced by `t17_install.sh` | ASK USER |
| `~/t18-stage` | 76 M | in use by T18 | KEEP |
| `~/t17-docs` | 624 K | diffs of CLAUDE.md and proof, `tex/`; unreferenced | ASK USER |
| `~/problem1`, `~/run.sh`, `~/slurm-*.out` | tiny | unrelated | leave |

## 6. `~/incoming` (750 M; reported, no judgment)

| entry | mtime | note |
|---|---|---|
| `nvbit/` | 2026-09-28 10:59 | 750 M: `1.7.1/`, `1.8/` (extracted), the two `.tar.bz2` (0.6 and 0.9 MB), `releases.json`, `work/` (mtime 09-28 14:34; T13's spike work dir) |
| `ecl/ECL-Suite-main.tar.gz` | 2026-09-28 17:01 | 40 KB |

## 7. Plan

Space accounting: current 37.8 G.

| path | size | readers | action | recovered |
|---|---|---|---|---|
| `traces_keep.prefix_fe694b5` | 3.7 G | none by name | move + symlink to BeeGFS | 3.7 G |
| `traces_keep` | 3.1 G | see 3 | move + symlink | 3.1 G |
| `traces_keep.prefix_36a93d08` | 2.8 G | none by name | move + symlink | 2.8 G |
| `traces_keep_evcand` | 970 M | `p_evcand.sh` | move + symlink | 0.97 G |
| `traces_keep_fpfix_tr` | 673 M | `p_fpfix_tr.sh` | move + symlink | 0.67 G |
| `traces_keep_fpfix` | 572 M | `p_fpfix*.sh` | move + symlink | 0.57 G |
| `corpora` | 1.3 G | build scripts | move + symlink (regenerable via `build_corpora.py`, but moving is cheaper) | 1.3 G |
| `setup/tools/supercollider-artifacts-v1.zip` + NVBit tarballs | 160 M | unpacked copies exist | move + symlink | 0.16 G |
| `setup/tools/iGUARD-SOSP21`, `supercollider`, `hirace_venv`, `HiRace` | 1.45 G | run scripts | ASK USER (a venv moved by symlink is probably fine since nodes see home, but not checked) | 0 |
| `bin`, `confirm*`, `build`, `.env`, `third_party`, `store_index`, `oracle_pi` | | | keep | 0 |
| `~/.accel_scratch` | 14 G | none in repo | ASK USER (Sep 10 scratch from Phase 4); proposed: move + symlink to BeeGFS, or delete if the user says it is disposable | 14 G |
| `~/.cache/pip` | 334 M | | `pip cache purge` (base and `.env`) | 0.33 G |
| `miniconda3/pkgs` | 1.0 G | | `conda clean -a -y` | up to 1.0 G (not measured) |
| `~/.nv/ComputeCache` | 41 M | | rm (regenerates) | 0.04 G |
| `~/.debug` | 786 M | | ASK USER | 0 |
| `wt-proof` | 103 M | | `git worktree remove` | 0.10 G |
| `wt-T1a`, `wt-T3`, `wt-T6` | 380 M | | remove with `--force` after user OK | 0.38 G |
| other worktrees, stage dirs, `incoming`, `rt-prev` | | | ASK USER / KEEP | 0 |

Totals (G): the "without `.accel_scratch`" set (6 trace dirs 11.85, corpora 1.3, tools 0.16, pip 0.33, ComputeCache 0.04, 4 worktrees 0.48) = 14.2 G, plus up to 1.0 G for conda.
Projected: 37.8 - 14.2 = 23.6 G, or about 22.6 G if conda clean recovers 1 G. That is under the 25 G bar, narrowly, without touching `.accel_scratch`. With `.accel_scratch` moved: about 8.6-9.6 G. If the user wants to leave the worktrees alone, the no-scratch figure is about 24.1 G, still under 25.
The BeeGFS mount was not checked in Phase 1 (not mounted on the login node; no `srun` was run).

## 8. Phase 2 commands (not run)

Run on a node with BeeGFS (`srun -p normal -n 1 -t 04:00:00 --pty bash`).
```
A=/mnt/beegfs/$USER/home_archive/eval_baselines; B=/home/fzheng4/AccelProf/eval/baselines
mount | grep -i beegfs; mkdir -p $A
for d in traces_keep.prefix_fe694b5 traces_keep traces_keep.prefix_36a93d08 traces_keep_evcand traces_keep_fpfix_tr traces_keep_fpfix corpora; do
  rsync -a $B/$d/ $A/$d/
  test -z "$(rsync -a --checksum --dry-run --itemize-changes $B/$d/ $A/$d/)" || exit 1
  [ "$(find $B/$d -type f | wc -l)" = "$(find $A/$d -type f | wc -l)" ] || exit 1
  # mirror meta.json files into store_index/<tag>/ first (traces_keep* only), per T0 step 5
  mv $B/$d $B/$d.moving && ln -s $A/$d $B/$d
  # reader check: parallel.py analyze --results-dir /tmp/$USER/hcheck --confirm-dir confirm on 3 ids from traces_keep
  rm -rf $B/$d.moving
done
# setup/tools zip + tarballs: same pattern into $A/setup_tools/
# worktrees (from the main checkout, user-approved ones only):
git worktree remove ../wt-proof; git worktree remove --force ../wt-T1a ../wt-T3 ../wt-T6; git worktree prune
conda clean -a -y; pip cache purge; /home/fzheng4/AccelProf/.env/bin/pip cache purge; rm -rf ~/.nv/ComputeCache
# ~/.accel_scratch: only on the user's word, same rsync / verify / symlink pattern into /mnt/beegfs/$USER/home_archive/accel_scratch
```
Phase 3 (regrowth guard): `_keep_trace` default destination to `/mnt/beegfs/$USER/cuvein_traces/keep/<tag>`, and a 35 GB home-usage check in the `p_*.sh` preamble.

## 9. Not measured

`study-nvbit-spike` size; conda clean recovery; BeeGFS mount and space; whether `store_index/evcand` mirrors `traces_keep_evcand`; whether moved venvs work through a symlink.

Phase 2 not run -- awaiting go-ahead.

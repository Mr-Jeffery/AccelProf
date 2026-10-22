**Runtime (every result below).** Install commit `f551ca0` (cuVein, merged into this branch as `9e29b3f`): libsanalyzer `5a20fd14ab6c6806`,
collector `b746b4dd23e90f46`, fatbin `a2d7368bc1c61986` (late fatbin `e96343121c74ca0a`). The hashes were verified on the compute node by
prep job 317627 (c26) and again at the top of every recall job (exit 99 on a mismatch); each `meta.json` of the store
`/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10/<id>/` carries them under `t21b.runtime`. Oracles: commit `bc71082`, read, never edited.
Pre-T24 outputs of the first attempt were moved to `/mnt/beegfs/fzheng4/realworld/pre-t24-discarded/` before any new result was written.

**Status at this writing: partial.** Not all 28 targets are scored; the rows below are what has run. Pending and open items are in 2.4.

**Configuration** (X1b's, with shards): `harness/recall_job.sh`; one job per target variant pair, both modes (vector-clock then scalar-clock)
per id, 16 CPUs (`nproc` = 16, so `YOSEMITE_HB_SHARDS=16` for the scalar-clock sync pass; the script would take 32 at nproc >= 64),
`BASELINE_HB_DUMP=0`, `YOSEMITE_HB_STATS=1`, `--confirm`, `--reps 1`, `--timeout-cap 1200`, `--analysis-timeout 3600`, atomic-scope sidecar via
`accelprof -n 1` (parallel.py), CUDA 13.3 toolchain for the sanitizer (`/usr/local/cuda-13.3`), artifacts relinked with `--cudart shared`
(manifest `eval/realworld/manifest_t21b.csv`; llamacpp excepted). Results `eval/results/realworld/`, confirm files `eval/baselines/confirm_realworld/`.
`certain` flavor (`YOSEMITE_HB_GATE_POLICY=certain`, vector-clock only) for `cccl-3`, `raft-1`, `cmssw-1`; `vc5400` flavor for timeouts.
Attribution: `harness/rw_attribute.py` (kernel-aware, after the alignment stage, `nvdisasm --print-line-info-inline` of the loaded cubin,
inlined frames included; the regenerated CFG equals the stored dot where `dots equal` is reported). Scoring: `harness/rw_score.py`;
pair table `eval/realworld/recall_pairs.json`; queue `eval/realworld/triage_queue.md`.

**Defects and facts found while running (harness-side; nothing under `python/`, `sanalyzer/`, `nv-compute/`, `bin/` was touched).**
1. `llamacpp-2/-4/-5`: `parallel.py`/`run_cuvein.py` split the manifest `args` on whitespace without a shell, so the single quotes of
   `-p '...'` reached `test-backend-ops` literally and the filter matched no test ("0/0 tests passed" in the native line of the first run: no kernel
   launched, status ERROR `no-kernel-json`). Fixed in `manifest_t21b.csv` and `mk_manifest_t21b.py` (quotes removed; the strings contain no
   spaces); the first-run rows of these three targets are void and were re-queued (2.4). This is a driver defect (cause m1 class), not a detector one.
2. Attribution of runs with thousands of kernel launches is the slowest step: it re-runs `sync_dominance.analyze` over every kernel JSON of both modes
   and calls `nvdisasm` on whole cubins. `raft-1-buggy` took about 4 h 40 min, `amrex-1-buggy` and `hecbench-hungarian-1-buggy` (1,246 and about
   6,900 kernel JSONs) had not finished at the 5 h job limit. For runs whose status is ERROR or TIMEOUT the attribution is not needed for scoring (not scored).
3. `lit-fbgemm-1` (miss, 2.2): the pair reported at pcs `0x27d0` (LDS) and `0x2b00` (STS) is the pair the oracle's own SASS note lists
   (`LDS at 0x27d0 (first copy)`, `STS at 0x2b00 (second copy)`), but `nvdisasm --print-line-info-inline` attributes both pcs to
   `sm_30_intrinsics.hpp:439 <- fast_gemv.cuh:65 <- fast_gemv.cu:149`, not to `fast_gemv.cu:141/145`; by the brief's line rule it scores MISSED. Queued
   for triage as an attribution (line-table) question, not as a detector miss. The oracle SASS offsets are the builder's and were not re-checked by the reviewers.
4. BeeGFS: from about 06:00 on 2026-10-22 newly allocated nodes (c26, c40, c41, c43, c56, c61, c62, c63, c76, c77) reported
   `/mnt/beegfs/fzheng4` missing at job start (the header exits 97 with the hostname); several of these had worked at 02:14. Jobs submitted through
   `harness/recall_retry.sh` re-queue themselves without the node (list in `eval/x_logs/bad_nodes.txt`). c26 carries a second GPU (RTX 2060); the
   job selects the sm_89 device (`CUDA_VISIBLE_DEVICES`).
5. A second helper replaced `recall_job.sh` in place while array 317630 tasks 0-6 ran; tasks 2, 3, 6 exited non-zero in the loop's tail. Detector runs and
   attribution of the ids they had finished are unaffected (task 6 = `kokkos-6`: both ids complete).


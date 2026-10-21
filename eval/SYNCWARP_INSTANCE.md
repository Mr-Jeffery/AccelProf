# T24 — a diverged WARPSYNC is one warp-barrier instance (DRAFT, in progress)

Branch `fix/syncwarp-instance` from `cuVein` 38af04e, worktree `/home/fzheng4/wt-t24`. Unmerged; the
runtime is not installed (a private build in `/home/fzheng4/stage-t24`, see §6). Nothing under
`nv-compute/` changes. Legend as in CLAUDE.md A4: **proved-in-effect** (an invariant checked over N real
traces), **tested** (a specific verdict asserted), **assumed/unverified**.

Status of this draft: steps 1–3 and 5 done; step 4 (parity) and step 6 (timing) running.

## 1. The test (step 1) — tested

- `python/testdata/syncwarp_diverged_waw.cu`: X5b's counterfactual as a kernel of its own. The shape of
  ECL-CC's `cc_vertex_data`: lane 0 clears `updated[warp]`, lane 16 sets it, every lane reads it after a
  `__syncwarp()`. The first `__syncwarp()` is removed; the remaining one sits inside a two-round loop
  (`lanes 0..15` in round 0, `16..31` in round 1, one call site), so the warp reaches it diverged.
- `python/testdata/syncwarp_converged_clean.cu`: the same with the first `__syncwarp()` put back
  (converged): the positive control.
- SASS on sm_89 (probe job 316786, c62): the `__syncwarp()` compiles to `BRA.CONV ~URZ` + `CALL.REL.NOINC`
  to the helper `WARPSYNC 0xffffffff` (0x2c0) + `NOP` (0x1c0), the shape X5b found in ECL-CC. Records per
  warp: syncwarp 0x2c0 active `0x0000ffff`, lane 16's set, syncwarp 0x2c0 active `0xffff0000`, syncwarp
  0x1c0 active `0xffffffff` (converged after the helper). **2 records per diverged instance in all 8
  warps.**
- `python/test_syncwarp.py`: 11 synthetic cases (oracle against `barrier_only_pairs`) and 10 GPU cases
  (both kernels, both modes).

| run | runtime | result |
|---|---|---|
| job 316788 (c63), 38af04e + the test | installed (libsanalyzer `a01c16667b592e5d`) | **11 failed**, 9 passed, 1 skipped — the WAW is reported in neither mode |
| job 316792 (c63), the fix | private (libsanalyzer `d8c5d656394f3e01`) | **20 passed, 1 skipped** |

The skip is by design (the specification is compared on the vector-clock recording).

## 2. The change (steps 2, 3)

(to be completed)

## 3. Parity (step 4)

(running)

## 4. The 60 recordings of X5b §4 (step 4)

(pending)

## 5. Timing (step 6)

(pending)

## 6. The proof paragraph (step 5) — awaiting Jeffery's check

In `design/proof/hb_proof.tex` (Definition "Instances", the paragraph "Warp barriers (T24)", Algorithm 1's
syncwarp line).

## 7. What remains unverified

(to be completed)

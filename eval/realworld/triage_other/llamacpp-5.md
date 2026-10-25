# llamacpp-5: T21c step 3 triage of 512 other reports (1 group)

repo ggml-org/llama.cpp | buggy 039e20a2db9e87b2477c76cc04905f3e1acad77f | fixed fb83cc9a072b4e85b329d4f95c59478180204c87.

The oracle race (targets.jsonl race_description) names two hazards in `ssm_scan_f32`:
1. BlockLoad TempStorage reuse at ssm-scan.cu L69-70.
2. smemB/smemC at L87-88 vs L103-104.

Result: 1 group / 512 rows class (c), harness. The reports are hazard (1) itself, not a separate race.

Evidence used:
- `ggml/src/ggml-cuda/ssm-scan.cu` at both commits. The fix adds `__syncthreads()` at fixed L70 (between the Loads) and
  L109, and removes the unused dynamic smem.
- CUB headers: the frames name `/usr/local/cuda-13.4/targets/x86_64-linux/include/cccl/cub/...` (CUB_VERSION 300403).
  The lines match 13.4: block_load.cuh:1001 is the `WarpStripedToBlocked` call in 13.4 and a closing brace in 13.3.
- SASS: `dots/ssm-scan.sm_89.dot`, kernel `ssm_scan_f32<128,16,0>`, both builds.
- Thread ids: `vector-clock/kernel_0.json` `hb_races`. Grid 4x8, 128 threads, tid = block x 1024 + thread.
- Attribution: `attrib/llamacpp-5-{buggy,fixed}.json`.
- Scoring: `eval/realworld/harness/rw_score.py`, `eval/realworld/recall_pairs.json` and `eval/realworld/oracle/llamacpp-5.json`.

## llamacpp-5#01: uninitialized_copy.cuh:37 vs uninitialized_copy.cuh:37 (512 rows: buggy 256 VC + 256 SC)

Accesses (shared, `BLOCK_LOAD_WARP_TRANSPOSE`, float x 16 items):

- A, LDS: uninitialized_copy.cuh:37 `*ptr = val`, from block_exchange.cuh:537 (the read-out loop of
  `WarpStripedToBlocked`, `output_items[i] = temp_storage.buff[warp_offset + i + lane_id*16]`), :999, block_load.cuh:1001,
  then ssm-scan.cu:69 (first `BlockLoad(...).Load(A_block, regA)`).
  - SASS: 16 `LDS` at 0x730-0x820.
- B, STS: uninitialized_copy.cuh:37, from block_exchange.cuh:524 (the scatter loop, `temp_storage.buff[warp_offset +
  i*32 + lane_id] = input_items[i]`), :999, block_load.cuh:1001, then ssm-scan.cu:70 (second Load, `s0_block` to
  `regs0`).
  - SASS: 16 `STS` at 0x850-0x940.
- The 256 distinct pc pairs are the 16 x 16 LDS x STS combinations. Every row is shared WAR, DR. Buggy only: the fixed
  attribution has 0 reports in both modes.

Thread relation: same warp in all 256 vector-clock entries (dist warp, `a2_uncertain` 0). Example: block 7 thread 97
(warp 3, lane 1) `LDS` item 0 at 0x730 vs block 7 thread 112 (warp 3, lane 16) `STS` item 0 at 0x850, same smem word,
count 128.

What orders them, or fails to:
- Inside each Load, `__syncwarp(0xffffffff)` (block_exchange.cuh:527) separates that Load's STS from its LDS. The SASS
  shows a `NOP` at that position (0x720, 0x950).
- Between the first Load's last LDS (0x820) and the second Load's first STS (0x850) there are only two `ISETP`. There
  is no `BAR`, `WARPSYNC` or shuffle; the kernel's first `BAR.SYNC` is at 0xcc0 (ssm-scan.cu:90).
- Under independent thread scheduling, lanes of one warp are not ordered, so this is a DR. The code is warp-synchronous;
  CUB's contract requires `__syncthreads()` before TempStorage is reused.
- The fixed build has `BAR.SYNC` at 0x830 (fixed ssm-scan.cu:70) between the two Loads.

Why this is not a new race, and why it is in other_reports:
- targets.jsonl `race_description` lists this hazard as part (1) of the oracle race. oracle/llamacpp-5.json records it
  too, in `thread_pair_example`, in `buggy_expected` ("may appear as additional DR hazards in cub files") and in
  `open_questions` ("a second racing pair of the same target and not in the two sites above").
- But `recall_pairs.json["llamacpp-5"]` has only one pair, smemB/smemC store L87-88 vs load L103-104, plus its fixed
  equiv. `rw_score.py` puts every report that matches no pair into other_reports.csv (lines 230-238).
- The reports' own chains contain ssm-scan.cu:69 (A) and ssm-scan.cu:70 (B). `rw_score.match` walks all inlined frames
  with TOL = 2, so a pair `A=[["ssm-scan.cu",69,69]]`, `B=[["ssm-scan.cu",70,70]]` would match all 512 rows. It would not
  match the smemB/smemC reports (frames L87/L103).
- So these reports are the oracle race seen through CUB's inlined frames, and their absence from the score is a
  pair-table defect.

Class (c), harness (scoring data), not detector:
- The race itself is real: a DR, same warp. Concrete pair: block 7 t97 reads `temp_storage.buff` in Load #1 (L69); block
  7 t112 overwrites the same word in Load #2 (L70).
- The source fix is the upstream one: `__syncthreads()` between the two Loads.

## Defects

### D-llamacpp5-1, class (c), harness: recall_pairs.json omits oracle hazard (1) (512 rows)

Minimal input: any target whose pair table registers only one hazard while the kernel also contains:

```cuda
#include <cub/block/block_load.cuh>
__global__ void k(const float *a, const float *b, float *out) {
  using BL = cub::BlockLoad<float, 128, 16, cub::BLOCK_LOAD_WARP_TRANSPOSE>;
  __shared__ typename BL::TempStorage ts;
  float x[16], y[16];
  BL(ts).Load(a, x);   // line N
  BL(ts).Load(b, y);   // line N+1: reuses ts with no __syncthreads()
  float s = 0.f; for (int i = 0; i < 16; ++i) s += x[i] * y[i];
  out[blockIdx.x * 128 + threadIdx.x] = s;
}
```

- cuVein reports the LDS(N) / STS(N+1) WAR, with chains ending in `block_load.cuh:1001 <- k.cu:N` and `<- k.cu:N+1`.
- Without a pair for N vs N+1, rw_score.py files these reports under other_reports.csv.
- Fix (not applied, read-only): add the pair below to `recall_pairs.json["llamacpp-5"]`. Its `role` (primary or family)
  is Jeffery's scoring call.

  ```json
  {"name": "BlockLoad TempStorage reuse L69 vs L70", "cls": "DR",
   "A": [["ssm-scan.cu", 69, 69]], "B": [["ssm-scan.cu", 70, 70]]}
  ```

- For the fixed build, an `equiv` would cover L69 vs L71, the second Load after the inserted barrier (inferred from the
  fix diff). None is expected, because the fixed build has 0 reports.

### Note: attribution `cuda_home` is wrong for llamacpp-5 (metadata only)

- `attrib/llamacpp-5-{buggy,fixed}.json` and `meta.json` say `cuda_home` = `/usr/local/cuda-13.3`.
- The build's `cmake-configure.txt` shows `/usr/local/cuda/bin/nvcc`, "The CUDA compiler identification is NVIDIA
  13.4.92", and `ldd` resolves libcudart from `/usr/local/cuda-13.4`.
- The line table names the cuda-13.4 CUB headers.
- Header lines for this target should therefore be read from 13.4, not 13.3. This does not change any verdict.

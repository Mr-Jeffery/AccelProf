# lit-exllamav3-1: triage of 4 other reports in 2 groups

repo turboderp-org/exllamav3 | buggy 0c4804c4 | fixed 3daf2d5d | file `exllamav3/exllamav3_ext/routing.cu` | kernel `routing_std_kernel`

**Result:** both groups (4 rows) are class (a), DR, same-value, high confidence. They are one source statement:

- #01 is the buggy build, at L634.
- #02 is the fixed build, at L640. The fix's first two hunks add 4 + 2 lines above it, so the statement moves; it is otherwise unchanged.

This is not the oracle race. The oracle is the stage-loop and `max_red`/`sh_v` aliasing WAR.

## Shared mechanism

**Source.** At buggy L628-L639; at fixed, the same lines shifted by +6:

```
half max_logit = t < num_experts ? scores[t] : __ushort_as_half(0xfbff);
max_logit = warp_reduce_max_h(max_logit);
max_logit = __shfl_sync(0xffffffffu, max_logit, 0);      // L630: every lane gets lane 0's max
if (num_warps > 1)
{
    max_red[warp_id] = max_logit;                         // L634 (fixed: L640)  <- both accesses
    __syncthreads();
    ...
```

- `max_red = sh_v` aliases dynamic shared memory (L620, L623).

**SASS.** From `dots/driver.sm_89.dot`, `_Z18routing_std_kernelPK6__halfPlPS_PK13__nv_bfloat16iii`. It is identical on both builds up to 0x2f0:

```
0220: SHFL.IDX PT, R2, R2, RZ, 0x1f        ; __shfl_sync(..., 0)
0250: PRMT R6, R2, 0x7610, R6              ; R6 = broadcast max_logit
0260: SHF.R.S32.HI R2, RZ, 0x5, R3         ; warp_id
0290: @!P0 BRA (.L_x_499)                  ; num_warps > 1 test
02a0: IMAD.SHL.U32 R7, R2, 0x2, RZ         ; &max_red[warp_id] (half)
02d0: STS.U16 [R7], R6                     ; unpredicated: all 32 lanes store
02f0: BAR.SYNC.DEFER_BLOCKING 0x0          ; L635 __syncthreads
```

**Thread relation.** From `vector-clock/kernel_2.json` `hb_races`. The tid encoding is `loc_block*1024 + threadIdx.x` (inferred from loc_block and addr).

- **Buggy:** a_tid 3168 and b_tid 3169, which are block 3 threadIdx 96 and 97, i.e. warp 3 lanes 0 and 1.
  - Entry: addr 6 = `max_red[3]`, kind WAW, class DR, dist = warp, count 15872, a2_uncertain 0.
- **Fixed:** a_tid 3136 and b_tid 3137, which are block 3 threadIdx 64 and 65, i.e. warp 2 lanes 0 and 1.
  - Entry: addr 4 = `max_red[2]`, WAW, DR, dist = warp, count 15872, a2_uncertain 0.
- **Count:** 15872 = 32 warps (4 blocks x 8) x C(32,2) = 32 x 496. Every lane pair of every warp is reported.
- **sc rows:** the scalar-clock JSONs have no `hb_races`; the sc rows are the same pc pair from the scalar matrix.

**What orders them.** Nothing does.

- The two accesses are the same dynamic STS.U16 executed by two lanes of one warp.
- The `__shfl_sync` (SHFL.IDX at 0x220) comes before both stores and the `__syncthreads` (0x2f0) comes after both, so neither orders one lane's store against another's.
- Both stores are weak (plain STS.U16).
- PTX §8.7.1: these are two conflicting writes by different threads that are not morally strong and not ordered by causality order, so this is a data race.
- The stored values are equal in every lane: R6 is lane 0's value broadcast by `__shfl_sync(0xffffffffu, max_logit, 0)`. So it is a same-value WAW race. It is harmless on current hardware, but it is still a DR under PTX.

## lit-exllamav3-1#01: routing.cu:634 vs routing.cu:634 (2 rows: buggy/ve, buggy/sc)
- **Accesses:** A and B are both routing.cu:634 at 0c4804c4, `max_red[warp_id] = max_logit`. STS.U16 at pc 0x2d0, shared, WAW.
- **Threads:** block 3 threadIdx 96 and 97 (warp 3 lanes 0 and 1). Same warp, same block, dist = warp.
- **Ordering:** none (see above).
- **Class:** (a) DR, same-value.
- **same_in_fixed:** yes. The identical pc pair (0x2d0/0x2d0, same statement) is reported on the fixed build as #02 at L640.
- **Pair:** t96 and t97 of block 3 both store `max_red[3]`.
- **Fix:** `if (lane_id == 0) max_red[warp_id] = max_logit;`

## lit-exllamav3-1#02: routing.cu:640 vs routing.cu:640 (2 rows: fixed/ve, fixed/sc)
- **Accesses:** A and B are both routing.cu:640 at 3daf2d5d, the same statement as buggy L634. STS.U16 at pc 0x2d0, shared, WAW.
- **Threads:** block 3 threadIdx 64 and 65 (warp 2 lanes 0 and 1). Same warp, same block, dist = warp.
- **Ordering:** none.
  - The upstream fix adds a `__syncthreads()` after L644 (fixed numbering), which orders the `max_red[lane_id]` reads before the later `sh_v` writes.
  - It does nothing about the multi-lane store at L640.
- **Class:** (a) DR, same-value.
- **same_in_fixed:** yes. This group is the fixed-build occurrence, and the same pair is #01 on buggy.
- **Pair:** t64 and t65 of block 3 both store `max_red[2]`.
- **Fix:** `if (lane_id == 0) max_red[warp_id] = max_logit;`

## Defects
None. No group is class (c).

## Notes
- **Sources:**
  - `~/t21c_triage/lit-exllamav3-1.md`.
  - `attrib/lit-exllamav3-1-{buggy,fixed}.json`; buggy is cuda-13.3 and fixed is cuda-13.4.
  - `realworld-2026-10/lit-exllamav3-1-{buggy,fixed}/vector-clock/kernel_2.json`.
  - `dots/driver.sm_89.dot`.
  - `exllamav3.git` at both commits.
- **Inferred:** the tid encoding and the "harmless on current hardware" remark.

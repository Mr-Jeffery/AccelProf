# T21c triage: droidslam-new-1 (DROID-SLAM 2dfd39f0dcad44012ca7bbb8aa70b55edbfa9c99, `frame_distance_kernel`)

Inputs: `eval/results/realworld_t21c/attrib/droidslam-new-1-buggy.json` (scalar-clock, 1 kernel JSON, 67 reports, 0 SC, 18 ordered,
151 skipped; dot equal to the regenerated dot), `other_reports.csv` (7 rows), `recall.csv` (SC component DETECTED-AS-DR),
racecheck `eval/realworld/racecheck/droidslam-new-1-buggy.txt`, SASS of the traced build
(`/mnt/beegfs/fzheng4/realworld_t21c/build/droidslam-new-1/buggy/driver`, md5 9223004c08a9ae7caf24f78346d44091, `nvdisasm -g -c`, CUDA 13.3),
trace edges of `cuvein_traces/realworld-2026-10-t21c/droidslam-new-1-buggy/scalar-clock/kernel_0.json`.
Launch: `frame_distance_kernel<<<6, 256>>>`, 4 frames 48x64 (12 pixel iterations per thread).

## Groups

| # | kernel | pcs (a -> b) | file:line pair | n | class | reason |
|---|---|---|---|---|---|---|
| G1 | frame_distance_kernel | 0x1960..0x1aa0, 0x1be0..0x1d20, 0x1e60..0x1fa0 (20 pairs per blockReduce call, 3 calls) | droid_kernels.cu:46..51 x 46..51 (warpReduce, inlined via L62 from L657/L658/L659); 18 RAW (step k store -> step k+1 load), 42 WAR (step k load -> later-step store) | 60 | **(a)** | intra-warp (warp 0 of every block), no `__syncwarp`/WARPSYNC between the steps; volatile = plain LDS/STS on sm_89 (DR per D20). Oracle pair L46->L47 is in this group. Finding `findings/droidslam-new-1.md` |
| G2 | frame_distance_kernel | 0x7d0, 0x810, 0x850, 0x870, 0x880, 0x890 (each with itself) | droid_kernels.cu:107, 109, 110, 113, 114, 115 (relSE3 via L591), WAW | 6 | **(a) benign/same-value** | every thread of the block writes the same `qij[0..3]`, `tij[0..2]` (shared, L551) computed from the same shared inputs; cross-warp, no barrier between threads' stores; no thread reads them back from shared (SASS: no LDS of 0xc50..0xc68) |
| G3 | frame_distance_kernel | 0x8b0 -> 0x1840 | droid_kernels.cu:608 (LDS.128 [0]: ix, jx, fx, fy, hoisted load of `ix` for L611) -> droid_kernels.cu:651 (STS.64 [0]: thread 0's swap of ix/jx, L648-L652), WAR | 1 | **(a)** | cross-warp, same block: thread 0 swaps `ix`/`jx` after its own pixel loop with no barrier between the loop and the swap; a thread of another warp that has not yet loaded `ix` reads the swapped index. New race, finding `findings/droidslam-new-1-2.md` |

Totals: 67 reports, 67 class (a) (of which 6 benign/same-value), 0 (b), 0 (c), 0 (d). Two distinct real races: G1 (the oracle's,
warp-synchronous) and G3 (new, cross-warp). The 7 `other_reports.csv` rows are G2 (6) and G3 (1).

No report matches the known LDS vs ATOMS.CAST.SPIN false-report class (no atomics in this kernel).

## G1: warpReduce (the oracle race)

`blockReduce` (L54-L64) ends with `if (tid < 32) warpReduce(sdata, tid);` and warpReduce (L45-L52) does six
`sdata[tid] += sdata[tid + k]` (k = 32..1) on a `volatile float*`, executed by all 32 lanes of warp 0 (no `tid < k` guards).
Thread pair: block 0, thread 16 stores `sdata[16]` at L46 (`sdata[16] += sdata[48]`) and thread 0 loads `sdata[16]` at L47
(RAW); thread 0 loads `sdata[16]` at L47 while thread 16 stores `sdata[16]` at L47 (WAR). Same warp, same block. Nothing orders
them: the last barrier is the `__syncthreads()` at L60, the next one is at L63; there is no `__syncwarp`, shuffle or fence in
between. racecheck reports exactly this pair ("Warp Level Programming" warning, Write Thread (16,0,0) L46, Read Thread (0,0,0)
L47, block (0,0,0)); its 2,000 displayed hazards are all L46..L51 pairs. Trace edges for these pcs are all `intra_warp`.

SASS (traced build, per call): `LDS [R13.X4+off]`, `LDS [R13.X4+off+4k]`, `FADD`, `STS [R13.X4+off]` for each of the six steps:
12 LDS + 6 STS, i.e. every volatile load and store is kept, all plain (no `.STRONG`). No `WARPSYNC` inside; `BSSY B0` before the
`tid < 32` branch and `BSYNC B0` after L51; the only `WARPSYNC 0xffffffff` in the kernel is at 0x17d0 (lowering of the
`__syncthreads()` at L654). Warp 0 takes the `tid < 32` branch as a whole, so on this build the six steps execute converged.

Class: (a). Under PTX §8.7 the lanes of a warp are unordered without `bar.warp.sync` or a barrier. At the PTX source level the
accesses are `ld.volatile`/`st.volatile` (strong), so the record's `expected_class` is SC; the SASS has plain LDS/STS and the
frozen detector reports DR (D20), hence DETECTED-AS-DR in `recall.csv`. Observability: formal only on this build; see the
dossier for the perturbation design (faithful insertion predicted correct; forced divergence predicted wrong).

## G2: relSE3 stores (benign, same value)

`relSE3(ti, qi, tj, qj, tij, qij)` (L591, called by all 256 threads) writes the shared `qij[4]` and `tij[3]`. All inputs are
shared values written before the barrier at L588, and every thread runs the same instruction sequence, so every thread stores
bit-identical values. The stores (STS [0xc5c], STS.64 [0xc60], STS [0xc68], STS [0xc50], [0xc54], [0xc58]) have no barrier
between threads; the trace edge for 0x7d0 shows 1,488 same-instruction pairs and 42 `intra_block` (cross-warp) pairs. The
intermediate `tij = R*ti` of actSO3 (L112) is not stored (ptxas keeps it in registers), and no thread reads `qij`/`tij` back
from shared (they stay in registers for the loop). Class (a) under PTX (conflicting plain stores, unordered), benign/same-value.
Not a new finding.

## G3: ix/jx swap (new)

`for (int n=0; n<1; n++) { ... GPU_1D_KERNEL_LOOP(k, ht*wd) { ... Xi[3] = disps[ix][i][j]; ... } if (threadIdx.x == 0) { tmp = ix; ix = jx; jx = tmp; } __syncthreads(); }`
(L576-L656). In SASS the shared `ix` (offset 0) is loaded once per thread by `LDS.128 R4, [RZ]` at 0x8b0, right after relSE3 and
before the pixel loop (R4 = ix feeds `IMAD R23, R4, c[0x18c]`, the disps row offset); thread 0 stores the swapped pair with
`@!P2 STS.64 [RZ], R4` at 0x1840, after its loop and before `BAR.SYNC` at 0x1850. Between the barrier at L588 (0x4e0) and
0x1840 there is no barrier. Thread pair: block b, thread 0 (warp 0) stores `ix` at L651 vs thread 32 (warp 1) loads `ix` at
L608/L611. Different warps, same block. The trace edge 0x8b0 -> 0x17c0 (thread 0's `LDS.64 [RZ]` of L649) is `intra_block` (6,
one per block), confirming that other warps' reads and thread 0's swap touch the same words with only program order between
them in the trace. Class (a), DR (both plain). Formal under normal scheduling (warp 0 would have to finish 12 pixel iterations
before warp 1 executes about 60 instructions after the barrier), but not lock-step dependent: a delay of warps 1-7 produces
wrong distances. racecheck reported 0 errors for the run (18,591 warnings, displayed ones all warpReduce), so racecheck did not
flag this pair as an error in that run.

## Not checked

The other kernels that use blockReduce (projective_transform_kernel, EEt6x6_kernel, Ev6x1_kernel) were not traced (the driver
launches frame_distance_kernel only). Vector-clock mode was not run (Jeffery's instruction), so per-report thread ids come from
racecheck and the source, not from cuVein.

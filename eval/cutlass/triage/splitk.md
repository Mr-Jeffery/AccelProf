# Split-K serial triage (K1–K5, CUTLASS v4.8.1, sm_89 unit tests)

Source: `/home/jeffery/x9-cutlass-v4.8.1` (tag v4.8.1). Paths below are relative to `include/cutlass/` unless they start with `test/`.
Pair data: all of `wt-x9/eval/results/cutlass/pairs/{main,t5400}/*.json` was scanned. Every pair of K1–K5 is CONFIRMED, and both halves (`on` and `off`) give the same verdict and class.
Script: `scratchpad/sk/scan.py`.

## Verdict

| cluster | pcs (innermost) | pairs / kernels | kernel path (frame) | class |
|---|---|---|---|---|
| K1 | `semaphore.h:76` × `:106`, `106 × 106` | 98 + 50 / 50 | `Semaphore::fetch` / `release` in all four kernel types | **not (a)**. All accesses are morally strong (`LDG.E.STRONG.GPU` / `STG.E.STRONG.GPU`). `106×106` and the observing reads are also causality-ordered → **(b)**. The other spin reads are unordered but morally strong, so they are no race under §8.7.1. This is the informational SC output (D12), not a finding. |
| K2 | `arch/memory.h:153` × `:415`, `415 × 415` | 904 + 904 / 45 | default `Epilogue` source load (`predicated_tile_iterator.h:356/385`, `epilogue.h:273`) × store (`:447/481`, `epilogue.h:534`). Called at `conv/kernel/implicit_gemm_convolution.h:425`, `gemm/kernel/gemm.h:351`, `gemm/kernel/gemm_sparse_universal.h:770` (also `epilogue_with_broadcast.h`, `epilogue_with_reduction.h` in the fused conv kernels) | **(b)** |
| K3 | `arch/memory.h:85` (32 B load) × `:396` (32 B store), `396 × 396` | 96 + 96 / 3 | same epilogue, `implicit_gemm_convolution.h:425` | **(b)** |
| K4 | `arch/memory.h:204` (8 B load) × `:431` (8 B store), `431 × 431` | 64 + 64 / 1 | same epilogue, `implicit_gemm_convolution.h:425` (simt) | **(b)** |
| K5 | `epilogue/threadblock/epilogue_direct_store.h:260` × `:268`, `268 × 268` | 64 + 64 / 1 | `EpilogueDirectStore::compute_source_needed_` called at `gemm/kernel/gemm_universal.h:668` | **(b)**. This is the same split-K serial hand-off, not an overlapping-tile pattern (see K5) |

**(b) mechanism, same for K1–K5.** CUTLASS's `Semaphore` hands each tile from k-slice *i* to slice *i+1* in three steps:
1. In the releasing CTA, `bar.sync` runs, then thread 0 issues a **non-RMW** `st.release.gpu`.
2. In the next CTA, thread 0 spins on a **non-RMW** `ld.acquire.gpu` until it reads exactly *i+1*.
3. All threads of that CTA then pass `bar.red.and` and `bar.sync`.

SASS for the sequence: `BAR.SYNC; MEMBAR.ALL.GPU; ERRBAR; STG.E.STRONG.GPU` → `LDG.E.STRONG.GPU; CCTL.IVALL` → `BAR.RED.AND…; BAR.SYNC`. cuVein's model creates synchronization edges only between RMWs ((ATOM)) and only lets R3 chains start from RMWs. So this hand-off is invisible to it.

Pairs not covered by the semaphore: **none found** (§"Uncovered pairs").

GitHub #2775 is about this exact site, `Semaphore::release` having no `__threadfence`. It is a generic `semaphore.h` question and not specific to GemmSparseUniversal (`docs/eval/cutlass/known_fixes.md:87,102`). It was closed not_planned with no answer. The analysis below answers it: no fence is needed, and #2775 does not describe a bug.

## The synchronization (v4.8.1 source)

`semaphore.h`:
- `:64-69`: constructor. `wait_thread = (thread_id < 0 || thread_id == 0)`, so only thread 0 (`threadIdx.x == 0`) touches the lock. `state = -1`.
- `:73-81` `fetch()`: thread 0 runs `ld.global.acquire.gpu.b32 state, [lock]` (**:76**).
- `:91-97` `wait(status)`: `while (__syncthreads_and(state != status)) fetch();` (:92-93), then `__syncthreads()` (:96). Threads ≠ 0 keep `state == -1 ≠ status`, so the `and` equals thread 0's `state != status`. The loop leaves only after thread 0's acquire load has returned `status`. Calls from inside this loop appear as `semaphore.h:93` frames under `:76`.
- `:101-110` `release(status)`: `__syncthreads()` (:102), then thread 0 runs `st.global.release.gpu.b32 [lock], status` (**:106**).

Kernel use. The pattern is identical in all five kernel types:

| kernel | ctor (lock = `semaphore + m + n·grid_m`) | early `fetch()` | `iterator_C = iterator_D` if k>0; `wait(k)` | epilogue | `release(k+1 or 0)` |
|---|---|---|---|---|---|
| `gemm/kernel/gemm_universal.h` (mode `kGemm`, `grid.k()>1`) | 603 | 611 | 660-663 | 668 | 678-691 |
| `gemm/kernel/gemm.h` (`kSplitKSerial`) | 300 | 306 | 342-346 | 351 | 357-370 |
| `gemm/kernel/gemm_sparse_universal.h` (`kGemm`) | 707 | 715 | 761-765 | 770 | 780-793 |
| `conv/kernel/implicit_gemm_convolution.h` (`SplitKMode::kSerial`) | 361 | 371 | 411-415 | 425 | 431-444 |
| `conv/kernel/implicit_gemm_convolution_with_fused_epilogue.h` | 369 | 380 | 444-448 | 456-466 | 474-488 |

The last slice (`grid.k() == k+1`) releases 0, which resets the lock for the next grid. The workspace is zeroed on the host before the launch:
- `gemm/kernel/params_universal_base.h:172-194` (`cudaMemsetAsync`, :184), via `gemm/device/gemm_universal_base.h:416-417`. GemmUniversal and GemmSparseUniversal use this path; `gemm/device/gemm_sparse_universal.h:126` derives from `GemmUniversalBase`.
- `gemm/device/gemm.h:421`.
- `conv/device/implicit_gemm_convolution.h:247-270`.

**Lowering (probe, not the evaluated binary).** `triage/splitk_semprobe.cu` was compiled with CUDA 13.3, `-arch=sm_89 -O3`, against the tag's `semaphore.h`. Listing: `triage/splitk_semprobe.sm_89.sass.txt`.
- `fetch`: `LDG.E.STRONG.GPU R0,[R2.64]; CCTL.IVALL` (0x00e0, 0x0180).
- `wait`: `BAR.RED.AND.DEFER_BLOCKING 0x0,P2` in the loop (0x0130/0x01c0), then `BAR.SYNC.DEFER_BLOCKING` (0x0200).
- `release`: `BAR.SYNC.DEFER_BLOCKING` (0x02e0); `@P0 EXIT` for threads ≠ 0; `MEMBAR.ALL.GPU; ERRBAR; STG.E.STRONG.GPU` (0x0330-0x0350).

The evaluated binaries show `LDG.E.STRONG.GPU` / `STG.E.STRONG.GPU` at the K1 pcs, which matches. For example, `gemm_device_tensorop_f32_sm80-c02__k012` has `@!P1 LDG.E.STRONG.GPU R0,[R138.64]` at 0x2b30 and `STG.E.STRONG.GPU [R138.64],R205` at 0xac80. The pair records do not include the neighbouring instructions. `cuobjdump -sass` on the cluster cubins at those pcs ±0x40 would confirm `CCTL.IVALL` / `MEMBAR.ALL.GPU; ERRBAR` there.

## PTX ordering of the data pairs (K2–K5)

Let W be slice *i*'s epilogue store (weak `STG.E` / `ST.E`) by thread X. Let A be slice *i+1*'s source load (RAW/WAR), or its store (WAW), of the same element by thread Y. The chain is:

`W` -po→ `bar.sync`(X, :102) -sw→ `bar.sync`(T0) -po→ `st.release.gpu`(T0, :106) -sw→ `ld.acquire.gpu`(T0′, :76, reads *i+1*) -po→ `bar.red`(T0′, :92) -sw→ `bar.red`(Y) -po→ `A`

Each link:
- `bar.sync` / `bar.red` on barrier 0 synchronize with each other at CTA scope.
- The release/acquire pair are morally strong: both strong, both `.gpu`, same b32 location.
- The acquire reads from that release. Within one launch, value *i+1* on lock (m,n) is written only by slice *i*'s `release` (gemm_universal.h:687-691 and its analogues). The previous launch ended with the reset to 0, and kernel order separates the launches.

Base causality order is transitive across these links, so W precedes A in causality order. **The pair is ordered, not a data race.** Cumulativity across the CTA comes from the barriers in the chain. #2775's missing `__threadfence` is not needed: the `.release` itself lowers to `MEMBAR.ALL.GPU` before the store.

Two facts confirm that the reported instances are on this path:
1. Every one of the 50 kernels with a K2–K5 pair also has K1 pairs in the same record. The semaphore code runs only when `grid.k()>1` in serial mode. Counts: K2 45/45, K3 3/3, K4 1/1, K5 1/1 (`scan.py`).
2. The epilogue frame in each stack is the line between `wait` and `release` in the table above.

The test configurations select split-K serial:
- `test/unit/gemm/device/testbed_universal.h:466-526`: `kGemm`, `batch_counts {1,2,3,5,7}` as split-K slices, β = 2.0, so the source is needed.
- `test/unit/gemm/device/testbed_sparse.h:373,453-480`.
- `test/unit/gemm/device/testbed.h:469-505`.
- `test/unit/conv/device/conv2d_testbed.h:784-807`: `kSerial`, `split_k_slices {1,2,3,4,201}`.

Which threads and CTAs are involved: the pair records carry no thread or CTA ids (fields: `kid kernel space a_pc b_pc on off status frames_* sass_*`). The cross-CTA reading therefore comes from the code:
- Within a CTA every element of D is owned by one thread. For k>0 `iterator_C = iterator_D`, so the source load and the store of an element are by the same thread.
- Different (m,n) tiles are disjoint. Out-of-range CTAs return before touching D or the lock (`gemm_universal.h:483`, `gemm.h:215`, `gemm_sparse_universal.h:573`, `implicit_gemm_convolution.h:293`).
- So the only other accessor of a D element in a launch is another k-slice CTA of the same tile.

The per-instance tids in the kept trace would confirm this: `hb_events` / `hb_races` of the kernel JSON in the pair file's `store`, for example `/mnt/beegfs/fzheng4/cutlass/traces/main`.

## Why the detector did not certify

The scalar-clock verdict uses R1, then R3, then the barrier-only clock, and reports anything else as RACE (class from R2). See `docs/design/proof/hb_proof.tex` §5 matrix, D12 (`docs/CLAUDE.md:212-214, 671-675`).
- **R1**: barriers order threads of one CTA only, and these pairs are cross-CTA. The `syncs` pcs in the K2–K4 records sit between the two pcs, for example 0xa410/0xa4a0 for K2's rep (0xa3f0/0xa6a0). They are the epilogue's own intra-CTA barriers and do not span CTAs. K5's direct-store epilogue has none (`syncs: []`).
- **R3** (χ) starts only at "the PO-next RMW of u's thread … an instance with none has no release point: χ fails". It hops only over "observed atomic–atomic edges" (`hb_proof.tex` §5 "R3 as implemented"; `design/instance_gate.md` §7). The Semaphore has **no RMW**: it is `ld.acquire` / `st.release`. The limit is stated as assumption (R3b): "a lock released by a plain or `volatile` store, is not recognised".
- **(ATOM)** in the HB relation is defined only for RMWs ("(ATOM) r→q for RMWs with r ⊸ q, rel(r)=acq(q)=1", `hb_proof.tex` Def. hb, Def. gate). The instance gate's `fenced` would count `MEMBAR.ALL.GPU` (release, grid scope) and `CCTL.IVALL` (acquire, grid scope), but it is evaluated only on RMW records (`instance_gate.md` §1-3). Vector-clock mode has no edge either.
- **Barrier-only clock**: cross-CTA, so the pair is unordered.

Result: certificate applied = **none** (the pair records show `hb: None`). Class DR comes from R2: the epilogue accesses are weak `LDG.E.LTC128B` / `STG.E` / `LD.E` / `ST.E`. For K1, R2 gives SC (`hb: sc`). In scalar-clock mode the `sc` row "also holds strong–strong pairs that an atomic hand-off ordered (it cannot tell)" (`hb_proof.tex` §5).

This boundary is documented (R3b), so it is not a detector defect. It belongs in (b), not (c). What would let the detector certify: a synchronizes-with generator for a non-RMW strong release store → strong acquire load that reads from it. That needs the value read, or reads-from, which the collector does not record (D15).

## K1 detail (`semaphore.h:76 × 106`, `106 × 106`)

The detector applies these frame groups:
- `implicit_gemm_convolution.h:371|444`, `semaphore.h:93 > :415 | :444`, `:444|:444`.
- The fused-epilogue variants: `380/448/488`.
- `gemm_universal.h:611/663 | 691`, `gemm_sparse_universal.h:715/765 | 793`.
- The `gemm.h` frames (`:306/:346 | :370`) appear in the sm75 Gemm kernel.

What each pair is under PTX:
- **106 × 106 (WAW)**: slice *i*'s release (value *i+1*) and slice *j>i*'s release are always ordered by the chain above, and they are morally strong.
- **76 × 106 (RAW/WAR)**: a thread-0 acquire load of slice *j* against a release by slice *i*. If *j = i+1* and the load observed the store, they are ordered (synchronizes-with). If *j > i+1*, it is a spinning read racing a release it does not wait for. That pair is unordered, but both accesses are strong and `.gpu` across CTAs on one GPU, so they are morally strong.

Under PTX §8.7.1 a data race requires conflicting accesses that are *not morally strong* and are unordered. **No K1 pair is (a).** The `106×106` and observing-read pairs are (b), by the same mechanism as above. The spin reads are intentional synchronization accesses, not a race. The records cannot tell which 76×106 instance is which, because they have no tids or seq. The kept trace would decide that, but it would not change the class.

## K5 detail: why it is split-K and not overlapping tiles

- **Kernel and test.** `GemmUniversal<…, EpilogueDirectStore<…, PartitionsK=1, DirectStoreEpilogueIterator<float>>, GemmBatchedIdentityThreadblockSwizzle>`, from `test/unit/gemm/device/gemm_f16n_f16n_f16n_direct_store_tensor_op_f32_sm80.cu:64-107` (`SM80_Device_GemmUniversal_DirectStore_f16n_f16t_f32n_tensor_op_f32.128x128x32_64x64x32`, run through `TestAllGemmUniversal`: `kGemm`, slices 1/2/3/5/7, β = 2). Pair file `main/cutlass-gemm_device_tensorop_f32_sm80-c02__k012.json`.
- **Stack.** `epilogue_direct_store.h:260/268 > :197` (`compute_source_needed_`, β≠0) `> gemm_universal.h:668`. That is the call between `wait` (:663) and `release` (:691). The same kernel has K1 pairs at `gemm_universal.h:611/663 | 691`, so `grid.k()>1` held in this launch.
- **Accesses** (rep pcs 0x4480 / 0x4520):
  - `:259-260`: `output_fragment = *(source_ptr + nL)`, SASS `@P0 LD.E.64`.
  - `:268`: `*(output_ptr + nL) = …`, SASS `@P0 ST.E.64`. These are generic weak 8-byte accesses: `kAccumBlockN = 2` floats.
  - For k>0, `iterator_C = iterator_D` (gemm_universal.h:660-661), so `source_ptr == output_ptr` (`:243-244`).
- **No overlap inside a CTA** (`:171-182`, `:236-255`). Warp coordinates are `warp_m = idx % WarpCount::kM`, `warp_n = idx / WarpCount::kM`. With a 128×128 tile and 64×64 warps there are 4 warps, a 2×2 grid. Line 171 uses `WarpShape::kN` where `WarpCount::kN` looks intended, but here it only takes `idx % 128` with idx < 4, so it has no effect. Each thread owns rows `quad + 8·i` (i < 8) and the column pair `2·(lane&3) + 8·j` (j < 8) of its warp's 64×64 tile, so elements are disjoint within a CTA.
- **No overlap across tiles.** Tiles are at `(m·128, n·128)` (gemm_universal.h:588-591). The iterator is row-major with `stride = layout.stride(0)` (`direct_store_epilogue_iterator.h:71, 89-91, 127`), so distinct (m,n) tiles are disjoint in the kernel's row-major view.

So the only conflicting accessor is another k-slice of the same tile. That is the same hand-off as K2 → **(b)**.

Not checked: whether `GemmUniversalAdapter` passes a stride consistent with the column-major `f32n` D when the kernel was rebuilt from `GemmBase::GemmKernel::Mma`. A wrong stride would make tile writes overlap. Evidence against it:
- No K5 pair is outside the `:668` frame.
- Every K5-kernel pair co-occurs with K1.
- The upstream test asserts a correct result.

The cell addresses in the trace would decide it: do conflicting instances come from CTAs with equal (m,n) and different `blockIdx.z`?

## Uncovered pairs: checks made

| case | finding (source) |
|---|---|
| First slice (k=0) | It waits for 0, the zeroed workspace or the previous grid's reset. It reads **C** (`iterator_C` not replaced) and writes D, then releases 1. Its D writes are ordered before every later slice through the chain. Its C reads conflict with nothing unless C aliases D; the testbeds allocate separate C and D. Even with aliasing, slice 0's read precedes its own release, so it would still be ordered. |
| Last slice | Its `release(0)` (morally strong) is ordered after every earlier release by the chain. Slice 0 read 0 before releasing 1, so the reset cannot be observed by any wait of the same launch: values on a lock go 1, 2, …, K-1, 0 in coherence order, each written after acquiring the previous one. A next launch on the same stream is ordered by kernel completion. Different streams sharing one workspace do not occur in the unit tests. |
| Semaphore index | `block_idx = m + n·grid_m` is the same for all k-slices of a tile and different across tiles, in all five kernels. In the two conv kernels `block_idx` is computed from the first `get_tile_offset` (`:286` / analogue). It is recomputed at `:364` with the same swizzle and same arguments, so the values are equal. |
| Wait-value logic `wait(k)` | Slice k proceeds only after reading k, which only slice k-1 writes in this launch. Slices cannot be skipped or reordered, and `__syncthreads_and` makes the whole CTA wait on thread 0's value. |
| Early `fetch()` | If the early acquire (:611) already reads k, the loop exits at its first `bar.red`, which still follows that acquire in program order. The chain holds. |
| Slices with no k-iterations (`gemm.h:273`) | They still execute `wait` and `release`. |

## Summary for the table

K1 not (a) (SC: morally strong; 106×106 and observing reads ordered = (b)). K2, K3, K4, K5: (b), the split-K serial Semaphore hand-off (non-RMW `st.release.gpu` / `ld.acquire.gpu` plus CTA barriers), outside cuVein's RMW-only (ATOM)/R3 (R3b). No (a), (c) or (d) pairs. K5 is the DirectStore epilogue on the same split-K serial path.

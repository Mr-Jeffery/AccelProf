# New groups triage (CUTLASS v4.8.1, sm_89 unit tests)

This continues `triage/splitk.md` (K1–K5) and `triage/streamk.md` (S1a/S1b/S2), and uses the same class definitions.

Source: `/home/jeffery/x9-cutlass-v4.8.1` (`git describe` = `v4.8.1`). Paths are relative to `include/cutlass/` unless they say otherwise. `SK` = `gemm/kernel/gemm_universal_streamk.h`.

Pair data: every pair in `wt-x9/eval/results/cutlass/pairs/{main,t5400}/*.json` was scanned, 2,233 files with no unreadable ones. A pair is matched by its innermost **CUTLASS** frame on each side. CUDA-header frames such as `sm_60_atomic_functions.hpp:294` are skipped, which is the same rule `summary.json` uses. Files are assigned to families through the `parents` lists in `summary.json`, and every matched file was assigned to a family.
Scripts: `scratchpad/ng/scan.py` (extracts the pairs into `ng/recs.json`), `ng/an.py` (per-group stacks, kernel frames, semaphore co-occurrence), `ng/sk.py` (group 4), `ng/ef.py` and `ng/pt.py` (pc/SASS detail).

For every pair in all four groups: status CONFIRMED, verdict RACE in both the `on` and `off` halves, `hb` = None in both, conflict class DR.

## Verdict

| # | group (family) | pairs / kernels checked | path | mechanism | class |
|---|---|---|---|---|---|
| 1 | conv-sm80: `memory.h:204×431`, `431×431` | 128 / 2 | `ImplicitGemmConvolution` epilogue at `conv/kernel/implicit_gemm_convolution.h:425` | split-K serial Semaphore hand-off (K4 shape, 8 B) | **(b)** |
| 1 | conv-sm80: `memory.h:252×447`, `252×pti:447`, `447×447`, `pti:447×pti:447` | 384 / 3 | `implicit_gemm_convolution.h:425` (320 pairs), `conv/kernel/implicit_gemm_convolution_strided_dgrad.h:455` (64 pairs) | same hand-off, 4 B access width | **(b)** |
| 2 | simt: `memory.h:252×447`, `252×pti:447`, `447×447`, `pti:447×pti:447` | 1,752 / 22 | `implicit_gemm_convolution.h:425` (1,536 pairs), `conv/kernel/implicit_gemm_convolution_with_fused_epilogue.h:458` (216 pairs) | same hand-off | **(b)** |
| 2 | simt: `memory.h:298×463`, `463×463` | 512 / 2 | `implicit_gemm_convolution.h:425` | same hand-off, 2 B (`U16`) access width | **(b)** |
| 3 | epilogue-fusion: `memory.h:153×415`, `415×415` | 64 / 2 | `GemmWithFusedEpilogue` (`EpilogueWithReduction`) at `gemm/kernel/gemm_with_fused_epilogue.h:1469` | same hand-off, now in a fifth kernel type | **(b)** |
| 3 | epilogue-fusion: `semaphore.h:76×106`, `106×106` | 6 / 2 | `Semaphore::fetch/wait/release` in the same 2 kernels | the K1 shape | **not (a)**: morally strong, SC-informational; 106×106 and the observing reads are (b) |
| 4 | tensorop-sm80-multistage: `block_striped.h:194×functional.h:963` | 464 / 10 | first peer's `store` (SK:772) × later peer's `reduce` (SK:790) | **S1a** | **(b)** |
| 4 | tensorop-sm80-multistage: `functional.h:134×functional.h:963` | 464 / 10 | later peer's `reduce` (SK:790) × finisher's `load_add` (SK:813) after `wait_eq_reset` (SK:809) | **S1b** | **(a) DR**. This is a further instance of the confirmed `GenericBarrier::wait_eq_reset` finding, not a new finding |

`pti:447` means `epilogue/threadblock/predicated_tile_iterator.h:447`, the call site of `arch::global_store`. See "Notes" for why some stores have this as their innermost frame.

**No pair in groups 1–4 falls outside these mechanisms.** Two frame-attribution oddities in groups 2 and 3 are explained under "Notes". Neither changes the class, and neither is a new candidate.

## Groups 1–3: split-K serial (the K-cluster mechanism, class (b))

### Checks, per group

For each group, three things were checked on every pair:
1. The kernel-level frame on both sides is the epilogue call that sits between `semaphore.wait(k)` and `semaphore.release(...)`.
2. The same kernel record also has `semaphore.h:76×106` / `106×106` pairs, so `grid.k()>1` held in serial mode in that launch.
3. The inner frames identify the access as a source load or a destination store of the default epilogue.

| kernel (file) | early `fetch` | `iterator_C = iterator_D` if k>0; `wait(k)` | epilogue (frame in data pairs) | `release` |
|---|---|---|---|---|
| `conv/kernel/implicit_gemm_convolution.h` | 371 | 411-415 | **425** | 431-444 |
| `conv/kernel/implicit_gemm_convolution_strided_dgrad.h` | 402 | 447-448, **451** | **455** | 467-480 |
| `conv/kernel/implicit_gemm_convolution_with_fused_epilogue.h` | 380 | 444-445, 448 | **458** (456-469) | 474-488 |
| `gemm/kernel/gemm_with_fused_epilogue.h` (`kGemm`, `grid.k()>1`) | 1379 | 1454-1455, **1458** | **1469** | 1487-1500 |

The semaphore frames found in the same kernels match these lines exactly:
- `implicit_gemm_convolution.h:371|444`, `semaphore.h:93>…:415 | :444`, `:444|:444`.
- strided dgrad `:402|:480`, `semaphore.h:93>…:451 | :480`, `:480|:480`.
- fused conv `:380|:488`, `semaphore.h:93>…:448 | :488`, `:488|:488`.
- gemm fused `:1379|:1500`, `semaphore.h:93>…:1458 | :1500`, `:1500|:1500`.

All semaphore pairs are `LDG.E.STRONG.GPU` / `STG.E.STRONG.GPU` with `hb` = sc and class SC, the same as K1.

| group | pairs | kernels | kernels with semaphore pairs | data-pair kernel frame (both sides, every pair) |
|---|---|---|---|---|
| conv-sm80 204×431 | 128 | 2 | **2/2** | `implicit_gemm_convolution.h:425` (128) |
| conv-sm80 252×447 (+pti) | 384 | 3 | **3/3** | `:425` (320), `strided_dgrad.h:455` (64) |
| simt 252×447 (+pti) | 1,752 | 22 | **22/22** | `:425` (1,536), `with_fused_epilogue.h:458` (216) |
| simt 298×463 | 512 | 2 | **2/2** | `:425` (512) |
| epilogue-fusion 153×415 | 64 | 2 | **2/2** | `gemm_with_fused_epilogue.h:1469` (64) |
| (also checked) simt 204×431 | 1,152 | 11 | 11/11 | `:425` (1,152) |

The pair and kernel counts match `groups.tsv` (for example 191+191+1+1 = 384 over 3 kernels, and 868+868+8+8 = 1,752 over 22 kernels).

### Stacks, all pairs

In every stack below the outer `device_kernel.h:84` frame is omitted. The load side is always the source load and the store side is always the destination store.

**Source load**:
- `memory.h:{153,204,252,298} > predicated_tile_iterator.h:356 > :385 > epilogue.h:273`, where `:273` is `source_iterator.load`.
- The conv-iterator and strided-dgrad variants: `predicated_tile_iterator_conv.h:350 > :361` and `predicated_tile_iterator_strided_dgrad.h:341 > :353`.
- Fused variants: `epilogue_with_broadcast.h:1479` (`source_iterator.load`) and `epilogue_with_reduction.h:576` (`source_iterator.load`).

**Destination store**:
- `memory.h:{415,431,447,463} > predicated_tile_iterator.h:447 > :481 > epilogue.h:534`, where `:534` is `destination_iterator.store`.
- Variants: `predicated_tile_iterator_conv.h:408 > :422`, `predicated_tile_iterator_strided_dgrad.h:404 > :416`, `epilogue_with_broadcast.h:1537` (`destination_iterator.store(frag_Z)`), `epilogue_with_reduction.h:640` (`destination_iterator.store`).

Distinct stacks: conv-sm80 204×431 has 2, conv-sm80 252×447 has 6, simt 252×447 has 14, simt 298×463 has 2, epilogue-fusion has 3. All of them have the shape above (full list from `ng/an.py`).

**SASS** (all weak):
- 8 B: `LDG.E.LTC128B.64` / `STG.E.64`.
- 4 B: `LDG.E.LTC128B` / `STG.E`.
- 2 B: `LDG.E.LTC128B.U16` / `STG.E.U16`.
- 16 B: `LDG.E.LTC128B.128` / `STG.E.128`.

The new pcs (`memory.h:252/447`, `298/463`) are simply the 4-byte and 2-byte `global_load` / `global_store` specializations (`arch/memory.h:244`/`:290` `global_load<…,4/2>`, asm at :252/:298; `:443`/`:459` `global_store<…,4/2>`, asm at :447/:463). They are reached from the same epilogue as K2–K4.

### Ordering

This is identical to `splitk.md` §"PTX ordering of the data pairs":

`W(slice i)` -po→ `bar.sync`(:102) -sw→ thread 0 `st.release.gpu`(:106) -sw→ thread 0′ `ld.acquire.gpu`(:76, reads i+1) -po→ `bar.red`(:92) -sw→ `A(slice i+1)`

Causality order holds through this chain, so the pairs are not a §8.7.1 race. The detector cannot certify them because of R3b: the Semaphore uses no RMW, and (ATOM)/R3 are RMW-only. Hence `hb` = None.

Test configurations that select split-K serial:
- conv: `test/unit/conv/device/conv2d_testbed.h:784-807` (`kSerial`, slices {1,2,3,4,201}). Fused-broadcast conv: `conv2d_with_broadcast_testbed.h:300` (default `kSerial`).
- gemm fused: `test/unit/gemm/device/gemm_with_reduction_f16n_f16n_f16n_tensorop_f32_sm75.cu:110-116` (`kGemm`, `batch_count` = 2 split-K slices, β = 2.25). Run via `testbed_gemm_with_reduction.h:406-445`.

### Group-specific checks

- **Strided dgrad (new kernel type in this triage).** Within one tile, different k-slices are ordered by the chain. Across tiles:
  - `block_idx = m + n·grid_m` (:391) differs between tiles.
  - The m-tiles are split into `stride_h·stride_w` filter phases (`conv/threadblock/threadblock_swizzle.h:59-64`). `start_r, start_s` (:310) range over `[0,stride)`.
  - `strided_dgrad_starting_coords` (`conv/conv2d_problem_size.h:635-653`) maps them one-to-one onto residues `start_h, start_w` mod stride. So different phases write disjoint output pixels.
  - All 64 strided-dgrad data pairs sit in the `:455` frame, between `wait` :451 and `release` :480.

  This disjointness argument comes from the source. The trace's per-instance CTA ids would confirm it, and those exist only in `hb_events` on the cluster.
- **GemmWithFusedEpilogue (fifth kernel type).** The Semaphore protocol is the same as in the other four kernel types (`:1371` ctor, `:1379` fetch, `:1454-1458` wait, `:1500` release). Workspace zeroing: `Params : UniversalParamsBase` (`gemm_with_fused_epilogue.h:959`), and the tests use `GemmUniversalAdapter` → `GemmUniversalBase` (`gemm_universal_adapter.h:721`), which zeroes the semaphore workspace (`params_universal_base.h:184`, as in splitk.md). The `Tensor` iterator (`:1431-1440`) and `ptr_Vector` (`:1469-1474`) are nullptr for every slice except the last, and a null-pointer iterator clears its mask (`epilogue/threadblock/predicated_tile_iterator.h:276-278`). So only D is touched by more than one slice.

## Group 4: stream-K f64. S1a (b) plus S1b (a), both already characterized

Kernels: `GemmUniversalStreamk<…MmaMultistage<GemmShape<{128,64,32}×{128,64,32}×16>…>, double…, ThreadblockSwizzleStreamK>`, 10 kernels from `t5400:cutlass-gemm_device_tensorop_f64-all__k032..k041`. The kids are `gemm_f64n_f64t_f64t_tensor_op_f64_sm80` (464 pairs) and `gemm_f64t_f64n_f64t_tensor_op_f64_sm80` (464 pairs).

`functional.h:963` is `atomic_add<double>::operator()` → `atomicAdd(double*)` for `__CUDA_ARCH__ >= 600` (`functional.h:953-977`). The SASS is `RED.E.ADD.F64.RN.STRONG.GPU`. It is the f64 analogue of `:943` (generic `atomicAdd`) and `:992` (`red…f16x2`) in streamk.md.

Every pair, 928 in total, has one of exactly two stacks. Frames `SK:1081 > 1155 > 1127` are present on both sides and omitted here.

```
464  sm_60_atomic_functions.hpp:294 > functional.h:963 > block_striped.h:229 > SK:790 > SK:968
       | block_striped.h:194 > SK:772 > SK:968                          WAW   S1a   RED.F64.STRONG.GPU × STG.E.64
464  sm_60_atomic_functions.hpp:294 > functional.h:963 > block_striped.h:229 > SK:790 > SK:968
       | functional.h:134 > block_striped.h:181 > SK:813 > SK:976       RAW   S1b   RED.F64.STRONG.GPU × LDG.E.64
```

- **194 × 963 is S1a.** The first peer's plain `STG` in `share_accumulators` (SK:772) is paired with a later peer's atomic `reduce` (SK:790), and the later peer reaches SK:790 after `wait_eq`/`wait_lt` (SK:786/780). This is the CTA-cumulative release (`arrive_inc`: `bar.sync`, `fence.acq_rel.gpu`, `red.relaxed.gpu`) → `ld.acquire.gpu` + `bar.sync` hand-off. **(b)**, with the same unmodeled mechanism as streamk.md S1a.
- **134 × 963 is S1b.** A peer's atomic reduce (SK:790) is paired with the finisher's plain `LDG.E.64` in `acquire_accumulators` → `load_add` (SK:813 → `block_striped.h:181` → `plus` at `functional.h:134`). The finisher reaches it after `wait_eq_reset` (SK:809): a relaxed `atom.cas` spin, then `bar.sync`, with no acquire. **(a) DR**, an additional instance (f64 element type) of the already-confirmed `GenericBarrier::wait_eq_reset` race. It is the same stack shape as streamk.md's `134 > SK:813 > 976 | 943 > SK:790 > 968` row. **Not a new finding.**

The other pairs in these 10 kernels also fit streamk.md exactly:
- 464 pairs `block_striped.h:194 × functional.h:134` (S1b).
- 24 pairs `block_striped.h:165 × :194` (S1b, separate reduction).
- 10 pairs `barrier.h:104 × :124` (S2).
- 10 pairs `barrier.h:104 × device_atomic_functions.hpp:202` (S2: the CAS at `barrier.h:175`, with the innermost frame inside the CUDA header).

No other shape occurs.

## Notes (looked at; none is a new candidate)

1. **Store with no `arch/memory.h` frame** (`pti:447` innermost): 9 pairs `252×pti:447` and 9 `pti:447×pti:447`, one store pc per kernel.
   - It occurs in 8 simt conv kernels (c00s00, c00s03s03, c00s04s00, c01s05, c01s07, c01s09, c01s11, c01s15) and in conv-sm80 `tensorop_f16_sm80-c01__k004`.
   - The SASS is the same `STG.E` as the `memory.h:447` stores. The rest of the stack is identical (`pti:447 > :481 > epilogue.h:534 > :405 > implicit_gemm_convolution.h:425`).
   - So it is the 4-byte `global_store` asm at the `pti:447` call site, with the innermost inlined frame missing from the line table. Same access, same class (b).
2. **Sibling-line attribution in the fused epilogues.** Some D source loads and D stores are attributed to the neighbouring `Tensor` call, `epilogue_with_reduction.h:579` (`tensor_iterator.load`), or `epilogue_with_broadcast.h:1542` (`tensor_iterator.store`). Affected pairs:
   - epilogue-fusion: 28 of 32 load-side pairs.
   - simt fused conv: 56+56+… of the 216 pairs (kernel `conv_device_simt-c01s04__k000`). The same pattern exists in the earlier K2 kernel `conv_device_tensorop_f32_sm75-c02__k002`.

   Per kernel, the first unrolled epilogue iteration's pcs carry the correct line (`:576` / `:1537`), and every later iteration's pcs carry the sibling line (`:579` / `:1542`). For example, in `gemm_with_fused_epilogue_tensorop-c00__k002` there are 2 pcs at `:576` and 14 at `:579`, the 579 loads come in pairs at a stride of about 2,600 bytes, and each is paired with a `:640` D store.

   Three facts show these accesses really are D, not Tensor:
   - The partner of each conflict is a D access (`:640` / `:1537` store, or `:1479` source load = D for k>0).
   - `Tensor`/`T` are separate allocations in the testbeds: `testbed_gemm_with_reduction.h:114,204,437` vs D at `:112,197,435`, and `conv2d_with_broadcast_testbed.h:143,215,332`.
   - In serial split-K the Tensor/T iterator is nullptr for every slice except the last (`gemm_with_fused_epilogue.h:1434-1437`, `implicit_gemm_convolution_with_fused_epilogue.h:417-423`), and null iterators mask all accesses (`predicated_tile_iterator.h:276-278`, `predicated_tile_iterator_conv.h:287-289`). So a real T access could have a conflicting partner only in another last-slice CTA of the same tile, and there is only one.

   This is a DWARF inlined-at attribution artefact on identical inlined iterator code. It does not affect the verdict, and it would not change the class even if the access were Tensor, because every access in the frame is between `wait` and `release`. Two things would settle the attribution directly: an `nvdisasm -g` line table at those pcs, or the instance addresses in the kept trace checked against the D and T allocation ranges.
3. **Thread/CTA ids** are not in the pair records. As in splitk.md and streamk.md, "different k-slice CTAs of the same tile" and "peer/finisher CTAs" are established from the source, not from the records. `hb_events` in the cluster store would confirm them, and they would not change any class.

## Summary for the table

- Groups 1, 2 and 3 (data pairs): **(b)**, the split-K serial Semaphore hand-off (non-RMW `st.release.gpu` / `ld.acquire.gpu` plus CTA barriers, R3b). The access widths (2 B, 4 B) and kernels (strided dgrad, fused-epilogue conv, `GemmWithFusedEpilogue`) are new; the mechanism is not. All 2,840 data pairs (+1,152 simt 204×431) sit in the epilogue frame between wait and release, in kernels that all carry semaphore pairs.
- Group 3 `semaphore.h:76×106`, `106×106`: **not (a)** (K1).
- Group 4: 464 pairs are S1a, **(b)**. 464 pairs are S1b, **(a) DR**: the same `wait_eq_reset` race, f64 instance, not a new finding.
- No pair needs its own analysis.

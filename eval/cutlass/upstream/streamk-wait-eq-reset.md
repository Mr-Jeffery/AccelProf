<!-- X9 step 8 draft. NOT FILED (D23): no upstream contact. -->
# [BUG] `GenericBarrier::wait_eq_reset` has no acquire: stream-K partials are read without memory ordering (PTX data race)

**Describe the bug**

`cutlass::GenericBarrier::wait_eq_reset` (`include/cutlass/barrier.h`, v4.8.1 lines 168-180) waits with thread 0 spinning on
`atomicCAS(flag_ptr, val, 0)` and then calls `Sync::sync()` (`__syncthreads`). `atomicCAS` lowers to a relaxed, gpu-scope
`atom.global.cas.b32`, and nothing follows it in thread 0 before the CTA barrier, so the waiting CTA performs no acquire.
The signalling side is correct (`arrive_inc` → `__syncthreads`; thread 0 `fence.acq_rel.gpu; red.relaxed.gpu`), and the
sibling waits `wait_eq`/`wait_lt` use `ld.global.acquire.gpu` (changed from relaxed in #760). Under the PTX memory
consistency model a relaxed RMW followed by `bar.sync` is not an acquire pattern, so there is no synchronizes-with edge
between the producer CTA's release and the consumer CTA, and the consumer's plain loads of the producer's workspace
partials are not causality-ordered after the producer's plain stores: a data race by the definition in the PTX ISA
("Data races"), on both 2.x stream-K paths:

- cooperative finisher: peer partials stored at `gemm_universal_streamk.h:772` (`block_striped.h:194`), read at `:813`
  after `wait_eq_reset` at `:809`;
- separate reduction: partials stored at `:989`, read by the reduction block at `:920` after `wait_eq_reset` at `:885`.

All eight call sites of `wait_eq_reset` are affected: `gemm_universal_streamk.h:809, :885`,
`gemm_streamk_with_fused_epilogue.h:813, :941, :1983, :2095`, `gemm_universal_with_visitor_streamk.h:592, :639`.
The 3.x sm90/sm100 stream-K schedulers use `wait_eq`/`wait_lt` and are not affected.

On sm_89 (CUDA 13.3) the stock SASS is `ATOMG.E.CAS.STRONG.GPU; BRA; BAR.SYNC; LDG.E`, with no `MEMBAR`/`CCTL.IVALL`
between the CAS and the loads, whereas `wait_eq` emits `LDG.E.STRONG.GPU; CCTL.IVALL`.

**Observed impact**

None observed: a reproducer (below) passed 400/400 runs on an RTX 4060 Ti, also with a `__nanosleep` before the
release to make the consumer spin. This is a memory-model conformance issue: correctness currently depends on the
consumer's SM holding no stale L1 line for the workspace, which PTX does not guarantee.

**Steps / environment**

CUTLASS v4.8.1, CUDA 13.3, sm_89, `-arch=sm_89 -O3`. A stream-K `device::GemmUniversal` with the simt f32 configuration
of `SM50_device_sgemm_nt.64x64x8_64x32x1`, `ThreadblockSwizzleStreamK`, M=N=128, K=256, split 2 (finisher path) and
split 3 (separate reduction, 32 reduction blocks). Found by a happens-before race detector; reproducer (75 lines) available.

**Proposed fix** (one fence; mirrors `red_release`)

```diff
--- a/include/cutlass/barrier.h
+++ b/include/cutlass/barrier.h
@@ -173,6 +173,13 @@
         // Spin-loop
         #pragma unroll 1
         while(atomicCAS(flag_ptr, val, 0) != val) {}
+#if (__CUDA_ARCH__ >= 700)
+        // Acquire pattern: the strong (relaxed) atom read above followed by an acq_rel fence.  (The fence
+        // also acquires for the other threads of the group, which read the data after the sync below)
+        asm volatile ("fence.acq_rel.gpu;" ::: "memory");
+#else
+        __threadfence();
+#endif
     }
 
     Sync::sync();
```

Fixed SASS: `ATOMG.E.CAS.STRONG.GPU; BRA; MEMBAR.ALL.GPU; ERRBAR; CCTL.IVALL; …; BAR.SYNC; LDG.E` at both stream-K sites.
Cost: one `MEMBAR.GPU` in one thread per finished tile / reduction fragment. Equivalent alternatives: `atom.acquire.gpu.cas`
via inline asm, or `cuda::atomic_ref<int, cuda::thread_scope_device>::compare_exchange_strong(..., cuda::memory_order_acquire)`.

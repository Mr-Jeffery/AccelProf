// O2 probe (T12): what each PTX ordering/scope lowers to on this arch.
#include <cuda/atomic>
#define K(name, body) extern "C" __global__ void name(int* p, int* q) { body }
using cuda::memory_order_relaxed; using cuda::memory_order_acquire;
using cuda::memory_order_release; using cuda::memory_order_acq_rel; using cuda::memory_order_seq_cst;
#define REF(S) cuda::atomic_ref<int, cuda::thread_scope_##S> a(*p)
K(rmw_relaxed_block, REF(block); q[1] = a.fetch_add(1, memory_order_relaxed); q[2] = q[3];)
K(rmw_acquire_block, REF(block); q[1] = a.fetch_add(1, memory_order_acquire); q[2] = q[3];)
K(rmw_release_block, REF(block); q[2] = q[3]; q[1] = a.fetch_add(1, memory_order_release);)
K(rmw_acqrel_block,  REF(block); q[2] = q[3]; q[1] = a.fetch_add(1, memory_order_acq_rel); q[4] = q[5];)
K(rmw_relaxed_dev, REF(device); q[1] = a.fetch_add(1, memory_order_relaxed); q[2] = q[3];)
K(rmw_acquire_dev, REF(device); q[1] = a.fetch_add(1, memory_order_acquire); q[2] = q[3];)
K(rmw_release_dev, REF(device); q[2] = q[3]; q[1] = a.fetch_add(1, memory_order_release);)
K(rmw_acqrel_dev,  REF(device); q[2] = q[3]; q[1] = a.fetch_add(1, memory_order_acq_rel); q[4] = q[5];)
K(rmw_seqcst_dev,  REF(device); q[2] = q[3]; q[1] = a.fetch_add(1, memory_order_seq_cst); q[4] = q[5];)
K(rmw_acquire_sys, REF(system); q[1] = a.fetch_add(1, memory_order_acquire); q[2] = q[3];)
K(rmw_release_sys, REF(system); q[2] = q[3]; q[1] = a.fetch_add(1, memory_order_release);)
K(cas_acquire_block, REF(block); int e = 0; while (!a.compare_exchange_strong(e, 1, memory_order_acquire)) e = 0; q[2] = q[3];)
K(cas_acquire_dev, REF(device); int e = 0; while (!a.compare_exchange_strong(e, 1, memory_order_acquire)) e = 0; q[2] = q[3];)
K(fence_acq_block, q[2] = q[3]; cuda::atomic_thread_fence(memory_order_acquire, cuda::thread_scope_block); q[4] = q[5];)
K(fence_rel_block, q[2] = q[3]; cuda::atomic_thread_fence(memory_order_release, cuda::thread_scope_block); q[4] = q[5];)
K(fence_acqrel_dev, q[2] = q[3]; cuda::atomic_thread_fence(memory_order_acq_rel, cuda::thread_scope_device); q[4] = q[5];)
K(fence_acq_dev, q[2] = q[3]; cuda::atomic_thread_fence(memory_order_acquire, cuda::thread_scope_device); q[4] = q[5];)
K(fence_rel_dev, q[2] = q[3]; cuda::atomic_thread_fence(memory_order_release, cuda::thread_scope_device); q[4] = q[5];)
K(threadfence_block, q[2] = q[3]; __threadfence_block(); q[4] = q[5];)
K(threadfence, q[2] = q[3]; __threadfence(); q[4] = q[5];)
K(threadfence_system, q[2] = q[3]; __threadfence_system(); q[4] = q[5];)
K(legacy_cas_fence, while (atomicCAS(p, 0, 1) != 0) {} __threadfence(); q[2] = q[3]; __threadfence(); atomicExch(p, 0);)
K(legacy_cas_block, while (atomicCAS_block(p, 0, 1) != 0) {} __threadfence_block(); q[2] = q[3]; __threadfence_block(); atomicExch_block(p, 0);)
extern "C" __global__ void smem_acquire_block(int* q) {
    __shared__ int s; if (threadIdx.x == 0) s = 0; __syncthreads();
    cuda::atomic_ref<int, cuda::thread_scope_block> a(s);
    q[1] = a.fetch_add(1, memory_order_acquire); q[2] = q[3];
    q[4] = a.fetch_add(1, memory_order_release); }

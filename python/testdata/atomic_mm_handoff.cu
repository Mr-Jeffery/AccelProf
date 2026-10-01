// Phase 2 memory-model discriminator: a cross-thread producer/consumer handoff of a
// non-atomic global (g_data[0]) ordered ONLY by an atomic flag. Two kernels differ in
// exactly one thing -- the memory order of the flag atomics:
//
//   handoff_strong : release/acquire (.STRONG scope) + __threadfence() -> a correct
//                    PTX release/acquire handoff, so the data read is ordered-after the
//                    data write. The HB model must report NORACE.
//   handoff_relaxed: memory_order_relaxed, no fence -> PTX does NOT order the data read
//                    after the data write. The read genuinely races the write. The HB
//                    model must report a RACE (a relaxed atomic must NOT synchronize).
//
// The model keys the release/acquire HB edge on the atomic's .STRONG coherence scope
// (sync_dominance.atomic_scope): STRONG.{CTA,SM}->BLOCK, STRONG.{GPU,SYS}->GRID, and a
// relaxed/unqualified atomic -> NONE (no release pickup). If handoff_relaxed also came
// back NORACE, the model would be treating relaxed atomics as synchronizing = a false
// negative on a real race = UNSOUND for the certificate. This pair decides it.
//
// Flag ops are RMW (exchange / fetch_add) so they disassemble to ATOM* opcodes that
// atomic_scope classifies (an atomic .store()/.load() would be ST/LD, not an atomic).
// Build:  nvcc -arch=native -lineinfo --cudart shared atomic_mm_handoff.cu -o <out>
#include <cuda/atomic>
#include <cstdio>

__device__ int g_data[1];     // the contested non-atomic global
__device__ int g_flag[1];     // handoff flag
__device__ int g_out[64];     // per-thread sink (no conflict) so the read is not DCE'd

__global__ void handoff_strong() {
    const int t = threadIdx.x;
    cuda::atomic_ref<int, cuda::thread_scope_device> flag(g_flag[0]);
    if (t == 0) {                                       // producer: warp 0, lane 0
        g_data[0] = 42;                                 // non-atomic write
        __threadfence();
        flag.exchange(1, cuda::memory_order_release);   // .STRONG release
    } else if (t == 32) {                               // consumer: warp 1, lane 0
        while (flag.fetch_add(0, cuda::memory_order_acquire) == 0) { /* spin */ }
        g_out[t] = g_data[0];                           // non-atomic read, ordered-after
    }
}

__global__ void handoff_relaxed() {
    const int t = threadIdx.x;
    cuda::atomic_ref<int, cuda::thread_scope_device> flag(g_flag[0]);
    if (t == 0) {                                       // producer: warp 0, lane 0
        g_data[0] = 42;                                 // non-atomic write
        flag.exchange(1, cuda::memory_order_relaxed);   // RELAXED: no .STRONG, no fence
    } else if (t == 32) {                               // consumer: warp 1, lane 0
        while (flag.fetch_add(0, cuda::memory_order_relaxed) == 0) { /* spin */ }
        g_out[t] = g_data[0];                           // NOT ordered by PTX -> races
    }
}

int main() {
    int zero = 0;
    for (int rep = 0; rep < 3; ++rep) {                 // a few launches to exercise the handoff
        cudaMemcpyToSymbol(g_flag, &zero, sizeof(int));
        cudaMemcpyToSymbol(g_data, &zero, sizeof(int));
        handoff_strong<<<1, 64>>>();
        cudaDeviceSynchronize();
    }
    for (int rep = 0; rep < 3; ++rep) {
        cudaMemcpyToSymbol(g_flag, &zero, sizeof(int));
        cudaMemcpyToSymbol(g_data, &zero, sizeof(int));
        handoff_relaxed<<<1, 64>>>();
        cudaDeviceSynchronize();
    }
    cudaError_t e = cudaGetLastError();
    if (e != cudaSuccess) { printf("CUDA error: %s\n", cudaGetErrorString(e)); return 1; }
    printf("done (strong->norace, relaxed->race expected)\n");
    return 0;
}

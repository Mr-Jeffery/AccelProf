#include "cutlass/barrier.h"
// Minimal stream-K hand-off probe: producer = share_accumulators (first peer), consumer = acquire_accumulators
__global__ void producer(int *flag, float *ws, float v) {
  ws[threadIdx.x] = v;                                        // block_striped store (plain STG)
  cutlass::Barrier::arrive_inc(flag, threadIdx.x, 0);         // bar.sync; t0: fence.acq_rel.gpu; red.relaxed.gpu
}
__global__ void peer(int *flag, float *ws, float v) {
  cutlass::Barrier::wait_eq(flag, threadIdx.x, 0, 1);         // t0: ld.acquire.gpu spin; bar.sync
  atomicAdd(ws + threadIdx.x, v);                             // block_striped reduce (RED)
  cutlass::Barrier::arrive_inc(flag, threadIdx.x, 0);
}
__global__ void consumer(int *flag, float *ws, float *out) {
  cutlass::Barrier::wait_eq_reset(flag, threadIdx.x, 0, 2);   // t0: atomicCAS spin; bar.sync
  out[threadIdx.x] = ws[threadIdx.x];                         // load_add (plain LDG)
}

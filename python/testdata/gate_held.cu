// T12 (design/instance_gate.md section 6): HbClock's deferred acquire. Thread 0 writes the lock
// word plainly, fences, and releases it with atomicExch; it then raises `go` with an UNFENCED
// atomicExch (rel = 0: `go` orders nothing). Thread 32 waits for `go` (an unfenced spin: no
// acquire either) and then CASes the lock, which acquires thread 0's release (rel = 1). Check of
// that CAS finds thread 0's plain store unordered by the CAS thread's own clock and ordered only by
// the pending acquire J -- the conflict is HELD until the CAS thread's next record:
//   held_fenced   : __threadfence() after the CAS  -> acq = 1 -> the held conflict is dropped
//   held_unfenced : no fence after the CAS          -> acq = 0 -> it is reported (DR, "atomic")
// The hand-off order is already forced by a flag spin (T18: thread 32 CASes the lock word only
// after `go` took effect, which is after thread 0's lock-word exchange and its record window
// closed), so the two RMW windows on the lock word cannot overlap whatever the collector's
// timing; nothing to change.
// Both kernels run in one binary; HbClock == specification on both is the check of the deferral.
#include <cstdio>

__device__ int lock_word;
__device__ int go;
__device__ int data;

__global__ void held_fenced(int* out) {
    if (threadIdx.x == 0) {
        lock_word = 5;
        __threadfence();
        atomicExch(&lock_word, 1);
        atomicExch(&go, 1);
    } else if (threadIdx.x == 32) {
        while (atomicAdd(&go, 0) == 0) {}
        int old = atomicCAS(&lock_word, 1, 2);
        __threadfence();
        out[0] = old + data;
    }
}

__global__ void held_unfenced(int* out) {
    if (threadIdx.x == 0) {
        lock_word = 5;
        __threadfence();
        atomicExch(&lock_word, 1);
        atomicExch(&go, 1);
    } else if (threadIdx.x == 32) {
        while (atomicAdd(&go, 0) == 0) {}
        int old = atomicCAS(&lock_word, 1, 2);
        out[0] = old + data;
    }
}

int main() {
    int* out;
    cudaMalloc(&out, sizeof(int));
    int zero = 0;
    held_fenced<<<1, 64>>>(out);
    cudaDeviceSynchronize();
    cudaMemcpyToSymbol(go, &zero, sizeof(int));
    cudaMemcpyToSymbol(lock_word, &zero, sizeof(int));
    held_unfenced<<<1, 64>>>(out);
    cudaError_t e = cudaDeviceSynchronize();
    printf("gate_held: %s\n", cudaGetErrorString(e));
    return e == cudaSuccess ? 0 : 1;
}

// C1: fixtures for collector-only mode (YOSEMITE_HB_TRACE unset: no HbClock, no hb_* keys; the verdicts
// come from the static certificates applied to the PCDepGraph edges alone). One block of 2 warps.
//   co_straight   a shared write, one __syncthreads, a cross-warp read: R1 dominance orders the pair
//   co_loop_red   the reduction shape: one barrier inside the loop, the pairs loop-carried around it
//   co_loop_tile  the tile shape: write tile / barrier / read tile / barrier, in a loop
//   co_missing    the same write and cross-warp read with no barrier: a race
#define TPB 64

__global__ void co_straight(const int* in, int* out) {
    __shared__ int s[TPB];
    const int t = threadIdx.x;
    s[t] = in[t];
    __syncthreads();
    out[t] = s[(t + 32) % TPB];
}

__global__ void co_loop_red(const int* in, int* out, const int n) {
    __shared__ int s[TPB];
    const int t = threadIdx.x;
    s[t] = in[t];
    __syncthreads();
    for (int stride = n / 2; stride > 0; stride >>= 1) {   // runtime bound: no unrolling
        if (t < stride) s[t] = s[t] + s[t + stride];
        __syncthreads();
    }
    if (t == 0) out[0] = s[0];
}

__global__ void co_loop_tile(const int* in, int* out, const int iters) {
    __shared__ int s[TPB];
    const int t = threadIdx.x;
    int acc = 0;
    for (int i = 0; i < iters; ++i) {                      // runtime bound: no unrolling
        s[t] = in[t] + i;
        __syncthreads();
        acc += s[(t + 32) % TPB];
        __syncthreads();
    }
    out[t] = acc;
}

__global__ void co_missing(const int* in, int* out) {
    __shared__ int s[TPB];
    const int t = threadIdx.x;
    s[t] = in[t];
    out[t] = s[(t + 32) % TPB];
}

int main() {
    int *in, *out;
    cudaMalloc((void**)&in, sizeof(int) * TPB);
    cudaMalloc((void**)&out, sizeof(int) * TPB);
    cudaMemset(in, 0, sizeof(int) * TPB);
    co_straight<<<1, TPB>>>(in, out);          cudaDeviceSynchronize();
    co_loop_red<<<1, TPB>>>(in, out, TPB);     cudaDeviceSynchronize();
    co_loop_tile<<<1, TPB>>>(in, out, 4);      cudaDeviceSynchronize();
    co_missing<<<1, TPB>>>(in, out);           cudaDeviceSynchronize();
    cudaError_t e = cudaGetLastError();
    return e == cudaSuccess ? 0 : 1;
}

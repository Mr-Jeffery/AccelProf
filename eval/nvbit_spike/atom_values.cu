// T13 value test (eval/NVBIT_SPIKE.md step 3). Three parts, one per argv[1]:
//   1            one warp, lane 0 only: atomicAdd(&x, 1) eight times
//   2            eight warps (one block of 256), all lanes: atomicAdd(&x, 1)
//   4            as 2, but the address is &x + off[tid] with off[] = 0 loaded
//                from memory, so ptxas cannot warp-aggregate: 256 per-lane
//                RMWs (part 2 compiles to one leader ATOMG per warp on sm_89,
//                and so does a per-lane increment with a constant address)
//   3 B W ITERS  lock idiom of matrix-multiplication: B blocks x W warps, lane 0
//                of each warp takes a global spin lock ITERS times
//                (atomicCAS(&lock, 0, tag) / fenced critical section /
//                atomicExch(&lock, 0)). tag is unique per critical section, so a
//                failed CAS's old value names the critical section it ran in and
//                the Exch's old value names the one it ends.
// The program checks its own results and prints them; the atom_after tool's
// records are checked by analyze_atom.py.
#include <cstdio>
#include <cstdlib>
#include <vector>

#define CK(x) do { cudaError_t ce_ = (x); if (ce_ != cudaSuccess) { \
    printf("CUDA %s at %s:%d\n", cudaGetErrorString(ce_), __FILE__, __LINE__); \
    exit(2); } } while (0)

__device__ unsigned x;
__device__ unsigned lock;
__device__ volatile unsigned cs_count;

__global__ void part1(unsigned* out) {
    if (threadIdx.x == 0)
        for (int i = 0; i < 8; i++) out[i] = atomicAdd(&x, 1u);
}

__global__ void part2(unsigned* out) {
    out[threadIdx.x] = atomicAdd(&x, 1u);
}

__global__ void part4(unsigned* out, const unsigned* off) {
    out[threadIdx.x] = atomicAdd(&x + off[threadIdx.x], 1u);
}

__global__ void part3(int iters, unsigned* order, unsigned* exch_old,
                      unsigned* fails) {
    if (threadIdx.x % 32 != 0) return;
    unsigned w = blockIdx.x * (blockDim.x / 32) + threadIdx.x / 32;
    for (int it = 0; it < iters; it++) {
        unsigned tag = ((w << 8) | it) + 1;
        unsigned nfail = 0;
        while (atomicCAS(&lock, 0u, tag) != 0u) nfail++;
        __threadfence();
        unsigned k = cs_count;
        cs_count = k + 1;
        order[k] = tag;
        __threadfence();
        exch_old[k] = atomicExch(&lock, 0u);
        fails[k] = nfail;
    }
}

int main(int argc, char** argv) {
    int part = argc > 1 ? atoi(argv[1]) : 1;
    unsigned zero = 0;
    CK(cudaMemcpyToSymbol(x, &zero, 4));
    CK(cudaMemcpyToSymbol(lock, &zero, 4));
    CK(cudaMemcpyToSymbol(cs_count, &zero, 4));
    int bad = 0;
    if (part == 1 || part == 2 || part == 4) {
        int n = part == 1 ? 8 : 256;
        unsigned* d; CK(cudaMalloc(&d, n * 4));
        if (part == 1) part1<<<1, 32>>>(d);
        else if (part == 2) part2<<<1, 256>>>(d);
        else {
            unsigned* off; CK(cudaMalloc(&off, 256 * 4));
            CK(cudaMemset(off, 0, 256 * 4));
            part4<<<1, 256>>>(d, off);
        }
        CK(cudaDeviceSynchronize());
        std::vector<unsigned> h(n); CK(cudaMemcpy(h.data(), d, n * 4, cudaMemcpyDeviceToHost));
        std::vector<int> seen(n, 0);
        for (int i = 0; i < n; i++) {
            if (h[i] >= (unsigned)n || seen[h[i]]++) bad++;
            if (part == 1 && h[i] != (unsigned)i) bad++;
        }
        printf("part%d: %d values, %s\n", part, n, bad ? "WRONG" : "ok");
    } else {
        int B = argc > 2 ? atoi(argv[2]) : 4, W = argc > 3 ? atoi(argv[3]) : 4;
        int iters = argc > 4 ? atoi(argv[4]) : 8;
        int n = B * W * iters;
        unsigned *order, *ex, *fails;
        CK(cudaMalloc(&order, n * 4)); CK(cudaMalloc(&ex, n * 4)); CK(cudaMalloc(&fails, n * 4));
        part3<<<B, W * 32>>>(iters, order, ex, fails);
        CK(cudaDeviceSynchronize());
        std::vector<unsigned> o(n), e(n), f(n);
        CK(cudaMemcpy(o.data(), order, n * 4, cudaMemcpyDeviceToHost));
        CK(cudaMemcpy(e.data(), ex, n * 4, cudaMemcpyDeviceToHost));
        CK(cudaMemcpy(f.data(), fails, n * 4, cudaMemcpyDeviceToHost));
        unsigned cnt; CK(cudaMemcpyFromSymbol(&cnt, cs_count, 4));
        long tf = 0;
        for (int k = 0; k < n; k++) { if (e[k] != o[k]) bad++; tf += f[k]; }
        if (cnt != (unsigned)n) bad++;
        printf("part3: B=%d W=%d iters=%d critical sections %u, failed CAS %ld, %s\n",
               B, W, iters, cnt, tf, bad ? "WRONG" : "ok");
        // critical-section order, for analyze_atom.py
        printf("ORDER");
        for (int k = 0; k < n; k++) printf(" %u", o[k]);
        printf("\n");
    }
    return bad ? 1 : 0;
}

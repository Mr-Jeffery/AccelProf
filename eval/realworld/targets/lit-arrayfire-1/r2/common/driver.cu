// cuRace T21a lit-arrayfire-1 (R2): host driver for the verbatim ArrayFire CUDA scan-by-key kernels
// (src/backend/cuda/kernel/scan_dim_by_key_impl.hpp and scan_first_by_key_impl.hpp, buggy a35a2d08 / fixed a7a297ba).
// Identical for both variants; the variant is selected only by the -I$SRC that finds the kernel files.
// It calls the files' own host entry points (scan_dim_by_key / scan_first_by_key), which launch
//   scan_dim_nonfinal_kernel<int,int,int,af_add_t,1,8,true>   grid (1,2)  block (32,8)   (dims 32x300, 2 blocks along dim 1)
//   scan_nonfinal_kernel<int,int,int,af_add_t,256,true>       grid (2,1)  block (256,1)  (dims 8193,    2 blocks along dim 0)
// followed by the *_final and bcast kernels of the same files.   usage: driver [reps]   (default 1)
#include <cstdio>
#include <cstdlib>
#include <vector>

#include "src/backend/cuda/kernel/scan_first_by_key_impl.hpp"
#include "src/backend/cuda/kernel/scan_dim_by_key_impl.hpp"

template<typename T> static T* upload(const std::vector<T> &h)
{
    T *d = NULL;
    CUDA_CHECK(cudaMalloc((void**)&d, h.size() * sizeof(T)));
    CUDA_CHECK(cudaMemcpy(d, h.data(), h.size() * sizeof(T), cudaMemcpyHostToDevice));
    return d;
}

static void mkstrides(const dim_t *dims, dim_t *strides)
{
    strides[0] = 1;
    for (int k = 1; k < 4; k++) strides[k] = strides[k - 1] * dims[k - 1];
}

// scan along dim 1 of a 32 x 300 array: nonfinal kernel with DIMY = 8 and blocks_all[1] = divup(300, 8 * 32) = 2
static long run_dim(int reps, unsigned long long *sum)
{
    dim_t dims[4] = {32, 300, 1, 1}, strides[4];
    mkstrides(dims, strides);
    const size_t n = (size_t)(strides[3] * dims[3]);
    std::vector<int> hin(n), hkey(n);
    for (int y = 0; y < dims[1]; y++)
        for (int x = 0; x < dims[0]; x++) {
            hin[x + y * dims[0]]  = 1 + (x * 7 + y * 3) % 5;
            hkey[x + y * dims[0]] = (y + x) / 37;          // segments of 37 along dim 1, shifted per column
        }
    int *din = upload(hin), *dkey = upload(hkey), *dout = NULL;
    CUDA_CHECK(cudaMalloc((void**)&dout, n * sizeof(int)));
    long bad = 0;
    for (int r = 0; r < reps; r++) {
        CUDA_CHECK(cudaMemset(dout, 0, n * sizeof(int)));
        cuda::Param<int> out;
        out.ptr = dout;
        for (int k = 0; k < 4; k++) { out.dims[k] = dims[k]; out.strides[k] = strides[k]; }
        cuda::CParam<int> cin(din, dims, strides), ckey(dkey, dims, strides);
        cuda::kernel::scan_dim_by_key<int, int, int, af_add_t, 1, true>(out, cin, ckey);
        CUDA_CHECK(cudaDeviceSynchronize());
        std::vector<int> hout(n);
        CUDA_CHECK(cudaMemcpy(hout.data(), dout, n * sizeof(int), cudaMemcpyDeviceToHost));
        long b = 0;
        for (int x = 0; x < dims[0]; x++) {
            int acc = 0;
            for (int y = 0; y < dims[1]; y++) {
                size_t i = x + (size_t)y * dims[0];
                acc = (y == 0 || hkey[i] != hkey[i - dims[0]]) ? hin[i] : acc + hin[i];
                if (hout[i] != acc) b++;
            }
        }
        bad += b;
        if (r == 0) for (size_t i = 0; i < n; i++) *sum = *sum * 1315423911ull + (unsigned)hout[i];
    }
    cudaFree(din); cudaFree(dkey); cudaFree(dout);
    return bad;
}

// scan along dim 0 of an 8193 x 1 array: threads_x = 256, blocks_x = divup(8193, 256 * 32) = 2
static long run_first(int reps, unsigned long long *sum)
{
    dim_t dims[4] = {8193, 1, 1, 1}, strides[4];
    mkstrides(dims, strides);
    const size_t n = (size_t)(strides[3] * dims[3]);
    std::vector<int> hin(n), hkey(n);
    for (size_t x = 0; x < n; x++) {
        hin[x]  = 1 + (int)((x * 7) % 5);
        hkey[x] = (int)(x / 300);                           // segments of 300; a segment crosses the block boundary
    }
    int *din = upload(hin), *dkey = upload(hkey), *dout = NULL;
    CUDA_CHECK(cudaMalloc((void**)&dout, n * sizeof(int)));
    long bad = 0;
    for (int r = 0; r < reps; r++) {
        CUDA_CHECK(cudaMemset(dout, 0, n * sizeof(int)));
        cuda::Param<int> out;
        out.ptr = dout;
        for (int k = 0; k < 4; k++) { out.dims[k] = dims[k]; out.strides[k] = strides[k]; }
        cuda::CParam<int> cin(din, dims, strides), ckey(dkey, dims, strides);
        cuda::kernel::scan_first_by_key<int, int, int, af_add_t, true>(out, cin, ckey);
        CUDA_CHECK(cudaDeviceSynchronize());
        std::vector<int> hout(n);
        CUDA_CHECK(cudaMemcpy(hout.data(), dout, n * sizeof(int), cudaMemcpyDeviceToHost));
        long b = 0;
        int acc = 0;
        for (size_t i = 0; i < n; i++) {
            acc = (i == 0 || hkey[i] != hkey[i - 1]) ? hin[i] : acc + hin[i];
            if (hout[i] != acc) b++;
        }
        bad += b;
        if (r == 0) for (size_t i = 0; i < n; i++) *sum = *sum * 1315423911ull + (unsigned)hout[i];
    }
    cudaFree(din); cudaFree(dkey); cudaFree(dout);
    return bad;
}

int main(int argc, char **argv)
{
    int reps = argc > 1 ? atoi(argv[1]) : 1;
    if (reps < 1) reps = 1;
    unsigned long long s1 = 0, s2 = 0;
    long b1 = run_dim(reps, &s1);
    printf("scan_dim_by_key   dims 32x300  (dim 1, DIMY 8, 2 blocks) reps %d: mismatches vs host reference %ld, checksum %016llx\n", reps, b1, s1);
    long b2 = run_first(reps, &s2);
    printf("scan_first_by_key dims 8193    (dim 0, DIMX 256, 2 blocks) reps %d: mismatches vs host reference %ld, checksum %016llx\n", reps, b2, s2);
    printf("lit-arrayfire-1 driver done\n");
    return 0;
}

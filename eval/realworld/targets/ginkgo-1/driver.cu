// T21a ginkgo-1 driver ("direct launch"): launches Ginkgo's generic_kernel_col_reduction_2d_blocked
// (common/cuda_hip/base/kernel_launch_reduction.hpp, namespace gko::kernels::cuda) directly, exactly as
// run_kernel_col_reduction_cached would, but with a one-block grid so that the kernel's column-block loop runs twice:
//   grid (1, 1), default_block_size threads, rows = 8, cols = 64 (col_step = gridDim.y * warp_size = 32 -> 2 iterations).
// The kernel header is the checked-out revision's own header (nothing is copied or edited); this file only supplies the
// functors the kernel is templated on.  The real launch path needs cols > 65535*32 to get a second iteration with the full
// 65535-block grid; the same loop is reached here with a one-block grid.
#include "common/unified/base/kernel_launch_reduction.hpp"

#include <cstdio>
#include <vector>

namespace {

struct rw_fn {  // fn(row, col, args...)
    __device__ double operator()(gko::int64 row, gko::int64 col) const
    {
        return static_cast<double>(row + col);
    }
};

struct rw_op {  // ReductionOp
    __device__ double operator()(double a, double b) const { return a + b; }
};

struct rw_fin {  // FinalizeOp
    __device__ double operator()(double a) const { return a; }
};

}  // namespace


int main()
{
    using namespace gko::kernels::cuda;
    const gko::int64 rows = 8;
    const gko::int64 cols = 64;
    double* d_result{};
    if (cudaMalloc(&d_result, sizeof(double) * cols) != cudaSuccess) {
        std::printf("ginkgo-1 driver: cudaMalloc failed\n");
        return 2;
    }
    cudaMemset(d_result, 0, sizeof(double) * cols);
    std::printf("ginkgo-1 driver: default_block_size=%d warp_size=%d rows=%ld cols=%ld grid=(1,1)\n",
                static_cast<int>(default_block_size), static_cast<int>(config::warp_size),
                static_cast<long>(rows), static_cast<long>(cols));
    generic_kernel_col_reduction_2d_blocked<<<dim3(1, 1), default_block_size>>>(
        rows, cols, rw_fn{}, rw_op{}, rw_fin{}, 0.0, d_result);
    const cudaError_t err = cudaDeviceSynchronize();
    if (err != cudaSuccess) {
        std::printf("ginkgo-1 driver: kernel failed: %s\n", cudaGetErrorString(err));
        return 3;
    }
    std::vector<double> h(cols);
    cudaMemcpy(h.data(), d_result, sizeof(double) * cols, cudaMemcpyDeviceToHost);
    int bad = 0;
    for (gko::int64 c = 0; c < cols; c++) {
        // sum over rows r of (r + c) = rows*(rows-1)/2 + rows*c
        const double expect = 0.5 * rows * (rows - 1) + static_cast<double>(rows) * c;
        if (h[c] != expect) {
            bad++;
        }
    }
    std::printf("ginkgo-1 driver: %d of %ld columns differ from the reference %s\n", bad, static_cast<long>(cols),
                bad ? "MISMATCH" : "OK");
    cudaFree(d_result);
    return bad ? 1 : 0;
}

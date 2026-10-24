// T21c pcl-new-1 host main (R2).  The verbatim gpu/features/src/normal_3d.cu of PCL 66e1d0ea8c is #included (with warp.hpp, internal.hpp and the
// other PCL headers it includes, all byte-for-byte from the same commit).
// The kernel is launched exactly as pcl::device::computeNormals() (normal_3d.cu, last function) launches it:
//     NormalsEstimator est; est.indices = nn_indices; est.sizes = nn_indices.sizes; est.points = cloud; est.normals = normals;
//     EstimateNormalsKernel<<<divUp(normals.size(), NormalsEstimator::WAPRS), NormalsEstimator::CTA_SIZE>>>(est);
// computeNormals() takes DeviceArray objects whose allocation lives in PCL's non-header device_memory.cpp, so this driver fills the
// five estimator fields from raw cudaMalloc pointers (same layout: PtrStep<int> indices, int sizes, float4 points, PtrSz<float4> normals).
#include "gpu/features/src/normal_3d.cu"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); return 2; } } while (0)

int main(int argc, char** argv)
{
    using namespace pcl::device;
    const int N = argc > 1 ? std::atoi(argv[1]) : 1000;     // 1,000 points -> 1,000 warps -> grid 125 x 256 threads
    const int K = argc > 2 ? std::atoi(argv[2]) : 40;       // neighbours per point (> 32: lanes 0..7 loop twice)
    const int PITCH_INTS = 64;                              // row pitch of the neighbour-index matrix (K <= 64)

    // a slightly noisy plane z = 0.1 x + 0.01 sin(i) on a 40-wide grid; the neighbours of point i are the K following indices (mod N)
    std::vector<float4> h_pts(N);
    for (int i = 0; i < N; ++i) {
        float x = 0.05f * (i % 40), y = 0.05f * (i / 40);
        h_pts[i] = make_float4(x, y, 0.1f * x + 0.01f * std::sin((float)i), 0.f);
    }
    std::vector<int> h_idx((size_t)N * PITCH_INTS, 0), h_sizes(N, K);
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < K; ++j) h_idx[(size_t)i * PITCH_INTS + j] = (i + j) % N;

    float4 *d_pts = nullptr, *d_normals = nullptr; int *d_idx = nullptr, *d_sizes = nullptr;
    CK(cudaMalloc(&d_pts, N * sizeof(float4)));
    CK(cudaMalloc(&d_normals, N * sizeof(float4)));
    CK(cudaMalloc(&d_idx, h_idx.size() * sizeof(int)));
    CK(cudaMalloc(&d_sizes, N * sizeof(int)));
    CK(cudaMemcpy(d_pts, h_pts.data(), N * sizeof(float4), cudaMemcpyHostToDevice));
    CK(cudaMemcpy(d_idx, h_idx.data(), h_idx.size() * sizeof(int), cudaMemcpyHostToDevice));
    CK(cudaMemcpy(d_sizes, h_sizes.data(), N * sizeof(int), cudaMemcpyHostToDevice));
    CK(cudaMemset(d_normals, 0, N * sizeof(float4)));

    NormalsEstimator est;
    est.indices.data = d_idx; est.indices.step = PITCH_INTS * sizeof(int);
    est.sizes = d_sizes;
    est.points = d_pts;
    est.normals.data = d_normals; est.normals.size = N;

    int block = NormalsEstimator::CTA_SIZE;
    int grid = pcl::device::divUp(N, (int)NormalsEstimator::WAPRS);
    EstimateNormalsKernel<<<grid, block>>>(est);
    CK(cudaGetLastError());
    CK(cudaDeviceSynchronize());

    std::vector<float4> h_n(N);
    CK(cudaMemcpy(h_n.data(), d_normals, N * sizeof(float4), cudaMemcpyDeviceToHost));
    double sumz = 0; int nonzero = 0;
    for (int i = 0; i < N; ++i) { sumz += std::fabs(h_n[i].z); nonzero += (h_n[i].x != 0.f || h_n[i].y != 0.f || h_n[i].z != 0.f); }
    std::printf("EstimateNormalsKernel N=%d K=%d grid=%d block=%d normal[0]=(%g,%g,%g) curvature[0]=%g mean|nz|=%g nonzero=%d/%d\n",
                N, K, grid, block, h_n[0].x, h_n[0].y, h_n[0].z, h_n[0].w, sumz / N, nonzero, N);
    return 0;
}

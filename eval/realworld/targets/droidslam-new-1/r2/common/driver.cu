// T21c droidslam-new-1 host main (R2).  The verbatim src/droid_kernels.cu of DROID-SLAM 2dfd39f0dc is #included whole.
// The kernel is launched exactly as frame_distance_cuda() (droid_kernels.cu) launches it:
//     frame_distance_kernel<<<num, THREADS=256>>>(poses, disps, intrinsics, ii, jj, dist, beta)
// with the same PackedTensorAccessor32<..., RestrictPtrTraits> arguments, here built from raw cudaMalloc pointers (the accessor class is a
// header-only ATen template; no libtorch symbol is linked: the file's torch::Tensor host functions are discarded by --gc-sections).
// Input: 4 frames, 48x64 disparity maps (DROID's 1/8-resolution maps), the 6 pairs (i<j), beta = 0.5.
#include "src/droid_kernels.cu"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); return 2; } } while (0)

int main(int argc, char** argv)
{
    const int NF = 4, HT = argc > 1 ? std::atoi(argv[1]) : 48, WD = argc > 2 ? std::atoi(argv[2]) : 64;
    const float beta = 0.5f;
    std::vector<LongType> h_ii, h_jj;
    for (int i = 0; i < NF; ++i) for (int j = i + 1; j < NF; ++j) { h_ii.push_back(i); h_jj.push_back(j); }
    const int num = (int)h_ii.size();   // 6 blocks of 256 threads

    // poses [NF,7] = (tx,ty,tz,qx,qy,qz,qw) with small motion; disps [NF,HT,WD] in (0.1, 1); intrinsics (fx,fy,cx,cy)
    std::vector<float> h_poses(NF * 7), h_disps((size_t)NF * HT * WD), h_intr = {48.f, 48.f, WD / 2.f, HT / 2.f};
    for (int f = 0; f < NF; ++f) {
        float a = 0.02f * f;
        float q[4] = {0.f, std::sin(a / 2), 0.f, std::cos(a / 2)};   // rotation about y
        float t[3] = {0.05f * f, 0.01f * f, 0.02f * f};
        for (int k = 0; k < 3; ++k) h_poses[f * 7 + k] = t[k];
        for (int k = 0; k < 4; ++k) h_poses[f * 7 + 3 + k] = q[k];
    }
    unsigned s = 777u;
    for (auto& d : h_disps) { s = s * 1664525u + 1013904223u; d = 0.1f + 0.9f * (((s >> 8) & 0xffff) / 65536.0f); }

    float *d_poses, *d_disps, *d_intr, *d_dist; LongType *d_ii, *d_jj;
    CK(cudaMalloc(&d_poses, h_poses.size() * 4)); CK(cudaMalloc(&d_disps, h_disps.size() * 4)); CK(cudaMalloc(&d_intr, 16));
    CK(cudaMalloc(&d_dist, num * 4)); CK(cudaMalloc(&d_ii, num * sizeof(LongType))); CK(cudaMalloc(&d_jj, num * sizeof(LongType)));
    CK(cudaMemcpy(d_poses, h_poses.data(), h_poses.size() * 4, cudaMemcpyHostToDevice));
    CK(cudaMemcpy(d_disps, h_disps.data(), h_disps.size() * 4, cudaMemcpyHostToDevice));
    CK(cudaMemcpy(d_intr, h_intr.data(), 16, cudaMemcpyHostToDevice));
    CK(cudaMemcpy(d_ii, h_ii.data(), num * sizeof(LongType), cudaMemcpyHostToDevice));
    CK(cudaMemcpy(d_jj, h_jj.data(), num * sizeof(LongType), cudaMemcpyHostToDevice));
    CK(cudaMemset(d_dist, 0, num * 4));

    int32_t sz_poses[2] = {NF, 7}, st_poses[2] = {7, 1};
    int32_t sz_disps[3] = {NF, HT, WD}, st_disps[3] = {HT * WD, WD, 1};
    int32_t sz_intr[1] = {4}, st_intr[1] = {1};
    int32_t sz_n[1] = {num}, st_n[1] = {1};
    frame_distance_kernel<<<num, THREADS>>>(
        torch::PackedTensorAccessor32<float, 2, torch::RestrictPtrTraits>(d_poses, sz_poses, st_poses),
        torch::PackedTensorAccessor32<float, 3, torch::RestrictPtrTraits>(d_disps, sz_disps, st_disps),
        torch::PackedTensorAccessor32<float, 1, torch::RestrictPtrTraits>(d_intr, sz_intr, st_intr),
        torch::PackedTensorAccessor32<LongType, 1, torch::RestrictPtrTraits>(d_ii, sz_n, st_n),
        torch::PackedTensorAccessor32<LongType, 1, torch::RestrictPtrTraits>(d_jj, sz_n, st_n),
        torch::PackedTensorAccessor32<float, 1, torch::RestrictPtrTraits>(d_dist, sz_n, st_n), beta);
    CK(cudaGetLastError());
    CK(cudaDeviceSynchronize());

    std::vector<float> h_dist(num);
    CK(cudaMemcpy(h_dist.data(), d_dist, num * 4, cudaMemcpyDeviceToHost));
    std::printf("frame_distance_kernel frames=%d disp=%dx%d pairs=%d grid=%d block=%d dist=", NF, HT, WD, num, num, THREADS);
    for (int i = 0; i < num; ++i) std::printf("%s%g", i ? "," : "", h_dist[i]);
    std::printf("\n");
    return 0;
}

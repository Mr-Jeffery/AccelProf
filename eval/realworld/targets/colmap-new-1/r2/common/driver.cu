// T21c colmap-new-1 host main (R2).  The verbatim src/colmap/mvs/patch_match_cuda.cu of the pinned commit 6db3867f (with the project's own mvs/util headers,
// also copied, plus gpu_mat_prng.cu and gpu_mat_ref_image.cu) is #included.  The host class PatchMatchCuda in that file is compiled but never used (it
// needs Image/Bitmap/Problem I/O from the rest of COLMAP); instead this main performs the same steps PatchMatchCuda::{InitRefImage, InitSourceImages,
// InitTransforms, InitWorkspaceMemory, RunWithWindowSizeAndStep} perform for the first sweep (rotation 0) and launches the real kernels exactly as that
// code does, with the same grid and block (sweep_grid = ceil(W/32), sweep_block = 32 = THREADS_PER_BLOCK):
//   ComputeInitialCost<7,1><<<ceil(W/32), 32>>>  then  SweepFromTopToBottom<7,1,false,false,false><<<ceil(W/32), 32>>>
// with window radius 3 (kWindowSize 7), step 1, geom_consistency off, num_samples 5, W x H reference image and NS source images.
// Stubs defined here: colmap::CudaSafeCall / CudaCheck / CudaSyncAndCheck (cudacc.cc is not compiled).
#include "colmap/mvs/patch_match_cuda.cu"
#include "colmap/mvs/gpu_mat_prng.cu"
#include "colmap/mvs/gpu_mat_ref_image.cu"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

namespace colmap {
void CudaSafeCall(const cudaError_t error, const std::string& file, const int line) {
  if (error != cudaSuccess) {
    std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(error), file.c_str(), line);
    std::exit(2);
  }
}
void CudaCheck(const char* file, const int line) { CudaSafeCall(cudaGetLastError(), file, line); }
void CudaSyncAndCheck(const char* file, const int line) {
  CudaSafeCall(cudaDeviceSynchronize(), file, line);
  CudaCheck(file, line);
}
}  // namespace colmap

using namespace colmap;
using namespace colmap::mvs;

static cudaTextureDesc MakeDesc(cudaTextureFilterMode filter, cudaTextureReadMode read) {   // as in PatchMatchCuda::Init*
  cudaTextureDesc d;
  std::memset(&d, 0, sizeof(d));
  d.addressMode[0] = cudaAddressModeBorder;
  d.addressMode[1] = cudaAddressModeBorder;
  d.addressMode[2] = cudaAddressModeBorder;
  d.filterMode = filter;
  d.readMode = read;
  d.normalizedCoords = false;
  return d;
}

int main(int argc, char** argv) {
  constexpr int kWindowRadius = 3, kWindowSize = 2 * kWindowRadius + 1, kWindowStep = 1;
  const int W = argc > 1 ? std::atoi(argv[1]) : 32;     // reference image width: 32 -> one 32-thread block
  const int H = argc > 2 ? std::atoi(argv[2]) : 32;     // rows swept by the kernels
  const int NS = argc > 3 ? std::atoi(argv[3]) : 2;     // source images
  const float depth_min = 1.0f, depth_max = 3.0f;
  const float sigma_spatial = kWindowRadius, sigma_color = 0.2f;   // PatchMatchOptions defaults (sigma_spatial <= 0 -> window_radius)
  const float fx = 40.f, fy = 40.f, cx = W / 2.f, cy = H / 2.f;

  // ---- images: smooth textured reference, source images are horizontally shifted copies ----
  auto pix = [&](int x, int y) {
    float v = 128.f + 90.f * std::sin(0.45f * x) * std::cos(0.37f * y) + 30.f * std::sin(0.11f * (x + 2 * y)) + (float)((x * 7 + y * 13) % 11);
    return (uint8_t)std::fmax(0.f, std::fmin(255.f, v));
  };
  std::vector<uint8_t> h_ref((size_t)W * H), h_src((size_t)W * H * NS);
  for (int y = 0; y < H; ++y) for (int x = 0; x < W; ++x) {
    h_ref[(size_t)y * W + x] = pix(x, y);
    for (int i = 0; i < NS; ++i) h_src[((size_t)i * H + y) * W + x] = pix(x + 3 * (i + 1), y);
  }

  // ---- InitRefImage / BindRefImageTexture ----
  GpuMatRefImage ref_image(W, H);
  ref_image.Filter(h_ref.data(), kWindowRadius, kWindowStep, sigma_spatial, sigma_color);
  auto ref_tex = CudaArrayLayeredTexture<uint8_t>::FromGpuMat(MakeDesc(cudaFilterModePoint, cudaReadModeNormalizedFloat), *ref_image.image);

  // ---- InitSourceImages ----
  auto src_tex = CudaArrayLayeredTexture<uint8_t>::FromHostArray(MakeDesc(cudaFilterModeLinear, cudaReadModeNormalizedFloat), W, H, NS, h_src.data());

  // ---- InitTransforms (rotation 0): calibration constants and the 43-float pose record per source image ----
  float ref_K_host[4] = {fx, cx - 0.5f, fy, cy - 0.5f};
  float ref_inv_K_host[4] = {1.0f / ref_K_host[0], -ref_K_host[1] / ref_K_host[0], 1.0f / ref_K_host[2], -ref_K_host[3] / ref_K_host[2]};
  CUDA_SAFE_CALL(cudaMemcpyToSymbol(ref_K, ref_K_host, sizeof(float) * 4, 0, cudaMemcpyHostToDevice));
  CUDA_SAFE_CALL(cudaMemcpyToSymbol(ref_inv_K, ref_inv_K_host, sizeof(float) * 4, 0, cudaMemcpyHostToDevice));
  const int kNumTformParams = 4 + 9 + 3 + 3 + 12 + 12;
  std::vector<float> poses((size_t)kNumTformParams * NS);
  for (int i = 0; i < NS; ++i) {      // reference camera = identity pose; source i = pure translation (0.1*(i+1), 0, 0), same intrinsics
    const float Tx = 0.1f * (i + 1);
    const float K[4] = {fx, cx - 0.5f, fy, cy - 0.5f}, R[9] = {1, 0, 0, 0, 1, 0, 0, 0, 1}, T[3] = {Tx, 0, 0}, C[3] = {-Tx, 0, 0};
    const float P[12] = {fx, 0, cx - 0.5f, fx * Tx, 0, fy, cy - 0.5f, 0, 0, 0, 1, 0};
    const float invP[12] = {1 / fx, 0, -(cx - 0.5f) / fx, C[0], 0, 1 / fy, -(cy - 0.5f) / fy, 0, 0, 0, 1, 0};
    float* p = &poses[(size_t)i * kNumTformParams];
    std::memcpy(p, K, 16); std::memcpy(p + 4, R, 36); std::memcpy(p + 13, T, 12); std::memcpy(p + 16, C, 12);
    std::memcpy(p + 19, P, 48); std::memcpy(p + 31, invP, 48);
  }
  auto poses_tex = CudaArrayLayeredTexture<float>::FromHostArray(MakeDesc(cudaFilterModePoint, cudaReadModeElementType), kNumTformParams, NS, 1, poses.data());

  // ---- InitWorkspaceMemory ----
  GpuMatPRNG rand_state_map(W, H);
  GpuMat<float> depth_map(W, H);
  depth_map.FillWithRandomNumbers(depth_min, depth_max, rand_state_map);
  GpuMat<float> normal_map(W, H, 3);
  GpuMat<float> sel_prob_map(W, H, NS), prev_sel_prob_map(W, H, NS), cost_map(W, H, NS);
  prev_sel_prob_map.FillWithScalar(0.5f);
  GpuMat<float> global_workspace(std::max(W, H), NS, 2);
  GpuMat<uint8_t> consistency_mask(0, 0, 0);

  const dim3 sweep_block(THREADS_PER_BLOCK, 1, 1), sweep_grid((W - 1) / THREADS_PER_BLOCK + 1, 1, 1);                            // ComputeCudaConfig()
  const dim3 elem_block(THREADS_PER_BLOCK, THREADS_PER_BLOCK, 1), elem_grid((W - 1) / THREADS_PER_BLOCK + 1, (H - 1) / THREADS_PER_BLOCK + 1, 1);
  InitNormalMap<<<elem_grid, elem_block>>>(normal_map.View(), rand_state_map.View());

  // ---- RunWithWindowSizeAndStep<7,1>: ComputeInitialCost, then the first sweep ----
  CUDA_SYNC_AND_CHECK();
  ComputeInitialCost<kWindowSize, kWindowStep><<<sweep_grid, sweep_block>>>(
      cost_map.View(), depth_map.View(), normal_map.View(), ref_tex->GetObj(), ref_image.sum_image->View(), ref_image.squared_sum_image->View(),
      src_tex->GetObj(), poses_tex->GetObj(), sigma_spatial, sigma_color);
  CUDA_SYNC_AND_CHECK();

  SweepOptions so;
  so.depth_min = depth_min; so.depth_max = depth_max; so.sigma_spatial = sigma_spatial; so.sigma_color = sigma_color;
  so.num_samples = 5; so.ncc_sigma = 0.6f;
  so.min_triangulation_angle = DEG2RAD(1.0f); so.incident_angle_sigma = 0.9f;
  so.geom_consistency_regularizer = 0.3f; so.geom_consistency_max_cost = 3.0f;
  so.filter_min_ncc = 0.1f; so.filter_min_triangulation_angle = DEG2RAD(3.0f); so.filter_min_num_consistent = 2; so.filter_geom_consistency_max_cost = 1.0f;
  so.perturbation = 1.0f / std::pow(2.0f, 0 + 0 / 4.0f);       // iter 0, sweep 0
  so.prev_sel_prob_weight = 0.0f;                              // (iter*4 + sweep) / total_num_steps

  SweepFromTopToBottom<kWindowSize, kWindowStep, false, false, false><<<sweep_grid, sweep_block>>>(
      global_workspace.View(), rand_state_map.View(), cost_map.View(), depth_map.View(), normal_map.View(), consistency_mask.View(),
      sel_prob_map.View(), prev_sel_prob_map.View(), ref_tex->GetObj(), ref_image.sum_image->View(), ref_image.squared_sum_image->View(),
      src_tex->GetObj(), 0, poses_tex->GetObj(), so);
  CUDA_SYNC_AND_CHECK();

  // ---- cheap host check: depth / normal / cost maps are finite after the sweep ----
  std::vector<float> h_depth((size_t)W * H), h_cost((size_t)W * H * NS), h_normal((size_t)W * H * 3);
  depth_map.CopyToHost(h_depth.data(), W * sizeof(float));
  cost_map.CopyToHost(h_cost.data(), W * sizeof(float));
  normal_map.CopyToHost(h_normal.data(), W * sizeof(float));
  int bad = 0; double dsum = 0, csum = 0;
  for (float v : h_depth) { bad += !(std::isfinite(v) && v > 0.f); dsum += v; }
  for (float v : h_cost) { bad += !(std::isfinite(v) && v >= 0.f && v <= 2.f); csum += v; }
  for (float v : h_normal) bad += !std::isfinite(v);
  std::printf("ComputeInitialCost<%d,%d> + SweepFromTopToBottom<%d,%d,0,0,0> W=%d H=%d NS=%d grid=%u block=%u mean_depth=%.4f mean_cost=%.4f nonfinite_or_out_of_range=%d\n",
              kWindowSize, kWindowStep, kWindowSize, kWindowStep, W, H, NS, sweep_grid.x, sweep_block.x, dsum / h_depth.size(), csum / h_cost.size(), bad);
  return 0;
}

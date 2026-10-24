// T21c opencv_contrib-new-1 host main (R2).  The verbatim modules/cudaobjdetect/src/cuda/hog.cu of opencv_contrib eca97a4adb is #included.
// It is driven exactly as cv::cuda::HOG_Impl::computeBlockHistograms() (modules/cudaobjdetect/src/hog.cpp) drives it for the
// default configuration (win 64x128, block 16x16, block stride 8x8, cell 8x8, 9 bins, sigma = (16+1)/2 = 8.5):
//   hog::set_up_constants(...);  hog::compute_gradients_8UC1(...) [replaced here by host-filled grad/qangle];  hog::compute_hists(...)
// compute_hists() (verbatim, in hog.cu) launches compute_hists_kernel_many_blocks<4><<<(2,15), (32,2,4), smem>>>.
// Stub: cv::error() (OpenCV core's failure hook behind cudaSafeCall; a library function, not part of the headers).
#include "modules/cudaobjdetect/src/cuda/hog.cu"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

namespace cv {
void error(Error::Code code, const String& err, const char* func, const char* file, int line)
{
    std::fprintf(stderr, "OpenCV error %d: %s (%s, %s:%d)\n", (int)code, err.c_str(), func ? func : "", file ? file : "", line);
    std::exit(2);
}
}

#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); return 2; } } while (0)

int main(int argc, char** argv)
{
    using namespace cv::cuda;
    namespace H = cv::cuda::device::hog;

    const int height = argc > 2 ? std::atoi(argv[2]) : 128, width = argc > 1 ? std::atoi(argv[1]) : 64;   // 64x128 image
    const int nbins = 9, bs_x = 8, bs_y = 8, cell_x = 8, cell_y = 8, ncb_x = 2, ncb_y = 2;
    const int win_w = 64, win_h = 128, blk_w = 16, blk_h = 16;
    const int nblocks_win_x = (win_w - blk_w) / bs_x + 1, nblocks_win_y = (win_h - blk_h) / bs_y + 1;   // 7 x 15
    const float sigma = (blk_w + 1) / 2.0f;                                                              // getWinSigma() default
    const int img_block_w = (width - ncb_x * cell_x + bs_x) / bs_x, img_block_h = (height - ncb_y * cell_y + bs_y) / bs_y;
    const int block_hist_size = nbins * ncb_x * ncb_y;

    // grad: CV_32FC2 (vote for bin.x, vote for bin.y), qangle: CV_8UC2 (the two bins) -- pseudo-random, as the gradient kernel would produce
    std::vector<float> h_grad((size_t)height * width * 2);
    std::vector<unsigned char> h_q((size_t)height * width * 2);
    unsigned s = 4242u;
    for (size_t i = 0; i < (size_t)height * width; ++i) {
        s = s * 1664525u + 1013904223u; float mag = ((s >> 8) & 0xffff) / 65536.0f * 100.0f;
        s = s * 1664525u + 1013904223u; float frac = ((s >> 8) & 0xffff) / 65536.0f;
        s = s * 1664525u + 1013904223u; unsigned b = (s >> 8) % nbins;
        h_grad[2 * i] = mag * (1.f - frac); h_grad[2 * i + 1] = mag * frac;
        h_q[2 * i] = (unsigned char)b; h_q[2 * i + 1] = (unsigned char)((b + 1) % nbins);
    }
    float* d_grad = nullptr; unsigned char* d_q = nullptr; float* d_hists = nullptr;
    const size_t nhist = (size_t)img_block_h * img_block_w * block_hist_size;
    CK(cudaMalloc(&d_grad, h_grad.size() * sizeof(float)));
    CK(cudaMalloc(&d_q, h_q.size()));
    CK(cudaMalloc(&d_hists, nhist * sizeof(float)));
    CK(cudaMemcpy(d_grad, h_grad.data(), h_grad.size() * sizeof(float), cudaMemcpyHostToDevice));
    CK(cudaMemcpy(d_q, h_q.data(), h_q.size(), cudaMemcpyHostToDevice));
    CK(cudaMemset(d_hists, 0, nhist * sizeof(float)));

    cudaStream_t stream = 0;
    PtrStepSzf grad(height, width, d_grad, (size_t)width * 2 * sizeof(float));
    PtrStepSzb qangle(height, width, d_q, (size_t)width * 2);

    H::set_up_constants(nbins, bs_x, bs_y, nblocks_win_x, nblocks_win_y, ncb_x, ncb_y, stream);
    H::compute_hists(nbins, bs_x, bs_y, height, width, grad, qangle, sigma, d_hists, cell_x, cell_y, ncb_x, ncb_y, stream);
    CK(cudaGetLastError());
    CK(cudaDeviceSynchronize());

    std::vector<float> h_hists(nhist);
    CK(cudaMemcpy(h_hists.data(), d_hists, nhist * sizeof(float), cudaMemcpyDeviceToHost));
    double sum = 0; for (float v : h_hists) sum += v;
    std::printf("compute_hists_kernel_many_blocks<4> img=%dx%d block_hists=%dx%dx%d grid=(%d,%d) block=(32,2,4) sum=%g\n",
                width, height, img_block_h, img_block_w, block_hist_size, (img_block_w + 3) / 4, img_block_h, sum);
    return 0;
}

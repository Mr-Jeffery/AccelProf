// cuRace T21a opencv-2 (R2): host driver for the verbatim OpenCV 2.4 file modules/gpu/src/cuda/canny.cu
// (buggy ce42593f / fixed 7fd21d21), which it #includes.  Identical for both variants.
// It calls the file's own host function canny::edgesHysteresisLocal(map, st), which launches
//   canny::edgesHysteresisLocalKernel<<<(4,4), (16,16)>>>(map, st)   on a 64 x 64 int edge map (0 / 1 / 2),
// the kernel under test (16 unrolled flood-fill steps on the volatile 18 x 18 shared tile smem).
// Input: 1-chains (two vertical and two horizontal lines per 16x16 tile, spanning all warps of the block) seeded with 2.
// The result is compared with a host simulation of the barrier-correct (step-synchronous) semantics; mismatches are printed.
//   usage: driver
#include <cstdio>
#include <cstdlib>
#include <vector>

#include "modules/gpu/src/cuda/canny.cu"

static const int ROWS = 64, COLS = 64;

static int input_value(int y, int x)
{
    const int bx = x / 16, by = y / 16, lx = x % 16, ly = y % 16;
    int v = 0;
    if (lx == 5 || lx == 10 || ly == 4 || ly == 11)
        v = 1;                                   // chains of 1s crossing all rows / columns of the tile
    if (lx == 5 && ly == 0 && ((bx + by) % 2 == 0))
        v = 2;                                   // seed at the top of a vertical chain
    if (lx == 10 && ly == 15 && ((bx + by) % 2 == 1))
        v = 2;                                   // seed at the bottom of a vertical chain
    if (lx == 0 && ly == 4)
        v = 2;                                   // seed at the left end of a horizontal chain
    return v;
}

int main()
{
    int ndev = 0;
    if (cudaGetDeviceCount(&ndev) != cudaSuccess || ndev == 0) {
        printf("no CUDA device, nothing to do\n");
        return 0;
    }
    std::vector<int> h(ROWS * COLS), ref(ROWS * COLS);
    for (int y = 0; y < ROWS; ++y)
        for (int x = 0; x < COLS; ++x)
            h[y * COLS + x] = input_value(y, x);

    // host reference: per 16x16 tile (halo of the original map, outside = 0), 16 step-synchronous flood-fill steps
    long refEdgePending = 0;
    for (int by = 0; by < ROWS / 16; ++by)
        for (int bx = 0; bx < COLS / 16; ++bx) {
            int s[18][18];
            for (int i = 0; i < 18; ++i)
                for (int j = 0; j < 18; ++j) {
                    int y = by * 16 + i - 1, x = bx * 16 + j - 1;
                    s[i][j] = (y >= 0 && y < ROWS && x >= 0 && x < COLS) ? h[y * COLS + x] : 0;
                }
            for (int k = 0; k < 16; ++k) {
                int t[18][18];
                for (int i = 0; i < 18; ++i)
                    for (int j = 0; j < 18; ++j)
                        t[i][j] = s[i][j];
                for (int i = 1; i < 17; ++i)
                    for (int j = 1; j < 17; ++j) {
                        int n = 0;
                        if (s[i][j] == 1)
                            for (int di = -1; di <= 1; ++di)
                                for (int dj = -1; dj <= 1; ++dj)
                                    if ((di || dj) && s[i + di][j + dj] == 2)
                                        ++n;
                        if (n > 0)
                            t[i][j] = 2;
                    }
                for (int i = 0; i < 18; ++i)
                    for (int j = 0; j < 18; ++j)
                        s[i][j] = t[i][j];
            }
            for (int i = 1; i < 17; ++i)
                for (int j = 1; j < 17; ++j) {
                    ref[(by * 16 + i - 1) * COLS + bx * 16 + j - 1] = s[i][j];
                    if (s[i][j] == 2) {
                        int n = 0;
                        for (int di = -1; di <= 1; ++di)
                            for (int dj = -1; dj <= 1; ++dj)
                                if ((di || dj) && s[i + di][j + dj] == 1)
                                    ++n;
                        if (n > 0)
                            ++refEdgePending;
                    }
                }
        }

    int *d_map = NULL;
    short2 *d_st = NULL;
    cudaSafeCall(cudaMalloc((void**)&d_map, ROWS * COLS * sizeof(int)));
    cudaSafeCall(cudaMalloc((void**)&d_st, ROWS * COLS * sizeof(short2)));
    cudaSafeCall(cudaMemcpy(d_map, h.data(), ROWS * COLS * sizeof(int), cudaMemcpyHostToDevice));

    PtrStepSzi map(ROWS, COLS, d_map, COLS * sizeof(int));
    canny::edgesHysteresisLocal(map, d_st);

    std::vector<int> out(ROWS * COLS);
    cudaSafeCall(cudaMemcpy(out.data(), d_map, ROWS * COLS * sizeof(int), cudaMemcpyDeviceToHost));
    int count = -1;
    cudaSafeCall(cudaMemcpyFromSymbol(&count, canny::counter, sizeof(int)));

    long bad = 0, twos = 0;
    unsigned long long sum = 0;
    for (int i = 0; i < ROWS * COLS; ++i) {
        if (out[i] != ref[i])
            ++bad;
        if (out[i] == 2)
            ++twos;
        sum = sum * 1315423911ull + (unsigned)out[i];
    }
    printf("edgesHysteresisLocal 64x64 grid (4,4) block (16,16): cells==2 %ld, mismatches vs step-synchronous host reference %ld, "
           "stack entries %d (reference %ld), checksum %016llx\n", twos, bad, count, refEdgePending, sum);
    printf("opencv-2 driver done\n");
    cudaFree(d_map);
    cudaFree(d_st);
    return 0;
}

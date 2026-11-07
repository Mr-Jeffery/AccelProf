// T26 parity: replay a capture_shim stream (cap.<pid>.bin) through the libsanalyzer this process
// loads (no RPATH: LD_LIBRARY_PATH picks the installed or the worktree's library). Every captured call
// is made again in order with the same arguments; each drain is rebuilt as MemoryAccess records with
// the captured fields and lane addresses (the other lanes zero) and handed over with the captured drain
// size. The tool writes dependency_<YOSEMITE_APP_NAME>_<date>/kernel_<i>.json into the cwd.
//   YOSEMITE_TOOL_NAME=pc_dependency_analysis YOSEMITE_DEVICE=nvc YOSEMITE_WORKER_COUNT=<N> \
//     LD_LIBRARY_PATH=<lib dir>:... t26_replay cap.<pid>.bin
#include "sanalyzer.h"
#include "gpu_patch.h"

#include <chrono>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

static_assert(sizeof(MemoryAccess) == 304, "MemoryAccess layout (capture_shim.cpp's Rec)");
static_assert(offsetof(MemoryAccess, accessSize) == 256 && offsetof(MemoryAccess, ctaId) == 264
              && offsetof(MemoryAccess, pc) == 272 && offsetof(MemoryAccess, warpId) == 280
              && offsetof(MemoryAccess, active_mask) == 288 && offsetof(MemoryAccess, type) == 296,
              "MemoryAccess layout (capture_shim.cpp's Rec)");

static FILE* f = nullptr;
static const char* path = nullptr;
// fread_unlocked: the analyzer's threads make the process multi-threaded, and glibc's locked fread
// then dominates a field-by-field parse (profile, job 329142) -- the driver's cost, not the library's
static void rd(void* p, size_t n) {
    if (fread_unlocked(p, 1, n, f) != n) { fprintf(stderr, "t26_replay: %s: short read\n", path); exit(2); }
}
template <class T> static T get() { T v; rd(&v, sizeof(T)); return v; }
static std::string get_str() {
    const uint32_t n = get<uint32_t>();
    std::string s(n, '\0');
    if (n) rd(&s[0], n);
    return s;
}

int main(int argc, char** argv) {
    if (argc != 2) { fprintf(stderr, "usage: t26_replay <cap.bin>\n"); return 2; }
    path = argv[1];
    f = std::fopen(path, "rb");
    if (f == nullptr) { fprintf(stderr, "t26_replay: cannot open %s\n", path); return 2; }
    static char buf[1 << 22];
    setvbuf(f, buf, _IOFBF, sizeof(buf));
    char magic[4];
    rd(magic, 4);
    if (std::memcmp(magic, "T26C", 4) != 0 || get<uint32_t>() != 1) { fprintf(stderr, "t26_replay: bad header\n"); return 2; }
    AccelProfOptions_t opt;
    if (yosemite_init(opt) != YOSEMITE_SUCCESS) { fprintf(stderr, "t26_replay: yosemite_init failed\n"); return 2; }
    const auto t0 = std::chrono::steady_clock::now();
    std::vector<MemoryAccess> recs;
    // seconds inside the library: every call, the drains alone, the kernel ends alone (JSON flush)
    using clk = std::chrono::steady_clock;
    double lib_s = 0, data_s = 0, end_s = 0;
    auto timed = [&](double& acc, auto&& call) {
        const auto a = clk::now();
        call();
        const double d = std::chrono::duration<double>(clk::now() - a).count();
        acc += d;
        lib_s += d;
    };
    double other_s = 0;
    unsigned long long drains = 0, records = 0, kernels = 0;
    bool terminated = false;
    for (;;) {
        uint8_t t;
        if (fread_unlocked(&t, 1, 1, f) != 1) break;
        switch (t) {
            case 'A': case 'F': {
                const uint64_t p = get<uint64_t>(), s = get<uint64_t>();
                const int ty = get<int>(), d = get<int>();
                timed(other_s, [&] { if (t == 'A') yosemite_alloc_callback(p, s, ty, d); else yosemite_free_callback(p, s, ty, d); });
                break;
            }
            case 'C': {
                const uint64_t dst = get<uint64_t>(), src = get<uint64_t>(), s = get<uint64_t>();
                const bool as = get<uint8_t>() != 0;
                const uint32_t dir = get<uint32_t>();
                const int d = get<int>();
                yosemite_memcpy_callback(dst, src, s, as, dir, d);
                break;
            }
            case 'S': {
                const uint64_t dst = get<uint64_t>();
                const uint32_t s = get<uint32_t>();
                const int v = get<int>();
                const bool as = get<uint8_t>() != 0;
                const int d = get<int>();
                yosemite_memset_callback(dst, s, v, as, d);
                break;
            }
            case 'T': case 't': {
                const uint64_t p = get<uint64_t>();
                const int64_t a = get<int64_t>(), ta = get<int64_t>(), tr = get<int64_t>();
                const int d = get<int>();
                if (t == 'T') yosemite_tensor_malloc_callback(p, a, ta, tr, d);
                else yosemite_tensor_free_callback(p, a, ta, tr, d);
                break;
            }
            case 'K': {
                const std::string name = get_str();
                const int d = get<int>();
                uint32_t dims[6];
                rd(dims, sizeof(dims));
                timed(other_s, [&] { yosemite_kernel_start_callback(name, d, dims[0], dims[1], dims[2], dims[3], dims[4], dims[5]); });
                kernels += 1;
                break;
            }
            case 'E': {
                const std::string name = get_str();
                const int d = get<int>();
                timed(end_s, [&] { yosemite_kernel_end_callback(name, d); });
                break;
            }
            case 'D': {
                const uint64_t n = get<uint64_t>();
                recs.resize(n);
                for (uint64_t i = 0; i < n; ++i) {
                    MemoryAccess& a = recs[i];
                    std::memset(static_cast<void*>(&a), 0, sizeof(a));
                    a.type = static_cast<MemoryType>(get<uint8_t>());
                    a.accessSize = get<uint32_t>(); a.flags = get<uint32_t>(); a.warpId = get<uint32_t>();
                    a.distinct_sector_count = get<uint32_t>(); a.active_mask = get<uint32_t>();
                    a.unique_address_mask = get<uint32_t>(); a.ctaId = get<uint64_t>(); a.pc = get<uint64_t>();
                    for (uint32_t m = a.active_mask | a.unique_address_mask; m != 0; m &= m - 1)
                        a.addresses[__builtin_ctz(m)] = get<uint64_t>();
                }
                timed(data_s, [&] { yosemite_gpu_data_analysis(recs.data(), n); });
                drains += 1;
                records += n;
                break;
            }
            case 'X':
                yosemite_terminate();
                terminated = true;
                break;
            default:
                fprintf(stderr, "t26_replay: %s: unknown tag %u\n", path, t);
                return 2;
        }
    }
    if (!terminated) yosemite_terminate();
    fprintf(stderr, "[t26_replay] %s: %llu kernels, %llu drains, %llu records, %.3f s%s\n", path, kernels, drains,
            records, std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count(),
            terminated ? "" : " (no terminate in the stream)");
    fprintf(stderr, "[t26_replay] library %.3f s: drains %.3f s, kernel ends %.3f s, other calls %.3f s\n",
            lib_s, data_s, end_s, other_s);
    return 0;
}

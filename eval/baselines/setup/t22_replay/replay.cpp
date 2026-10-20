// T22 replay, step 2: feed pack.py's record files through libsanalyzer's pc_dependency tool -- one
// kernel launch per file, the records in drains of DRAIN (default 262,144) -- as the collector
// does, without a GPU. With YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=scalar-clock YOSEMITE_HB_DUMP=0
// the tool writes dependency_<date>/kernel_<i>.json with HbClock's aggregates (hb_sync_pass,
// hb_rmw_points, tv_violation), so one recorded trace runs at any YOSEMITE_HB_SHARDS and the
// outputs compare exactly (a GPU re-recording is another execution). The PCDepGraph half sees
// no allocations and no unique-address masks: its output is not compared.
//   YOSEMITE_TOOL_NAME=pc_dependency_analysis YOSEMITE_DEVICE=nvc YOSEMITE_WORKER_COUNT=1 \
//   YOSEMITE_ATOMIC_SCOPE_FILE=<sidecar> ... replay <kernel.bin>...
#include "sanalyzer.h"
#include "gpu_patch.h"

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

static void need(bool ok, const char* what, const char* file) {
    if (!ok) { fprintf(stderr, "replay: %s: %s\n", file, what); exit(2); }
}

int main(int argc, char** argv) {
    AccelProfOptions_t opt;
    if (yosemite_init(opt) != YOSEMITE_SUCCESS) { fprintf(stderr, "replay: yosemite_init failed\n"); return 2; }
    const char* d = std::getenv("REPLAY_DRAIN");
    const size_t drain = d ? std::strtoull(d, nullptr, 10) : 262144;
    std::vector<MemoryAccess> buf(drain);
    for (int fi = 1; fi < argc; ++fi) {
        const char* path = argv[fi];
        FILE* f = std::fopen(path, "rb");
        need(f != nullptr, "cannot open", path);
        char magic[4];
        uint32_t ver = 0, len = 0, dims[6];
        uint64_t nrec = 0;
        need(std::fread(magic, 1, 4, f) == 4 && std::memcmp(magic, "T22R", 4) == 0, "bad magic", path);
        need(std::fread(&ver, 4, 1, f) == 1 && ver == 1 && std::fread(&len, 4, 1, f) == 1, "bad header", path);
        std::string name(len, '\0');
        need(std::fread(&name[0], 1, len, f) == len && std::fread(dims, 4, 6, f) == 6
             && std::fread(&nrec, 8, 1, f) == 1, "bad header", path);
        const auto t0 = std::chrono::steady_clock::now();
        yosemite_kernel_start_callback(name, 0, dims[0], dims[1], dims[2], dims[3], dims[4], dims[5]);
        size_t n = 0;
        for (uint64_t r = 0; r < nrec; ++r) {
            uint8_t type; uint8_t pad[3]; uint32_t warp; uint64_t block; uint32_t pc, mask, size, flags;
            need(std::fread(&type, 1, 1, f) == 1 && std::fread(pad, 1, 3, f) == 3
                 && std::fread(&warp, 4, 1, f) == 1 && std::fread(&block, 8, 1, f) == 1
                 && std::fread(&pc, 4, 1, f) == 1 && std::fread(&mask, 4, 1, f) == 1
                 && std::fread(&size, 4, 1, f) == 1 && std::fread(&flags, 4, 1, f) == 1, "short record", path);
            MemoryAccess& a = buf[n];
            std::memset(&a, 0, sizeof(a));
            a.type = static_cast<MemoryType>(type);
            a.warpId = warp; a.ctaId = block; a.pc = pc; a.active_mask = mask;
            a.unique_address_mask = mask; a.accessSize = size; a.flags = flags;
            if (a.type == MemoryType::Global || a.type == MemoryType::Shared)
                for (uint32_t m = mask; m != 0; m &= m - 1)
                    need(std::fread(&a.addresses[__builtin_ctz(m)], 8, 1, f) == 1, "short lanes", path);
            if (++n == drain) { yosemite_gpu_data_analysis(buf.data(), n); n = 0; }
        }
        if (n != 0) yosemite_gpu_data_analysis(buf.data(), n);
        yosemite_kernel_end_callback(name, 0);
        std::fclose(f);
        fprintf(stderr, "[replay] %s: %llu records, %.3f s\n", path, (unsigned long long)nrec,
                std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count());
    }
    return 0;
}

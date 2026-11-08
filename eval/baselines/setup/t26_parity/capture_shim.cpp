// T26 parity: a capture shim named libsanalyzer.so. A collector relinked with its RPATH on this
// shim's directory loads it instead of the analyzer; every yosemite_* call is forwarded to the real
// library (CAP_REAL_LIB, dlopen'ed by path) and, with CAP_DIR set, the calls the PCDepGraph pass
// depends on -- allocations, frees, tensor events, memcpy/memset, kernel start/end and every drain
// with its records -- are written in call order to CAP_DIR/cap.<pid>.bin (replay.cpp reads it). A
// GPU re-recording is another execution; one captured stream fed to two libraries is the same one.
// Records keep every field the analyzer reads; addresses are kept for the lanes in
// active_mask | unique_address_mask (the only lanes either pass reads). CAP_MAX_KERNELS=k ends the
// stream after the k-th kernel end (a prefix). Nothing in the analyzer or
// the collector is changed: the shim sits between them.
#include "sanalyzer.h"

#include <dlfcn.h>
#include <unistd.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <string>

// The harness refuses an HB collection when the library the collector loads lacks this string (the
// pre-T8 guard, hb_modes.require_collector_support); the shim forwards to CAP_REAL_LIB, which reads it.
extern "C" __attribute__((used, visibility("default"))) const char t26_capture_forwards_env[] = "YOSEMITE_HB_MODE";

namespace {
// MemoryAccess as nv-compute/gpu_src/include/gpu_patch.h lays it out (checked by replay.cpp,
// which includes the header and static_asserts the same size and offsets)
struct Rec {
    uint64_t addresses[32];
    uint32_t accessSize;
    uint32_t flags;
    uint64_t ctaId;
    uint64_t pc;
    uint32_t warpId;
    uint32_t distinct_sector_count;
    uint32_t active_mask;
    uint32_t unique_address_mask;
    int type;
};
static_assert(sizeof(Rec) == 304, "MemoryAccess layout");

std::mutex mu;
void* real = nullptr;
FILE* out = nullptr;
bool tried = false;
unsigned long long drains = 0, records = 0, kends = 0;

void* sym(const char* name) {
    if (real == nullptr) {
        const char* p = std::getenv("CAP_REAL_LIB");
        if (p == nullptr) { fprintf(stderr, "[t26-capture] CAP_REAL_LIB is not set\n"); std::abort(); }
        real = dlopen(p, RTLD_NOW | RTLD_LOCAL);
        if (real == nullptr) { fprintf(stderr, "[t26-capture] dlopen %s: %s\n", p, dlerror()); std::abort(); }
    }
    void* f = dlsym(real, name);
    if (f == nullptr) { fprintf(stderr, "[t26-capture] dlsym %s: %s\n", name, dlerror()); std::abort(); }
    return f;
}
#define REAL(type, mangled) static auto fn = reinterpret_cast<type>(sym(mangled))

FILE* file() {   // under mu
    if (!tried) {
        tried = true;
        const char* d = std::getenv("CAP_DIR");
        if (d != nullptr && *d != '\0') {
            const std::string path = std::string(d) + "/cap." + std::to_string(getpid()) + ".bin";
            out = std::fopen(path.c_str(), "wb");
            if (out == nullptr) { fprintf(stderr, "[t26-capture] cannot open %s\n", path.c_str()); std::abort(); }
            static char buf[1 << 22];
            setvbuf(out, buf, _IOFBF, sizeof(buf));
            std::fwrite("T26C", 1, 4, out);
            const uint32_t ver = 1;
            std::fwrite(&ver, 4, 1, out);
        }
    }
    return out;
}
template <class T> void put(FILE* f, const T& v) { std::fwrite(&v, sizeof(T), 1, f); }
void put_str(FILE* f, const std::string& s) {
    const uint32_t n = static_cast<uint32_t>(s.size());
    put(f, n);
    std::fwrite(s.data(), 1, n, f);
}
void tag(FILE* f, char c) { put(f, static_cast<uint8_t>(c)); }
}  // namespace

YosemiteResult_t yosemite_init(AccelProfOptions_t& options) {
    REAL(YosemiteResult_t (*)(AccelProfOptions_t&), "_Z13yosemite_initR16AccelProfOptions");
    { std::lock_guard<std::mutex> l(mu); file(); }
    return fn(options);
}

YosemiteResult_t yosemite_terminate() {
    REAL(YosemiteResult_t (*)(), "_Z18yosemite_terminatev");
    {
        std::lock_guard<std::mutex> l(mu);
        if (FILE* f = file()) { tag(f, 'X'); std::fflush(f); }
    }
    const YosemiteResult_t r = fn();
    std::lock_guard<std::mutex> l(mu);
    if (out != nullptr) {
        fprintf(stderr, "[t26-capture] %llu drains, %llu records\n", drains, records);
        std::fclose(out);
        out = nullptr;
    }
    return r;
}

YosemiteResult_t yosemite_alloc_callback(uint64_t ptr, uint64_t size, int type, int device_id) {
    REAL(YosemiteResult_t (*)(uint64_t, uint64_t, int, int), "_Z23yosemite_alloc_callbackmmii");
    {
        std::lock_guard<std::mutex> l(mu);
        if (FILE* f = file()) { tag(f, 'A'); put(f, ptr); put(f, size); put(f, type); put(f, device_id); std::fflush(f); }
    }
    return fn(ptr, size, type, device_id);
}

YosemiteResult_t yosemite_free_callback(uint64_t ptr, uint64_t size, int type, int device_id) {
    REAL(YosemiteResult_t (*)(uint64_t, uint64_t, int, int), "_Z22yosemite_free_callbackmmii");
    {
        std::lock_guard<std::mutex> l(mu);
        if (FILE* f = file()) { tag(f, 'F'); put(f, ptr); put(f, size); put(f, type); put(f, device_id); std::fflush(f); }
    }
    return fn(ptr, size, type, device_id);
}

YosemiteResult_t yosemite_memcpy_callback(uint64_t dst, uint64_t src, uint64_t size, bool is_async,
                                          uint32_t direction, int device_id) {
    REAL(YosemiteResult_t (*)(uint64_t, uint64_t, uint64_t, bool, uint32_t, int), "_Z24yosemite_memcpy_callbackmmmbji");
    {
        std::lock_guard<std::mutex> l(mu);
        if (FILE* f = file()) {
            tag(f, 'C'); put(f, dst); put(f, src); put(f, size); put(f, static_cast<uint8_t>(is_async));
            put(f, direction); put(f, device_id); std::fflush(f);
        }
    }
    return fn(dst, src, size, is_async, direction, device_id);
}

YosemiteResult_t yosemite_memset_callback(uint64_t dst, uint32_t size, int value, bool is_async, int device_id) {
    REAL(YosemiteResult_t (*)(uint64_t, uint32_t, int, bool, int), "_Z24yosemite_memset_callbackmjibi");
    {
        std::lock_guard<std::mutex> l(mu);
        if (FILE* f = file()) {
            tag(f, 'S'); put(f, dst); put(f, size); put(f, value); put(f, static_cast<uint8_t>(is_async));
            put(f, device_id); std::fflush(f);
        }
    }
    return fn(dst, size, value, is_async, device_id);
}

YosemiteResult_t yosemite_host_op_callback(const YosemiteHostOp_t& op) {
    // T2's host operations (YOSEMITE_HB_HOST_MEMCPY only): forwarded, not captured
    REAL(YosemiteResult_t (*)(const YosemiteHostOp_t&), "_Z25yosemite_host_op_callbackRK14YosemiteHostOp");
    return fn(op);
}

YosemiteResult_t yosemite_kernel_start_callback(std::string kernel_name, int device_id,
                                                uint32_t gx, uint32_t gy, uint32_t gz,
                                                uint32_t bx, uint32_t by, uint32_t bz) {
    REAL(YosemiteResult_t (*)(std::string, int, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t),
         "_Z30yosemite_kernel_start_callbackNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEEijjjjjj");
    {
        std::lock_guard<std::mutex> l(mu);
        if (FILE* f = file()) {
            tag(f, 'K'); put_str(f, kernel_name); put(f, device_id);
            put(f, gx); put(f, gy); put(f, gz); put(f, bx); put(f, by); put(f, bz); std::fflush(f);
        }
    }
    return fn(kernel_name, device_id, gx, gy, gz, bx, by, bz);
}

YosemiteResult_t yosemite_kernel_end_callback(std::string kernel_name, int device_id) {
    REAL(YosemiteResult_t (*)(std::string, int),
         "_Z28yosemite_kernel_end_callbackNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEEi");
    {
        std::lock_guard<std::mutex> l(mu);
        if (FILE* f = file()) {
            tag(f, 'E'); put_str(f, kernel_name); put(f, device_id); std::fflush(f);
            // CAP_MAX_KERNELS=k: the stream ends after the k-th kernel end (a prefix of the run, for programs
            // whose whole stream does not fit on disk); the run itself goes on, forwarded as before
            static const long max_k = [] { const char* e = std::getenv("CAP_MAX_KERNELS"); return e ? std::atol(e) : 0L; }();
            if (max_k > 0 && ++kends >= static_cast<unsigned long long>(max_k)) {
                tag(f, 'X'); std::fflush(f);
                fprintf(stderr, "[t26-capture] stream closed after %llu kernels (CAP_MAX_KERNELS): %llu drains, %llu records\n",
                        kends, drains, records);
                std::fclose(f);
                out = nullptr;   // tried stays true: nothing more is written
            }
        }
    }
    return fn(kernel_name, device_id);
}

YosemiteResult_t yosemite_gpu_data_analysis(void* data, uint64_t size) {
    REAL(YosemiteResult_t (*)(void*, uint64_t), "_Z26yosemite_gpu_data_analysisPvm");
    {
        std::lock_guard<std::mutex> l(mu);
        if (FILE* f = file()) {
            tag(f, 'D');
            put(f, size);
            const Rec* r = static_cast<const Rec*>(data);
            for (uint64_t i = 0; i < size; ++i) {
                const Rec& a = r[i];
                put(f, static_cast<uint8_t>(a.type));
                put(f, a.accessSize); put(f, a.flags); put(f, a.warpId); put(f, a.distinct_sector_count);
                put(f, a.active_mask); put(f, a.unique_address_mask); put(f, a.ctaId); put(f, a.pc);
                for (uint32_t m = a.active_mask | a.unique_address_mask; m != 0; m &= m - 1)
                    put(f, a.addresses[__builtin_ctz(m)]);
            }
            std::fflush(f);
            drains += 1;
            records += size;
        }
    }
    return fn(data, size);
}

YosemiteResult_t yosemite_gpu_data_late_keys(const uint64_t* keys, uint64_t size, uint32_t mode) {
    // T15's late keys (YOSEMITE_HB_LATE_SEQ only, compiled out of the default fatbin): not captured
    REAL(YosemiteResult_t (*)(const uint64_t*, uint64_t, uint32_t), "_Z27yosemite_gpu_data_late_keysPKmmj");
    return fn(keys, size, mode);
}

YosemiteResult_t yosemite_tensor_malloc_callback(uint64_t ptr, int64_t alloc_size, int64_t total_allocated,
                                                 int64_t total_reserved, int device_id) {
    REAL(YosemiteResult_t (*)(uint64_t, int64_t, int64_t, int64_t, int), "_Z31yosemite_tensor_malloc_callbackmllli");
    {
        std::lock_guard<std::mutex> l(mu);
        if (FILE* f = file()) {
            tag(f, 'T'); put(f, ptr); put(f, alloc_size); put(f, total_allocated); put(f, total_reserved);
            put(f, device_id); std::fflush(f);
        }
    }
    return fn(ptr, alloc_size, total_allocated, total_reserved, device_id);
}

YosemiteResult_t yosemite_tensor_free_callback(uint64_t ptr, int64_t alloc_size, int64_t total_allocated,
                                               int64_t total_reserved, int device_id) {
    REAL(YosemiteResult_t (*)(uint64_t, int64_t, int64_t, int64_t, int), "_Z29yosemite_tensor_free_callbackmllli");
    {
        std::lock_guard<std::mutex> l(mu);
        if (FILE* f = file()) {
            tag(f, 't'); put(f, ptr); put(f, alloc_size); put(f, total_allocated); put(f, total_reserved);
            put(f, device_id); std::fflush(f);
        }
    }
    return fn(ptr, alloc_size, total_allocated, total_reserved, device_id);
}

YosemiteResult_t yosemite_operator_start_callback(void* ctx, std::string op_name) {
    REAL(YosemiteResult_t (*)(void*, std::string),
         "_Z32yosemite_operator_start_callbackPvNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE");
    return fn(ctx, op_name);
}

YosemiteResult_t yosemite_operator_end_callback(void* ctx, std::string op_name) {
    REAL(YosemiteResult_t (*)(void*, std::string),
         "_Z30yosemite_operator_end_callbackPvNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE");
    return fn(ctx, op_name);
}

YosemiteResult_t yosemite_query_active_ranges(void* ranges, uint32_t limit, uint32_t* count) {
    REAL(YosemiteResult_t (*)(void*, uint32_t, uint32_t*), "_Z28yosemite_query_active_rangesPvjPj");
    return fn(ranges, limit, count);
}

YosemiteResult_t yosemite_query_active_tensors(void* ranges, uint32_t limit, uint32_t* count) {
    REAL(YosemiteResult_t (*)(void*, uint32_t, uint32_t*), "_Z29yosemite_query_active_tensorsPvjPj");
    return fn(ranges, limit, count);
}

#include "tools/pc_dependency_analysis.h"
#include "utils/helper.h"

#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <memory>
#include <cassert>
#include <iostream>
#include <sstream>
#include <set>
#include <utility>
#include <iomanip>
#include <thread>
#include <atomic>
#include <limits>
#include <tuple>


using namespace yosemite;

namespace yosemite {

// Streaming scoped vector-clock happens-before: a 1:1 port of the reference
// spec python/hb_oracle.py (analyze()). Runs over the raw MemoryAccess buffer in
// temporal order (-n 1); every verdict falls out of the clocks with no pattern
// special-cased. Exact for the corpus; the FastTrack epoch collapse and bounded
// per-thread clocks are the scale knobs, not needed here.
// ponytail: full sparse VCs + full reader sets, O(threads) memory. Collapse
// last_reads to a single read-epoch (FastTrack) and cap the per-thread clock only
// when the eval workloads need it — the corpus is tiny.
struct HbEngine {
    // sync scopes match sync_dominance.SCOPES: NONE=0, (WARP=1), BLOCK=2, GRID=3.
    static constexpr int SCOPE_NONE = 0;
    static constexpr int SCOPE_BLOCK = 2;
    static constexpr int SCOPE_GRID = 3;

    using Clock = std::unordered_map<uint32_t, uint64_t>;   // tid -> logical clock
    using Loc = std::tuple<int, uint64_t, uint64_t>;        // (space, block-or-0, addr)

    // pc offset -> atomic coherence scope; absence => plain ld/st (not an atomic).
    std::unordered_map<uint32_t, int> atom_scope;

    std::unordered_map<uint32_t, Clock> vc;                 // tid -> vector clock
    struct Released { Clock clk; uint64_t block; int scope; };
    std::unordered_map<uint64_t, Released> released;        // addr -> release record
    struct Writer { uint32_t tid; uint64_t clock; uint32_t pc; };
    std::map<Loc, Writer> last_write;                       // loc -> last writer epoch
    std::map<Loc, Clock> last_reads;                        // loc -> {reader tid -> clock}

    struct Race { uint64_t addr; int space; uint64_t loc_block;
                  uint32_t a_tid; long a_pc; uint32_t b_tid; uint32_t b_pc; const char* kind; };
    std::vector<Race> races;

    // Block-barrier instance assembly (see the barrier branch in process): buffer
    // per-warp arrivals per (block, bar_index) until the instance is complete.
    // block_thread_count is the expected participant count for a plain __syncthreads
    // (whose per-record thread_count is 0); set per-kernel by hb_engine_reset.
    uint64_t block_thread_count = 0;
    std::map<std::pair<uint64_t, uint32_t>, std::set<uint32_t>> pending_barriers;

    void reset() {
        vc.clear(); released.clear(); last_write.clear(); last_reads.clear(); races.clear();
        pending_barriers.clear();  // block_thread_count is (re)set by hb_engine_reset
    }

    static uint32_t tid_of(uint64_t block, uint32_t warp, uint32_t lane) {
        return static_cast<uint32_t>((block << 10) | (warp << 5) | lane);
    }
    static uint64_t clk_get(const Clock& c, uint32_t t) {
        auto it = c.find(t); return it == c.end() ? 0 : it->second;
    }
    // a thread's own clock starts at 1: an unsynced peer knows it only as 0, so a
    // write (t@>=1) vs 0 is caught as a race.
    uint64_t own(uint32_t t) {
        uint64_t& v = vc[t][t];
        if (v == 0) v = 1;
        return v;
    }
    static void join_into(Clock& dst, const Clock& src) {
        for (const auto& kv : src) { uint64_t& d = dst[kv.first]; if (kv.second > d) d = kv.second; }
    }
    // barrier/syncwarp: everyone joins everyone's pre-sync clock, then each ticks
    // its own component (post-sync accesses ordered after the join, concurrent with
    // each other).
    void sync_group(const std::vector<uint32_t>& tids) {
        for (uint32_t t : tids) own(t);
        Clock j;
        for (uint32_t t : tids) join_into(j, vc[t]);
        for (uint32_t t : tids) { Clock nv = j; nv[t] += 1; vc[t] = std::move(nv); }
    }
    void add_race(uint64_t addr, int space, uint64_t loc_block,
                  uint32_t a_tid, long a_pc, uint32_t b_tid, uint32_t b_pc, const char* kind) {
        races.push_back(Race{addr, space, loc_block, a_tid, a_pc, b_tid, b_pc, kind});
    }

    void load_scopes(const char* path) {
        atom_scope.clear();
        if (path == nullptr) return;
        std::ifstream f(path);
        if (!f) return;
        uint32_t pc = 0; int scope = 0;
        while (f >> pc >> scope) atom_scope[pc] = scope;
    }

    void process(const MemoryAccess* buf, uint64_t size) {
        for (uint64_t i = 0; i < size; ++i) {
            const MemoryAccess& a = buf[i];
            if (a.type == MemoryType::BlockExit) continue;
            const uint32_t pc = static_cast<uint32_t>(a.pc & 0x00FFFFFFu);

            if (a.type == MemoryType::Syncwarp) {
                // syncwarp is genuinely per-warp: join THIS warp's masked lanes now
                // (sync_mask carried in accessSize).
                std::vector<uint32_t> tids;
                for (uint32_t m = a.accessSize; m != 0; m &= (m - 1))
                    tids.push_back(tid_of(a.ctaId, a.warpId, static_cast<uint32_t>(__builtin_ctz(m))));
                sync_group(tids);
                continue;
            }
            if (a.type == MemoryType::Barrier) {
                // A block-wide barrier (__syncthreads / bar.sync) emits ONE arrival
                // record per warp (active_mask = arrived lanes). Buffer arrivals per
                // (block, bar_index) and join the UNION of all participants only once
                // the instance is complete, so warp 0's pre-barrier writes are ordered
                // before every warp's post-barrier reads (the cross-warp tile idiom).
                // A loop reuses (block, bar_index): the barrier prevents any warp
                // reaching instance k+1 before k completes, so accumulate-then-reset
                // segments dynamic instances. thread_count (accessSize) is the expected
                // participant count; 0 for a plain __syncthreads means the whole block,
                // so fall back to block_thread_count. flags carries the static bar_index.
                const uint64_t expected = (a.accessSize != 0) ? a.accessSize : block_thread_count;
                const std::pair<uint64_t, uint32_t> key{a.ctaId, a.flags};
                std::set<uint32_t>& arrived = pending_barriers[key];
                for (uint32_t m = a.active_mask; m != 0; m &= (m - 1))
                    arrived.insert(tid_of(a.ctaId, a.warpId, static_cast<uint32_t>(__builtin_ctz(m))));
                // fire once complete; expected==0 (unknown count, unreachable for a
                // launched kernel) degrades to per-warp so the engine never stalls.
                if (expected == 0 || arrived.size() >= expected) {
                    std::vector<uint32_t> tids(arrived.begin(), arrived.end());
                    sync_group(tids);
                    pending_barriers.erase(key);
                }
                continue;
            }

            const bool is_atomic = atom_scope.count(pc) != 0;
            const bool is_write = (a.flags & SANITIZER_MEMORY_DEVICE_FLAG_WRITE) != 0;
            const int space = (a.type == MemoryType::Shared) ? 1
                            : (a.type == MemoryType::Local)  ? 2 : 0;

            for (uint32_t lm = a.active_mask; lm != 0; lm &= (lm - 1)) {
                const uint32_t lane = static_cast<uint32_t>(__builtin_ctz(lm));
                const uint32_t t = tid_of(a.ctaId, a.warpId, lane);
                const uint64_t addr = a.addresses[lane];
                const uint64_t loc_block = (space == 1) ? a.ctaId : 0;  // shared is per-block
                const Loc loc{space, loc_block, addr};

                if (is_atomic) {
                    // scoped acquire-release: pick up a's release only if the min of
                    // the two atomics' .STRONG scopes covers both threads.
                    const int my_scope = atom_scope[pc];
                    auto rit = released.find(addr);
                    if (rit != released.end()) {
                        const int eff = std::min(my_scope, rit->second.scope);
                        if (eff == SCOPE_GRID || (eff == SCOPE_BLOCK && rit->second.block == a.ctaId))
                            join_into(vc[t], rit->second.clk);
                    }
                    // an atomic RMW is a write: races a prior writer the scoped
                    // acquire did NOT order (a coherence race at too-narrow scope).
                    auto wit = last_write.find(loc);
                    if (wit != last_write.end() && wit->second.tid != t
                        && wit->second.clock > clk_get(vc[t], wit->second.tid))
                        add_race(addr, space, a.ctaId, wit->second.tid,
                                 static_cast<long>(wit->second.pc), t, pc, "atomic");
                    const uint64_t nc = own(t) + 1;
                    vc[t][t] = nc;
                    released[addr] = Released{vc[t], a.ctaId, my_scope};
                    last_write[loc] = Writer{t, nc, pc};
                    last_reads[loc].clear();
                    continue;
                }

                const uint64_t clk = own(t);
                auto wit = last_write.find(loc);
                if (wit != last_write.end() && wit->second.tid != t
                    && wit->second.clock > clk_get(vc[t], wit->second.tid))
                    add_race(addr, space, a.ctaId, wit->second.tid,
                             static_cast<long>(wit->second.pc), t, pc, is_write ? "WAW" : "RAW");
                if (is_write) {
                    auto lrit = last_reads.find(loc);
                    if (lrit != last_reads.end())
                        for (const auto& kv : lrit->second)
                            if (kv.first != t && kv.second > clk_get(vc[t], kv.first))
                                add_race(addr, space, a.ctaId, kv.first, -1, t, pc, "WAR");
                    last_write[loc] = Writer{t, clk, pc};
                    last_reads[loc].clear();
                } else {
                    last_reads[loc][t] = clk;
                }
            }
        }
    }

    void emit(std::ostream& jout) {
        // dedup identical race tuples (addr, a_tid, a_pc, b_tid, b_pc, kind).
        std::set<std::tuple<uint64_t, uint32_t, long, uint32_t, uint32_t, std::string>> seen;
        std::vector<const Race*> uniq;
        for (const auto& r : races) {
            auto key = std::make_tuple(r.addr, r.a_tid, r.a_pc, r.b_tid, r.b_pc, std::string(r.kind));
            if (seen.insert(key).second) uniq.push_back(&r);
        }
        jout << ",\n  \"hb_races\": [\n";
        for (size_t i = 0; i < uniq.size(); ++i) {
            const Race& r = *uniq[i];
            const char* sp = (r.space == 1) ? "shared" : (r.space == 2) ? "local" : "global";
            jout << "    {\"addr\": " << r.addr
                 << ", \"space\": \"" << sp << "\""
                 << ", \"loc_block\": " << r.loc_block
                 << ", \"a_tid\": " << r.a_tid
                 << ", \"a_pc\": " << (r.a_pc < 0 ? std::string("null")
                                                  : std::to_string(static_cast<uint32_t>(r.a_pc)))
                 << ", \"b_tid\": " << r.b_tid
                 << ", \"b_pc\": " << r.b_pc
                 << ", \"kind\": \"" << r.kind << "\"}";
            if (i + 1 < uniq.size()) jout << ",";
            jout << "\n";
        }
        jout << "  ]";
    }
};

}  // namespace yosemite

namespace {
static std::string json_escape(const std::string& s) {
    std::string out;
    out.reserve(s.size() + 8);
    for (char c : s) {
        switch (c) {
            case '\"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\b': out += "\\b"; break;
            case '\f': out += "\\f"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                // control chars
                if (static_cast<unsigned char>(c) < 0x20) {
                    std::ostringstream oss;
                    oss << "\\u"
                        << std::hex << std::setw(4) << std::setfill('0')
                        << (int)static_cast<unsigned char>(c);
                    out += oss.str();
                } else {
                    out += c;
                }
        }
    }
    return out;
}

static std::string hex_u32(uint32_t v) {
    std::ostringstream oss;
    oss << "0x" << std::hex << v;
    return oss.str();
}
static std::string flags_to_string(uint32_t flags) {
    std::ostringstream oss;
    if (flags & SANITIZER_MEMORY_DEVICE_FLAG_READ) oss << "READ";
    if (flags & SANITIZER_MEMORY_DEVICE_FLAG_WRITE) oss << "WRITE";
    if (flags & SANITIZER_MEMORY_DEVICE_FLAG_ATOMIC) oss << "ATOMIC";
    if (flags & SANITIZER_MEMORY_DEVICE_FLAG_PREFETCH) oss << "PREFETCH";
    oss << " ";
    if (flags & SANITIZER_MEMORY_GLOBAL) oss << "GLOBAL";
    if (flags & SANITIZER_MEMORY_SHARED) oss << "SHARED";
    if (flags & SANITIZER_MEMORY_LOCAL) oss << "LOCAL";

    return oss.str();
}

static inline uint64_t pack_shadow_entry(uint8_t generation, uint32_t pc24, uint32_t flat_thread_id) {
    const uint32_t encoded_pc = (static_cast<uint32_t>(generation) << 24)
                              | (pc24 & 0x00FFFFFFu);
    return (static_cast<uint64_t>(flat_thread_id) << 32) | static_cast<uint64_t>(encoded_pc);
}

static inline uint32_t unpack_shadow_pc_encoded(uint64_t packed) {
    return static_cast<uint32_t>(packed & 0xFFFFFFFFu);
}

static inline uint32_t unpack_shadow_flat_tid(uint64_t packed) {
    return static_cast<uint32_t>(packed >> 32);
}

static inline const memory_region* find_memory_region_containing(
    const std::vector<memory_region>& regions,
    uint64_t addr
) {
    auto it = std::upper_bound(
        regions.begin(),
        regions.end(),
        addr,
        [](uint64_t value, const memory_region& region) {
            return value < region.get_start();
        }
    );
    if (it == regions.begin()) {
        return nullptr;
    }
    --it;
    return it->contains(addr) ? &(*it) : nullptr;
}

static uint32_t read_env_u32(const char* key, uint32_t default_value) {
    const char* raw = std::getenv(key);
    if (raw == nullptr) {
        return default_value;
    }
    char* end_ptr = nullptr;
    const unsigned long parsed = std::strtoul(raw, &end_ptr, 10);
    if (end_ptr == raw || *end_ptr != '\0') {
        return default_value;
    }
    if (parsed > std::numeric_limits<uint32_t>::max()) {
        return default_value;
    }
    return static_cast<uint32_t>(parsed);
}
} // namespace


PcDependency::PcDependency() : Tool(PC_DEPENDENCY_ANALYSIS) {
    const char* torch_prof = std::getenv("TORCH_PROFILE_ENABLED");
    if (torch_prof && std::string(torch_prof) == "1") {
        fprintf(stdout, "Enabling torch profiler in PcDependency.\n");
        _torch_enabled = true;
    }

    const char* env_app_name = std::getenv("YOSEMITE_APP_NAME");
    if (env_app_name != nullptr) {
        output_directory = "dependency_" + std::string(env_app_name)
                            + "_" + get_current_date_n_time();
    } else {
        output_directory = "dependency_" + get_current_date_n_time();
    }
    check_folder_existance(output_directory);

    _hb_trace = read_env_u32("YOSEMITE_HB_TRACE", 0) != 0;

    _worker_count = std::max(1u, read_env_u32("YOSEMITE_WORKER_COUNT", std::thread::hardware_concurrency()));
    const uint32_t sm_count = read_env_u32("YOSEMITE_GPU_SM_COUNT", 128);
    const uint32_t max_active_blocks_per_sm = read_env_u32("YOSEMITE_GPU_MAX_ACTIVE_BLOCKS_PER_SM", 24);
    const uint32_t pool_slack_percent = read_env_u32("YOSEMITE_SHARED_SHADOW_POOL_SLACK_PERCENT", 150);
    const uint64_t total_block_capacity =
        static_cast<uint64_t>(sm_count) * static_cast<uint64_t>(max_active_blocks_per_sm);
    const uint64_t slack_block_capacity =
        (total_block_capacity * static_cast<uint64_t>(pool_slack_percent) + 99ull) / 100ull;
    _shared_shadow_object_cap_per_worker =
        static_cast<uint32_t>(std::max<uint64_t>(32ull, (slack_block_capacity + _worker_count - 1) / _worker_count));
    _shared_shadow_bytes_per_object = read_env_u32("YOSEMITE_GPU_MAX_SHARED_MEMORY_PER_BLOCK", 102400u);
    if (_shared_shadow_bytes_per_object == 0) {
        _shared_shadow_bytes_per_object = 1;
    }

    _worker_shadow_memory_shared.resize(_worker_count);
    for (auto& worker_state : _worker_shadow_memory_shared) {
        worker_state.object_entries.resize(_shared_shadow_object_cap_per_worker, nullptr);
        worker_state.object_owner_cta.assign(_shared_shadow_object_cap_per_worker, std::numeric_limits<uint64_t>::max());
        worker_state.object_active_threads.assign(_shared_shadow_object_cap_per_worker, 0u);
        worker_state.free_object_indices.reserve(_shared_shadow_object_cap_per_worker);
        for (uint32_t idx = 0; idx < _shared_shadow_object_cap_per_worker; ++idx) {
            worker_state.free_object_indices.push_back(_shared_shadow_object_cap_per_worker - 1u - idx);
            shared_shadow_memory_entry* entries = static_cast<shared_shadow_memory_entry*>(
                mmap(
                    nullptr,
                    static_cast<size_t>(_shared_shadow_bytes_per_object) * sizeof(shared_shadow_memory_entry),
                    PROT_READ | PROT_WRITE,
                    MAP_PRIVATE | MAP_ANONYMOUS,
                    -1,
                    0
                )
            );
            assert(entries != MAP_FAILED);
            worker_state.object_entries[idx] = entries;
        }
    }
    _job_worker_trace_indices.resize(_worker_count);
    _job_worker_pc_statistics.resize(_worker_count);
    _job_worker_pc_flags.resize(_worker_count);
    _job_worker_distinct_sector_count.resize(_worker_count);
    _workers.reserve(_worker_count);
    for (uint64_t worker_idx = 0; worker_idx < _worker_count; ++worker_idx) {
        _workers.emplace_back(&PcDependency::worker_loop, this, worker_idx);
    }
}


PcDependency::~PcDependency() {
    {
        std::lock_guard<std::mutex> guard(_worker_pool_mutex);
        _worker_pool_shutdown = true;
        ++_worker_job_generation;
    }
    _worker_pool_cv.notify_all();
    for (auto& worker : _workers) {
        if (worker.joinable()) {
            worker.join();
        }
    }
    for (auto& worker_state : _worker_shadow_memory_shared) {
        for (auto* entries : worker_state.object_entries) {
            if (entries != nullptr) {
                munmap(
                    entries,
                    static_cast<size_t>(_shared_shadow_bytes_per_object) * sizeof(shared_shadow_memory_entry)
                );
            }
        }
    }
}


void PcDependency::kernel_start_callback(std::shared_ptr<KernelLaunch_t> kernel) {

    kernel->kernel_id = kernel_id++;
    _shared_kernel_generation = kernel->kernel_id + 1u;
    _current_kernel_cta_count = kernel->grid_cta_count;
    _current_block_thread_count = kernel->block_thread_count;
    kernel_events.emplace(_timer.get(), kernel);
    _pc_statistics.clear();
    _pc_flags.clear();
    _distinct_sector_count.clear();
    _unknown_region_shadow.clear();
    _hb_events.clear();
    _hb_seq = 0;
    hb_engine_reset();
    for (uint64_t worker_idx = 0; worker_idx < _worker_count; ++worker_idx) {
        auto& worker_state = _worker_shadow_memory_shared[worker_idx];
        worker_state.pool_miss_count = 0;
        uint64_t worker_cta_slots = 0;
        if (_current_kernel_cta_count > worker_idx) {
            worker_cta_slots = (_current_kernel_cta_count + _worker_count - 1u - worker_idx) / _worker_count;
        }
        worker_state.cta_slot_to_object.assign(
            static_cast<size_t>(worker_cta_slots),
            worker_shared_shadow_state::k_invalid_object
        );
    }
    _kernel_generation = static_cast<uint8_t>(_kernel_generation + 1u);
    if (_kernel_generation == 0) {
        for (auto& shadow_memory_iter : _shadow_memories) {
            shadow_memory_iter.second->reset_entries();
        }
        printf("[PC_DEPENDENCY] Shadow generation wrapped, resetting entries\n");
    }
    _timer.increment(true);
}


void PcDependency::hb_collect_events(const MemoryAccess* buffer, uint64_t size) {
    // Serialize each trace record (in buffer/temporal order) to a compact JSON
    // object appended to _hb_events. Called per buffer drain so the stream spans
    // the whole kernel. Memory records expand to active lanes; sync records carry
    // participation (barrier threadCount / syncwarp mask).
    for (uint64_t i = 0; i < size; ++i) {
        const MemoryAccess& a = buffer[i];
        std::ostringstream o;
        const uint64_t seq = _hb_seq++;
        o << "{\"seq\": " << seq
          << ", \"block\": " << a.ctaId
          << ", \"warp\": " << a.warpId
          << ", \"pc\": " << (a.pc & 0x00FFFFFFu);
        if (a.type == MemoryType::Barrier) {
            o << ", \"type\": \"barrier\", \"thread_count\": " << a.accessSize
              << ", \"bar_index\": " << a.flags
              << ", \"active_mask\": " << a.active_mask << "}";
        } else if (a.type == MemoryType::Syncwarp) {
            o << ", \"type\": \"syncwarp\", \"sync_mask\": " << a.accessSize
              << ", \"active_mask\": " << a.active_mask << "}";
        } else if (a.type == MemoryType::BlockExit) {
            continue;  // block exit is not a happens-before event
        } else {
            const char* kind = (a.flags & SANITIZER_MEMORY_DEVICE_FLAG_ATOMIC) ? "atomic"
                             : (a.flags & SANITIZER_MEMORY_DEVICE_FLAG_WRITE)  ? "write"
                             : "read";
            const char* space = (a.type == MemoryType::Shared) ? "shared"
                              : (a.type == MemoryType::Local)  ? "local" : "global";
            o << ", \"type\": \"" << kind << "\", \"space\": \"" << space
              << "\", \"size\": " << a.accessSize
              << ", \"active_mask\": " << a.active_mask << ", \"lanes\": [";
            bool first = true;
            uint32_t mask = a.active_mask;
            while (mask != 0) {
                const uint32_t j = static_cast<uint32_t>(__builtin_ctz(mask));
                mask &= (mask - 1);
                if (!first) o << ", ";
                first = false;
                o << "{\"lane\": " << j << ", \"addr\": " << a.addresses[j] << "}";
            }
            o << "]}";
        }
        _hb_events.push_back(o.str());
    }
}


// The engine state is a file-static singleton, NOT a PcDependency member: adding a
// member re-triggers a latent heap-corruption UB (see the header note). Only the
// single enabled pc_dependency tool instance ever processes kernels, so one
// singleton is correct; the 2 discarded tool temporaries never call reset().
// ponytail: singleton, not per-instance. Key by `this` only if two instances ever
// process concurrently (they don't — one tool is enabled at a time).
namespace {
std::unique_ptr<HbEngine>& hb_engine_singleton() {
    static std::unique_ptr<HbEngine> engine;
    return engine;
}
}  // namespace

void PcDependency::hb_engine_process(const MemoryAccess* buffer, uint64_t size) {
    auto& engine = hb_engine_singleton();
    if (engine) engine->process(buffer, size);
}

void PcDependency::hb_engine_reset() {
    if (!_hb_trace) return;  // engine only runs in HB-trace mode
    auto& engine = hb_engine_singleton();
    if (!engine) {
        engine = std::make_unique<HbEngine>();
        engine->load_scopes(std::getenv("YOSEMITE_ATOMIC_SCOPE_FILE"));
    }
    engine->reset();
    // expected participant count for a plain __syncthreads (thread_count 0 in the
    // trace) -> the whole block; used to assemble block-barrier instances.
    engine->block_thread_count = _current_block_thread_count;
}

void PcDependency::hb_engine_emit(std::ofstream& jout) {
    auto& engine = hb_engine_singleton();
    if (engine) engine->emit(jout);
}


void PcDependency::kernel_trace_flush(std::shared_ptr<KernelLaunch_t> kernel) {
    // JSON output for building PC dependency graph (joinable with CFG)
    std::string json_filename = output_directory + "/kernel_"
                                + std::to_string(kernel->kernel_id) + ".json";
    std::ofstream jout(json_filename);
    jout << "{\n";
    jout << "  \"tool\": \"pc_dependency_analysis\",\n";
    jout << "  \"kernel\": {\n";
    jout << "    \"kernel_id\": " << kernel->kernel_id << ",\n";
    jout << "    \"kernel_name\": \"" << json_escape(kernel->kernel_name) << "\",\n";
    jout << "    \"device_id\": " << kernel->device_id << ",\n";
    jout << "    \"kernel_pc\": " << kernel->kernel_pc << ",\n";
    jout << "    \"kernel_pc_hex\": \"" << hex_u32((uint32_t)kernel->kernel_pc) << "\",\n";
    jout << "    \"grid_dim\": [" << kernel->grid_dim_x << ", " << kernel->grid_dim_y << ", " << kernel->grid_dim_z << "],\n";
    jout << "    \"grid_cta_count\": " << kernel->grid_cta_count << ",\n";
    jout << "    \"block_dim\": [" << kernel->block_dim_x << ", " << kernel->block_dim_y << ", " << kernel->block_dim_z << "],\n";
    jout << "    \"block_thread_count\": " << kernel->block_thread_count << "\n";
    jout << "  },\n";
    jout << "  \"shadow_memory_granularity_bytes\": 1,\n";
    jout << "  \"sample_stride_bytes\": 4,\n";

    // Collect nodes (all current PCs + all non-cold ancient PCs)
    std::set<uint32_t> nodes;
    for (const auto& kv : _pc_statistics) {
        const uint32_t cur_pc = unpack_current_pc_offset(kv.first);
        const uint32_t anc_pc = unpack_ancient_pc_offset(kv.first);
        nodes.insert(cur_pc);
        if (anc_pc != 0u) {
            nodes.insert(anc_pc);
        }
    }

    jout << "  \"nodes\": [\n";
    {
        bool first = true;
        for (uint32_t pc : nodes) {
            if (!first) jout << ",\n";
            first = false;
            auto fit = _pc_flags.find(pc);
            bool has_flags = (fit != _pc_flags.end());
            uint32_t flags = has_flags ? fit->second.first : 0;
            uint32_t access_size = has_flags ? fit->second.second : 0;
            bool has_distinct_sector_count = (_distinct_sector_count.find(pc) != _distinct_sector_count.end());
            jout << "    {\"pc\": " << pc
                 << ", \"pc_hex\": \"" << hex_u32(pc) << "\"";
            if (has_flags) {
                jout << ", \"flags\": \"" << flags_to_string(flags) << "\""
                     << ", \"flags_hex\": \"" << hex_u32(flags) << "\""
                     << ", \"access_size\": " << access_size;
            } else {
                jout << ", \"flags\": null, \"flags_hex\": null, \"access_size\": null";
            }
            if (has_distinct_sector_count) {
                jout << ", \"distinct_sector_count\": {";
                for (int i = 1; i <= 32; i++) {
                    jout << "\"" << i << "\": " << _distinct_sector_count[pc][i - 1];
                    if (i != 32) {
                        jout << ", ";
                    }
                }
                jout << "}";
                jout << ", \"active_lane_count\": {";
                for (int i = 0; i <= 32; i++) {
                    jout << "\"" << i << "\": " << _distinct_sector_count[pc][32 + i];
                    if (i != 32) {
                        jout << ", ";
                    }
                }
                jout << "}";
                jout << ", \"distinct_address_count\": {";
                for (int i = 1; i <= 32; i++) {
                    jout << "\"" << i << "\": " << _distinct_sector_count[pc][65 + i - 1];
                    if (i != 32) {
                        jout << ", ";
                    }
                }
                jout << "}";
            } else {
                jout << ", \"distinct_sector_count\": null, \"active_lane_count\": null, \"distinct_address_count\": null";
            }
            jout << "}";
        }
        jout << "\n";
    }
    jout << "  ],\n";

    // Edges: ancient_pc -> current_pc, with per-scope counts.
    jout << "  \"edges\": [\n";
    {
        // Stable order: sort by current pc then ancient pc
        struct EdgeRow {
            uint32_t cur_pc;
            uint32_t anc_pc;
            const PC_statisitics* st;
        };
        std::vector<EdgeRow> edges;
        edges.reserve(_pc_statistics.size());
        for (const auto& kv : _pc_statistics) {
            edges.push_back(EdgeRow{
                unpack_current_pc_offset(kv.first),
                unpack_ancient_pc_offset(kv.first),
                &kv.second
            });
        }
        std::sort(edges.begin(), edges.end(), [](const EdgeRow& a, const EdgeRow& b) {
            if (a.cur_pc != b.cur_pc) return a.cur_pc < b.cur_pc;
            return a.anc_pc < b.anc_pc;
        });

        bool first_edge = true;
        for (const auto& e : edges) {
            const uint32_t cur_pc = e.cur_pc;
            const uint32_t anc_pc = e.anc_pc;
            const PC_statisitics& st = *(e.st);

            if (!first_edge) jout << ",\n";
            first_edge = false;

            const bool cold_miss = (anc_pc == 0u);

            // current flags if available
            auto cfit = _pc_flags.find(cur_pc);
            const bool has_cflags = (cfit != _pc_flags.end());
            const uint32_t cflags = has_cflags ? cfit->second.first : 0;
            const uint32_t c_access_size = has_cflags ? cfit->second.second : 0;

            jout << "    {\"current_pc\": " << cur_pc
                 << ", \"current_pc_hex\": \"" << hex_u32(cur_pc) << "\""
                 << ", \"ancient_pc\": ";
            if (cold_miss) {
                jout << "null";
            } else {
                jout << anc_pc;
            }
            jout << ", \"ancient_pc_hex\": ";
            if (cold_miss) {
                jout << "null";
            } else {
                jout << "\"" << hex_u32(anc_pc) << "\"";
            }
            jout << ", \"cold_miss\": " << (cold_miss ? "true" : "false");

            if (has_cflags) {
                jout << ", \"current_flags\": " << cflags
                     << ", \"current_flags_hex\": \"" << hex_u32(cflags) << "\""
                     << ", \"current_access_size\": " << c_access_size;
            } else {
                jout << ", \"current_flags\": null, \"current_flags_hex\": null";
            }

            jout << ", \"dist\": {"
                 << "\"intra_thread\": " << st.dist[0]
                 << ", \"intra_instance_launch\": " << st.dist[1]
                 << ", \"intra_warp\": " << st.dist[2]
                 << ", \"intra_block\": " << st.dist[3]
                 << ", \"intra_grid\": " << st.dist[4]
                 << "}}";
        }
        jout << "\n";
    }
    jout << "  ]";

    // Phase 2 HB oracle: raw temporally-ordered per-instance event stream.
    if (_hb_trace) {
        jout << ",\n  \"hb_events\": [\n";
        for (size_t i = 0; i < _hb_events.size(); ++i) {
            jout << "    " << _hb_events[i];
            if (i + 1 < _hb_events.size()) jout << ",";
            jout << "\n";
        }
        jout << "  ]";
        // Phase 2 dynamic-HB engine verdicts (streaming; mirrors hb_oracle.py).
        hb_engine_emit(jout);
    }

    jout << "\n}\n";
    printf("Dumping pc dependency graph json to %s\n", json_filename.c_str());
}


void PcDependency::kernel_end_callback(std::shared_ptr<KernelEnd_t> kernel) {
    auto evt = std::prev(kernel_events.end())->second;
    evt->end_time = _timer.get();
    kernel_trace_flush(evt);

    _timer.increment(true);
}


void PcDependency::mem_alloc_callback(std::shared_ptr<MemAlloc_t> mem) {
    // TODO： add shadow memory allocation here
    alloc_events.emplace(_timer.get(), mem);
    active_memories.emplace(mem->addr, mem);
    memory_region memory_region_current = memory_region((uint64_t)mem->addr, (uint64_t)(mem->addr + mem->size));
    _memory_regions.insert(
        std::lower_bound(_memory_regions.begin(), _memory_regions.end(), memory_region_current),
        memory_region_current
    );
    _shadow_memories.emplace(memory_region_current, std::make_unique<shadow_memory>(mem->size));

    printf("[PC_DEPENDENCY] Allocating shadow memory for memory region: %p - %p, size: %lu\n", (void*)memory_region_current.get_start(), (void*)memory_region_current.get_end(), mem->size);
    _timer.increment(true);
}

void PcDependency::mem_free_callback(std::shared_ptr<MemFree_t> mem) {
    auto it = active_memories.find(mem->addr);
    if(it == active_memories.end()) {
        printf("[PC_DEPENDENCY] Memory free callback: memory %lu not found, it is not regularly allocated. Active memories: %ld\n", mem->addr, active_memories.size());
        return;
    }
    // assert(it != active_memories.end());

    uint64_t sz = it->second->size;   // 从 alloc 事件拿 size
    active_memories.erase(it);

    memory_region r((uint64_t)mem->addr, (uint64_t)mem->addr + sz);

    auto vit = std::lower_bound(_memory_regions.begin(), _memory_regions.end(), r);
    if (vit != _memory_regions.end() && *vit == r) _memory_regions.erase(vit);

    _shadow_memories.erase(r);
    printf("[PC_DEPENDENCY] Freeing shadow memory for memory region: %p - %p, size: %lu\n", (void*)r.get_start(), (void*)r.get_end(), sz);
    _timer.increment(true);
}


void PcDependency::ten_alloc_callback(std::shared_ptr<TenAlloc_t> ten) {
    tensor_events.emplace(_timer.get(), ten);
    active_tensors.emplace(ten->addr, ten);
    // memory_region memory_region_current((uint64_t)ten->addr, (uint64_t)(ten->addr + ten->size));
    // _memory_regions.insert(
    //     std::lower_bound(_memory_regions.begin(), _memory_regions.end(), memory_region_current),
    //     memory_region_current
    // );
    // _shadow_memories.emplace(memory_region_current, std::make_unique<shadow_memory>(ten->size));
    // printf("[PC_DEPENDENCY] Allocating shadow memory for tensor region: %p - %p, size: %lu\n", (void*)ten->addr, (void*)(ten->addr + ten->size), ten->size);

    _timer.increment(true);
}


void PcDependency::ten_free_callback(std::shared_ptr<TenFree_t> ten) {
    auto it = active_tensors.find(ten->addr);
    assert(it != active_tensors.end());

    // TenFree.size may be negative (e.g., accounting-style events). Use size from TenAlloc.
    const uint64_t sz = static_cast<uint64_t>(it->second->size);
    active_tensors.erase(it);

    // memory_region r((uint64_t)ten->addr, (uint64_t)ten->addr + sz);

    // auto vit = std::lower_bound(_memory_regions.begin(), _memory_regions.end(), r);
    // if (vit != _memory_regions.end() && *vit == r) {
    //     _memory_regions.erase(vit);
    // }

    // _shadow_memories.erase(r);
    // printf("[PC_DEPENDENCY] Freeing shadow memory for tensor region: %p - %p, size: %lu\n",
        //    (void*)r.get_start(), (void*)r.get_end(), sz);
    _timer.increment(true);
}

void PcDependency::unit_access(
    uint64_t ptr,
    uint32_t pc_offset,
    uint64_t current_block_id,
    uint32_t current_warp_id,
    uint32_t current_lane_id,
    memory_region& memory_region_target,
    int access_size,
    phmap::flat_hash_map<uint64_t, PC_statisitics>& local_pc_statistics
) {
    // auto& shadow_memory = this->_shadow_memories[memory_region_target];
    auto shadow_memory_it = this->_shadow_memories.find(memory_region_target);
    if (shadow_memory_it == this->_shadow_memories.end()) {
        printf("shadow memory not found for memory region: %lu - %lu\n", memory_region_target.get_start(), memory_region_target.get_end());
        return;
    }
    auto& shadow_memory = *(shadow_memory_it->second);
    const uint32_t current_flat_thread_id =
        static_cast<uint32_t>((current_block_id << 10) | (current_warp_id << 5) | current_lane_id);

    for (int i = 0; i < access_size; i += 4) {
        const uint64_t addr = ptr + i;
        // Byte-granularity shadow memory: addr is byte offset within allocation.
        // Bound check to avoid OOB on allocations at end boundary or odd sizes.
        if (addr >= shadow_memory._size) {
            break;
        }

        auto& entry = shadow_memory.get_entry(addr);
        const uint64_t old_packed = __atomic_exchange_n(
            &entry.packed,
            pack_shadow_entry(_kernel_generation, pc_offset, current_flat_thread_id),
            __ATOMIC_ACQ_REL
        );
        const bool is_cold_miss = (old_packed == 0);

        if (is_cold_miss) {
            const uint64_t pc_ancient_pairs = pack_pc_ancient_pairs(pc_offset, 0u);
            local_pc_statistics[pc_ancient_pairs].dist[0] += 1;
            continue;
        }

        const uint32_t last_pc_encoded = unpack_shadow_pc_encoded(old_packed);
        const uint8_t last_generation = static_cast<uint8_t>(last_pc_encoded >> 24);
        if (last_generation != _kernel_generation) {
            const uint64_t pc_ancient_pairs = pack_pc_ancient_pairs(pc_offset, 0u);
            local_pc_statistics[pc_ancient_pairs].dist[0] += 1;
            continue;
        }
        const uint32_t last_pc = (last_pc_encoded & 0x00FFFFFFu);
        const uint32_t last_flat_thread_id = unpack_shadow_flat_tid(old_packed);
        const uint64_t last_block_id = static_cast<uint64_t>(last_flat_thread_id >> 10);
        const uint64_t last_warp_id = static_cast<uint64_t>((last_flat_thread_id >> 5) & 0x1F);
        const uint64_t last_lane_id = static_cast<uint64_t>(last_flat_thread_id & 0x1F);
        const uint64_t pc_ancient_pairs = pack_pc_ancient_pairs(pc_offset, last_pc);
        if (last_block_id != current_block_id) {
            local_pc_statistics[pc_ancient_pairs].dist[4] += 1;
        } else if (last_warp_id != current_warp_id) {
            local_pc_statistics[pc_ancient_pairs].dist[3] += 1;
        } else if (last_lane_id != current_lane_id) {
            local_pc_statistics[pc_ancient_pairs].dist[2] += 1;
        } else {
            local_pc_statistics[pc_ancient_pairs].dist[0] += 1;
        }
    }
}

void PcDependency::unit_access_unknown(
    uint64_t abs_addr,
    uint32_t pc_offset,
    uint64_t current_block_id,
    uint32_t current_warp_id,
    uint32_t current_lane_id,
    int access_size,
    phmap::flat_hash_map<uint64_t, PC_statisitics>& local_pc_statistics
) {
    const uint32_t current_flat_thread_id =
        static_cast<uint32_t>((current_block_id << 10) | (current_warp_id << 5) | current_lane_id);

    for (int i = 0; i < access_size; i += 4) {
        const uint64_t sampled_addr = abs_addr + static_cast<uint64_t>(i);
        const uint64_t new_packed =
            pack_shadow_entry(_kernel_generation, pc_offset, current_flat_thread_id);

        // Atomically insert-or-update under the shard's lock.
        // try_emplace_l: if key exists  -> calls lambda(value_ref), returns false.
        //                if key missing -> inserts with new_packed,  returns true.
        uint64_t old_packed = 0;
        const bool inserted = _unknown_region_shadow.try_emplace_l(
            sampled_addr,
            [&](auto& kv) {
                old_packed = kv.second;
                kv.second = new_packed;
            },
            new_packed   // value used when the key is first inserted
        );

        if (inserted) {
            // First-ever access to this address this kernel → cold miss.
            local_pc_statistics[pack_pc_ancient_pairs(pc_offset, 0u)].dist[0] += 1;
            continue;
        }

        // Key already existed; old_packed holds the previous entry.
        const bool is_cold_miss = (old_packed == 0);
        if (is_cold_miss) {
            local_pc_statistics[pack_pc_ancient_pairs(pc_offset, 0u)].dist[0] += 1;
            continue;
        }

        const uint32_t last_pc_encoded = unpack_shadow_pc_encoded(old_packed);
        const uint8_t last_generation = static_cast<uint8_t>(last_pc_encoded >> 24);
        if (last_generation != _kernel_generation) {
            local_pc_statistics[pack_pc_ancient_pairs(pc_offset, 0u)].dist[0] += 1;
            continue;
        }

        const uint32_t last_pc            = (last_pc_encoded & 0x00FFFFFFu);
        const uint32_t last_flat_thread_id = unpack_shadow_flat_tid(old_packed);
        const uint64_t last_block_id       = static_cast<uint64_t>(last_flat_thread_id >> 10);
        const uint64_t last_warp_id        = static_cast<uint64_t>((last_flat_thread_id >> 5) & 0x1F);
        const uint64_t last_lane_id        = static_cast<uint64_t>(last_flat_thread_id & 0x1F);

        const uint64_t pc_ancient_pairs = pack_pc_ancient_pairs(pc_offset, last_pc);
        if (last_block_id != current_block_id) {
            local_pc_statistics[pc_ancient_pairs].dist[4] += 1;
        } else if (last_warp_id != current_warp_id) {
            local_pc_statistics[pc_ancient_pairs].dist[3] += 1;
        } else if (last_lane_id != current_lane_id) {
            local_pc_statistics[pc_ancient_pairs].dist[2] += 1;
        } else {
            local_pc_statistics[pc_ancient_pairs].dist[0] += 1;
        }
    }
}


void PcDependency::unit_access_shared(
    uint64_t ptr,
    uint32_t pc_offset,
    uint32_t object_idx,
    uint64_t current_block_id,
    uint32_t current_warp_id,
    uint32_t current_lane_id,
    int access_size,
    phmap::flat_hash_map<uint64_t, PC_statisitics>& local_pc_statistics,
    worker_shared_shadow_state& local_shadow_memory_shared
) {
    const uint32_t base_addr_low32 = static_cast<uint32_t>(ptr & 0xFFFFFFFFull);
    const uint32_t current_flat_thread_id =
        static_cast<uint32_t>((current_warp_id << 5) | current_lane_id);

    for (int i = 0; i < access_size; i += 4) {
        const uint32_t addr = base_addr_low32 + static_cast<uint32_t>(i);
        if (addr >= _shared_shadow_bytes_per_object) {
            const uint64_t pc_ancient_pairs = pack_pc_ancient_pairs(pc_offset, 0u);
            local_pc_statistics[pc_ancient_pairs].dist[0] += 1;
            continue;
        }
        auto& entry = get_shared_shadow_entry(local_shadow_memory_shared, object_idx, addr);
        const bool is_cold_miss = (entry.generation != _shared_kernel_generation)
                               || (entry.flat_block_id != static_cast<uint32_t>(current_block_id));

        if (is_cold_miss) {
            entry.pc_offset = pc_offset;
            entry.flat_thread_id = current_flat_thread_id;
            entry.flat_block_id = static_cast<uint32_t>(current_block_id);
            entry.generation = _shared_kernel_generation;
            const uint64_t pc_ancient_pairs = pack_pc_ancient_pairs(pc_offset, 0u);
            local_pc_statistics[pc_ancient_pairs].dist[0] += 1;
            continue;
        }

        const uint32_t last_pc = entry.pc_offset;
        const uint32_t last_flat_thread_id = entry.flat_thread_id;
        const uint64_t last_warp_id = static_cast<uint64_t>((last_flat_thread_id >> 5) & 0x1F);
        const uint64_t last_lane_id = static_cast<uint64_t>(last_flat_thread_id & 0x1F);

        entry.pc_offset = pc_offset;
        entry.flat_thread_id = current_flat_thread_id;
        entry.flat_block_id = static_cast<uint32_t>(current_block_id);
        entry.generation = _shared_kernel_generation;
        const uint64_t pc_ancient_pairs = pack_pc_ancient_pairs(pc_offset, last_pc);
        if (last_warp_id != current_warp_id) {
            local_pc_statistics[pc_ancient_pairs].dist[3] += 1;
        } else if (last_lane_id != current_lane_id) {
            local_pc_statistics[pc_ancient_pairs].dist[2] += 1;
        } else {
            local_pc_statistics[pc_ancient_pairs].dist[0] += 1;
        }
    }
}

uint32_t PcDependency::acquire_shared_shadow_object(
    worker_shared_shadow_state& local_shadow_memory_shared,
    uint64_t cta_id
) {
    const uint64_t local_slot_u64 = cta_id / _worker_count;
    if (local_slot_u64 >= local_shadow_memory_shared.cta_slot_to_object.size()) {
        local_shadow_memory_shared.cta_slot_to_object.resize(
            static_cast<size_t>(local_slot_u64 + 1u),
            worker_shared_shadow_state::k_invalid_object
        );
    }
    const uint32_t local_slot = static_cast<uint32_t>(local_slot_u64);
    const uint32_t mapped_object = local_shadow_memory_shared.cta_slot_to_object[local_slot];
    if (mapped_object != worker_shared_shadow_state::k_invalid_object) {
        return mapped_object;
    }
    if (local_shadow_memory_shared.free_object_indices.empty()) {
        local_shadow_memory_shared.pool_miss_count += 1;
        return std::numeric_limits<uint32_t>::max();
    }
    const uint32_t object_idx = local_shadow_memory_shared.free_object_indices.back();
    local_shadow_memory_shared.free_object_indices.pop_back();
    local_shadow_memory_shared.object_owner_cta[object_idx] = cta_id;
    local_shadow_memory_shared.object_active_threads[object_idx] = _current_block_thread_count;
    local_shadow_memory_shared.cta_slot_to_object[local_slot] = object_idx;
    return object_idx;
}

void PcDependency::release_shared_shadow_object(
    worker_shared_shadow_state& local_shadow_memory_shared,
    uint64_t cta_id,
    uint32_t exiting_threads
) {
    const uint64_t local_slot_u64 = cta_id / _worker_count;
    if (local_slot_u64 >= local_shadow_memory_shared.cta_slot_to_object.size()) {
        return;
    }
    const uint32_t local_slot = static_cast<uint32_t>(local_slot_u64);
    const uint32_t object_idx = local_shadow_memory_shared.cta_slot_to_object[local_slot];
    if (object_idx == worker_shared_shadow_state::k_invalid_object) {
        return;
    }
    uint32_t& active_threads = local_shadow_memory_shared.object_active_threads[object_idx];
    if (active_threads > exiting_threads) {
        active_threads -= exiting_threads;
        return;
    }
    active_threads = 0;
    local_shadow_memory_shared.cta_slot_to_object[local_slot] = worker_shared_shadow_state::k_invalid_object;
    local_shadow_memory_shared.object_owner_cta[object_idx] = std::numeric_limits<uint64_t>::max();
    local_shadow_memory_shared.object_active_threads[object_idx] = 0u;
    local_shadow_memory_shared.free_object_indices.push_back(object_idx);
}

shared_shadow_memory_entry& PcDependency::get_shared_shadow_entry(
    worker_shared_shadow_state& local_shadow_memory_shared,
    uint32_t object_idx,
    uint32_t addr
) {
    assert(addr < _shared_shadow_bytes_per_object);
    return local_shadow_memory_shared.object_entries[object_idx][addr];
}

void PcDependency::unit_access_local(uint64_t ptr, uint32_t pc_offset, uint64_t current_block_id, uint32_t current_warp_id, uint32_t current_lane_id, int access_size) {
    // TODO: implement local memory access
}


void PcDependency::worker_loop(uint64_t worker_idx) {
    uint64_t seen_generation = 0;
    while (true) {
        uint64_t current_generation = 0;
        {
            std::unique_lock<std::mutex> lock(_worker_pool_mutex);
            _worker_pool_cv.wait(lock, [&]{
                return _worker_pool_shutdown || _worker_job_generation > seen_generation;
            });
            if (_worker_pool_shutdown) {
                return;
            }
            current_generation = _worker_job_generation;
        }

        auto& local_pc_statistics = _job_worker_pc_statistics[worker_idx];
        auto& local_pc_flags = _job_worker_pc_flags[worker_idx];
        auto& local_distinct_sector_count = _job_worker_distinct_sector_count[worker_idx];
        auto& local_shadow_memory_shared = _worker_shadow_memory_shared[worker_idx];
        const auto& trace_indices = _job_worker_trace_indices[worker_idx];

        for (uint64_t i : trace_indices) {
            const MemoryAccess& trace = _job_accesses_buffer[i];
            uint32_t pc_offset = (trace.pc & 0x00FFFFFFu);
            uint32_t flags = trace.flags;
            uint32_t access_size = trace.accessSize;
            uint32_t distinct_sector_count = trace.distinct_sector_count;
            uint32_t active_mask = trace.active_mask;
            switch (trace.type) {
                case MemoryType::Local:{
                        flags |= SANITIZER_MEMORY_LOCAL;
                        break;
                    }
                case MemoryType::Shared:{
                        flags |= SANITIZER_MEMORY_SHARED;
                        const uint32_t object_idx =
                            acquire_shared_shadow_object(local_shadow_memory_shared, trace.ctaId);
                        if (object_idx == std::numeric_limits<uint32_t>::max()) {
                            // Hard capacity hit: keep behavior safe by treating accesses as cold misses.
                            const uint32_t samples = (trace.accessSize + 3u) / 4u;
                            const uint64_t pc_ancient_pairs = pack_pc_ancient_pairs(pc_offset, 0u);
                            local_pc_statistics[pc_ancient_pairs].dist[0] +=
                                static_cast<uint64_t>(samples) * static_cast<uint64_t>(__builtin_popcount(active_mask));
                            break;
                        }
                        // Repeat lanes are intra-instance-launch reuse.
                        const uint32_t unique_mask = trace.unique_address_mask;
                        const uint32_t repeat_count = __builtin_popcount(active_mask & ~unique_mask);
                        if (repeat_count > 0) {
                            local_pc_statistics[pack_pc_ancient_pairs(pc_offset, pc_offset)].dist[1] += repeat_count;
                        }
                        uint32_t remaining_mask = unique_mask;
                        while (remaining_mask != 0) {
                            const uint32_t j = static_cast<uint32_t>(__builtin_ctz(remaining_mask));
                            remaining_mask &= (remaining_mask - 1);
                            unit_access_shared(
                                trace.addresses[j],
                                pc_offset,
                                object_idx,
                                trace.ctaId,
                                trace.warpId,
                                j,
                                trace.accessSize,
                                local_pc_statistics,
                                local_shadow_memory_shared
                            );
                        }
                        break;
                    }
                case MemoryType::Global:{
                        flags |= SANITIZER_MEMORY_GLOBAL;
                        if (active_mask == 0) {
                            break;
                        }
                        // Repeat lanes (same address as an earlier lane in this warp) are
                        // intra-instance-launch reuse: classify directly without shadow access.
                        const uint32_t unique_mask = trace.unique_address_mask;
                        const uint32_t repeat_count = __builtin_popcount(active_mask & ~unique_mask);
                        if (repeat_count > 0) {
                            local_pc_statistics[pack_pc_ancient_pairs(pc_offset, pc_offset)].dist[1] += repeat_count;
                        }
                        const uint32_t first_lane = static_cast<uint32_t>(__builtin_ctz(active_mask));
                        const uint64_t first_valid_address = trace.addresses[first_lane];
                        const memory_region* memory_region_target_ptr =
                            find_memory_region_containing(this->_memory_regions, first_valid_address);
                        uint32_t remaining_mask = unique_mask;
                        if (memory_region_target_ptr == nullptr) {
                            // Fallback: region not tracked (static __device__ global,
                            // VMM-mapped memory, etc.).  Use the concurrent hashmap.
                            while (remaining_mask != 0) {
                                const uint32_t j = static_cast<uint32_t>(__builtin_ctz(remaining_mask));
                                remaining_mask &= (remaining_mask - 1);
                                unit_access_unknown(
                                    trace.addresses[j],
                                    pc_offset,
                                    trace.ctaId,
                                    trace.warpId,
                                    j,
                                    access_size,
                                    local_pc_statistics
                                );
                            }
                        } else {
                            memory_region memory_region_target = *memory_region_target_ptr;
                            uint64_t memory_region_start = memory_region_target.get_start();
                            while (remaining_mask != 0) {
                                const uint32_t j = static_cast<uint32_t>(__builtin_ctz(remaining_mask));
                                remaining_mask &= (remaining_mask - 1);
                                unit_access(
                                    trace.addresses[j] - memory_region_start,
                                    pc_offset,
                                    trace.ctaId,
                                    trace.warpId,
                                    j,
                                    memory_region_target,
                                    access_size,
                                    local_pc_statistics
                                );
                            }
                        }
                        break;
                    }
                case MemoryType::BlockExit:{
                        const uint32_t exiting_threads = __builtin_popcount(active_mask);
                        release_shared_shadow_object(local_shadow_memory_shared, trace.ctaId, exiting_threads);
                        continue;
                    }
                case MemoryType::Barrier:
                case MemoryType::Syncwarp:
                    // Phase 2 sync events: no shadow/pc-statistics update. Consumed
                    // by hb_collect_events (HB oracle) and, later, the epoch engine.
                    continue;
                default:
                    printf("unknown memory type\n");
                    break;
            }
            auto& local_flag = local_pc_flags[pc_offset];
            local_flag.first |= flags;
            if (local_flag.second == 0) {
                local_flag.second = access_size;
            } else if (local_flag.second != access_size) {
                local_flag.second = std::max(local_flag.second, access_size);
            }
            if (distinct_sector_count >= 1 && distinct_sector_count <= 32) {
                local_distinct_sector_count[pc_offset][distinct_sector_count - 1] += 1;
            }
            const uint32_t active_lane_count = __builtin_popcount(active_mask);
            if (active_lane_count <= 32) {
                local_distinct_sector_count[pc_offset][32 + active_lane_count] += 1;
            }
            const uint32_t distinct_address_count = __builtin_popcount(trace.unique_address_mask);
            if (distinct_address_count >= 1 && distinct_address_count <= 32) {
                local_distinct_sector_count[pc_offset][65 + distinct_address_count - 1] += 1;
            }
        }

        {
            std::lock_guard<std::mutex> guard(_worker_pool_mutex);
            seen_generation = current_generation;
            if (!trace_indices.empty()) {
                assert(_worker_pending_jobs > 0);
                _worker_pending_jobs -= 1;
                if (_worker_pending_jobs == 0) {
                    _worker_pool_done_cv.notify_one();
                }
            }
        }
    }
}


void PcDependency::gpu_data_analysis(void* data, uint64_t size) {
    printf("[PC_DEPENDENCY] GPU data analysis called with size = %lu\n", size);
    MemoryAccess* accesses_buffer = (MemoryAccess*)data;
    if (size == 0) {
        return;
    }

    if (_hb_trace) {
        hb_collect_events(accesses_buffer, size);
        // YOSEMITE_HB_NO_ENGINE isolates the event-dump cost from the engine cost
        // (A/B lever for the bounded-clock / FastTrack-epoch calibration). On a
        // reduction of 4M elts (136K events) the engine's exact unbounded VCs add
        // ~4s vs ~1.3s for the dump — the growing per-thread clocks under heavy
        // __syncthreads are the target of the scale knobs.
        if (std::getenv("YOSEMITE_HB_NO_ENGINE") == nullptr) hb_engine_process(accesses_buffer, size);
    }

    for (uint64_t worker_idx = 0; worker_idx < _worker_count; ++worker_idx) {
        _job_worker_trace_indices[worker_idx].clear();
        _job_worker_pc_statistics[worker_idx].clear();
        _job_worker_pc_flags[worker_idx].clear();
        _job_worker_distinct_sector_count[worker_idx].clear();
        _job_worker_trace_indices[worker_idx].reserve((size / _worker_count) + 1);
    }

    // Stable assignment by block id keeps intra-block trace order.
    for (uint64_t i = 0; i < size; ++i) {
        const uint64_t worker_idx = accesses_buffer[i].ctaId % _worker_count;
        _job_worker_trace_indices[worker_idx].push_back(i);
    }

    uint64_t pending_jobs = 0;
    for (uint64_t worker_idx = 0; worker_idx < _worker_count; ++worker_idx) {
        if (!_job_worker_trace_indices[worker_idx].empty()) {
            pending_jobs += 1;
        }
    }
    if (pending_jobs == 0) {
        return;
    }

    {
        std::lock_guard<std::mutex> guard(_worker_pool_mutex);
        _job_accesses_buffer = accesses_buffer;
        _worker_pending_jobs = pending_jobs;
        ++_worker_job_generation;
    }
    _worker_pool_cv.notify_all();
    {
        std::unique_lock<std::mutex> lock(_worker_pool_mutex);
        _worker_pool_done_cv.wait(lock, [&]{
            return _worker_pending_jobs == 0;
        });
    }

    for (auto& local_flags_map : _job_worker_pc_flags) {
        for (auto& [pc, local_flag] : local_flags_map) {
            auto& global_flag = this->_pc_flags[pc];
            global_flag.first |= local_flag.first;
            if (global_flag.second == 0) {
                global_flag.second = local_flag.second;
            } else if (global_flag.second != local_flag.second) {
                global_flag.second = std::max(global_flag.second, local_flag.second);
            }
        }
    }

    for (auto& local_distinct_map : _job_worker_distinct_sector_count) {
        for (auto& [pc, local_hist] : local_distinct_map) {
            auto& global_hist = this->_distinct_sector_count[pc];
            for (size_t idx = 0; idx < global_hist.size(); ++idx) {
                global_hist[idx] += local_hist[idx];
            }
        }
    }

    for (auto& local_map : _job_worker_pc_statistics) {
        for (auto& kv : local_map) {
            auto& global_stats = this->_pc_statistics[kv.first];
            for (int d = 0; d < 5; ++d) {
                global_stats.dist[d] += kv.second.dist[d];
            }
        }
    }

}


void PcDependency::evt_callback(EventPtr_t evt) {
    switch (evt->evt_type) {
        case EventType_KERNEL_LAUNCH:
            kernel_start_callback(std::dynamic_pointer_cast<KernelLaunch_t>(evt));
            break;
        case EventType_KERNEL_END:
            kernel_end_callback(std::dynamic_pointer_cast<KernelEnd_t>(evt));
            break;
        case EventType_MEM_ALLOC:
            mem_alloc_callback(std::dynamic_pointer_cast<MemAlloc_t>(evt));
            break;
        case EventType_MEM_FREE:
            mem_free_callback(std::dynamic_pointer_cast<MemFree_t>(evt));
            break;
        case EventType_TEN_ALLOC:
            ten_alloc_callback(std::dynamic_pointer_cast<TenAlloc_t>(evt));
            break;
        case EventType_TEN_FREE:
            ten_free_callback(std::dynamic_pointer_cast<TenFree_t>(evt));
            break;
        default:
            break;
    }
}


void PcDependency::flush() {
}

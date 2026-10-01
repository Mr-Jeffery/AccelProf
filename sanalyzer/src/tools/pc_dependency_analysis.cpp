#include "tools/pc_dependency_analysis.h"
#include "utils/helper.h"

#include <algorithm>
#include <cctype>
#include <cstdint>
#include <cstdlib>
#include <cstdio>
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
#include <unordered_set>
#include <algorithm>
#include <numeric>

// T15: see pc_dependency_set_late_keys.
namespace {
std::vector<uint64_t> g_late_keys;      // keys of the next drain, empty = none handed over
uint32_t g_late_mode = 0;               // 1 atomic counter, 2 %globaltimer
uint32_t g_late_kernel_mode = 0;        // the mode this kernel's dump was ordered by
uint64_t g_hb_bpos_base = 0;            // buffer slots drained so far in this kernel
// T4 (design/no_dump.md): what the hb_events array would hold -- records (non-local) and
// lane-accesses -- counted on every drain, written as hb_events_count / hb_lanes_count whether
// or not the array itself is written (YOSEMITE_HB_DUMP).
uint64_t g_hb_events_count = 0, g_hb_lanes_count = 0;
}  // namespace


using namespace yosemite;

namespace yosemite {

// Streaming scoped vector-clock happens-before: a 1:1 port of the reference
// spec python/hb_oracle.py (analyze()), which is Algorithm 1 "Detect" of
// design/proof/hb_proof.tex with the trusting gate (I4). Runs over the raw MemoryAccess
// buffer in temporal order (-n 1); every verdict falls out of the clocks with no pattern
// special-cased. Per location it keeps one bucket per (thread, record key) -- never a
// FastTrack collapse across threads, which Theorem "Sound" does not survive (T9, I2).
// ponytail: sparse VCs over shared bases (T5b); a clock is O(threads) only in what it knows.
// HbClock is the computation (vector-clock mode's runtime): it owns the thread clocks, of the
// value type VClock below, and the per-location state.
struct HbClock {
    // sync scopes match sync_dominance.SCOPES: NONE=0, (WARP=1), BLOCK=2, GRID=3.
    static constexpr int SCOPE_NONE = 0;
    static constexpr int SCOPE_BLOCK = 2;
    static constexpr int SCOPE_GRID = 3;

    // Thread id: (block << 10) | (warp << 5) | lane, 64-bit so no grid size overflows it
    // and a high bit is free for a thread's async-copy agent (T1a, ASYNC_BIT).
    using Tid = uint64_t;
    using Clock = std::unordered_map<Tid, uint64_t>;        // tid -> logical clock
    using Loc = std::tuple<int, uint64_t, uint64_t>;        // (space, block-or-0, addr)

    // pc offset -> coherent-access info; absence => plain ld/st. rmw = an atomic RMW
    // (release/acquire point + write); !rmw = a .STRONG load/store (cuda::atomic
    // load()/store()): pairwise same-address coherence only, otherwise an ordinary
    // read/write. pcs are function-relative, so the table is per kernel (sidecar line
    // `<pc> <scope> <kind> <kernel>`); `merged` serves legacy `<pc> <scope>` sidecars
    // and kernels the sidecar does not name.
    struct PcInfo { int scope; bool rmw; };
    using PcTable = std::unordered_map<uint32_t, PcInfo>;
    std::unordered_map<std::string, PcTable> kernel_tables;
    PcTable merged;
    const PcTable* atom_scope = &merged;
    // T10 (D9): the sidecar's strength column, `# strength <pc> <strong|weak> <scope|-> <kernel>`
    // for every memory pc: a record's strong scope (-1 = weak), read off the SASS
    // .STRONG.<scope> token, for its key and moral strength. Without it (a pre-T10 sidecar,
    // or a pre-T10 --strong-ldst policy) the coherent-pc lines decide, as before.
    using StrengthTable = std::unordered_map<uint32_t, int>;
    std::unordered_map<std::string, StrengthTable> kernel_strength;
    StrengthTable merged_strength, no_strength;
    const StrengthTable* strength = &merged_strength;
    bool has_strength = false;
    // T12 (design/instance_gate.md; hb_proof.tex Definition "Gate"): the instance gate's table,
    // sidecar lines `# gate <rmw pc> rel|acq <kernel> <pc>...` -- per RMW pc the record pcs p
    // with fenced(p, r, scope(r), release) and q with fenced(r, q, scope(r), acquire). rel(r) =
    // t's previous record pc listed (or none), acq(r) = t's next record pc listed (or none: the
    // end of the kernel). A kernel with a `# gate-kernel` line runs the instance gate unless
    // YOSEMITE_HB_GATE=trusting; any other kernel (a pre-T12 sidecar) the trusting gate.
    struct GateSets { std::unordered_set<uint32_t> rel, acq; };
    using GateTable = std::unordered_map<uint32_t, GateSets>;
    std::unordered_map<std::string, GateTable> kernel_gates;
    const GateTable* gate = nullptr;                        // nullptr: the trusting gate
    bool gate_env_trusting = false;
    // each thread's latest record pc + 1 (0: none), per warp: rel(r) needs t's previous record
    std::unordered_map<uint64_t, std::array<uint32_t, 32>> last_pc;

    // T5b: the main clock in the sync-only clock's representation (eval/MEMORY_FOOTPRINT.md
    // "After the fix"). A thread's clock is the pointwise max of an immutable base, shared by
    // every clock that holds it (a sync group's joined clock, a release's snapshot), a delta
    // of the entries above it (acquires since then), and its own component, which lives only
    // in `own`. A barrier allocates one base for its participants, not one clock each, and a
    // release stores a pointer + the delta. The values are those of the full clocks, so the
    // representation is invisible to every test on them; hb_oracle.py keeps full clocks.
    // A base is immutable, so it is a flat vector sorted by tid (one allocation; a merge is one
    // linear pass; lookup by binary search) rather than a node-based map.
    using Base = std::vector<std::pair<Tid, uint64_t>>;
    using BaseP = std::shared_ptr<const Base>;
    static uint64_t base_get(const Base& b, Tid u) {
        const auto it = std::lower_bound(b.begin(), b.end(), u,
            [](const std::pair<Tid, uint64_t>& e, Tid x) { return e.first < x; });
        return (it != b.end() && it->first == u) ? it->second : 0;
    }
    // pointwise max; a_has_all / b_has_all: the result equals a / b (then a caller may keep it)
    static Base base_merge(const Base& a, const Base& b, bool* a_has_all = nullptr,
                           bool* b_has_all = nullptr) {
        Base out;
        out.reserve(a.size() + b.size());
        bool ga = true, gb = true;                          // a ⊒ b, b ⊒ a so far
        auto i = a.begin(), j = b.begin();
        while (i != a.end() && j != b.end()) {
            if (i->first < j->first) { out.push_back(*i++); gb = false; }
            else if (j->first < i->first) { out.push_back(*j++); ga = false; }
            else {
                if (i->second < j->second) ga = false;
                if (j->second < i->second) gb = false;
                out.emplace_back(i->first, std::max(i->second, j->second)); ++i; ++j;
            }
        }
        if (i != a.end()) gb = false;
        if (j != b.end()) ga = false;
        out.insert(out.end(), i, a.end());
        out.insert(out.end(), j, b.end());
        if (a_has_all) *a_has_all = ga;
        if (b_has_all) *b_has_all = gb;
        return out;
    }
    static Base base_sorted(std::vector<std::pair<Tid, uint64_t>> v) {   // sort, max per tid
        std::sort(v.begin(), v.end());
        Base out;
        out.reserve(v.size());
        for (const auto& e : v) {
            if (!out.empty() && out.back().first == e.first) out.back().second = e.second;  // sorted: last is max
            else out.push_back(e);
        }
        return out;
    }
    static Base base_of(const Clock& c) { return base_sorted(Base(c.begin(), c.end())); }

    // VClock is a clock value (T5b's shared base + delta + own component), not the computation:
    // HbClock owns one per thread (vc, pd) and copies them into releases and commits.
    struct VClock {
        BaseP base;
        Clock delta;                                        // never holds `self`
        uint64_t own = 0;
        Tid self = 0;
        uint64_t get(Tid u) const {
            if (u == self) return own;
            const uint64_t v = base ? base_get(*base, u) : 0;
            if (delta.empty()) return v;
            const auto it = delta.find(u);
            return (it != delta.end() && it->second > v) ? it->second : v;
        }
    };
    std::unordered_map<Tid, VClock> vc;                     // tid -> vector clock
    VClock& V(Tid t) {
        auto r = vc.try_emplace(t);
        if (r.second) r.first->second.self = t;
        return r.first->second;
    }
    // d ⊔= (u: v), keeping the representation's invariants (self in own, delta above base)
    static void raise(VClock& d, Tid u, uint64_t v) {
        if (u == d.self) { if (v > d.own) d.own = v; return; }
        if (d.base && base_get(*d.base, u) >= v) return;
        uint64_t& x = d.delta[u];
        if (v > x) x = v;
    }
    // Joining another base: a small one goes into the delta; a large one is merged with ours
    // into a new base, memoised on the pair, so the threads of one sync group acquiring from
    // releases of one other group share the merged base. A delta that has grown past a
    // 32nd of its base (and 64 entries) is folded into a private base, so a release keeps
    // copying O(delta) and the fold's O(base) cost is amortised over the entries it absorbs.
    static constexpr size_t DELTA_JOIN_MAX = 64, FOLD_MIN = 64;
    struct MergeKey {
        const Base* a; const Base* b;
        bool operator==(const MergeKey& o) const { return a == o.a && b == o.b; }
    };
    struct MergeKeyHash {
        size_t operator()(const MergeKey& k) const {
            return std::hash<const void*>()(k.a) * 0x9e3779b97f4a7c15ULL ^ std::hash<const void*>()(k.b);
        }
    };
    // weak references: an entry pins no base, and one whose input or result was freed (its
    // address may since be reused) is a miss, so a key's pointers name live bases only
    struct Merged { std::weak_ptr<const Base> a, b, out; };
    std::unordered_map<MergeKey, Merged, MergeKeyHash> merge_memo;
    static constexpr size_t MERGE_MEMO_MAX = size_t(1) << 20;
    BaseP merge_bases(const BaseP& a, const BaseP& b) {
        const MergeKey k = a.get() < b.get() ? MergeKey{a.get(), b.get()} : MergeKey{b.get(), a.get()};
        const auto it = merge_memo.find(k);
        if (it != merge_memo.end() && !it->second.a.expired() && !it->second.b.expired())
            if (auto o = it->second.out.lock()) return o;
        BaseP out;
        bool ga = false, gb = false;
        Base m = base_merge(*a, *b, &ga, &gb);
        out = ga ? a : gb ? b : std::make_shared<const Base>(std::move(m));
        if (merge_memo.size() >= MERGE_MEMO_MAX) merge_memo.clear();
        merge_memo[k] = Merged{a, b, out};
        return out;
    }
    // `skip` (T14's pd): entries it already covers need not be stored -- only the join
    // skip ⊔ d is ever read -- so they are dropped where it is cheap (delta, own, a small
    // base); a large base is shared as it is.
    void join_vc(VClock& d, const VClock& s, const VClock* skip = nullptr) {
        auto put = [&](Tid u, uint64_t v) {
            if (skip == nullptr || v > skip->get(u)) raise(d, u, v);
        };
        if (s.base && s.base != d.base) {
            if (s.base->size() <= DELTA_JOIN_MAX && (d.base || skip != nullptr)) {
                for (const auto& kv : *s.base) put(kv.first, kv.second);
            } else if (!d.base) {
                d.base = s.base;
            } else {
                d.base = merge_bases(d.base, s.base);
            }
            if (d.base) {                                   // own holds self's whole value
                const uint64_t v = base_get(*d.base, d.self);
                if (v > d.own) d.own = v;
            }
        }
        for (const auto& kv : s.delta) put(kv.first, kv.second);
        if (s.own != 0) put(s.self, s.own);
        const size_t bsz = d.base ? d.base->size() : 0;
        if (d.delta.size() > FOLD_MIN && d.delta.size() * 32 > bsz) {
            const Base dl = base_of(d.delta);
            d.base = std::make_shared<const Base>(d.base ? base_merge(*d.base, dl) : dl);
            d.delta.clear();
        }
    }
    // second clock advanced by barriers/syncwarps ONLY (never by atomic release/
    // acquire): its races (hb_races_sync_only) tell the verdict matrix which dynamically
    // ordered pairs rest on schedule-independent barrier joins alone. It changes only
    // in sync_group, where every participant ends with the same joined clock plus its
    // own tick, so a sync group SHARES one immutable base and each thread keeps just
    // its own component: a barrier costs O(threads), not O(threads^2) like vc.
    struct SyncClock { BaseP base; uint64_t own = 0; };   // T5b: a flat base, like vc's
    std::unordered_map<Tid, SyncClock> vs;
    bool sync_only_pass = true;                             // YOSEMITE_HB_NO_SYNC_ONLY=1 disables
    // T12: clk is the chain clock Ch_loc, a join (has_clk false: bottom -- the chain broke and
    // no RMW has released since); block/scope label the last RMW on the location. Under the
    // trusting gate has_clk is always true and clk is the last RMW's post-acquire clock.
    struct Released { VClock clk; uint64_t block; int scope; VClock pd; bool has_clk = true; };
    // keyed by location, not raw address: shared-memory addresses are per-block
    // offsets, so with >1 block another block's release on the same offset would
    // clobber this block's and its next acquire would miss it (spurious atomic race).
    std::map<Loc, Released> released;                       // loc -> release record
    // Buckets (T9, I2; hb_proof.tex Algorithm 1): per location, per record key (kind,
    // strong scope; -1 = weak), per thread: the (vc epoch, vs epoch, pc) of that thread's
    // latest record on the location with that key. A replaced entry is PO-before its
    // replacement, which is what Theorem "Sound" needs; both clocks share the bucket
    // because both runs of Detect replace it at the same records.
    static constexpr uint8_t KIND_R = 0, KIND_W = 1, KIND_RMW = 2;
    struct Entry { uint64_t clock; uint64_t sclock; uint32_t pc; };
    struct KeyGroup { uint8_t kind; int scope; std::unordered_map<Tid, Entry> by_tid; };
    std::map<Loc, std::vector<KeyGroup>> buckets;           // loc -> its key groups

    // race kind labels (the report's orientation) and DR/SC class (Definition "Verdicts")
    static constexpr uint8_t RK_ATOMIC = 0, RK_WAW = 1, RK_RAW = 2, RK_WAR = 3;
    static constexpr const char* RACE_KIND[] = {"atomic", "WAW", "RAW", "WAR"};
    // hb_races is aggregated per (a_pc, b_pc, kind, class, space, thread distance, async
    // side): one example record (the first) and the number of conflicting record pairs
    // Check found. Without the FastTrack collapse the record pairs are O(threads^2) per
    // location (T9 re-score: 1.66e9 on P1); every consumer works on pc pairs, their class,
    // widest distance, warp and async side. hb_oracle.py aggregates identically.
    static constexpr const char* DIST_NAME[] = {"none", "warp", "block", "grid"};
    struct Race { uint64_t addr; int space; uint64_t loc_block;
                  Tid a_tid; long a_pc; Tid b_tid; uint32_t b_pc; uint8_t kind; bool sc;
                  uint8_t dist; uint8_t asy; uint64_t count; uint64_t a2; };   // a2: T14
    std::vector<Race> races;                                // one per key, first-report order
    struct RaceKey {
        long a_pc; uint32_t b_pc; uint8_t kind; bool sc; int space; uint8_t dist; uint8_t asy;
        bool operator==(const RaceKey& o) const {
            return a_pc == o.a_pc && b_pc == o.b_pc && kind == o.kind && sc == o.sc
                && space == o.space && dist == o.dist && asy == o.asy;
        }
    };
    struct RaceKeyHash {
        size_t operator()(const RaceKey& k) const {
            uint64_t h = static_cast<uint64_t>(k.a_pc) * 0x9e3779b97f4a7c15ULL;
            for (uint64_t v : {static_cast<uint64_t>(k.b_pc), static_cast<uint64_t>(k.kind),
                               static_cast<uint64_t>(k.sc), static_cast<uint64_t>(k.space),
                               static_cast<uint64_t>(k.dist), static_cast<uint64_t>(k.asy)})
                h = (h ^ v) * 0x100000001b3ULL;
            return static_cast<size_t>(h ^ (h >> 29));
        }
    };
    std::unordered_map<RaceKey, size_t, RaceKeyHash> race_index;   // key -> index in races
    // sync_dominance.thread_distance of two tids (async bit cleared)
    static uint8_t thread_distance(Tid a, Tid b) {
        if ((a >> 10) != (b >> 10)) return 3;
        return ((a >> 5) != (b >> 5)) ? 2 : 1;
    }
    // T4: per pair also the widest thread distance of its unordered conflicts and the
    // (earlier, later) pcs of the first one -- what sync_dominance.barrier_only_pairs hands
    // back through dist_out / order_out, so a dump without hb_events (hb_sync_pass) serves
    // the verdict layer as the offline pass does.
    struct SyncPair { uint64_t count = 0; uint8_t dist = 0; uint32_t first_pc = 0, second_pc = 0; };
    std::map<std::pair<uint32_t, uint32_t>, SyncPair> sync_pairs;  // (pc_lo, pc_hi) -> ...
    // T4 (design/no_dump.md section 4): vector_pass false = Detect(T, sync) alone, the instance
    // scalar-clock mode runs: the barrier/syncwarp/exit assembly, vs, the buckets' sclock, the
    // sync pairs, the TV monitor and the RMW points; no vc, released, gate, possible clock,
    // races or coherence profile, and emit writes none of their keys.
    bool vector_pass = true;
    // T4 (design/no_dump.md section 2, row 4): R3's release and acquire points from the trace,
    // as sync_dominance.trace_rmw_points computes them offline -- per lane thread the non-RMW
    // pcs since its last RMW and that RMW's pc; per non-RMW pc the PO-next RMW pcs of its
    // observed instances (stranded: some instance had none) and the PO-previous ones (orphan:
    // some instance had none). RMW-ness is the sidecar's rmw column, the predicate
    // (sd.atomic_scope) analyze() applies to the CFG. Keyed by the lane's own tid: a cp.async
    // copy counts as the issuing thread's access here, as offline.
    struct RmwThread { std::vector<uint32_t> pending; uint32_t last = 0; bool has_last = false; };
    std::unordered_map<Tid, RmwThread> rmw_thr;
    struct RmwPc { std::set<uint32_t> rel, acq; bool stranded = false, orphan = false; };
    std::map<uint32_t, RmwPc> rmw_pts;
    void rmw_note(Tid t0, uint32_t pc, bool is_rmw) {
        RmwThread& r = rmw_thr[t0];
        if (is_rmw) {
            for (uint32_t u : r.pending) rmw_pts[u].rel.insert(pc);
            r.pending.clear();
            r.last = pc;
            r.has_last = true;
        } else {
            if (std::find(r.pending.begin(), r.pending.end(), pc) == r.pending.end())
                r.pending.push_back(pc);
            RmwPc& p = rmw_pts[pc];
            if (r.has_last) p.acq.insert(r.last); else p.orphan = true;
        }
    }
    void rmw_finish() {       // kernel end: a pc still pending in some thread is stranded
        for (const auto& kv : rmw_thr)
            for (uint32_t u : kv.second.pending) rmw_pts[u].stranded = true;
    }

    // Block-barrier instance assembly (see the barrier branch in process): buffer
    // per-warp arrivals per (block, bar_index) until the instance is complete.
    // block_thread_count is the expected participant count for a plain __syncthreads
    // (whose per-record thread_count is 0); set per-kernel by hb_clock_reset.
    // T3b (hb_proof.tex Definition "Instances"): a whole-block segment expects
    // block_thread_count minus the block's exited threads; a counted one (bar.sync id, n)
    // keeps n. `count` is the segment's thread_count (0 = whole block), so an exit can
    // re-check the segment (procedure Complete).
    uint64_t block_thread_count = 0;
    struct Pending { std::set<Tid> arrived; uint64_t count = 0; };
    std::map<std::pair<uint64_t, uint32_t>, Pending> pending_barriers;
    std::unordered_map<uint64_t, uint64_t> exited_count;               // block -> exited threads
    std::map<std::pair<uint64_t, uint32_t>, uint32_t> exited_lanes;     // (block,warp) -> lane mask

    // --- Trace-validity (TV) invariants: 1:1 with hb_oracle. ON by default; set
    // YOSEMITE_HB_STRICT=0 to disable. A violation is a collector/trace bug: it prints
    // a loud banner and is recorded in `tv_violation` (surfaced in the JSON output) so
    // corpus/validation runs can assert zero. The oracle raises AlignmentError; the
    // HbClock cannot unwind the streaming process, so it records-and-continues instead
    // (equivalent on valid traces, where no violation ever fires).
    bool strict = true;
    std::string tv_violation;
    std::map<std::pair<uint64_t, uint32_t>, std::set<uint32_t>> bar_warps_seen;  // (block,bar_index)->warps ever arrived
    std::map<std::pair<uint64_t, uint32_t>, std::pair<uint64_t, uint32_t>> warp_waiting;  // (block,warp)->pending key

    // Coherence profile Pi (Phase 3, observational — never affects a verdict): per
    // address touched by >=1 atomic, the observed sequence of (tid, that thread's atomic
    // index) in event order. Same FNV-1a as hb_oracle.coherence_hash so the two profiles
    // cross-check. Only addresses with an atomic are kept.
    std::unordered_map<Tid, uint64_t> atom_idx;        // tid -> atomics issued so far
    std::map<uint64_t, std::vector<std::pair<Tid, uint64_t>>> coherence;  // addr -> order

    // YOSEMITE_HB_STATS_EVERY=<n> (T5a): also print the stats line after n, 2n, 4n, ...
    // processed records of a kernel, so a kernel killed before its end still leaves its
    // growth curve. Counted per record, not per buffer drain (one drain can hold a whole
    // kernel: 198,617 records for Indigo3 CC 1296n); doubling keeps the cost of walking
    // the state bounded. 0 = only at kernel end (YOSEMITE_HB_STATS).
    uint64_t stats_every = 0, processed = 0, next_snapshot = 0;
    void snapshot() {
        std::ostringstream o;
        stats(o);
        fprintf(stderr, "[HB_STATS] mid-kernel after %llu records: {%s} rss_kb %llu\n",
                static_cast<unsigned long long>(processed), o.str().c_str(),
                static_cast<unsigned long long>(self_rss_kb()));
        next_snapshot = 2 * processed;
    }

    // T1a (eval/CP_ASYNC_REPORT.md): a cp.async copy (LDGSTS, sidecar kind "async") is an
    // access by the issuing thread t's async agent agent_of(t), not by t. The agent's clock
    // joins t's at every issue (the copy follows t's earlier accesses); commit_group pushes
    // a snapshot of the agent's clocks onto t's group list and ticks the agent (later copies
    // get a newer epoch); wait_group N joins into t the snapshot of the newest group older
    // than the N most recent. So t's own accesses see a copy only after a wait covering its
    // group, and every other thread only through t (barriers, releases) after that wait.
    // Mirrored in hb_oracle.py and sync_dominance.barrier_only_pairs.
    static constexpr Tid ASYNC_BIT = Tid(1) << 62;
    static Tid agent_of(Tid t) { return t | ASYNC_BIT; }
    std::unordered_map<std::string, std::unordered_set<uint32_t>> kernel_async;
    std::unordered_set<uint32_t> merged_async, no_async;
    const std::unordered_set<uint32_t>* async_pcs = &merged_async;
    struct Group { VClock vc; Base vs; VClock pd; };        // an agent's clocks at a commit
    std::unordered_map<Tid, std::vector<Group>> groups;     // t -> committed groups, oldest first

    // the sync-only clock of u as one full clock (base + own component)
    Base vs_full(Tid u) {
        const SyncClock& c = vs[u];
        const Base me{{u, c.own}};
        return c.base ? base_merge(*c.base, me) : me;
    }
    void async_issue(Tid t, Tid ag) {
        if (vector_pass) {
            own(t);
            join_vc(V(ag), V(t));
            pd_join(ag, pd_of(t));                          // T14
            own(ag);
        }
        if (!sync_only_pass) return;
        owns(t);
        SyncClock& a = vs[ag];
        const Base ft = vs_full(t);
        a.base = std::make_shared<const Base>(a.base ? base_merge(*a.base, ft) : ft);
        owns(ag);
    }
    void async_commit(Tid t) {
        const Tid ag = agent_of(t);
        if (vector_pass) own(ag);
        if (sync_only_pass) owns(ag);
        groups[t].push_back(Group{vector_pass ? V(ag) : VClock{},
                                  sync_only_pass ? vs_full(ag) : Base(),
                                  vector_pass ? pd_of(ag) : VClock{}});
        if (vector_pass) V(ag).own += 1;
        if (sync_only_pass) vs[ag].own += 1;
    }
    void async_wait(Tid t, uint64_t n) {
        auto it = groups.find(t);
        if (it == groups.end() || it->second.size() <= n) return;
        const size_t done = it->second.size() - static_cast<size_t>(n);  // groups [0, done)
        const Group& g = it->second[done - 1];                           // snapshots only grow
        if (vector_pass) {
            own(t);
            join_vc(V(t), g.vc);
            pd_join(t, g.pd);                               // T14
        }
        if (sync_only_pass) {
            owns(t);
            SyncClock& c = vs[t];
            c.base = std::make_shared<const Base>(c.base ? base_merge(*c.base, g.vs) : g.vs);
        }
        it->second.erase(it->second.begin(), it->second.begin() + static_cast<long>(done));
    }

    // T3b: the expected participant count of an open segment (Definition "Instances"):
    // n for a counted barrier, else the block size minus the block's exited threads.
    uint64_t expected_of(const std::pair<uint64_t, uint32_t>& key, const Pending& p) const {
        if (p.count != 0) return p.count;
        const auto x = exited_count.find(key.first);
        const uint64_t gone = (x == exited_count.end()) ? 0 : x->second;
        return (block_thread_count > gone) ? block_thread_count - gone : 0;
    }
    // the instance of an open segment: join its participants and close the segment
    void fire(std::map<std::pair<uint64_t, uint32_t>, Pending>::iterator it) {
        std::vector<Tid> tids(it->second.arrived.begin(), it->second.arrived.end());
        if (strict)
            for (Tid t : tids)
                warp_waiting.erase({it->first.first, static_cast<uint32_t>((t >> 5) & 0x1f)});
        sync_group(tids);
        pending_barriers.erase(it);
    }
    // procedure Complete (hb_proof.tex Algorithm 1): called after every arrival on the key
    // and every exit in its block; -> true if the segment completed.
    bool complete(std::map<std::pair<uint64_t, uint32_t>, Pending>::iterator it) {
        const Pending& p = it->second;
        const uint64_t expected = expected_of(it->first, p);
        if (p.arrived.empty() || expected == 0 || p.arrived.size() < expected) return false;
        fire(it);
        return true;
    }
    // An exit record: the lanes of one warp that terminate. They leave the expected count
    // of every later whole-block segment of their block, and the block's open segments are
    // re-checked (the last non-arrived thread leaving is what the hardware waits for).
    void on_exit(const MemoryAccess& a) {
        uint32_t& gone = exited_lanes[{a.ctaId, a.warpId}];
        const uint32_t fresh = a.active_mask & ~gone;
        if (strict && (a.active_mask & gone))
            tv_fail("TV-record-after-exit: block " + std::to_string(a.ctaId) + " warp "
                    + std::to_string(a.warpId) + " lanes mask "
                    + std::to_string(a.active_mask & gone) + " exit twice");
        gone |= a.active_mask;
        exited_count[a.ctaId] += static_cast<uint64_t>(__builtin_popcount(fresh));
        auto it = pending_barriers.lower_bound({a.ctaId, 0});
        while (it != pending_barriers.end() && it->first.first == a.ctaId) {
            // W2: an exiting thread cannot be waiting at an open segment.
            if (strict)
                for (uint32_t m = fresh; m != 0; m &= (m - 1))
                    if (it->second.arrived.count(tid_of(a.ctaId, a.warpId,
                            static_cast<uint32_t>(__builtin_ctz(m))))) {
                        tv_fail("TV-barrier-completion-order: block " + std::to_string(a.ctaId)
                                + " warp " + std::to_string(a.warpId)
                                + " exits a thread still pending at barrier "
                                + std::to_string(it->first.second));
                        break;
                    }
            auto next = std::next(it);
            complete(it);   // erases `it` if it completes
            it = next;
        }
    }
    // TV-barrier-pending-at-end (hb_proof.tex section 1, the fifth monitor check, the runtime
    // form of A3): every open segment is complete at the end of the kernel. Independent of
    // YOSEMITE_HB_STRICT: pending_barriers is maintained regardless.
    void check_pending_at_end() {
        if (pending_barriers.empty()) return;
        const auto& kv = *pending_barriers.begin();
        tv_fail("TV-barrier-pending-at-end: " + std::to_string(pending_barriers.size())
                + " barrier segment(s) open at the end of the kernel; first: block "
                + std::to_string(kv.first.first) + ", bar " + std::to_string(kv.first.second)
                + ", arrived " + std::to_string(kv.second.arrived.size()) + " of expected "
                + std::to_string(expected_of(kv.first, kv.second)));
    }

    // --- T14 (design/a2_flag.md): the a2_uncertain flag, 1:1 with hb_oracle.py. The
    // "possible" clock poss[t] = vc[t] ⊔ pd[t]: pd follows vc through every recorded operation
    // and gets, in addition, a late acquire when an RMW's window [record, the thread's next
    // record) closes -- the join of its cluster (the RMWs on the location whose windows
    // chain-overlap), or of the multi cluster before it. No verdict reads it: it counts, per
    // aggregated record (DR or SC), the instances a window-consistent coherence order could
    // order.
    // T5b: in the main clock's representation, so a barrier's joined pd is one shared base
    std::unordered_map<Tid, VClock> pd;                     // tid -> delta (absent = empty)
    struct PendKey {                                        // a decision held on a window
        size_t race; Tid other; uint64_t ep; uint8_t side;
        bool operator==(const PendKey& o) const {
            return race == o.race && other == o.other && ep == o.ep && side == o.side;
        }
    };
    struct PendKeyHash {
        size_t operator()(const PendKey& k) const {
            uint64_t h = static_cast<uint64_t>(k.race) * 0x9e3779b97f4a7c15ULL;
            for (uint64_t v : {static_cast<uint64_t>(k.other), k.ep, static_cast<uint64_t>(k.side)})
                h = (h ^ v) * 0x100000001b3ULL;
            return static_cast<size_t>(h ^ (h >> 29));
        }
    };
    struct Held { size_t race; uint64_t count; int remaining; bool flagged; };  // on two windows
    // T12: a conflict of Check(r) held until acq(r) is known, and a reported one whose flag
    // decision waits for the gate (it depends on the pending join J through the possible clock)
    struct GHeld { Tid u; Entry e; uint32_t pc; uint8_t kind; bool sc; uint64_t addr; int space;
                   uint64_t loc_block; uint64_t te; };
    struct GDefer { size_t idx; Tid u; uint64_t ue; uint32_t upc; uint32_t pc; Loc loc; uint64_t te; };
    struct Win {                                            // a thread's open RMW window
        Loc loc; int scope = SCOPE_NONE; uint64_t ep = 0; uint64_t blk = 0;
        std::unordered_map<PendKey, uint64_t, PendKeyHash> pend;
        std::vector<std::tuple<std::shared_ptr<Held>, Tid, uint64_t>> held;
        // T12, the instance gate: this RMW's pc, rel(r), and the deferred acquire J (+ its
        // possible-clock part) with what Check(r) held on it
        bool g = false, g_rel = true, g_hasj = false; uint32_t g_pc = 0;
        VClock J, Jpd;
        std::vector<GHeld> gheld;
        std::vector<GDefer> gdefer;
    };
    std::unordered_map<Tid, Win> wins;
    std::unordered_map<uint64_t, uint32_t> win_lanes;       // (block << 5 | warp) -> lanes with one
    // An ms-connectivity component of a cluster's RMWs (plus what the cluster before handed
    // on): blocks of its grid- and block-scope members (g, b; ag, ab only the cluster's own,
    // which is what it hands on) and the join J of their contributions. A grid-scope member is
    // morally strong with every grid-scope one and the block-scope ones of its block; a
    // block-scope one with its block's; a none-scope one with nothing.
    struct Comp {
        std::set<uint64_t> g, b, ag, ab;
        VClock J;                                           // T5b: shares bases like vc
        bool links(int s, uint64_t blk) const {
            return s == SCOPE_GRID ? (!g.empty() || b.count(blk) != 0)
                                   : (g.count(blk) != 0 || b.count(blk) != 0);
        }
    };
    // a member of scope s in block blk joins the components it links (merging them) -> index
    size_t comp_add(std::vector<Comp>& cs, int s, uint64_t blk, bool actual) {
        std::vector<size_t> linked;
        for (size_t i = 0; i < cs.size(); ++i)
            if (cs[i].links(s, blk)) linked.push_back(i);
        if (linked.empty()) { cs.emplace_back(); linked.push_back(cs.size() - 1); }
        const size_t k = linked[0];
        for (size_t j = linked.size(); j-- > 1;) {          // merge, erasing from the back
            Comp& o = cs[linked[j]];
            cs[k].g.insert(o.g.begin(), o.g.end()); cs[k].b.insert(o.b.begin(), o.b.end());
            cs[k].ag.insert(o.ag.begin(), o.ag.end()); cs[k].ab.insert(o.ab.begin(), o.ab.end());
            join_vc(cs[k].J, o.J);
            cs.erase(cs.begin() + static_cast<long>(linked[j]));
        }
        (s == SCOPE_GRID ? cs[k].g : cs[k].b).insert(blk);
        if (actual) (s == SCOPE_GRID ? cs[k].ag : cs[k].ab).insert(blk);
        return k;
    }
    // the component of a member (unique: grid-scope members are all linked, and so are the
    // block-scope members of one block)
    static Comp* comp_of(std::vector<Comp>& cs, int s, uint64_t blk) {
        for (Comp& c : cs)
            if ((s == SCOPE_GRID ? c.g : c.b).count(blk) != 0) return &c;
        return nullptr;
    }
    struct Clu {                                            // a location's current RMW cluster
        uint32_t open = 0, members = 0;                     // open windows; RMWs (>= 2: multi)
        bool has_comps = false, has_inflow = false, need_prev = false, has_prev = false;
        std::vector<Comp> comps, inflow;                    // its components; the multi one's before
        Released prev;                                      // the single RMW before, if no inflow
    };
    std::map<Loc, Clu> clus;
    static const Clock& empty_clock() { static const Clock e; return e; }
    static const VClock& empty_vclock() { static const VClock e; return e; }
    static bool vc_empty(const VClock& c) { return !c.base && c.delta.empty() && c.own == 0; }
    const VClock& pd_of(Tid t) const {
        auto it = pd.find(t);
        return it == pd.end() ? empty_vclock() : it->second;
    }
    uint64_t poss(Tid t, Tid u) {
        auto it = pd.find(t);
        return std::max(V(t).get(u), it == pd.end() ? uint64_t(0) : it->second.get(u));
    }
    VClock& pd_ref(Tid t) {
        auto r = pd.try_emplace(t);
        if (r.second) r.first->second.self = t;
        return r.first->second;
    }
    void pd_drop_if_empty(Tid t) {
        auto it = pd.find(t);
        if (it != pd.end() && vc_empty(it->second)) pd.erase(it);
    }
    void pd_join(Tid t, const Clock& src) {                 // pd[t] ⊔= src, beyond what vc[t] knows
        if (src.empty()) return;
        const VClock& cur = V(t);
        VClock* d = nullptr;
        for (const auto& kv : src) {
            if (kv.second <= cur.get(kv.first)) continue;
            if (d == nullptr) d = &pd_ref(t);
            raise(*d, kv.first, kv.second);
        }
    }
    void pd_join(Tid t, const VClock& src) {
        if (vc_empty(src)) return;
        join_vc(pd_ref(t), src, &V(t));
        pd_drop_if_empty(t);
    }
    bool rmw_pc(uint32_t pc) const {
        const auto it = atom_scope->find(pc);
        return it != atom_scope->end() && it->second.rmw;
    }
    // An RMW of t (block blk) on loc opens its window: it joins loc's open cluster or starts
    // one. Components are built once the cluster is multi, or at once when the cluster before
    // it was (its inflow); two singletons in a row need none -- the recorded chain is exact.
    void a2_open(Tid t, const Loc& loc, int scope, uint64_t blk) {
        Clu& st = clus[loc];
        if (st.open == 0) {                                 // every earlier window closed: new
            st.members = 0; st.comps.clear(); st.has_comps = false;
            st.need_prev = !st.has_inflow; st.has_prev = false;
        }
        st.members += 1; st.open += 1;
        if (!st.has_comps && (st.has_inflow || st.members == 2)) {
            st.comps.clear();
            if (st.has_inflow) {                            // what the multi cluster before hands on
                for (const Comp& c : st.inflow) {
                    Comp v; v.g = c.ag; v.b = c.ab; v.J = c.J;
                    st.comps.push_back(std::move(v));
                }
            } else {
                if (st.has_prev && st.prev.scope != SCOPE_NONE) {   // the single RMW before
                    Comp& c = st.comps[comp_add(st.comps, st.prev.scope, st.prev.block, false)];
                    if (st.prev.has_clk) { join_vc(c.J, st.prev.clk); join_vc(c.J, st.prev.pd); }
                }
                const auto rit = released.find(loc);        // the first member, as published
                if (rit != released.end() && rit->second.scope != SCOPE_NONE) {
                    Comp& c = st.comps[comp_add(st.comps, rit->second.scope, rit->second.block, true)];
                    if (rit->second.has_clk) {              // (T12: bottom = nothing released)
                        join_vc(c.J, rit->second.clk); join_vc(c.J, rit->second.pd);
                    }
                }
            }
            st.has_comps = true;
        }
        if (st.has_comps && scope != SCOPE_NONE) comp_add(st.comps, scope, blk, true);
        Win& w = wins[t];
        w.loc = loc; w.scope = scope; w.ep = own(t); w.blk = blk; w.pend.clear(); w.held.clear();
        w.g = false; w.g_rel = true; w.g_hasj = false; w.g_pc = 0;           // T12
        w.J = VClock{}; w.Jpd = VClock{}; w.gheld.clear(); w.gdefer.clear();
        win_lanes[((t >> 10) << 5) | ((t >> 5) & 31)] |= 1u << (t & 31);
    }
    // t's next record (pc nxt - 1; nxt = 0: the end of the kernel) closes its window: under the
    // instance gate first acq(r) and the deferred acquire (T12), then the late acquire, then
    // the decisions held on the window.
    void a2_close(Tid t, uint32_t nxt) {
        auto wit = wins.find(t);
        bool acq = true, grel = true;
        if (wit->second.g) {
            Win& g = wit->second;
            grel = g.g_rel;
            acq = nxt == 0 || gate_listed(g.g_pc, nxt - 1, false);
            if (acq) {                                      // the deferred acquire
                if (g.g_hasj) { join_vc(V(t), g.J); pd_join(t, g.Jpd); }
            } else {                                        // no acquire: report what it held
                for (const GHeld& h : g.gheld)
                    g.gdefer.push_back(GDefer{report(h.addr, h.space, h.loc_block, h.u, h.e, t,
                                                     h.pc, h.kind, h.sc),
                                              h.u, h.e.clock, h.e.pc, h.pc,
                                              Loc{h.space, h.space == 1 ? h.loc_block : 0, h.addr},
                                              h.te});
            }
            std::vector<GDefer> defer = std::move(g.gdefer);
            g.gheld.clear();
            for (const GDefer& d : defer)
                a2_decide(d.idx, d.u, d.ue, d.upc, t, d.pc, t, d.loc, d.te);
            wit = wins.find(t);
        }
        Win w = std::move(wit->second);
        wins.erase(wit);
        const auto lit = win_lanes.find(((t >> 10) << 5) | ((t >> 5) & 31));
        if (lit != win_lanes.end() && (lit->second &= ~(1u << (t & 31))) == 0) win_lanes.erase(lit);
        Clu& st = clus[w.loc];
        if (st.has_comps && w.scope != SCOPE_NONE && acq) {
            const Comp* c = comp_of(st.comps, w.scope, w.blk);
            if (c != nullptr && !vc_empty(c->J)) {
                pd_join(t, c->J);
                Released& rr = released[w.loc];
                if (st.members == 1 && grel && rr.has_clk) join_vc(rr.pd, c->J);   // hands on
            }
        }
        for (const auto& kv : w.pend)
            if (kv.first.ep <= poss(t, kv.first.other)) races[kv.first.race].a2 += kv.second;
        for (const auto& h : w.held) {                      // flagged if either window orders it
            Held& x = *std::get<0>(h);
            x.flagged = x.flagged || std::get<2>(h) <= poss(t, std::get<1>(h));
            if (--x.remaining == 0 && x.flagged) races[x.race].a2 += x.count;
        }
        if (--st.open == 0) {                               // complete; a multi one hands on
            st.inflow.clear(); st.has_inflow = false;       // its members' components
            if (st.has_comps && st.members >= 2) {
                for (Comp& c : st.comps)
                    if (!c.ag.empty() || !c.ab.empty()) st.inflow.push_back(std::move(c));
                st.has_inflow = true;
            }
            st.comps.clear(); st.has_comps = false; st.has_prev = false; st.prev = Released{};
            st.members = 0;
        }
    }
    void a2_close_lanes(uint64_t block, uint32_t warp, uint32_t mask, uint32_t pc) {
        const auto it = win_lanes.find((block << 5) | warp);
        if (it == win_lanes.end()) return;
        for (uint32_t m = it->second & mask; m != 0; m &= (m - 1))
            a2_close(tid_of(block, warp, static_cast<uint32_t>(__builtin_ctz(m))), pc + 1);
    }
    void a2_close_all() {                                   // order-independent
        std::vector<Tid> ts;
        for (const auto& kv : wins) ts.push_back(kv.first);
        std::sort(ts.begin(), ts.end());
        for (Tid t : ts) a2_close(t, 0);                    // T12: no next record, acq = 1
    }
    // T12: is pc listed on RMW r's rel (release) or acq line; an RMW the table does not name is
    // one whose scope names none (never ms: the gate is moot) -- 1 -- unless its scope is known
    bool gate_listed(uint32_t r, uint32_t pc, bool rel) const {
        const auto it = gate->find(r);
        if (it == gate->end()) {
            const auto pit = atom_scope->find(r);
            return pit == atom_scope->end() || pit->second.scope <= SCOPE_NONE;
        }
        const auto& set = rel ? it->second.rel : it->second.acq;
        return set.count(pc) != 0;
    }
    void note_pc(uint64_t block, uint32_t warp, uint32_t mask, uint32_t pc) {
        if (gate == nullptr) return;
        auto& a = last_pc[(block << 5) | warp];
        for (uint32_t m = mask; m != 0; m &= (m - 1)) a[__builtin_ctz(m)] = pc + 1;
    }
    // One reported instance (u's record at epoch ue, then t's): flagged now if the possible clock
    // orders it; else held on an RMW endpoint's open window -- t's RMW, whose window just
    // opened, or u's RMW, whose window has not closed -- and decided when it closes.
    void a2_decide(size_t idx, Tid u, uint64_t ue, uint32_t upc, Tid t, uint32_t pc, Tid obs,
                   const Loc& loc, uint64_t te_at = UINT64_MAX) {
        const uint64_t te = te_at != UINT64_MAX ? te_at : V(t).own;
        if (ue <= poss(obs, u)) { races[idx].a2 += 1; return; }
        Win* w1 = nullptr;
        Win* w2 = nullptr;
        if (rmw_pc(pc)) {
            const auto i = wins.find(t);
            if (i != wins.end()) w1 = &i->second;
        }
        if (rmw_pc(upc)) {
            const auto i = wins.find(u);
            if (i != wins.end() && i->second.ep == ue && i->second.loc == loc) w2 = &i->second;
        }
        if (w1 != nullptr && w2 != nullptr) {
            auto h = std::make_shared<Held>(Held{idx, 1, 2, false});
            w1->held.emplace_back(h, u, ue);
            w2->held.emplace_back(h, t, te);
        } else if (w1 != nullptr) {
            w1->pend[PendKey{idx, u, ue, 1}] += 1;
        } else if (w2 != nullptr) {
            w2->pend[PendKey{idx, t, te, 2}] += 1;
        }
    }

    void reset() {
        pd.clear(); wins.clear(); win_lanes.clear(); clus.clear();   // T14
        last_pc.clear();                                            // T12
        vc.clear(); vs.clear(); released.clear(); buckets.clear(); merge_memo.clear();
        races.clear(); race_index.clear(); sync_pairs.clear();
        rmw_thr.clear(); rmw_pts.clear();                           // T4
        pending_barriers.clear();  // block_thread_count is (re)set by hb_clock_reset
        exited_count.clear(); exited_lanes.clear();
        bar_warps_seen.clear(); warp_waiting.clear(); tv_violation.clear();
        atom_idx.clear(); coherence.clear();
        groups.clear();
        processed = 0; next_snapshot = stats_every;
    }

    // Stable 64-bit FNV-1a of a (tid, atomic-index) sequence; byte-for-byte identical to
    // hb_oracle.coherence_hash (tid as 4 bytes LE, idx as 8 bytes LE, per pair).
    static uint64_t coherence_hash(const std::vector<std::pair<Tid, uint64_t>>& seq) {
        uint64_t h = 0xcbf29ce484222325ULL;
        for (const auto& p : seq) {
            for (int s = 0; s < 32; s += 8) { h ^= (p.first >> s) & 0xFF; h *= 0x100000001b3ULL; }
            for (int s = 0; s < 64; s += 8) { h ^= (p.second >> s) & 0xFF; h *= 0x100000001b3ULL; }
        }
        return h;
    }

    void tv_fail(const std::string& msg) {
        std::cerr << "\n[HB_CLOCK] *** TRACE-VALIDITY VIOLATION *** " << msg
                  << "\n  (the single-trace certificate assumes this cannot happen; "
                     "verdict for this kernel is untrustworthy)\n" << std::endl;
        if (tv_violation.empty()) tv_violation = msg;  // keep the first
    }

    static Tid tid_of(uint64_t block, uint32_t warp, uint32_t lane) {
        return (block << 10) | (static_cast<Tid>(warp) << 5) | lane;
    }
    static uint64_t clk_get(const Clock& c, Tid t) {
        auto it = c.find(t); return it == c.end() ? 0 : it->second;
    }
    // a thread's own clock starts at 1: an unsynced peer knows it only as 0, so a
    // write (t@>=1) vs 0 is caught as a race.
    uint64_t own(Tid t) {
        uint64_t& v = V(t).own;
        if (v == 0) v = 1;
        return v;
    }
    static void join_into(Clock& dst, const Clock& src) {
        for (const auto& kv : src) { uint64_t& d = dst[kv.first]; if (kv.second > d) d = kv.second; }
    }
    // barrier/syncwarp: everyone joins everyone's pre-sync clock, then each ticks
    // its own component (post-sync accesses ordered after the join, concurrent with
    // each other).
    // Applied to both clocks; it is the ONLY thing that advances vs.
    // T5b: the join of a group's clocks as one base: each distinct input base once, plus the
    // loose entries (deltas, own components)
    // (largest first, pairwise linear merges; a base the running join covers costs one scan)
    static BaseP join_group(std::vector<BaseP> bs, std::vector<std::pair<Tid, uint64_t>> loose) {
        Base acc = base_sorted(std::move(loose));
        std::sort(bs.begin(), bs.end(), [](const BaseP& x, const BaseP& y) { return x->size() > y->size(); });
        for (const BaseP& b : bs) {
            if (acc.empty()) { acc = *b; continue; }
            bool ga = false;
            Base m = base_merge(acc, *b, &ga);
            if (!ga) acc = std::move(m);
        }
        return std::make_shared<const Base>(std::move(acc));
    }
    void sync_group(const std::vector<Tid>& tids) {
        std::unordered_set<const Base*> seen;
        if (vector_pass) sync_group_vc(tids, seen);         // T4: the sync instance skips vc
        if (!sync_only_pass) return;
        for (Tid t : tids) owns(t);
        std::vector<BaseP> sbs;                             // each shared base once
        std::vector<std::pair<Tid, uint64_t>> sloose;
        sloose.reserve(tids.size());
        seen.clear();
        for (Tid t : tids) {
            const SyncClock& c = vs[t];
            if (c.base && seen.insert(c.base.get()).second) sbs.push_back(c.base);
            sloose.emplace_back(t, c.own);
        }
        const BaseP js = join_group(sbs, std::move(sloose));
        for (Tid t : tids) { SyncClock& c = vs[t]; c.own = base_get(*js, t) + 1; c.base = js; }
    }
    // the main clock's (and the possible clock's) part of a sync group
    void sync_group_vc(const std::vector<Tid>& tids, std::unordered_set<const Base*>& seen) {
        std::vector<BaseP> pbs;                             // T14: the possible deltas join too
        std::vector<std::pair<Tid, uint64_t>> ploose;       // (T5b: into one shared base)
        bool any_pd = false;
        if (!pd.empty()) {
            for (Tid t : tids) {
                const auto it = pd.find(t);
                if (it == pd.end()) continue;
                const VClock& c = it->second;
                any_pd = true;
                if (c.base && seen.insert(c.base.get()).second) pbs.push_back(c.base);
                ploose.insert(ploose.end(), c.delta.begin(), c.delta.end());
                if (c.own != 0) ploose.emplace_back(c.self, c.own);
                pd.erase(it);
            }
        }
        for (Tid t : tids) own(t);
        if (!tids.empty()) {
            // T5b: one base for the group; each participant keeps it plus its tick -- the
            // values of `nv = j; nv[t] += 1`
            std::vector<VClock*> cs;
            cs.reserve(tids.size());
            for (Tid t : tids) cs.push_back(&V(t));
            std::vector<BaseP> bs;
            std::vector<std::pair<Tid, uint64_t>> loose;
            loose.reserve(cs.size());
            seen.clear();
            for (const VClock* c : cs) {
                if (c->base && seen.insert(c->base.get()).second) bs.push_back(c->base);
                loose.insert(loose.end(), c->delta.begin(), c->delta.end());
                loose.emplace_back(c->self, c->own);
            }
            const BaseP j = join_group(bs, std::move(loose));
            for (VClock* c : cs) { c->own = base_get(*j, c->self) + 1; c->delta.clear(); c->base = j; }
        }
        if (any_pd) {                                       // each participant shares it; what
            const BaseP pb = join_group(pbs, std::move(ploose));   // vc now covers is kept,
            if (!pb->empty())                                   // which no poss() can tell
                for (Tid t : tids) {
                    VClock& d = pd_ref(t);
                    d.base = pb;
                    d.own = base_get(*pb, t);
                }
        }
    }
    uint64_t owns(Tid t) {
        uint64_t& v = vs[t].own;
        if (v == 0) v = 1;
        return v;
    }
    // what thread t knows of thread u on the sync-only clock
    uint64_t vs_get(Tid t, Tid u) {
        const SyncClock& c = vs[t];
        if (u == t) return c.own;
        return c.base ? base_get(*c.base, u) : 0;
    }
    // ms of two records from their strong scopes (-1 = weak) and their threads' blocks:
    // both strong and each scope covers the other thread (sync_dominance.morally_strong)
    static bool morally_strong(int s1, uint64_t b1, int s2, uint64_t b2) {
        if (s1 < 0 || s2 < 0) return false;
        const int eff = std::min(s1, s2);
        return eff == SCOPE_GRID || (eff == SCOPE_BLOCK && b1 == b2);
    }
    static uint64_t block_of(Tid t) { return (t & ~ASYNC_BIT) >> 10; }
    // one unordered-ness test per clock for a conflicting (prev, current) pair
    // the pair as seen by `obs`: t itself, or for two copies of one agent the issuing
    // thread (the agent always knows its own copies; the thread only those a wait completed)
    // gw (T12): t's RMW window with a pending acquire J -- a conflict J would order is held
    // there (reported iff acq(r) = 0); the flag decision of any other waits for the gate.
    void conflict(uint64_t addr, int space, uint64_t loc_block, Tid p_tid, const Entry& p,
                  Tid t, uint32_t pc, uint8_t kind, bool sc, Tid obs, Win* gw = nullptr) {
        if (vector_pass && p.clock > V(obs).get(p_tid)) {
            const uint64_t te = V(t).own;
            const Loc loc{space, space == 1 ? loc_block : 0, addr};
            if (gw != nullptr && p.clock <= gw->J.get(p_tid)) {
                gw->gheld.push_back(GHeld{p_tid, p, pc, kind, sc, addr, space, loc_block, te});
            } else {
                const size_t idx = report(addr, space, loc_block, p_tid, p, t, pc, kind, sc);
                if (gw != nullptr) gw->gdefer.push_back(GDefer{idx, p_tid, p.clock, p.pc, pc, loc, te});
                else a2_decide(idx, p_tid, p.clock, p.pc, t, pc, obs, loc);   // T14: DR and SC
            }
        }
        if (sync_only_pass && p.sclock > vs_get(obs, p_tid)) {
            SyncPair& sp = sync_pairs[{std::min(p.pc, pc), std::max(p.pc, pc)}];
            if (sp.count == 0) { sp.first_pc = p.pc; sp.second_pc = pc; }   // T4: first conflict
            sp.count += 1;
            sp.dist = std::max(sp.dist, thread_distance(p_tid & ~ASYNC_BIT, t & ~ASYNC_BIT));
        }
    }
    // count one reportable record pair in its aggregate -> the aggregate's index
    size_t report(uint64_t addr, int space, uint64_t loc_block, Tid p_tid, const Entry& p,
                  Tid t, uint32_t pc, uint8_t kind, bool sc) {
        {
            const Tid a0 = p_tid & ~ASYNC_BIT, b0 = t & ~ASYNC_BIT;
            const uint8_t asy = static_cast<uint8_t>(((p_tid & ASYNC_BIT) ? 1 : 0)
                                                   | ((t & ASYNC_BIT) ? 2 : 0));
            const uint8_t dist = thread_distance(a0, b0);
            const RaceKey k{static_cast<long>(p.pc), pc, kind, sc, space, dist, asy};
            auto it = race_index.find(k);
            size_t idx;
            if (it == race_index.end()) {
                idx = races.size();
                race_index.emplace(k, idx);
                races.push_back(Race{addr, space, loc_block, a0, static_cast<long>(p.pc),
                                     b0, pc, kind, sc, dist, asy, 1, 0});
            } else {
                idx = it->second;
                races[idx].count += 1;
            }
            return idx;
        }
    }
    // Procedure Check: every other thread's buckets on loc that conflict with this record
    // (one of the two a write). Morally strong pairs are SC unless both are RMWs, which are
    // never reportable (a whole key group is skipped when its scope makes that certain).
    void check(uint64_t addr, int space, uint64_t loc_block, const Loc& loc, Tid t,
               uint8_t kind, int scope, uint32_t pc, Win* gw = nullptr) {
        auto bit = buckets.find(loc);
        if (bit == buckets.end()) return;
        const uint64_t tb = block_of(t);
        for (const KeyGroup& g : bit->second) {
            if (kind == KIND_R && g.kind == KIND_R) continue;
            const bool both_rmw = kind == KIND_RMW && g.kind == KIND_RMW;
            if (both_rmw && g.scope >= 0 && scope >= 0 && std::min(g.scope, scope) == SCOPE_GRID)
                continue;
            const uint8_t label = g.kind == KIND_R ? RK_WAR : kind == KIND_RMW ? RK_ATOMIC
                                : kind == KIND_W ? RK_WAW : RK_RAW;
            for (const auto& kv : g.by_tid) {
                if (kv.first == t) continue;
                const bool strong = morally_strong(g.scope, block_of(kv.first), scope, tb);
                if (strong && both_rmw) continue;
                conflict(addr, space, loc_block, kv.first, kv.second, t, pc, label, strong, t, gw);
            }
        }
    }
    KeyGroup& group_of(const Loc& loc, uint8_t kind, int scope) {
        std::vector<KeyGroup>& gs = buckets[loc];
        for (KeyGroup& g : gs)
            if (g.kind == kind && g.scope == scope) return g;
        gs.push_back(KeyGroup{kind, scope, {}});
        return gs.back();
    }

    static std::string norm_name(const std::string& n) {
        std::string o;
        for (char c : n) if (!std::isspace(static_cast<unsigned char>(c))) o += c;
        return o;
    }
    // sidecar lines: `<pc> <scope> <kind> <kernel>` (kind rmw|ldst, kernel = demangled
    // name without whitespace), `# kernel <kernel>` declaring a kernel (so one without
    // coherent pcs gets an empty table, not the merged one), or the legacy
    // `<pc> <scope>` (rmw, all kernels merged); `# async` (T1a) and `# strength` (T10) lines
    // as parsed below.
    void load_scopes(const char* path) {
        kernel_tables.clear(); merged.clear(); atom_scope = &merged;
        kernel_async.clear(); merged_async.clear(); async_pcs = &merged_async;
        kernel_strength.clear(); merged_strength.clear(); strength = &merged_strength;
        has_strength = false;
        kernel_gates.clear(); gate = nullptr;                       // T12
        const char* ge = std::getenv("YOSEMITE_HB_GATE");
        gate_env_trusting = ge != nullptr && std::string(ge) == "trusting";
        if (path == nullptr) return;
        std::ifstream f(path);
        if (!f) return;
        std::string line;
        while (std::getline(f, line)) {
            std::istringstream ls(line);
            uint32_t pc = 0; int scope = 0; std::string kind, kernel;
            if (line.rfind("# kernel ", 0) == 0) {
                kernel_tables[norm_name(line.substr(9))];
                continue;
            }
            if (line.rfind("# gate-kernel ", 0) == 0) {   // T12: the kernel has a gate table
                kernel_gates[norm_name(line.substr(14))];
                continue;
            }
            if (line.rfind("# gate ", 0) == 0) {   // T12: `# gate <rmw pc> rel|acq <kernel> <pc>...`
                std::istringstream gs(line.substr(7));
                std::string side;
                if (gs >> pc >> side >> kernel) {
                    GateSets& g = kernel_gates[kernel][pc];
                    auto& set = (side == "rel") ? g.rel : g.acq;
                    uint32_t q = 0;
                    while (gs >> q) set.insert(q);
                }
                continue;
            }
            if (line.rfind("# async ", 0) == 0) {   // T1a: `# async <pc> <kernel>` (LDGSTS)
                std::istringstream as(line.substr(8));
                if (as >> pc) {
                    as >> kernel;
                    if (!kernel.empty()) kernel_async[kernel].insert(pc);
                    merged_async.insert(pc);
                }
                continue;
            }
            if (line.rfind("# strength ", 0) == 0) {   // T10: `# strength <pc> <str> <scope|-> <kernel>`
                std::istringstream ss(line.substr(11));
                std::string str, sc;
                if (ss >> pc >> str >> sc) {
                    ss >> kernel;
                    int s = -1;
                    if (str == "strong") {
                        char* end = nullptr;
                        const long v = std::strtol(sc.c_str(), &end, 10);
                        if (end == sc.c_str() || *end != '\0') continue;   // malformed: skip
                        s = static_cast<int>(v);
                    }
                    if (!kernel.empty()) kernel_strength[kernel][pc] = s;
                    // the merged fallback lists a pc strong if some kernel has it strong (the
                    // first such, in file order), as the merged coherent-pc table does
                    auto mit = merged_strength.emplace(pc, s).first;
                    if (mit->second < 0 && s >= 0) mit->second = s;
                    has_strength = true;
                }
                continue;
            }
            if (!(ls >> pc >> scope)) continue;
            ls >> kind >> kernel;
            const PcInfo info{scope, kind != "ldst"};
            if (!kernel.empty()) kernel_tables[kernel][pc] = info;
            merged.emplace(pc, info);
        }
    }
    void select_kernel(const std::string& kernel_name) {
        auto it = kernel_tables.find(norm_name(kernel_name));
        atom_scope = (it != kernel_tables.end()) ? &it->second : &merged;
        auto ait = kernel_async.find(norm_name(kernel_name));
        async_pcs = (ait != kernel_async.end()) ? &ait->second
                  : (it != kernel_tables.end()) ? &no_async : &merged_async;
        const auto git = kernel_gates.find(norm_name(kernel_name));   // T12
        gate = (vector_pass && !gate_env_trusting && git != kernel_gates.end())   // T4: vc only
             ? &git->second : nullptr;
        auto sit = kernel_strength.find(norm_name(kernel_name));   // T10
        strength = (sit != kernel_strength.end()) ? &sit->second
                 : (it != kernel_tables.end()) ? &no_strength : &merged_strength;
        if (it == kernel_tables.end() && !kernel_tables.empty())
            std::cerr << "[HB_CLOCK] kernel '" << kernel_name << "' not in the atomic-scope "
                         "sidecar; using the merged pc table" << std::endl;
    }
    // T10: a record's strong scope (-1 = weak), the scope of key(e) and ms. An RMW keeps its
    // coherent-pc line's scope (the RMW column); a load/store takes the strength column when
    // the sidecar has one, else its `ldst` line as before. Both columns come from one table
    // (atomic_scope_sidecar.py), so a T10 sidecar gives the same answer either way.
    int strong_scope(uint32_t pc, PcTable::const_iterator pit) const {
        const bool listed = pit != atom_scope->end();
        if (!has_strength || (listed && pit->second.rmw)) return listed ? pit->second.scope : -1;
        const auto sit = strength->find(pc);
        return (sit != strength->end()) ? sit->second : -1;
    }

    // order (T15): the drain's record order when the late key is on, else buffer order.
    void process(const MemoryAccess* buf, uint64_t size, const uint32_t* order = nullptr) {
        for (uint64_t i = 0; i < size; ++i) {
            if (stats_every && ++processed >= next_snapshot) snapshot();   // T5a
            const MemoryAccess& a = buf[order ? order[i] : i];
            if (a.type == MemoryType::BlockExit) {   // T3b: the exiting lanes of one warp
                if (!wins.empty())                   // T14; T12: the exit's pc is q
                    a2_close_lanes(a.ctaId, a.warpId, a.active_mask,
                                   static_cast<uint32_t>(a.pc & 0x00FFFFFFu));
                on_exit(a);
                continue;
            }
            // I5 (D14): local memory is outside the HB model (hb_proof.tex Definition
            // "Records"); skipped before the monitor, as the oracle skips an older dump's
            // local records (the HB trace no longer carries them, hb_collect_events).
            if (a.type == MemoryType::Local) continue;
            const uint32_t pc = static_cast<uint32_t>(a.pc & 0x00FFFFFFu);
            // TV-record-after-exit (W3): no record of a thread follows its exit.
            if (strict && !exited_lanes.empty()) {
                const auto xit = exited_lanes.find({a.ctaId, a.warpId});
                const uint32_t lanes = (a.type == MemoryType::Syncwarp) ? a.accessSize
                                                                        : a.active_mask;
                if (xit != exited_lanes.end() && (xit->second & lanes))
                    tv_fail("TV-record-after-exit: block " + std::to_string(a.ctaId)
                            + " warp " + std::to_string(a.warpId) + " lanes mask "
                            + std::to_string(xit->second & lanes) + " issue a record at pc "
                            + std::to_string(pc) + " after their exit");
            }
            if (a.type != MemoryType::Global && a.type != MemoryType::Shared) {
                const uint32_t sm = a.type == MemoryType::Syncwarp ? a.accessSize : a.active_mask;
                if (!wins.empty())   // T14: a sync record is its lanes' next record
                    a2_close_lanes(a.ctaId, a.warpId, sm, pc);
                note_pc(a.ctaId, a.warpId, sm, pc);                  // T12
            }
            if (a.type == MemoryType::PipelineCommit || a.type == MemoryType::PipelineWait) {
                for (uint32_t m = a.active_mask; m != 0; m &= (m - 1)) {   // T1a
                    const Tid t = tid_of(a.ctaId, a.warpId, static_cast<uint32_t>(__builtin_ctz(m)));
                    if (a.type == MemoryType::PipelineCommit) async_commit(t);
                    else async_wait(t, a.accessSize);
                }
                continue;
            }

            if (a.type == MemoryType::Syncwarp) {
                // syncwarp is genuinely per-warp: join THIS warp's masked lanes now
                // (sync_mask carried in accessSize).
                std::vector<Tid> tids;
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
                // T3b: a plain __syncthreads expects the block's NON-EXITED threads.
                const std::pair<uint64_t, uint32_t> key{a.ctaId, a.flags};
                Pending& p = pending_barriers[key];
                p.count = a.accessSize;
                for (uint32_t m = a.active_mask; m != 0; m &= (m - 1))
                    p.arrived.insert(tid_of(a.ctaId, a.warpId, static_cast<uint32_t>(__builtin_ctz(m))));
                if (strict) bar_warps_seen[key].insert(a.warpId);
                const uint64_t expected = expected_of(key, p);
                // TV-barrier-overfill: arrivals must never EXCEED the expected count.
                if (strict && expected != 0 && p.arrived.size() > expected)
                    tv_fail("TV-barrier-overfill: barrier (block " + std::to_string(a.ctaId)
                            + ", bar " + std::to_string(a.flags) + ") arrived "
                            + std::to_string(p.arrived.size()) + " > expected "
                            + std::to_string(expected));
                // fire once complete; expected==0 (unknown count, unreachable for a
                // launched kernel) degrades to per-warp so HbClock never stalls.
                if (expected == 0) {
                    // TV-expected-nonzero-multiwarp: the per-warp fallback with an unknown
                    // count is exactly the pre-fix bug for a >1-warp block.
                    if (strict && bar_warps_seen[key].size() > 1)
                        tv_fail("TV-expected-nonzero-multiwarp: barrier (block "
                                + std::to_string(a.ctaId) + ", bar " + std::to_string(a.flags)
                                + ") has " + std::to_string(bar_warps_seen[key].size())
                                + " warps but expected count is unknown (block_thread_count "
                                  "missing) -> per-warp degrade unsound");
                    fire(pending_barriers.find(key));
                } else if (!complete(pending_barriers.find(key)) && strict) {
                    // instance still pending: this warp is now blocked at the barrier.
                    warp_waiting[{a.ctaId, a.warpId}] = key;
                }
                continue;
            }

            const auto pit = atom_scope->find(pc);
            const bool is_atomic = pit != atom_scope->end() && pit->second.rmw;
            const int my_coh = strong_scope(pc, pit);          // T10: the strength column
            const bool is_write = (a.flags & SANITIZER_MEMORY_DEVICE_FLAG_WRITE) != 0;
            const bool is_async = async_pcs->count(pc) != 0;   // T1a: the agent's access
            const int space = (a.type == MemoryType::Shared) ? 1 : 0;
            const uint8_t kind = is_atomic ? KIND_RMW : is_write ? KIND_W : KIND_R;

            // TV-barrier-completion-order: a warp blocked at a pending barrier cannot
            // execute a post-barrier memory access before its instance fires. This is the
            // segmentation property block-barrier assembly relies on. (TV-seq-monotonic is
            // structural here: HbClock consumes the trace buffer in native order, so the
            // event sequence is monotonic by construction — the oracle checks it because it
            // reads an external JSON that could be reordered.)
            if (strict && warp_waiting.count({a.ctaId, a.warpId}))
                tv_fail("TV-barrier-completion-order: block " + std::to_string(a.ctaId)
                        + " warp " + std::to_string(a.warpId)
                        + " issues a post-barrier access at pc " + std::to_string(pc)
                        + " while still pending at a barrier");

            for (uint32_t lm = a.active_mask; lm != 0; lm &= (lm - 1)) {
                const uint32_t lane = static_cast<uint32_t>(__builtin_ctz(lm));
                if (!wins.empty()) a2_close_lanes(a.ctaId, a.warpId, 1u << lane, pc);   // T14
                const Tid t0 = tid_of(a.ctaId, a.warpId, lane);
                rmw_note(t0, pc, is_atomic);                        // T4: R3's trace points
                uint32_t prev = 0;                                  // T12: t0's previous record
                if (gate != nullptr) {
                    uint32_t& lp = last_pc[(a.ctaId << 5) | a.warpId][lane];
                    prev = lp;
                    lp = pc + 1;
                }
                const Tid t = is_async ? agent_of(t0) : t0;
                if (is_async) async_issue(t0, t);
                const uint64_t addr = a.addresses[lane];
                const uint64_t loc_block = (space == 1) ? a.ctaId : 0;  // shared is per-block
                const Loc loc{space, loc_block, addr};

                bool chain_ok = false;                              // T12
                Win* gw = nullptr;
                if (is_atomic && vector_pass) {                     // T4: no chain in the sync instance
                    // Coherence profile Pi (observational): append this thread's next
                    // atomic index to the address's observed atomic order.
                    coherence[addr].push_back({t, atom_idx[t]});
                    atom_idx[t] += 1;
                    a2_open(t, loc, pit->second.scope, a.ctaId);    // T14
                    // scoped acquire: the chain continues only if the min of the two atomics'
                    // .STRONG scopes covers both threads. Trusting gate: join now. Instance
                    // gate (T12): rel(r) from t's previous record now; the acquire J is held in
                    // r's window until t's next record decides acq(r).
                    auto rit = released.find(loc);
                    if (rit != released.end()) {
                        const int eff = std::min(pit->second.scope, rit->second.scope);
                        chain_ok = eff == SCOPE_GRID || (eff == SCOPE_BLOCK && rit->second.block == a.ctaId);
                        if (chain_ok && gate == nullptr) {
                            join_vc(V(t), rit->second.clk);
                            pd_join(t, rit->second.pd);             // T14
                        }
                    }
                    if (gate != nullptr) {
                        Win& w = wins[t];
                        w.g = true;
                        w.g_pc = pc;
                        w.g_rel = prev == 0 || gate_listed(pc, prev - 1, true);
                        w.g_hasj = chain_ok && rit->second.has_clk;
                        if (w.g_hasj) { w.J = rit->second.clk; w.Jpd = rit->second.pd; }
                        if (w.g_hasj) gw = &w;
                    }
                }
                const uint64_t clk = vector_pass ? own(t) : 0;
                const uint64_t sclk = sync_only_pass ? owns(t) : 0;
                check(addr, space, a.ctaId, loc, t, kind, my_coh, pc, gw);
                KeyGroup& g = group_of(loc, kind, my_coh);
                if (kind == KIND_W && is_async) {
                    // two copies of one thread: PTX orders no two cp.async operations, so
                    // they are unordered until a wait completes the first
                    auto mit = g.by_tid.find(t);
                    if (mit != g.by_tid.end())
                        conflict(addr, space, a.ctaId, t, mit->second, t, pc, RK_WAW, false, t0);
                }
                g.by_tid[t] = Entry{clk, sclk, pc};
                if (is_atomic && vector_pass) {
                    // I1 (D1): publish the pre-tick clock -- the RMW's own epoch is clk, so a
                    // later acquirer is ordered after the RMW, not after t's next accesses --
                    // then tick. Overwriting equals Algorithm 1's join under the trusting gate.
                    Clu& st = clus[loc];                            // T14
                    const auto rit2 = released.find(loc);
                    Released nr{V(t), a.ctaId, pit->second.scope, pd_of(t)};
                    if (gate != nullptr) {
                        // T12: Ch_loc is a join; it breaks when r is not ms with the last RMW;
                        // only a releasing r publishes; the label is always r's
                        nr.clk = VClock{}; nr.pd = VClock{}; nr.has_clk = false;
                        if (chain_ok && rit2->second.has_clk) {
                            nr.clk = rit2->second.clk; nr.pd = rit2->second.pd; nr.has_clk = true;
                        }
                        if (wins[t].g_rel) {
                            if (!nr.has_clk) { nr.clk = V(t); nr.pd = pd_of(t); }
                            else { join_vc(nr.clk, V(t)); join_vc(nr.pd, pd_of(t)); }
                            nr.has_clk = true;
                        }
                    }
                    const bool contributes = gate == nullptr || wins[t].g_rel;
                    if (st.has_comps && pit->second.scope != SCOPE_NONE && contributes) {
                        Comp* c = comp_of(st.comps, pit->second.scope, a.ctaId);   // its component
                        if (c != nullptr) {
                            if (gate == nullptr) { join_vc(c->J, V(t)); join_vc(c->J, pd_of(t)); }
                            else { join_vc(c->J, nr.clk); join_vc(c->J, nr.pd); }
                        }
                    }
                    if (rit2 == released.end()) {
                        released.emplace(loc, std::move(nr));
                    } else {
                        if (st.members == 1 && st.need_prev) {      // a new cluster keeps the
                            st.prev = std::move(rit2->second);      // single RMW before it
                            st.has_prev = true;
                        }
                        rit2->second = std::move(nr);
                    }
                    V(t).own = clk + 1;
                }
            }
        }
    }

    // YOSEMITE_HB_STATS (T5a): what HbClock holds at kernel end, per container.
    // Entry counts are exact; bytes are estimates from libstdc++'s node layouts (hash
    // node = next pointer + value, tree node = 32 bytes of links + value, each rounded to
    // a glibc malloc chunk; buckets = one pointer each) and leave out allocator slack.
    // Observational only: nothing here feeds a verdict, so hb_oracle.py has no twin.
    static uint64_t self_rss_kb() {                 // VmRSS of this process, kB
        std::ifstream st("/proc/self/status");
        for (std::string line; std::getline(st, line);)
            if (line.rfind("VmRSS:", 0) == 0) return std::strtoull(line.c_str() + 6, nullptr, 10);
        return 0;
    }
    static uint64_t mchunk(uint64_t n) {            // glibc chunk for an n-byte request
        const uint64_t c = (n + 8 + 15) & ~uint64_t(15);
        return c < 32 ? 32 : c;
    }
    template <class M> static uint64_t hash_buckets(const M& m) {  // 1 bucket = inline, no alloc
        return m.bucket_count() > 1 ? m.bucket_count() * sizeof(void*) : 0;
    }
    static uint64_t clock_bytes(const Clock& c) {
        return c.size() * mchunk(sizeof(void*) + sizeof(Clock::value_type)) + hash_buckets(c);
    }
    void stats(std::ostream& o) const {
        // T5b: a main clock = a shared base + a delta + own. `entries` counts what is stored
        // (each distinct base once, plus the deltas and the own components); a base is
        // attributed to vc if some thread holds it, else to the releases that do.
        std::set<const Base*> mbases;
        uint64_t vc_base_entries = 0, vc_delta_entries = 0, vc_max_delta = 0, vc_max_base = 0;
        uint64_t vc_bytes = vc.size() * mchunk(sizeof(void*) + sizeof(decltype(vc)::value_type))
                          + hash_buckets(vc);
        auto add_base = [&](const BaseP& b, uint64_t& entries, uint64_t& bytes) {
            if (!b || !mbases.insert(b.get()).second) return;
            entries += b->size();
            bytes += mchunk(16 + sizeof(Base)) + mchunk(b->capacity() * sizeof(Base::value_type));
        };
        for (const auto& kv : vc) {
            vc_delta_entries += kv.second.delta.size();
            vc_max_delta = std::max<uint64_t>(vc_max_delta, kv.second.delta.size());
            if (kv.second.base) vc_max_base = std::max<uint64_t>(vc_max_base, kv.second.base->size());
            vc_bytes += clock_bytes(kv.second.delta);
            add_base(kv.second.base, vc_base_entries, vc_bytes);
        }
        const uint64_t vc_bases = mbases.size();
        const uint64_t vc_entries = vc_base_entries + vc_delta_entries + vc.size();
        uint64_t rel_base_entries = 0, rel_delta_entries = 0;
        uint64_t rel_bytes = released.size() * mchunk(32 + sizeof(decltype(released)::value_type));
        for (const auto& kv : released) {
            rel_delta_entries += kv.second.clk.delta.size();
            rel_bytes += clock_bytes(kv.second.clk.delta);
            add_base(kv.second.clk.base, rel_base_entries, rel_bytes);
        }
        const uint64_t rel_bases = mbases.size() - vc_bases;
        const uint64_t rel_entries = rel_base_entries + rel_delta_entries + released.size();
        uint64_t bk_groups = 0, bk_entries = 0;
        uint64_t bk_bytes = buckets.size() * mchunk(32 + sizeof(decltype(buckets)::value_type));
        for (const auto& kv : buckets) {
            bk_groups += kv.second.size();
            bk_bytes += mchunk(kv.second.capacity() * sizeof(KeyGroup));
            for (const KeyGroup& g : kv.second) {
                bk_entries += g.by_tid.size();
                bk_bytes += g.by_tid.size() *
                            mchunk(sizeof(void*) + sizeof(std::pair<const Tid, Entry>))
                          + hash_buckets(g.by_tid);
            }
        }
        std::set<const Base*> bases;
        uint64_t vs_base_entries = 0;
        uint64_t vs_bytes = vs.size() * mchunk(sizeof(void*) + sizeof(decltype(vs)::value_type))
                          + hash_buckets(vs);
        for (const auto& kv : vs)
            if (kv.second.base && bases.insert(kv.second.base.get()).second) {
                vs_base_entries += kv.second.base->size();
                vs_bytes += mchunk(16 + sizeof(Base))
                          + mchunk(kv.second.base->capacity() * sizeof(Base::value_type));
            }
        uint64_t arrivals = 0;
        for (const auto& kv : pending_barriers) arrivals += kv.second.arrived.size();
        const uint64_t pend_bytes =
            pending_barriers.size() * mchunk(32 + sizeof(decltype(pending_barriers)::value_type))
            + arrivals * mchunk(32 + sizeof(Tid));
        o << "\"vc\": {\"threads\": " << vc.size() << ", \"entries\": " << vc_entries
          << ", \"bases\": " << vc_bases << ", \"base_entries\": " << vc_base_entries
          << ", \"max_base\": " << vc_max_base << ", \"delta_entries\": " << vc_delta_entries
          << ", \"max_delta\": " << vc_max_delta << ", \"bytes_est\": " << vc_bytes << "}"
          << ", \"released\": {\"records\": " << released.size() << ", \"entries\": "
          << rel_entries << ", \"own_bases\": " << rel_bases << ", \"delta_entries\": "
          << rel_delta_entries << ", \"bytes_est\": " << rel_bytes << "}"
          << ", \"merge_memo\": " << merge_memo.size()
          << ", \"buckets\": {\"locations\": " << buckets.size() << ", \"groups\": "
          << bk_groups << ", \"entries\": " << bk_entries << ", \"bytes_est\": " << bk_bytes << "}"
          << ", \"pending_barriers\": {\"instances\": " << pending_barriers.size()
          << ", \"arrivals\": " << arrivals << ", \"bytes_est\": " << pend_bytes << "}"
          << ", \"vs\": {\"threads\": " << vs.size() << ", \"unique_bases\": " << bases.size()
          << ", \"base_entries\": " << vs_base_entries << ", \"bytes_est\": " << vs_bytes << "}"
          << ", \"races\": {\"records\": " << races.size() << ", \"bytes_est\": "
          << races.capacity() * sizeof(Race) + race_index.size() * mchunk(8 + sizeof(RaceKey) + 8)
             + hash_buckets(race_index) << "}"
          << ", \"sync_pairs\": " << sync_pairs.size()
          << ", \"coherence_addrs\": " << coherence.size();
        // T14: the possible clock's state (entry counts; no verdict reads it)
        // T5b: pd entries = deltas + own components + each distinct pd base once
        uint64_t pd_entries = 0, held = 0, multi = 0, clu_entries = 0, rel_pd = 0, pd_bases = 0;
        std::set<const Base*> pbs;
        for (const auto& kv : pd) {
            pd_entries += kv.second.delta.size() + (kv.second.own != 0);
            if (kv.second.base && pbs.insert(kv.second.base.get()).second)
                pd_entries += kv.second.base->size(), pd_bases += 1;
        }
        for (const auto& kv : wins) held += kv.second.pend.size() + kv.second.held.size();
        for (const auto& kv : clus) {
            multi += kv.second.has_comps && kv.second.members >= 2;
            for (const auto* cs : {&kv.second.comps, &kv.second.inflow})
                for (const Comp& c : *cs) clu_entries += c.J.delta.size() + (c.J.base ? c.J.base->size() : 0);
            clu_entries += kv.second.prev.clk.delta.size();
        }
        for (const auto& kv : released) rel_pd += kv.second.pd.delta.size();
        o << ", \"a2\": {\"pd_threads\": " << pd.size() << ", \"pd_entries\": " << pd_entries
          << ", \"pd_bases\": " << pd_bases
          << ", \"released_pd_entries\": " << rel_pd << ", \"windows\": " << wins.size()
          << ", \"held\": " << held << ", \"clusters\": " << clus.size() << ", \"multi\": " << multi
          << ", \"cluster_clock_entries\": " << clu_entries << "}";
    }

    void emit(std::ostream& jout) {
        check_pending_at_end();   // T3b: before tv_violation is written below
        rmw_finish();             // T4: the pcs still pending in some thread are stranded
        if (vector_pass) emit_vc(jout);
        // T4 (design/no_dump.md section 3): the offline barrier-only pass's result, computed
        // online -- [pc_lo, pc_hi, count, dist, first_pc, second_pc]; both modes. In vector-
        // clock mode hb_races_sync_only (the triples) is written as well, above.
        if (sync_only_pass) {
            jout << ",\n  \"hb_sync_pass\": [";
            bool first_pair = true;
            for (const auto& kv : sync_pairs) {
                jout << (first_pair ? "" : ", ") << "[" << kv.first.first << ", "
                     << kv.first.second << ", " << kv.second.count << ", " << int(kv.second.dist)
                     << ", " << kv.second.first_pc << ", " << kv.second.second_pc << "]";
                first_pair = false;
            }
            jout << "]";
        }
        // T4: R3's release / acquire points from the trace (sync_dominance.trace_rmw_points):
        // per non-RMW pc the RMW pcs; [] = some instance had none (stranded / orphan).
        jout << ",\n  \"hb_rmw_points\": {\"release\": {";
        bool first_pc = true;
        for (const auto& kv : rmw_pts) {
            jout << (first_pc ? "" : ", ") << "\"" << kv.first << "\": [";
            if (!kv.second.stranded) {
                bool f = true;
                for (uint32_t r : kv.second.rel) { jout << (f ? "" : ", ") << r; f = false; }
            }
            jout << "]";
            first_pc = false;
        }
        jout << "}, \"acquire\": {";
        first_pc = true;
        for (const auto& kv : rmw_pts) {
            jout << (first_pc ? "" : ", ") << "\"" << kv.first << "\": [";
            if (!kv.second.orphan) {
                bool f = true;
                for (uint32_t r : kv.second.acq) { jout << (f ? "" : ", ") << r; f = false; }
            }
            jout << "]";
            first_pc = false;
        }
        jout << "}}";
        // Surface any trace-validity violation so corpus/validation runs (and the
        // Phase-4 harness) can assert zero. Absent key == none.
        if (!tv_violation.empty()) {
            std::string esc;
            for (char c : tv_violation) { if (c == '"' || c == '\\') esc += '\\'; esc += c; }
            jout << ",\n  \"tv_violation\": \"" << esc << "\"";
        }
    }
    // the vector-clock instance's keys (vector-clock mode only; absent in scalar-clock mode,
    // where an absent hb_races sends sync_dominance down its static-only path)
    void emit_vc(std::ostream& jout) {
        a2_close_all();           // T14: a thread with no next record: its window ends here
        // one record per aggregate key, with its count (see races) and a2_uncertain, how many
        // of its instances the possible clock orders (T14; DR and SC)
        jout << ",\n  \"hb_races\": [\n";
        for (size_t i = 0; i < races.size(); ++i) {
            const Race& r = races[i];
            const char* sp = (r.space == 1) ? "shared" : "global";
            jout << "    {\"addr\": " << r.addr
                 << ", \"space\": \"" << sp << "\""
                 << ", \"loc_block\": " << r.loc_block
                 << ", \"a_tid\": " << r.a_tid
                 << ", \"a_pc\": " << r.a_pc
                 << ", \"b_tid\": " << r.b_tid
                 << ", \"b_pc\": " << r.b_pc
                 << ", \"kind\": \"" << RACE_KIND[r.kind] << "\""
                 << ", \"class\": \"" << (r.sc ? "SC" : "DR") << "\""
                 << ", \"dist\": \"" << DIST_NAME[r.dist] << "\"";
            if (r.asy)   // T1a: which side is an agent's copy
                jout << ", \"async\": \"" << (r.asy == 3 ? "ab" : r.asy == 1 ? "a" : "b") << "\"";
            jout << ", \"count\": " << r.count << ", \"a2_uncertain\": " << r.a2;
            jout << "}";
            if (i + 1 < races.size()) jout << ",";
            jout << "\n";
        }
        jout << "  ]";
        jout << ",\n  \"hb_a2\": 1";   // T14: hb_races carry a2_uncertain (design/a2_flag.md)
        jout << ",\n  \"hb_gate\": \"" << (gate != nullptr ? "instance" : "trusting") << "\"";   // T12
        // barrier/syncwarp-only race pairs [pc_lo, pc_hi, count]; key absent when the
        // second pass is disabled so sync_dominance falls back to plain `latent`.
        if (sync_only_pass) {
            jout << ",\n  \"hb_races_sync_only\": [";
            bool first_pair = true;
            for (const auto& kv : sync_pairs) {
                jout << (first_pair ? "" : ", ") << "[" << kv.first.first << ", "
                     << kv.first.second << ", " << kv.second.count << "]";
                first_pair = false;
            }
            jout << "]";
        }
        // Coherence profile Pi (Phase 3): per atomic address, its observed atomic order
        // and hash. Additive/observational — the verdict above is unaffected.
        jout << ",\n  \"coherence_profile\": {";
        bool first_addr = true;
        for (const auto& kv : coherence) {
            if (!first_addr) jout << ",";
            first_addr = false;
            char hbuf[24];
            std::snprintf(hbuf, sizeof(hbuf), "0x%016llx",
                          static_cast<unsigned long long>(coherence_hash(kv.second)));
            jout << "\n    \"" << kv.first << "\": {\"len\": " << kv.second.size()
                 << ", \"hash\": \"" << hbuf << "\", \"seq\": [";
            for (size_t j = 0; j < kv.second.size(); ++j) {
                if (j) jout << ", ";
                jout << "[" << kv.second[j].first << ", " << kv.second[j].second << "]";
            }
            jout << "]}";
        }
        jout << (first_addr ? "}" : "\n  }");
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

// Analysis mode of an HB trace (YOSEMITE_HB_TRACE=1), read once per process:
//   YOSEMITE_HB_MODE=vector-clock  (default) the in-process HbClock runs over the
//                                  event stream and hb_races / hb_races_sync_only
//                                  are emitted next to hb_events;
//   YOSEMITE_HB_MODE=scalar-clock  hb_events are dumped only; the static leg and the
//                                  offline barrier-only pass decide.
// The pre-T8 switch YOSEMITE_HB_NO_ENGINE (set = scalar-clock) is retired, not renamed
// (T17): honoured for one more release with a deprecation warning; YOSEMITE_HB_MODE wins
// when both are set.
// File-static on purpose: PcDependency must not grow members (HARDENING_REPORT.md).
static bool hb_scalar_clock_mode() {
    static const bool scalar = [] {
        const char* mode = std::getenv("YOSEMITE_HB_MODE");
        const char* legacy = std::getenv("YOSEMITE_HB_NO_ENGINE");
        bool s = false;
        if (legacy != nullptr) {
            fprintf(stderr, "[cuVein] YOSEMITE_HB_NO_ENGINE is deprecated and will be removed: "
                            "use YOSEMITE_HB_MODE=scalar-clock\n");
            s = true;
        }
        if (mode != nullptr) {
            const std::string m(mode);
            if (m == "scalar-clock") {
                s = true;
            } else if (m == "vector-clock") {
                if (s) fprintf(stderr, "[cuVein] YOSEMITE_HB_MODE=vector-clock overrides "
                                       "the deprecated YOSEMITE_HB_NO_ENGINE\n");
                s = false;
            } else {
                fprintf(stderr, "[cuVein] YOSEMITE_HB_MODE=%s is neither scalar-clock nor "
                                "vector-clock; using %s\n", mode,
                        s ? "scalar-clock" : "vector-clock");
            }
        }
        return s;
    }();
    return scalar;
}

// YOSEMITE_HB_STATS=1 (T5a, eval/MEMORY_FOOTPRINT.md): attribute the HB state's memory
// at every kernel end (hb_stats_emit). Read once; zero cost when unset.
static bool hb_stats_enabled() {
    static const bool on = [] {
        const char* v = std::getenv("YOSEMITE_HB_STATS");
        return v != nullptr && *v != '\0' && std::string(v) != "0";
    }();
    return on;
}

// T4 (design/no_dump.md): YOSEMITE_HB_DUMP=0 keeps every record out of host memory -- no
// hb_events array in kernel_N.json; the aggregates the verdict layer reads from it (the
// barrier-only pass, R3's trace points, the counts) are computed by HbClock during the run,
// in both modes, and written at kernel end under "hb_aggregates": 1. Default 1: the lossless
// dump, with the same aggregates beside it. Read once; D4: T2's host analysis (python/host_hb.py)
// takes each kernel's footprint from the records, so the two flags together are refused.
static bool hb_dump_enabled() {
    static const bool on = [] {
        const char* v = std::getenv("YOSEMITE_HB_DUMP");
        const bool dump = v == nullptr || *v == '\0' || std::string(v) != "0";
        if (!dump && std::getenv("YOSEMITE_HB_HOST_MEMCPY") != nullptr) {
            fprintf(stderr, "[cuVein] YOSEMITE_HB_HOST_MEMCPY needs the hb_events dump "
                            "(host_hb.py takes each kernel's footprint from it): unset it, "
                            "or run with YOSEMITE_HB_DUMP=1\n");
            exit(EXIT_FAILURE);
        }
        return dump;
    }();
    return on;
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
    if (_hb_trace) (void)hb_dump_enabled();   // T4: read the switch (and D4's refusal) at start

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


static void hb_clock_select_kernel(const std::string& kernel_name);

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
    g_hb_bpos_base = 0;        // T15
    g_late_kernel_mode = 0;
    g_hb_events_count = g_hb_lanes_count = 0;   // T4
    hb_clock_reset();
    hb_clock_select_kernel(kernel->kernel_name);
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


// T15 (eval/LATE_SEQ.md): the late ordering key. With YOSEMITE_HB_LATE_SEQ the collector
// hands over, before each drain, one key per buffer slot drawn as the last action of the
// record's callback (yosemite_gpu_data_late_keys). The drain is then consumed -- by the dump
// and by HbClock alike -- in (key, slot) order; a buffer's keys all precede the next
// buffer's (the collector drains only after every key of the buffer has landed), so sorting
// within a drain orders the kernel. Each event carries both keys: "bpos" (its slot position
// in the kernel's buffer stream, the old order) and "lkey"; seq follows the late order.
// File statics, not PcDependency members (the header's latent-UB note).

void pc_dependency_set_late_keys(const uint64_t* keys, uint64_t size, uint32_t mode) {
    g_late_keys.assign(keys, keys + size);
    g_late_mode = mode;
}

void PcDependency::hb_collect_events(const MemoryAccess* buffer, uint64_t size,
                                     const uint32_t* order) {
    // Serialize each trace record (in buffer/temporal order) to a compact JSON
    // object appended to _hb_events. Called per buffer drain so the stream spans
    // the whole kernel. Memory records expand to active lanes; sync records carry
    // participation (barrier threadCount / syncwarp mask).
    // T4: with YOSEMITE_HB_DUMP=0 only the counters move (hb_events_count / hb_lanes_count);
    // nothing is kept.
    const bool dump = hb_dump_enabled();
    for (uint64_t k = 0; k < size; ++k) {
        const uint64_t i = order ? order[k] : k;
        const MemoryAccess& a = buffer[i];
        // I5 (D14): local memory is outside the HB model; the collector's default path and
        // its local-address tag are untouched, only the HB trace drops the record.
        if (a.type == MemoryType::Local) continue;
        g_hb_events_count += 1;
        if (a.type == MemoryType::Global || a.type == MemoryType::Shared)
            g_hb_lanes_count += static_cast<uint64_t>(__builtin_popcount(a.active_mask));
        if (!dump) continue;
        std::ostringstream o;
        const uint64_t seq = _hb_seq++;
        o << "{\"seq\": " << seq;
        if (order)   // T15: both keys, so one run measures both orders
            o << ", \"bpos\": " << (g_hb_bpos_base + i) << ", \"lkey\": " << g_late_keys[i];
        o << ", \"block\": " << a.ctaId
          << ", \"warp\": " << a.warpId
          << ", \"pc\": " << (a.pc & 0x00FFFFFFu);
        if (a.type == MemoryType::Barrier) {
            o << ", \"type\": \"barrier\", \"thread_count\": " << a.accessSize
              << ", \"bar_index\": " << a.flags
              << ", \"active_mask\": " << a.active_mask << "}";
        } else if (a.type == MemoryType::Syncwarp) {
            o << ", \"type\": \"syncwarp\", \"sync_mask\": " << a.accessSize
              << ", \"active_mask\": " << a.active_mask << "}";
        } else if (a.type == MemoryType::PipelineCommit) {   // T1a
            o << ", \"type\": \"pipeline_commit\", \"active_mask\": " << a.active_mask << "}";
        } else if (a.type == MemoryType::PipelineWait) {     // T1a: wait_group N
            o << ", \"type\": \"pipeline_wait\", \"groups\": " << a.accessSize
              << ", \"active_mask\": " << a.active_mask << "}";
        } else if (a.type == MemoryType::BlockExit) {       // T3b: the exiting lanes
            o << ", \"type\": \"exit\", \"active_mask\": " << a.active_mask << "}";
        } else {
            const char* kind = (a.flags & SANITIZER_MEMORY_DEVICE_FLAG_ATOMIC) ? "atomic"
                             : (a.flags & SANITIZER_MEMORY_DEVICE_FLAG_WRITE)  ? "write"
                             : "read";
            const char* space = (a.type == MemoryType::Shared) ? "shared" : "global";
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


// HbClock's state is a file-static singleton, NOT a PcDependency member: adding a
// member re-triggers a latent heap-corruption UB (see the header note). Only the
// single enabled pc_dependency tool instance ever processes kernels, so one
// singleton is correct; the 2 discarded tool temporaries never call reset().
// ponytail: singleton, not per-instance. Key by `this` only if two instances ever
// process concurrently (they don't — one tool is enabled at a time).
namespace {
std::unique_ptr<HbClock>& hb_clock_singleton() {
    static std::unique_ptr<HbClock> inst;
    return inst;
}
}  // namespace

// pcs are function-relative: bind HbClock to the launching kernel's pc table.
static void hb_clock_select_kernel(const std::string& kernel_name) {
    auto& hc = hb_clock_singleton();
    if (hc) hc->select_kernel(kernel_name);
}

void PcDependency::hb_clock_process(const MemoryAccess* buffer, uint64_t size,
                                     const uint32_t* order) {
    auto& hc = hb_clock_singleton();
    if (hc) hc->process(buffer, size, order);
}

void PcDependency::hb_clock_reset() {
    if (!_hb_trace) return;  // HbClock only runs in HB-trace mode
    auto& hc = hb_clock_singleton();
    if (!hc) {
        hc = std::make_unique<HbClock>();
        hc->load_scopes(std::getenv("YOSEMITE_ATOMIC_SCOPE_FILE"));
    }
    hc->reset();
    // expected participant count for a plain __syncthreads (thread_count 0 in the
    // trace) -> the whole block; used to assemble block-barrier instances.
    hc->block_thread_count = _current_block_thread_count;
    // TV invariants ON by default; YOSEMITE_HB_STRICT=0 disables them.
    const char* strict_env = std::getenv("YOSEMITE_HB_STRICT");
    hc->strict = (strict_env == nullptr) || (std::string(strict_env) != "0");
    hc->sync_only_pass = std::getenv("YOSEMITE_HB_NO_SYNC_ONLY") == nullptr;
    // T4: in scalar-clock mode HbClock runs the sync instance only (Detect(T, sync)): the
    // barrier-only pass, the TV monitor and R3's trace points online, no vector clock.
    hc->vector_pass = !hb_scalar_clock_mode();
    hc->stats_every = read_env_u32("YOSEMITE_HB_STATS_EVERY", 0);
    hc->next_snapshot = hc->stats_every;
}

void PcDependency::hb_clock_emit(std::ofstream& jout) {
    // In scalar-clock mode the sync instance writes NO hb_races / hb_races_sync_only (not
    // empty ones): an empty list is a claim ("nothing raced", "every pair is barrier-ordered")
    // that the verdict matrix would act on; an absent key sends sync_dominance down its
    // static-only path, where hb_sync_pass stands in for the offline pass (T4).
    auto& hc = hb_clock_singleton();
    if (hc) hc->emit(jout);
}


// YOSEMITE_HB_STATS=1: the kernel's HB memory at kernel end, when it peaks (HbClock
// resets at the next launch) -> "hb_stats" in kernel_N.json and one stderr line.
// hb_events: the kernel's event objects, buffered as one std::string each until this
// dump, so RAM = the string objects + their heap buffers; json_bytes = their text.
namespace {
void hb_stats_emit(std::ostream& jout, const std::vector<std::string>& ev,
                   const KernelLaunch_t& kernel) {
    uint64_t text = 0, heap = 0;
    for (const auto& e : ev) {
        text += e.size();
        if (e.capacity() > 15) heap += HbClock::mchunk(e.capacity() + 1);  // past SSO
    }
    const uint64_t ev_ram = ev.capacity() * sizeof(std::string) + heap;
    uint64_t rss = 0, hwm = 0;                      // kB
    std::ifstream st("/proc/self/status");
    for (std::string line; std::getline(st, line);) {
        if (line.rfind("VmRSS:", 0) == 0) rss = std::strtoull(line.c_str() + 6, nullptr, 10);
        else if (line.rfind("VmHWM:", 0) == 0) hwm = std::strtoull(line.c_str() + 6, nullptr, 10);
    }
    std::ostringstream o;
    o << "{\"hb_events\": {\"count\": " << g_hb_events_count << ", \"json_bytes\": " << text
      << ", \"ram_bytes_est\": " << ev_ram << "}, \"hb_clock\": ";
    auto& hc = hb_clock_singleton();
    if (hc) {                               // T4: the sync instance in scalar-clock mode too
        o << "{";
        hc->stats(o);
        o << "}";
    } else {
        o << "null";
    }
    o << ", \"rss_kb\": " << rss << ", \"hwm_kb\": " << hwm << "}";
    jout << ",\n  \"hb_stats\": " << o.str();
    fprintf(stderr, "[HB_STATS] kernel_%u %s %s\n", kernel.kernel_id,
            kernel.kernel_name.c_str(), o.str().c_str());
}
}  // namespace

// T2 (design/host_memcpy_model.md): the program's host-side operations in API order --
// copies, sets, launches (tied to their kernel_N.json), stream creation, synchronize and
// event calls -- as the collector reports them with YOSEMITE_HB_HOST_MEMCPY=1. Written as
// <dump dir>/host_ops.json at every kernel flush and at exit (a copy after the last kernel
// is common), for python/host_hb.py. File-static like HbClock: PcDependency must not
// grow members (HARDENING_REPORT.md).
namespace {
std::vector<std::string>& host_op_log() {
    // Never destroyed: the log is first used after the collector registered its atexit
    // cleanup, so a function-local static would be destroyed BEFORE that cleanup's final
    // flush() reads it (job 287950 left a truncated host_ops.json that way).
    static auto* log = new std::vector<std::string>();
    return *log;
}

void host_op_append(const YosemiteHostOp_t& op, long kernel_id, const std::string& kernel_name) {
    static const char* names[] = {"memcpy", "memset", "launch", "stream_create", "stream_sync",
                                  "ctx_sync", "event_record", "stream_wait", "event_sync",
                                  "host_alloc", "host_free"};
    auto& log = host_op_log();
    std::ostringstream o;
    o << "{\"seq\": " << log.size() << ", \"kind\": \""
      << (op.kind < sizeof(names) / sizeof(names[0]) ? names[op.kind] : "unknown") << "\""
      << ", \"stream\": " << op.stream << ", \"stream_ptr\": " << op.stream_ptr;
    switch (op.kind) {
        case YOSEMITE_HOST_MEMCPY:
            o << ", \"src\": " << op.src << ", \"dst\": " << op.dst << ", \"size\": " << op.size
              << ", \"width\": " << op.width << ", \"height\": " << op.height
              << ", \"depth\": " << op.depth << ", \"src_pitch\": " << op.src_pitch
              << ", \"dst_pitch\": " << op.dst_pitch << ", \"is_async\": " << op.is_async
              << ", \"direction\": " << op.direction;
            break;
        case YOSEMITE_HOST_MEMSET:
            o << ", \"dst\": " << op.dst << ", \"width\": " << op.width << ", \"height\": "
              << op.height << ", \"dst_pitch\": " << op.dst_pitch << ", \"element_size\": "
              << op.flags << ", \"is_async\": " << op.is_async;
            break;
        case YOSEMITE_HOST_LAUNCH:
            o << ", \"monitored\": " << (op.flags ? "true" : "false") << ", \"kernel_id\": ";
            if (kernel_id >= 0) o << kernel_id << ", \"kernel\": \"" << json_escape(kernel_name) << "\"";
            else o << "null";
            break;
        case YOSEMITE_HOST_STREAM_CREATE:
            o << ", \"flags\": " << op.flags;
            break;
        case YOSEMITE_HOST_EVENT_RECORD:
        case YOSEMITE_HOST_STREAM_WAIT:
        case YOSEMITE_HOST_EVENT_SYNC:
            o << ", \"event\": " << op.event;
            break;
        case YOSEMITE_HOST_ALLOC:
        case YOSEMITE_HOST_FREE:
            o << ", \"addr\": " << op.dst << ", \"size\": " << op.size << ", \"flags\": " << op.flags;
            break;
        default:
            break;
    }
    o << "}";
    log.push_back(o.str());
}

void host_op_write(const std::string& dir) {
    const auto& log = host_op_log();
    if (log.empty() || dir.empty()) return;
    const std::string tmp = dir + "/host_ops.json.tmp";
    {
        std::ofstream out(tmp);
        if (!out) return;
        out << "{\n  \"tool\": \"pc_dependency_analysis\",\n  \"host_ops\": [\n";
        for (size_t i = 0; i < log.size(); ++i)
            out << "    " << log[i] << (i + 1 < log.size() ? ",\n" : "\n");
        out << "  ]\n}\n";
    }
    std::rename(tmp.c_str(), (dir + "/host_ops.json").c_str());
}
}  // namespace

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
        if (hb_dump_enabled()) {
            jout << ",\n  \"hb_events\": [\n";
            for (size_t i = 0; i < _hb_events.size(); ++i) {
                jout << "    " << _hb_events[i];
                if (i + 1 < _hb_events.size()) jout << ",";
                jout << "\n";
            }
            jout << "  ]";
        } else {
            // T4 (design/no_dump.md section 3): no records; HbClock's aggregates below stand
            // in for them. Never a lossy hb_events (A4).
            jout << ",\n  \"hb_aggregates\": 1";
        }
        jout << ",\n  \"hb_events_count\": " << g_hb_events_count
             << ", \"hb_lanes_count\": " << g_hb_lanes_count;
        // T1a: this stream records cp.async commit / wait_group (pipeline_commit /
        // pipeline_wait). Offline consumers (hb_oracle, the scalar-clock barrier pass)
        // apply the async-agent model only to dumps carrying the marker: an older dump
        // has LDGSTS accesses but no commit/wait records, so its copies would never
        // complete.
        jout << ",\n  \"hb_async\": 1";
        // T3b: this stream carries exit records (type "exit"). Offline consumers run the
        // end-of-kernel TV-barrier-pending-at-end check only on dumps with the marker: an
        // older dump has no exits, so an early-exit kernel's segments stay open there.
        jout << ",\n  \"hb_exits\": 1";
        // T15: seq follows the late ordering key (events carry bpos = the buffer order and
        // lkey); absent = buffer order, as before.
        if (g_late_kernel_mode != 0)
            jout << ",\n  \"hb_late_seq\": 1, \"hb_late_seq_key\": \""
                 << (g_late_kernel_mode == 2 ? "timer" : "atomic") << "\"";
        // HbClock's verdicts (streaming; mirrors hb_oracle.py).
        hb_clock_emit(jout);
        if (hb_stats_enabled()) hb_stats_emit(jout, _hb_events, *kernel);
    }

    jout << "\n}\n";
    printf("Dumping pc dependency graph json to %s\n", json_filename.c_str());
    host_op_write(output_directory);   // T2: no-op unless host operations were reported
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
                case MemoryType::PipelineCommit:   // T1a (HB-trace runs only)
                case MemoryType::PipelineWait:
                    // Phase 2 sync events: no shadow/pc-statistics update. Consumed
                    // by hb_collect_events (HB oracle) and HbClock.
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
        // T15: the late key's order for this drain (identity without YOSEMITE_HB_LATE_SEQ).
        std::vector<uint32_t> late_order;
        if (!g_late_keys.empty()) {
            if (g_late_keys.size() != size) {
                fprintf(stderr, "[cuVein] T15: %zu late keys for a drain of %lu records\n",
                        g_late_keys.size(), (unsigned long)size);
                exit(EXIT_FAILURE);
            }
            late_order.resize(size);
            std::iota(late_order.begin(), late_order.end(), 0u);
            std::stable_sort(late_order.begin(), late_order.end(), [](uint32_t x, uint32_t y) {
                return g_late_keys[x] < g_late_keys[y];   // ties (timer) keep buffer order
            });
            g_late_kernel_mode = g_late_mode;
        }
        const uint32_t* order = late_order.empty() ? nullptr : late_order.data();
        hb_collect_events(accesses_buffer, size, order);
        // T4: HbClock consumes the drain in both modes -- the vector clock and the sync
        // instance in vector-clock mode, the sync instance alone in scalar-clock mode
        // (hb_clock_reset sets vector_pass) -- so a run without the dump still yields the
        // barrier-only pass, R3's trace points and the TV monitor. (Before T4 scalar-clock
        // mode only dumped: on a reduction of 4M elts, 136K events, the exact VCs added ~4 s
        // vs ~1.3 s for the dump.)
        hb_clock_process(accesses_buffer, size, order);
        g_hb_bpos_base += size;
        g_late_keys.clear();
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
        case EventType_HOST_OP: {   // T2: YOSEMITE_HB_HOST_MEMCPY=1 only
            const auto& op = std::dynamic_pointer_cast<HostOp_t>(evt)->op;
            long kid = -1;
            std::string kname;
            if (op.kind == YOSEMITE_HOST_LAUNCH && op.flags && !kernel_events.empty()) {
                const auto& k = std::prev(kernel_events.end())->second;   // its kernel-start event
                kid = static_cast<long>(k->kernel_id);                    // came just before
                kname = k->kernel_name;
            }
            host_op_append(op, kid, kname);
            break;
        }
        default:
            break;
    }
}


void PcDependency::flush() {
    host_op_write(output_directory);   // T2: host operations after the last kernel
}

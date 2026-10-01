#!/usr/bin/env python3
"""Full vector-clock happens-before oracle over the hb_events dump.

Exact per-instance *observed-schedule* happens-before, used as the correctness
spec for HbClock (roadmap Phase 2). Reads
the kernel CFG (only to classify which PCs are atomics + their scope, reusing
sync_dominance) and the pc_dependency trace JSON produced with YOSEMITE_HB_TRACE=1
(the `hb_events` per-instance stream).

Model (design/proof/hb_proof.tex, Algorithm 1 "Detect"): every thread carries a vector
clock. Synchronization updates the clocks -- a barrier / masked syncwarp joins its actual
participants; an atomic RMW acquires the clock released to its location, is checked,
publishes its pre-tick clock and then ticks (publish-then-tick, I1). Per location, every
thread keeps one bucket per record key (kind R/W/RMW, strong scope or weak) holding its
latest such record (I2). A conflict (same location, >=1 write, different threads) that
the resulting happens-before relation leaves unordered is reported with its class: "DR"
(data race) unless the two records are morally strong -- both strong, each scope covering
the other thread (atomic RMWs, or loads/stores whose SASS carries .STRONG.<scope>: the
strength column of the atomic-scope sidecar, sd.coherent_scope, T10; --strong-ldst keeps
the pre-T10 policies as ablations) -- then "SC" (unordered strong conflict); two morally
strong RMWs are never reported.
Local memory is outside the model (I5): `local` records are skipped. No pattern is
special-cased: the canary, named barriers, masked syncwarps and loop-carried handshakes
all fall out as a consequence of the clocks.

A second clock per thread is advanced by barriers/syncwarps ONLY (Detect(T, sync)). Its
races (`races_sync_only`, pc pairs with counts, DR and SC alike) tell the verdict matrix
which dynamically ordered pairs owe their order to schedule-independent barrier joins
alone and which to atomic release/acquire joins (which ignore fences -> stay latent).

This is the exact O(threads) reference; HbClock must agree
with it on every corpus binary. Not for large workloads.

Usage:  python hb_oracle.py <kernel_cfg.dot> <kernel_N.json> [-o out.json]
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import sync_dominance as sd


# Trace-validity (TV) invariants. The correctness argument assumes the collector
# emits "valid" traces; these turn four of those assumptions into checked runtime
# invariants that raise AlignmentError (never a silent verdict) when violated. ON
# by default in the oracle; set YOSEMITE_HB_STRICT=0 only to debug a known-bad trace.
def _strict_enabled():
    return os.environ.get("YOSEMITE_HB_STRICT", "1") != "0"


def tid_of(block, warp, lane):
    return (block << 10) | (warp << 5) | lane


_FNV64_OFFSET = 0xcbf29ce484222325
_FNV64_PRIME = 0x100000001b3
_MASK64 = (1 << 64) - 1


def coherence_hash(seq):
    """Stable 64-bit FNV-1a of a (tid, atomic-index) sequence. Byte-for-byte the same
    construction as HbClock::coherence_hash so oracle and HbClock profiles compare."""
    h = _FNV64_OFFSET
    for tid, idx in seq:
        for shift in (0, 8, 16, 24):                 # tid: 4 bytes little-endian
            h = ((h ^ ((tid >> shift) & 0xFF)) * _FNV64_PRIME) & _MASK64
        for shift in range(0, 64, 8):                # idx: 8 bytes little-endian
            h = ((h ^ ((idx >> shift) & 0xFF)) * _FNV64_PRIME) & _MASK64
    return h


class VC(dict):
    """tid -> logical clock; a missing entry reads 0."""
    def joined(self, other):
        out = VC(self)
        for t, c in other.items():
            if c > out.get(t, 0):
                out[t] = c
        return out


def _join_into(dst, src):
    """dst ⊔= src in place."""
    for t, c in src.items():
        if c > dst.get(t, 0):
            dst[t] = c


class _Clu:
    """T14 (design/a2_flag.md): one location's current RMW cluster -- the RMWs whose windows
    [record, the thread's next record) chain-overlap. `inflow` is what the cluster before it
    hands on: its components if it was multi (else None, and `prev` is its single RMW's
    publish); `comps` the cluster's own, once it needs them."""
    __slots__ = ("open", "members", "comps", "inflow", "prev")

    def __init__(self):
        self.open = 0          # members whose window is still open
        self.members = 0       # RMWs in the cluster; >= 2 = multi
        self.comps = None      # [_Comp]: after a multi cluster, or once this one is multi
        self.inflow = None
        self.prev = None


class _Comp:
    """T14: an ms-connectivity component of a cluster's RMWs (plus what the cluster before it
    handed on): the blocks of its grid-scope and block-scope members (g, b; ag, ab only the
    cluster's own members, which is what it hands on) and the join J of their contributions.
    A grid-scope member is morally strong with every grid-scope member and with the
    block-scope members of its block; a block-scope one with its block's; a none-scope one
    with nothing."""
    __slots__ = ("g", "b", "ag", "ab", "J")

    def __init__(self, g=(), b=(), J=None):
        self.g, self.b, self.ag, self.ab = set(g), set(b), set(), set()
        self.J = VC() if J is None else VC(J)

    def links(self, s, blk):
        return (bool(self.g) or blk in self.b) if s == sd.GRID else (blk in self.g or blk in self.b)


def _comp_add(comps, s, blk, actual):
    """a member of scope s in block blk joins the components it links (merging them) -> its own"""
    linked = [c for c in comps if c.links(s, blk)]
    if not linked:
        linked = [_Comp()]
        comps.append(linked[0])
    c = linked[0]
    for o in linked[1:]:
        c.g |= o.g
        c.b |= o.b
        c.ag |= o.ag
        c.ab |= o.ab
        _join_into(c.J, o.J)
        comps.remove(o)
    (c.g if s == sd.GRID else c.b).add(blk)
    if actual:
        (c.ag if s == sd.GRID else c.ab).add(blk)
    return c


def _comp_of(comps, s, blk):
    """the component of a member (unique: grid-scope members are all linked, and so are the
    block-scope members of one block)"""
    return next(c for c in comps if blk in (c.g if s == sd.GRID else c.b))




def analyze(dot_path, trace_path, strong_ldst=None, records=False, gate=None):
    """-> the report dict. `races` is aggregated per (a_pc, b_pc, kind, class, space, thread
    distance, async side): one example record plus `count`, the number of conflicting
    record pairs Check found (with repeats) -- a race set without the FastTrack collapse is
    O(threads^2) record pairs per location, which no consumer needs (the verdict layer works
    on pc pairs, their class, widest distance, warp and async). records=True also returns
    `race_records`, the set of record pairs (addr, a_tid, a_pc, b_tid, b_pc, class) with the
    issuing thread's id for an agent's access (design/algorithms_check.py compares it with
    Detect).

    gate (T12, hb_proof.tex Definition "Gate"; design/instance_gate.md): 'instance' gates
    every (ATOM) edge by fenced() on the thread's previous/next record pcs, 'trusting' joins
    every hand-off (the pre-T12 code). Default: $CUVEIN_GATE, else the gate that produced the
    dump (its `hb_gate` key), else 'trusting' -- a pre-T12 dump replays as it was recorded."""
    trace = json.loads(Path(trace_path).read_text())
    events = sorted(trace.get("hb_events", []), key=lambda e: e["seq"])
    if not events:
        raise sd.AlignmentError(f"{trace_path} has no hb_events "
                                "(run getall.sh with YOSEMITE_HB_TRACE=1)")

    kernels = sd.parse_dot(dot_path)
    mangled = sd.select_kernel(kernels, trace["kernel"]["kernel_name"])
    eng = sd.HBGraph(*kernels[mangled])
    # pc -> atomic coherence scope (sd.NONE/BLOCK/GRID); NONE = weak/unknown, no HB.
    atom_scope = {pc: s for pc in eng.pc_opcode
                  if (s := sd.atomic_scope(eng.pc_opcode[pc])) is not None}
    # pc -> coherent-access scope: the RMW atomics plus (per policy) .STRONG loads/
    # stores. Pairwise same-address coherence only — a coherent load/store is an
    # ordinary read/write otherwise (no release/acquire join).
    policy = sd.strong_ldst_policy(strong_ldst)
    coh_scope = {pc: s for pc in eng.pc_opcode
                 if (s := sd.coherent_scope(eng.pc_opcode[pc], policy)) is not None}
    # T1a: cp.async (LDGSTS) pcs -- accesses by the issuing thread's async agent. The
    # HbClock reads the same set from the sidecar's `# async` lines (sd.async_pcs rule);
    # a dump without HbClock's hb_async marker keeps the pre-T1a reading.
    async_pcs = sd.dump_async_pcs(eng, trace)
    # T12: the instance gate. rel(r) from t's previous record, acq(r) from its next one; the
    # acquire is DEFERRED to t's next record exactly as HbClock must (it cannot look ahead):
    # Check(r) runs against vc[t] and the conflicts only the pending join J would order are
    # held in r's window, reported iff acq(r) = 0 (design/instance_gate.md section 6).
    gate_on = sd.dump_gate(trace, gate) == "instance"
    gtab = eng.gate_table() if gate_on else {}
    last_pc = {}                      # tid -> pc of its latest record (rel)
    gstat = defaultdict(int)          # RMW lane records: rmw, rel0, acq0, held, held_reported
    ASYNC = sd.ASYNC_BIT
    groups = defaultdict(list)        # t -> [(vc, vs) of its agent at each commit], oldest first

    vc = defaultdict(VC)              # tid -> vector clock (barriers + atomic handoffs)
    vs = defaultdict(VC)              # tid -> barrier/syncwarp-ONLY vector clock
    released = {}                     # loc -> (clock, releaser_block, scope)
    # Buckets (hb_proof.tex Algorithm 1, T9/I2): per location, per record key
    # (kind, strong scope or None = weak), per thread: (vc epoch, vs epoch, pc) of that
    # thread's latest record on the location with that key. Never cleared across threads
    # (no FastTrack collapse: Theorem "Sound" needs a replaced entry PO-before its
    # replacement). One bucket serves both clocks: both runs replace it at the same records.
    buckets = defaultdict(dict)       # loc -> {(kind, scope): {tid: (clk, sclk, pc)}}
    agg = {}                          # aggregate key -> [example record, count, a2-flagged]
    rec_set = set() if records else None
    sync_pairs = defaultdict(int)     # (pc_lo, pc_hi) -> conflicts unordered by vs
    # T14 (design/a2_flag.md): the a2_uncertain flag. The "possible" clock poss[t] = vc[t] ⊔
    # pd[t]: pd follows vc through every recorded operation and gets, in addition, a late
    # acquire when an RMW's window [record, the thread's next record) closes -- the join of
    # its cluster, or of the multi cluster before it. No verdict reads it: it counts, per
    # aggregated record (DR or SC), the instances a window-consistent coherence order could
    # order.
    pd = {}                           # tid -> VC (absent = empty)
    wins = {}                         # tid -> [loc, scope, epoch, {(key, u, e, side): n}, [(r, u, e)]]
    clus = {}                         # loc -> _Clu
    a2_log = defaultdict(int) if records else None   # (a_tid, a_pc, a_ep, b_tid, b_pc, b_ep, flag)

    # Coherence profile Pi (Phase 3, observational — never affects a verdict). The
    # single-trace certificate is per-profile: the observed per-address coherence order
    # of atomics. Record, per address touched by >=1 atomic, the sequence of
    # (tid, that thread's atomic index) in event order, plus a stable hash of it (the
    # SAME FNV-1a HbClock emits, so the two profiles are cross-checkable).
    atom_idx = defaultdict(int)      # tid -> count of atomics this thread has issued
    coherence = defaultdict(list)    # addr -> [(tid, per-thread atomic index), ...]

    # Block-barrier instance assembly. A block-wide __syncthreads (BAR.SYNC) emits one
    # arrival record per warp; buffer arrivals per (block, bar_index) and join the
    # UNION of all participants only once the instance is complete, so warp 0's
    # pre-barrier writes are ordered before every warp's post-barrier reads (the
    # cross-warp tile idiom). thread_count is the expected participant count; 0 for a
    # plain __syncthreads means the whole block, so fall back to block_thread_count. A
    # loop reuses (block, bar_index): the barrier prevents any warp reaching instance
    # k+1 before k completes, so accumulate-then-reset segments dynamic instances.
    # T3b (hb_proof.tex Definition "Instances"): a whole-block segment expects
    # block_thread_count minus the block's exited threads (exit records); a counted one
    # (bar.sync id, n) keeps n; an exit re-checks the block's open segments (Complete).
    block_tc = trace["kernel"].get("block_thread_count")
    pending_bar = defaultdict(set)    # (block, bar_index) -> set of arrived tids
    pending_cnt = {}                  # (block, bar_index) -> the segment's thread_count
    exited = defaultdict(set)         # block -> exited tids
    exited_lanes = defaultdict(int)   # (block, warp) -> exited lane mask
    # --- Trace-validity (TV) invariant bookkeeping (see _strict_enabled) ---
    strict = _strict_enabled()
    bar_warps_seen = defaultdict(set)  # (block, bar_index) -> set of warp ids ever arrived
    warp_waiting = {}                  # (block, warp) -> key it is blocked on (not yet fired)

    def own(t):
        # a thread's own clock starts at 1: a write is then (t@>=1) while a thread
        # that never synced with t knows it only as 0, so >0 catches the race.
        if vc[t].get(t, 0) == 0:
            vc[t][t] = 1
        return vc[t][t]

    def owns(t):
        if vs[t].get(t, 0) == 0:
            vs[t][t] = 1
        return vs[t][t]

    def sync_group(tids):
        """Barrier/syncwarp: everyone learns everyone's pre-sync clock (join),
        then each ticks its own component so post-sync accesses are ordered after
        the join but concurrent with each other (two post-barrier writes race).
        Applied to both clocks; it is the ONLY thing that advances vs."""
        pj = VC()                         # T14: the participants' possible deltas join too
        for t in tids:
            if t in pd:
                _join_into(pj, pd.pop(t))
        for clocks, init in ((vc, own), (vs, owns)):
            for t in tids:
                init(t)
            j = VC()
            for t in tids:
                j = j.joined(clocks[t])
            for t in tids:
                nv = VC(j)
                nv[t] = nv.get(t, 0) + 1
                clocks[t] = nv
        for t in tids if pj else ():
            pd_join(t, pj)

    def conflict(prev_tid, prev_clk, prev_sclk, prev_pc, t, pc, kind, cls, rec, observer=None,
                 gheld=None):
        """One unordered-ness test per clock for a conflicting (prev, current) pair, as
        seen by `observer` (default t; the issuing thread for two copies of its agent).
        cls = "DR" (data race) or "SC" (unordered strong conflict, Definition "Verdicts").
        gheld (T12): the gate state of t's RMW with a pending acquire J -- a conflict J
        would order is held there; the flag decision of any other is taken after the gate
        resolves (it depends on J through the possible clock)."""
        o = t if observer is None else observer
        if prev_clk > vc[o].get(prev_tid, 0):
            te = vc[t][t]
            if gheld is not None:
                if prev_clk <= gheld[2].get(prev_tid, 0):
                    gheld[4].append((prev_tid, prev_clk, prev_pc, pc, kind, cls, dict(rec), te))
                else:
                    gheld[5].append((report(prev_tid, prev_clk, prev_pc, t, pc, kind, cls, rec),
                                     prev_tid, prev_clk, prev_pc, pc, dict(rec), te))
            else:
                key = report(prev_tid, prev_clk, prev_pc, t, pc, kind, cls, rec)
                a2_decide(key, prev_tid, prev_clk, prev_pc, t, pc, o, rec)   # T14: DR and SC
        if prev_sclk > vs[o].get(prev_tid, 0):
            sync_pairs[(min(prev_pc, pc), max(prev_pc, pc))] += 1

    def report(prev_tid, prev_clk, prev_pc, t, pc, kind, cls, rec):
        """count one reportable record pair in its aggregate -> the aggregate key"""
        if True:
            a0, b0 = prev_tid & ~ASYNC, t & ~ASYNC
            asy = "ab" if prev_tid & t & ASYNC else "a" if prev_tid & ASYNC else \
                  "b" if t & ASYNC else ""
            dist = sd.thread_distance(a0, b0)
            key = (prev_pc, pc, kind, cls, rec["space"], dist, asy)
            g = agg.get(key)
            if g is None:
                ex = {**rec, "a_tid": a0, "a_pc": prev_pc, "b_tid": b0, "b_pc": pc,
                      "kind": kind, "class": cls, "dist": sd.SCOPES[dist]}
                if asy:
                    ex["async"] = asy
                agg[key] = [ex, 1, 0]
            else:
                g[1] += 1
            if rec_set is not None:
                rec_set.add((rec["addr"], a0, prev_pc, b0, pc, cls))
            return key

    def check(t, kind, scope, pc, loc, rec, gheld=None):
        """Procedure Check: every other thread's buckets on loc that conflict with this
        record (one of the two a write); morally strong pairs are SC unless both are RMWs,
        which are never reportable."""
        for (pk, ps), group in buckets[loc].items():
            if kind == "R" and pk == "R":
                continue
            both_rmw = kind == "RMW" and pk == "RMW"
            if both_rmw and ps is not None and scope is not None \
                    and min(ps, scope) == sd.GRID:
                continue                  # every pair of the group is morally strong
            label = "WAR" if pk == "R" else "atomic" if kind == "RMW" else \
                    "WAW" if kind == "W" else "RAW"
            for u, (uc, usc, upc) in group.items():
                if u == t:
                    continue
                strong = sd.morally_strong(ps, u & ~ASYNC, scope, t & ~ASYNC)
                if strong and both_rmw:
                    continue
                conflict(u, uc, usc, upc, t, pc, label, "SC" if strong else "DR", rec,
                         gheld=gheld)

    # T1a: the async agent (see HbClock::async_issue/commit/wait; one-to-one)
    def async_issue(t, ag):
        own(t)
        vc[ag] = vc[ag].joined(vc[t])     # the copy follows t's earlier accesses
        pd_join(ag, pd.get(t))            # T14
        own(ag)
        owns(t)
        vs[ag] = vs[ag].joined(vs[t])
        owns(ag)

    def async_commit(t):
        ag = t | ASYNC
        own(ag), owns(ag)
        groups[t].append((VC(vc[ag]), VC(vs[ag]), VC(pd.get(ag, ()))))
        vc[ag][ag] += 1                   # later copies: a newer epoch than this group
        vs[ag][ag] += 1

    def async_wait(t, n):
        g = groups[t]
        if len(g) <= n:
            return
        done = len(g) - n                 # groups [0, done) are complete
        svc, svs, spd = g[done - 1]       # snapshots only grow
        own(t)
        vc[t] = vc[t].joined(svc)
        pd_join(t, spd)                   # T14
        owns(t)
        vs[t] = vs[t].joined(svs)
        del g[:done]

    def expected_of(key):
        if pending_cnt.get(key):
            return pending_cnt[key]
        return max(block_tc - len(exited[key[0]]), 0) if block_tc else block_tc

    def fire(key):
        arrived = pending_bar.pop(key)
        pending_cnt.pop(key, None)
        sync_group(sorted(arrived))
        for w in {(t >> 5) & 0x1f for t in arrived}:
            warp_waiting.pop((key[0], w), None)

    def complete(key):
        """procedure Complete: after every arrival on key and every exit in its block."""
        exp = expected_of(key)
        if pending_bar[key] and exp and len(pending_bar[key]) >= exp:
            fire(key)
            return True
        return False

    def loc_of(space, block, addr):
        # shared memory is per-block; global keyed by absolute address.
        return (space, block, addr) if space == "shared" else (space, addr)

    # --- T14: the possible clock and RMW windows (design/a2_flag.md section 3) -----------
    def poss(t, u):
        d = pd.get(t)
        return max(vc[t].get(u, 0), d.get(u, 0) if d else 0)

    def pd_join(t, src):
        """pd[t] ⊔= src, keeping only what vc[t] does not already know."""
        if not src:
            return
        cur, d = vc[t], pd.get(t)
        for u, c in src.items():
            if c > cur.get(u, 0) and (d is None or c > d.get(u, 0)):
                if d is None:
                    d = pd[t] = VC()
                d[u] = c

    def a2_open(t, loc, scope, blk):
        """An RMW of t (block blk) on loc opens its window [this record, t's next record): it
        joins loc's open cluster or starts one. Components are built once the cluster is multi,
        or at once when the cluster before it was (its inflow); two singletons in a row need
        none -- the recorded chain is then exact."""
        st = clus.get(loc)
        if st is None:
            st = clus[loc] = _Clu()
        if st.open == 0:              # every earlier window on loc closed: a new cluster
            st.members, st.comps = 0, None
            st.prev = released.get(loc) if st.inflow is None else None
        st.members += 1
        st.open += 1
        if st.comps is None and (st.inflow is not None or st.members == 2):
            if st.inflow is not None:     # what the multi cluster before hands on
                st.comps = [_Comp(c.ag, c.ab, c.J) for c in st.inflow]
            else:
                st.comps = []
                for r, actual in ((st.prev, False), (released.get(loc), True)):
                    if r is not None and r[2] != sd.NONE:   # the single RMW before; the first
                        c = _comp_add(st.comps, r[2], r[1], actual)   # member, as published
                        _join_into(c.J, r[0] or {})         # (None: T12, nothing released)
                        _join_into(c.J, r[3] or {})
        if st.comps is not None and scope != sd.NONE:
            _comp_add(st.comps, scope, blk, True)
        # [6]: T12 gate state of this RMW -- None, or [pc, rel, J, Jpd, held, defer]
        wins[t] = [loc, scope, own(t), {}, [], blk, None]

    def close_win(t, nxt_pc=None):
        """t's next record (pc nxt_pc; None = the end of the kernel) closes its RMW window:
        under the instance gate first acq(r) and the deferred acquire (T12), then the late
        acquire, then the decisions held on the window."""
        g = wins[t][6]
        acq = rel = True
        if g is not None:
            r_pc, rel, J, Jpd, held, defer = g
            acq = nxt_pc is None or nxt_pc in gtab[r_pc][2]
            gstat["acq0"] += not acq
            gstat["held"] += len(held)
            gstat["held_reported"] += 0 if acq else len(held)
            if acq:                   # the deferred acquire: join, drop what it orders
                if J:
                    vc[t] = vc[t].joined(J)
                pd_join(t, Jpd)
            else:                     # no acquire: the held conflicts are reported
                for u, uc, upc, pc, kind, cls, rec, te in held:
                    defer.append((report(u, uc, upc, t, pc, kind, cls, rec), u, uc, upc,
                                  pc, rec, te))
            for key, u, ue, upc, pc, rec, te in defer:
                a2_decide(key, u, ue, upc, t, pc, t, rec, te)
        loc, scope, w_ep, pend, shared, blk, _ = wins.pop(t)
        st = clus[loc]
        if st.comps is not None and scope != sd.NONE and acq:
            a = _comp_of(st.comps, scope, blk).J
            if a:
                pd_join(t, a)
                if st.members == 1 and rel and released[loc][0] is not None:
                    rc, rb, rs, rp = released[loc]   # a single RMW after a multi cluster:
                    released[loc] = (rc, rb, rs, rp.joined(a))   # what it hands on
        for (key, u, e, side), n in pend.items():
            f = e <= poss(t, u)
            if f:
                agg[key][2] += n
            if a2_log is not None:    # side 1: u's record came first, this RMW second
                a2_log[(u, key[0], e, t, key[1], w_ep, f) if side == 1
                       else (t, key[0], w_ep, u, key[1], e, f)] += n
        for rec2, u, e in shared:     # held on two windows: flagged if either orders it
            rec2[3] = rec2[3] or e <= poss(t, u)
            rec2[2] -= 1
            if rec2[2] == 0:
                if rec2[3]:
                    agg[rec2[0]][2] += rec2[1]
                if a2_log is not None:
                    a2_log[rec2[4] + (rec2[3],)] += rec2[1]
        st.open -= 1
        if st.open == 0:              # complete; a multi one hands on its members' components
            st.inflow = [c for c in st.comps if c.ag or c.ab] \
                if st.comps is not None and st.members >= 2 else None
            st.comps, st.prev, st.members = None, None, 0

    def close_lanes(block, warp, mask, pc):
        if wins:
            for k in range(32):
                if (mask >> k) & 1 and tid_of(block, warp, k) in wins:
                    close_win(tid_of(block, warp, k), pc)
        if gate_on:
            for k in range(32):
                if (mask >> k) & 1:
                    last_pc[tid_of(block, warp, k)] = pc

    def a2_decide(key, u, ue, upc, t, pc, o, rec, te=None):
        """One reported instance (u's record at epoch ue, then t's record at epoch te): flagged
        now if the possible clock orders it; else held on an RMW endpoint's open window -- t's
        RMW, whose window just opened, or u's RMW, whose window has not closed -- and decided
        there."""
        te = vc[t][t] if te is None else te
        if ue <= poss(o, u):
            agg[key][2] += 1
            if a2_log is not None:
                a2_log[(u, upc, ue, t, pc, te, True)] += 1
            return
        w1 = wins.get(t) if pc in atom_scope else None
        w2 = wins.get(u) if upc in atom_scope else None
        if w2 is not None and (w2[2] != ue or
                               w2[0] != loc_of(rec["space"], rec["loc_block"], rec["addr"])):
            w2 = None
        if w1 is not None and w2 is not None:
            r = [key, 1, 2, False, (u, upc, ue, t, pc, te)]
            w1[4].append((r, u, ue))
            w2[4].append((r, t, te))
        elif w1 is not None:
            w1[3][(key, u, ue, 1)] = w1[3].get((key, u, ue, 1), 0) + 1
        elif w2 is not None:
            w2[3][(key, t, te, 2)] = w2[3].get((key, t, te, 2), 0) + 1
        elif a2_log is not None:
            a2_log[(u, upc, ue, t, pc, te, False)] += 1

    prev_seq = None
    for e in events:
        # TV-seq-monotonic: events are consumed in strictly increasing seq. The
        # stream is pre-sorted by seq; seq <= prev means a duplicate/rewound record.
        seq = e["seq"]
        if strict and prev_seq is not None and seq <= prev_seq:
            raise sd.AlignmentError(
                f"TV-seq-monotonic: seq {seq} not > previous {prev_seq} "
                "(duplicate or non-monotonic hb_events)")
        prev_seq = seq

        typ = e["type"]
        if typ == "exit":             # T3b: the exiting lanes of one warp
            block, warp, mask = e["block"], e["warp"], e["active_mask"]
            close_lanes(block, warp, mask, e["pc"])           # T14; T12: its pc is q
            if strict and mask & exited_lanes[(block, warp)]:
                raise sd.AlignmentError(
                    f"TV-record-after-exit: block {block} warp {warp} lanes mask "
                    f"{mask & exited_lanes[(block, warp)]} exit twice (seq {seq})")
            exited_lanes[(block, warp)] |= mask
            gone = {tid_of(block, warp, k) for k in range(32) if (mask >> k) & 1}
            exited[block] |= gone
            for key in sorted(k for k in pending_bar if k[0] == block):
                # W2: an exiting thread cannot be waiting at an open segment.
                if strict and gone & pending_bar[key]:
                    raise sd.AlignmentError(
                        f"TV-barrier-completion-order: block {block} warp {warp} exits a "
                        f"thread still pending at barrier {key} (seq {seq})")
                complete(key)
            continue
        if e.get("space") == "local":
            # I5 (D14): local memory is outside the HB model (hb_proof.tex Definition
            # "Records"). The T9 collector no longer serializes local records; an older dump
            # still carries them and is replayed as if it did not -- before any monitor check.
            continue
        # TV-record-after-exit (W3): no record of a thread follows its exit.
        lanes_mask = e["sync_mask"] if typ == "syncwarp" else e.get("active_mask", 0)
        if strict and lanes_mask & exited_lanes.get((e["block"], e["warp"]), 0):
            raise sd.AlignmentError(
                f"TV-record-after-exit: block {e['block']} warp {e['warp']} issues a {typ} "
                f"at pc {hex(e['pc'])} (seq {seq}) after its exit")
        if "lanes" not in e:          # T14: a sync record is its lanes' next record
            close_lanes(e["block"], e["warp"], lanes_mask, e["pc"])
        if typ in ("pipeline_commit", "pipeline_wait"):   # T1a: cp.async commit / wait_group N
            for k in range(32):
                if (e["active_mask"] >> k) & 1:
                    t = tid_of(e["block"], e["warp"], k)
                    if typ == "pipeline_commit":
                        async_commit(t)
                    else:
                        async_wait(t, e["groups"])
            continue
        if typ == "syncwarp":
            # syncwarp is genuinely per-warp: join THIS warp's masked lanes now.
            mask = e["sync_mask"]
            tids = [tid_of(e["block"], e["warp"], k) for k in range(32) if (mask >> k) & 1]
            sync_group(tids)
            continue
        if typ == "barrier":
            block, warp = e["block"], e["warp"]
            mask = e["active_mask"]
            key = (block, e["bar_index"])
            arrived = pending_bar[key]
            arrived.update(tid_of(block, warp, k)
                           for k in range(32) if (mask >> k) & 1)
            bar_warps_seen[key].add(warp)
            pending_cnt[key] = e["thread_count"]
            expected = expected_of(key)
            # TV-barrier-overfill: arrivals must never EXCEED the expected participant
            # count. A well-formed instance lands on exactly `expected` and fires; more
            # means a stale/duplicated arrival or a wrong thread_count.
            if strict and expected and len(arrived) > expected:
                raise sd.AlignmentError(
                    f"TV-barrier-overfill: barrier {key} arrived {len(arrived)} > "
                    f"expected {expected}")
            # fire once complete; falsy expected (unknown count, unreachable for a
            # launched kernel) degrades to per-warp so the oracle never stalls.
            if not expected:
                # TV-expected-nonzero-multiwarp: the per-warp fallback (unknown expected)
                # is exactly the pre-fix bug for a multi-warp block. If >1 warp has ever
                # arrived at this static barrier, degrading to per-warp is unsound -> raise.
                if strict and len(bar_warps_seen[key]) > 1:
                    raise sd.AlignmentError(
                        f"TV-expected-nonzero-multiwarp: barrier {key} has "
                        f"{len(bar_warps_seen[key])} warps but expected count is "
                        "unknown (block_thread_count missing) -> per-warp degrade unsound")
                fire(key)
            elif not complete(key):
                # instance still pending: this warp is now blocked at the barrier.
                warp_waiting[(block, warp)] = key
            continue

        space = e["space"]
        # TV-barrier-completion-order: a warp blocked at a pending barrier cannot
        # execute a post-barrier memory access before its instance completes (fires).
        # This is the segmentation property the barrier-instance assembly relies on.
        if strict and (e["block"], e["warp"]) in warp_waiting:
            raise sd.AlignmentError(
                f"TV-barrier-completion-order: block {e['block']} warp {e['warp']} "
                f"issues a post-barrier {typ} at pc {hex(e['pc'])} (seq {seq}) while "
                f"still pending at barrier {warp_waiting[(e['block'], e['warp'])]}")

        pc = e["pc"]
        is_atomic = pc in atom_scope
        kind = "RMW" if is_atomic else "W" if typ == "write" else "R"
        my_coh, my_block = coh_scope.get(pc), e["block"]   # strong scope; None = weak
        is_async = pc in async_pcs
        for lane in e["lanes"]:
            t0 = tid_of(e["block"], e["warp"], lane["lane"])
            if t0 in wins:            # T14: this record closes the lane's RMW window
                close_win(t0, pc)
            t = t0 | ASYNC if is_async else t0
            if is_async:
                async_issue(t0, t)
            addr = lane["addr"]
            loc = loc_of(space, e["block"], addr)
            rec = {"addr": addr, "space": space, "loc_block": e["block"]}

            if is_atomic:
                # Coherence profile Pi (observational): this thread's next atomic index
                # appended to the address's observed atomic order.
                coherence[addr].append((t, atom_idx[t]))
                atom_idx[t] += 1
                # Scoped acquire (trusting gate, I4). The chain continues iff the previous
                # RMW on loc is morally strong with this one (min of the two .STRONG scopes
                # covers both threads: GRID = any block, BLOCK = same block, NONE = never);
                # this is what turns a block-scoped atomic used across blocks into a caught
                # race. Keyed by location, not raw address: shared-memory addresses are
                # per-block offsets, so with >1 block another block's release on the same
                # offset would clobber this block's (spurious atomic race).
                my_scope = atom_scope[pc]
                a2_open(t, loc, my_scope, my_block)           # T14
                rel = released.get(loc)
                chain_ok = False
                if rel is not None:
                    rclk, rblock, rscope, rpd = rel
                    eff = min(my_scope, rscope)
                    chain_ok = eff == sd.GRID or (eff == sd.BLOCK and rblock == my_block)
                    if chain_ok and not gate_on:
                        vc[t] = vc[t].joined(rclk)
                        pd_join(t, rpd)                       # T14
                if gate_on:                   # T12: rel(r) now, the acquire at the close
                    pt = last_pc.get(t0)
                    g_rel = pt is None or pt in gtab[pc][1]
                    gstat["rmw"] += 1
                    gstat["rel0"] += not g_rel
                    last_pc[t0] = pc
                    has_j = chain_ok and rel[0] is not None
                    wins[t][6] = [pc, g_rel, rel[0] if has_j else None,
                                  rel[3] if has_j else None, [], []]
            elif gate_on:
                last_pc[t0] = pc
            clk, sclk = own(t), owns(t)
            gheld = wins[t][6] if is_atomic and gate_on and wins[t][6][2] is not None else None
            check(t, kind, my_coh, pc, loc, rec, gheld)
            if kind == "W" and t & ASYNC:
                # two copies of one thread: PTX orders no two cp.async operations, so they
                # are unordered until a wait completes the first. The agent knows its own
                # copies; the thread knows only those a wait completed.
                mine = buckets[loc].get((kind, my_coh), {}).get(t)
                if mine is not None:
                    conflict(t, *mine, t, pc, "WAW", "DR", rec, observer=t0)
            buckets[loc].setdefault((kind, my_coh), {})[t] = (clk, sclk, pc)
            if is_atomic:
                # I1 (D1): publish the pre-tick clock -- the RMW's own epoch is clk, so a
                # later acquirer is ordered after the RMW but not after t's next accesses --
                # then tick. Overwriting released[loc] equals Algorithm 1's join under the
                # trusting gate (the clock already holds the chain unless it broke).
                st = clus[loc]
                if not gate_on:
                    released[loc] = (VC(vc[t]), my_block, my_scope, VC(pd.get(t, ())))
                    if st.comps is not None and my_scope != sd.NONE:   # T14: its component's
                        c = _comp_of(st.comps, my_scope, my_block)    # join
                        _join_into(c.J, vc[t])
                        _join_into(c.J, pd.get(t, {}))
                else:
                    # T12: Ch_loc is a join; it breaks when r is not ms with the last RMW
                    # (chain_ok False); only a releasing r publishes; the label is always r's
                    ch, chpd = (rel[0], rel[3]) if chain_ok else (None, None)
                    if wins[t][6][1]:
                        ch = VC(vc[t]) if ch is None else ch.joined(vc[t])
                        chpd = VC(pd.get(t, ())) if chpd is None else chpd.joined(pd.get(t, {}))
                        if st.comps is not None and my_scope != sd.NONE:
                            c = _comp_of(st.comps, my_scope, my_block)
                            _join_into(c.J, ch)
                            _join_into(c.J, chpd)
                    released[loc] = (ch, my_block, my_scope, chpd)
                vc[t][t] = clk + 1

    for t in sorted(wins):            # T14: no next record -- the window ends with the kernel
        close_win(t)                  # (T12: q does not exist, acq(r) = 1)

    # TV-barrier-pending-at-end (hb_proof.tex section 1, the fifth monitor check, the runtime
    # form of A3): every open segment completes by the end of the kernel. Only on dumps
    # with exit records (`hb_exits`): without them an early-exit kernel's segments stay
    # open, which is the pre-T3b reading those dumps keep. HbClock records it in
    # tv_violation whatever YOSEMITE_HB_STRICT says; the oracle raises, so like its other
    # checks it is off under YOSEMITE_HB_STRICT=0 (replaying a known-bad trace).
    open_segs = {k: v for k, v in pending_bar.items() if v}
    if strict and trace.get("hb_exits") and open_segs:
        k = min(open_segs)
        raise sd.AlignmentError(
            f"TV-barrier-pending-at-end: {len(open_segs)} barrier segment(s) open at the end "
            f"of the kernel; first: {k}, arrived {len(open_segs[k])} of expected "
            f"{expected_of(k)}")

    # aggregated race records, in first-report order (HbClock emits the same); each carries
    # a2_uncertain, how many of its instances the possible clock orders (T14; DR and SC)
    uniq = [dict(ex, count=n, a2_uncertain=f) for ex, n, f in agg.values()]

    # Coherence profile Pi: per atomic address, the observed atomic order and its hash.
    coherence_profile = {
        hex(addr): {"len": len(seq),
                    "hash": f"{coherence_hash(seq):#018x}",
                    "seq": [[t, i] for t, i in seq]}
        for addr, seq in sorted(coherence.items())
    }

    return {
        "inputs": {"cfg_dot": str(dot_path), "trace_json": str(trace_path)},
        "kernel": {"mangled": mangled, "name": trace["kernel"]["kernel_name"]},
        "atomic_pcs": {hex(pc): sd.SCOPES[s] for pc, s in sorted(atom_scope.items())},
        "races": uniq,
        **({"race_records": sorted(rec_set)} if rec_set is not None else {}),
        **({"a2_records": sorted([*k, n] for k, n in a2_log.items())}
           if a2_log is not None else {}),
        "races_sync_only": [[a, b, n] for (a, b), n in sorted(sync_pairs.items())],
        "gate": "instance" if gate_on else "trusting",
        "coherence_profile": coherence_profile,
        "summary": {"races": len(uniq), "events": len(events),
                    "sc": sum(r["class"] == "SC" for r in uniq),
                    "a2_uncertain": sum(r["a2_uncertain"] for r in uniq),
                    **({"gate": dict(gstat)} if gate_on else {}),
                    "atomic_addrs": len(coherence_profile)},
    }


def render(report):
    atoms = ", ".join(f"{pc}[{sc}]" for pc, sc in report["atomic_pcs"].items())
    lines = [f"kernel: {report['kernel']['name']}",
             f"atomics: {atoms or 'none'}"]
    for r in report["races"]:
        a = f"tid{r['a_tid']}@{hex(r['a_pc']) if r['a_pc'] is not None else 'read'}"
        b = f"tid{r['b_tid']}@{hex(r['b_pc'])}"
        tag = "RACE" if r.get("class", "DR") == "DR" else "STRONG-CONFLICT"
        lines.append(f"{tag} {r['kind']} {r['space']}[{hex(r['addr'])}]  {a}  vs  {b}"
                     f"  ({r['dist']}, x{r['count']})")
    lines.append(f"{report['summary']['races']} race(s) over "
                 f"{report['summary']['events']} events")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("cfg_dot", type=Path)
    ap.add_argument("trace_json", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--strong-ldst", choices=sd.STRONG_LDST_POLICIES,
                    help="which .STRONG loads/stores are strong: 'token' (every one with a "
                         "known scope, T10) or a pre-T10 ablation "
                         "(default: $CUVEIN_STRONG_LDST or 'token')")
    args = ap.parse_args(argv)
    try:
        report = analyze(args.cfg_dot, args.trace_json, strong_ldst=args.strong_ldst)
    except sd.AlignmentError as exc:
        print(f"ALIGNMENT FAILURE: {exc}", file=sys.stderr)
        return 1
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())

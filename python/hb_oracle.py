#!/usr/bin/env python3
"""Full vector-clock happens-before oracle over the hb_events dump.

Exact per-instance *observed-schedule* happens-before, used as the correctness
spec for the analyzer's scalable per-thread epoch engine (roadmap Phase 2). Reads
the kernel CFG (only to classify which PCs are atomics + their scope, reusing
sync_dominance) and the pc_dependency trace JSON produced with YOSEMITE_HB_TRACE=1
(the `hb_events` per-instance stream).

Model: every thread carries a vector clock. Synchronization updates the clocks —
a barrier / masked syncwarp joins its actual participants; an atomic acquires the
value released to its address and republishes. A conflict (same location, >=1
write, different threads) is a RACE iff the two accesses are not ordered by the
resulting happens-before relation and are not both coherent accesses (atomic RMWs or
cuda::atomic loads/stores, see sync_dominance.coherent_scope) whose .STRONG scopes
cover the two threads. No pattern is special-cased: the canary, named barriers,
masked syncwarps and loop-carried handshakes all fall out as a consequence of the
clocks.

A second clock per thread is advanced by barriers/syncwarps ONLY. Its races
(`races_sync_only`, pc pairs with counts) tell the verdict matrix which dynamically
ordered pairs owe their order to schedule-independent barrier joins alone and which
to atomic release/acquire joins (which ignore fences -> stay latent).

This is the exact O(threads) reference; the analyzer's epoch engine must agree
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
    construction as HbEngine::coherence_hash so oracle and engine profiles compare."""
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




def analyze(dot_path, trace_path, strong_ldst=None):
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
    # engine reads the same set from the sidecar's `# async` lines (sd.async_pcs rule);
    # a dump without the engine's hb_async marker keeps the pre-T1a reading.
    async_pcs = sd.dump_async_pcs(eng, trace)
    ASYNC = sd.ASYNC_BIT
    groups = defaultdict(list)        # t -> [(vc, vs) of its agent at each commit], oldest first

    vc = defaultdict(VC)              # tid -> vector clock (barriers + atomic handoffs)
    vs = defaultdict(VC)              # tid -> barrier/syncwarp-ONLY vector clock
    released = {}                     # loc -> (clock, releaser_block, scope)
    last_write = {}                   # loc -> (tid, clock, sync_clock, pc, coh, block)
    last_reads = defaultdict(dict)    # loc -> {tid: (clock, sync_clock, pc, coh, block)}
    races = []                        # list of race records
    sync_pairs = defaultdict(int)     # (pc_lo, pc_hi) -> conflicts unordered by vs

    # Coherence profile Pi (Phase 3, observational — never affects a verdict). The
    # single-trace certificate is per-profile: the observed per-address coherence order
    # of atomics. Record, per address touched by >=1 atomic, the sequence of
    # (tid, that thread's atomic index) in event order, plus a stable hash of it (the
    # SAME FNV-1a the engine emits, so the two profiles are cross-checkable).
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
    block_tc = trace["kernel"].get("block_thread_count")
    pending_bar = defaultdict(set)    # (block, bar_index) -> set of arrived tids
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

    def coherent(c1, b1, c2, b2):
        """Two coherent accesses whose min .STRONG scope covers both threads."""
        if c1 is None or c2 is None:
            return False
        eff = min(c1, c2)
        return eff == sd.GRID or (eff == sd.BLOCK and b1 == b2)

    def conflict(prev_tid, prev_clk, prev_sclk, prev_pc, t, pc, kind, rec, observer=None):
        """One unordered-ness test per clock for a conflicting (prev, current) pair, as
        seen by `observer` (default t; the issuing thread for two copies of its agent)."""
        o = t if observer is None else observer
        if prev_clk > vc[o].get(prev_tid, 0):
            races.append({**rec, "a_tid": prev_tid, "a_pc": prev_pc,
                          "b_tid": t, "b_pc": pc, "kind": kind})
        if prev_sclk > vs[o].get(prev_tid, 0):
            sync_pairs[(min(prev_pc, pc), max(prev_pc, pc))] += 1

    # T1a: the async agent (see HbEngine::async_issue/commit/wait; one-to-one)
    def async_issue(t, ag):
        own(t)
        vc[ag] = vc[ag].joined(vc[t])     # the copy follows t's earlier accesses
        own(ag)
        owns(t)
        vs[ag] = vs[ag].joined(vs[t])
        owns(ag)

    def async_commit(t):
        ag = t | ASYNC
        own(ag), owns(ag)
        groups[t].append((VC(vc[ag]), VC(vs[ag])))
        vc[ag][ag] += 1                   # later copies: a newer epoch than this group
        vs[ag][ag] += 1

    def async_wait(t, n):
        g = groups[t]
        if len(g) <= n:
            return
        done = len(g) - n                 # groups [0, done) are complete
        svc, svs = g[done - 1]            # snapshots only grow
        own(t)
        vc[t] = vc[t].joined(svc)
        owns(t)
        vs[t] = vs[t].joined(svs)
        del g[:done]

    def loc_of(space, block, addr):
        # shared memory is per-block; global/local keyed by absolute address.
        return (space, block, addr) if space == "shared" else (space, addr)

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
            expected = e["thread_count"] or block_tc
            # TV-barrier-overfill: arrivals must never EXCEED the expected participant
            # count. A well-formed instance lands on exactly `expected` and fires; more
            # means a stale/duplicated arrival or a wrong thread_count.
            if strict and expected and len(arrived) > expected:
                raise sd.AlignmentError(
                    f"TV-barrier-overfill: barrier {key} arrived {len(arrived)} > "
                    f"expected {expected}")
            # fire once complete; falsy expected (unknown count, unreachable for a
            # launched kernel) degrades to per-warp so the oracle never stalls.
            if not expected or len(arrived) >= expected:
                # TV-expected-nonzero-multiwarp: the per-warp fallback (unknown expected)
                # is exactly the pre-fix bug for a multi-warp block. If >1 warp has ever
                # arrived at this static barrier, degrading to per-warp is unsound -> raise.
                if strict and not expected and len(bar_warps_seen[key]) > 1:
                    raise sd.AlignmentError(
                        f"TV-expected-nonzero-multiwarp: barrier {key} has "
                        f"{len(bar_warps_seen[key])} warps but expected count is "
                        "unknown (block_thread_count missing) -> per-warp degrade unsound")
                sync_group(sorted(arrived))
                del pending_bar[key]
                for w in {(t >> 5) & 0x1f for t in arrived}:
                    warp_waiting.pop((block, w), None)
            else:
                # instance still pending: this warp is now blocked at the barrier.
                warp_waiting[(block, warp)] = key
            continue

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
        is_write = (typ == "write")
        space = e["space"]
        my_coh, my_block = coh_scope.get(pc), e["block"]
        is_async = pc in async_pcs
        for lane in e["lanes"]:
            t0 = tid_of(e["block"], e["warp"], lane["lane"])
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
                # Scoped acquire-release. The synchronization strength is the min
                # of the two atomics' .STRONG scopes; a release is picked up only
                # if that strength covers the two threads (GRID = any block,
                # BLOCK = same block, NONE = never). This is what turns a
                # block-scoped atomic used across blocks into a caught race.
                # Keyed by location, not raw address: shared-memory addresses are
                # per-block offsets, so with >1 block another block's release on the
                # same offset would clobber this block's (spurious atomic race).
                my_scope = atom_scope[pc]
                rel = released.get(loc)
                if rel is not None:
                    rclk, rblock, rscope = rel
                    eff = min(my_scope, rscope)
                    if eff == sd.GRID or (eff == sd.BLOCK and rblock == my_block):
                        vc[t] = vc[t].joined(rclk)
                # an atomic RMW is a write: it races a prior writer / reader that is
                # neither HB-ordered nor coherent with it — e.g. same-address atomics
                # at a scope too narrow for their distance, or a plain access.
                own(t), owns(t)
                w = last_write.get(loc)
                if w and w[0] != t and not coherent(my_coh, my_block, w[4], w[5]):
                    conflict(w[0], w[1], w[2], w[3], t, pc, "atomic", rec)
                for rt, (rc, rsc, rpc, rcoh, rblk) in last_reads[loc].items():
                    if rt != t and not coherent(my_coh, my_block, rcoh, rblk):
                        conflict(rt, rc, rsc, rpc, t, pc, "WAR", rec)
                vc[t][t] = own(t) + 1
                released[loc] = (VC(vc[t]), my_block, my_scope)
                last_write[loc] = (t, vc[t][t], owns(t), pc, my_coh, my_block)
                last_reads[loc] = {}
                continue

            clk, sclk = own(t), owns(t)
            # conflict with the last writer / concurrent readers not HB-before t
            w = last_write.get(loc)
            if w and not coherent(my_coh, my_block, w[4], w[5]):
                if w[0] != t:
                    conflict(w[0], w[1], w[2], w[3], t, pc, "WAW" if is_write else "RAW", rec)
                elif is_write and t & ASYNC:
                    # two copies of one thread: PTX orders no two cp.async operations, so
                    # they are unordered until a wait completes the first. The agent knows
                    # its own copies; the thread knows only those a wait completed.
                    conflict(w[0], w[1], w[2], w[3], t, pc, "WAW", rec, observer=t0)
            if is_write:
                # the reader pc is kept: a WAR record must name both pcs (a single-pc
                # key mis-attributes the race to every pair sharing it).
                for rt, (rc, rsc, rpc, rcoh, rblk) in last_reads[loc].items():
                    if rt != t and not coherent(my_coh, my_block, rcoh, rblk):
                        conflict(rt, rc, rsc, rpc, t, pc, "WAR", rec)
                last_write[loc] = (t, clk, sclk, pc, my_coh, my_block)
                last_reads[loc] = {}
            else:
                last_reads[loc][t] = (clk, sclk, pc, my_coh, my_block)

    # dedup identical race tuples (same pc pair, tid pair, addr); then report the issuing
    # thread's id for an agent's access with "async" naming the side(s) (as HbEngine emits)
    seen, uniq = set(), []
    for r in races:
        key = (r["addr"], r["a_tid"], r["a_pc"], r["b_tid"], r["b_pc"], r["kind"])
        if key not in seen:
            seen.add(key)
            a, b = r["a_tid"] & ASYNC, r["b_tid"] & ASYNC
            r = dict(r, a_tid=r["a_tid"] & ~ASYNC, b_tid=r["b_tid"] & ~ASYNC)
            if a or b:
                r["async"] = "ab" if a and b else "a" if a else "b"
            uniq.append(r)

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
        "races_sync_only": [[a, b, n] for (a, b), n in sorted(sync_pairs.items())],
        "coherence_profile": coherence_profile,
        "summary": {"races": len(uniq), "events": len(events),
                    "atomic_addrs": len(coherence_profile)},
    }


def render(report):
    atoms = ", ".join(f"{pc}[{sc}]" for pc, sc in report["atomic_pcs"].items())
    lines = [f"kernel: {report['kernel']['name']}",
             f"atomics: {atoms or 'none'}"]
    for r in report["races"]:
        a = f"tid{r['a_tid']}@{hex(r['a_pc']) if r['a_pc'] is not None else 'read'}"
        b = f"tid{r['b_tid']}@{hex(r['b_pc'])}"
        lines.append(f"RACE {r['kind']} {r['space']}[{hex(r['addr'])}]  {a}  vs  {b}")
    lines.append(f"{report['summary']['races']} race(s) over "
                 f"{report['summary']['events']} events")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("cfg_dot", type=Path)
    ap.add_argument("trace_json", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--strong-ldst", choices=sd.STRONG_LDST_POLICIES,
                    help="which .STRONG loads/stores are coherent accesses "
                         "(default: $CUVEIN_STRONG_LDST or 'generic')")
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

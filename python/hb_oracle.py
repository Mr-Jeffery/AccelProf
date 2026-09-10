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
resulting happens-before relation. No pattern is special-cased: the canary, named
barriers, masked syncwarps and loop-carried handshakes all fall out as a
consequence of the clocks.

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


class VC(dict):
    """tid -> logical clock; a missing entry reads 0."""
    def joined(self, other):
        out = VC(self)
        for t, c in other.items():
            if c > out.get(t, 0):
                out[t] = c
        return out




def analyze(dot_path, trace_path):
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

    vc = defaultdict(VC)              # tid -> vector clock
    released = {}                     # addr -> (clock, releaser_block, scope)
    last_write = {}                   # loc -> (tid, clock, pc)
    last_reads = defaultdict(dict)    # loc -> {tid: clock}
    races = []                        # list of race records

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

    def sync_group(tids):
        """Barrier/syncwarp: everyone learns everyone's pre-sync clock (join),
        then each ticks its own component so post-sync accesses are ordered after
        the join but concurrent with each other (two post-barrier writes race)."""
        for t in tids:
            own(t)
        j = VC()
        for t in tids:
            j = j.joined(vc[t])
        for t in tids:
            nv = VC(j)
            nv[t] = nv.get(t, 0) + 1
            vc[t] = nv

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
        for lane in e["lanes"]:
            t = tid_of(e["block"], e["warp"], lane["lane"])
            addr = lane["addr"]
            loc = loc_of(space, e["block"], addr)

            if is_atomic:
                # Scoped acquire-release. The synchronization strength is the min
                # of the two atomics' .STRONG scopes; a release is picked up only
                # if that strength covers the two threads (GRID = any block,
                # BLOCK = same block, NONE = never). This is what turns a
                # block-scoped atomic used across blocks into a caught race.
                my_scope, my_block = atom_scope[pc], e["block"]
                rel = released.get(addr)
                if rel is not None:
                    rclk, rblock, rscope = rel
                    eff = min(my_scope, rscope)
                    if eff == sd.GRID or (eff == sd.BLOCK and rblock == my_block):
                        vc[t] = vc[t].joined(rclk)
                # an atomic RMW is a write: it races a prior writer the scoped
                # acquire did NOT order — e.g. same-address atomics at a scope too
                # narrow for their distance (a coherence race).
                w = last_write.get(loc)
                if w and w[0] != t and w[1] > vc[t].get(w[0], 0):
                    races.append({"addr": addr, "space": space, "loc_block": e["block"],
                                  "a_tid": w[0], "a_pc": w[2], "b_tid": t, "b_pc": pc,
                                  "kind": "atomic"})
                vc[t][t] = own(t) + 1
                released[addr] = (VC(vc[t]), my_block, my_scope)
                last_write[loc] = (t, vc[t][t], pc)
                last_reads[loc] = {}
                continue

            clk = own(t)
            # conflict with the last writer / concurrent readers not HB-before t
            w = last_write.get(loc)
            if w and w[0] != t and w[1] > vc[t].get(w[0], 0):
                races.append({"addr": addr, "space": space, "loc_block": e["block"],
                              "a_tid": w[0], "a_pc": w[2], "b_tid": t, "b_pc": pc,
                              "kind": "WAW" if is_write else "RAW"})
            if is_write:
                for rt, rc in last_reads[loc].items():
                    if rt != t and rc > vc[t].get(rt, 0):
                        races.append({"addr": addr, "space": space, "loc_block": e["block"],
                                      "a_tid": rt, "a_pc": None, "b_tid": t, "b_pc": pc,
                                      "kind": "WAR"})
                last_write[loc] = (t, clk, pc)
                last_reads[loc] = {}
            else:
                last_reads[loc][t] = clk

    # dedup identical race tuples (same pc pair, tid pair, addr)
    seen, uniq = set(), []
    for r in races:
        key = (r["addr"], r["a_tid"], r["a_pc"], r["b_tid"], r["b_pc"], r["kind"])
        if key not in seen:
            seen.add(key)
            uniq.append(r)

    return {
        "inputs": {"cfg_dot": str(dot_path), "trace_json": str(trace_path)},
        "kernel": {"mangled": mangled, "name": trace["kernel"]["kernel_name"]},
        "atomic_pcs": {hex(pc): sd.SCOPES[s] for pc, s in sorted(atom_scope.items())},
        "races": uniq,
        "summary": {"races": len(uniq), "events": len(events)},
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
    args = ap.parse_args(argv)
    try:
        report = analyze(args.cfg_dot, args.trace_json)
    except sd.AlignmentError as exc:
        print(f"ALIGNMENT FAILURE: {exc}", file=sys.stderr)
        return 1
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())

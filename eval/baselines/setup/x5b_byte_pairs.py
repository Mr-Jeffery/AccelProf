#!/usr/bin/env python3
"""X5 byte pairs: why the barrier-only clock leaves X5's `other` pairs unlisted (read only).

  x5b_byte_pairs.py --pairs <X5 barrier_ordered_pairs.csv> --out <jsonl>

For every row of X5's per-pair csv whose bin is `other` (65 pairs x 2 modes):

  static  opcodes of u (ancient) and v (current); the NOP and BAR/WARPSYNC/DEPBAR/LDGDEPBAR
          instructions of the kernel that lie on EVERY instruction-level CFG path u -> v (a cut:
          v is not reachable from u once that pc is removed; X5's CfgBinner.ins_reach); the bin
          X5's CfgBinner gives the pair when the cutting NOPs are read as `WARPSYNC 0xffffffff`;
          R1's strength (HBGraph.ordered) on the CFG as printed and with that reading.
  x1      every launch of the kernel in the X1 recording X5 binned (<store>/<id>/<mode>): the
          PCDG edge u -> v and its distance buckets; whether hb_races, hb_races_sync_only and
          hb_sync_pass list the pc pair; the shared-memory pc pairs hb_races does list; the
          clock-base shape in hb_stats (a base is made only by a barrier or syncwarp join).
  events  the first store of EVENT_STORES that has hb_events for the same program and mode and
          the same dot file (md5): per launch, the sync records at the cut pcs; whether the
          records at u and v touch the same byte (and how many (block, word) pairs they share
          only through different bytes); every conflicting instance of the pc pair checked from
          the records for a syncwarp between its two accesses (instance_check); hb_oracle.analyze
          -- the specification HbClock matches bit for bit -- on the trace as recorded and with
          the sync records at the cut pcs removed: is the pc pair in races (vector clock) /
          races_sync_only (barrier-only clock), and which races_sync_only pairs end at u or v?

One JSON line per csv row goes to --out. Edited traces go to $TMPDIR and are deleted; the stores
are only read. Runs on a compute node (BeeGFS).
"""
import argparse
import bisect
import collections
import csv
import glob
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import x5_common as xc                       # noqa: E402  (sets CUVEIN_HOME, sys.path)
from x5_common import sd                     # noqa: E402
import barrier_ordered_bins as bob           # noqa: E402
import hb_oracle as ho                       # noqa: E402

ROOT = "/mnt/beegfs/fzheng4/cuvein_traces"
# stores recorded before no-dump mode became the default (they keep hb_events), newest first
EVENT_STORES = ("t16-certain", "t16-recorded-exits", "t16-certain-exits", "t12-after",
                "t10-after", "t9-after", "evcand", "t1a-p56")
SYNC_TYPES = ("syncwarp", "barrier", "pipeline_wait", "pipeline_commit")
SYNC_OPS = ("BAR", "WARPSYNC", "DEPBAR", "LDGDEPBAR")


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()[:12]


def kernel_jsons(d):
    return sorted(glob.glob(os.path.join(d, "kernel_*.json")),
                  key=lambda p: int(p.rsplit("_", 1)[1].split(".")[0]))


def launches(d, kernels, mangled):
    out = []
    for kj in kernel_jsons(d):
        t = json.loads(Path(kj).read_text())
        try:
            m = sd.select_kernel(kernels, t["kernel"]["kernel_name"])
        except sd.AlignmentError:
            continue
        if m == mangled:
            out.append((kj, t))
    return out


def pair_in(lst, key, a="a_pc", b="b_pc"):
    if lst is None:
        return None
    for r in lst:
        k = frozenset((r[a], r[b])) if isinstance(r, dict) else frozenset(r[:2])
        if k == key:
            return True
    return False


def static_facts(dot, mangled, u, v, race_type, observed, parsed):
    blocks, edges, entry = parsed[dot][mangled]
    eng = sd.HBGraph(blocks, edges, entry)
    ops = bob.sync_operands(dot, mangled)
    binner = bob.CfgBinner(eng, ops)
    op = eng.pc_opcode
    assert v in binner.ins_reach(u), (dot, mangled, hex(u), hex(v))

    def cuts(pc):
        return pc not in (u, v) and v not in binner.ins_reach(u, pc)
    nops = sorted(pc for pc, o in op.items() if o.split(".")[0] == "NOP")
    syncs = sorted(pc for pc, o in op.items() if o.split(".")[0] in SYNC_OPS)
    cut_nops = [pc for pc in nops if cuts(pc)]
    cut_syncs = [pc for pc in syncs if cuts(pc)]
    anc_read, cur_read = {"RAW": (False, True), "WAW": (False, False),
                          "WAR": (True, False)}[race_type]
    r1 = eng.ordered(v, u, observed, cur_read, anc_read)
    out = {"op_u": op[u], "op_v": op[v], "nops": [hex(p) for p in nops],
           "cut_nops": [hex(p) for p in cut_nops],
           "cut_syncs": [f"{p:#x} {op[p]}" for p in cut_syncs],
           "kernel_bar_warpsync": [f"{p:#x} {op[p]}" for p in syncs
                                   if op[p].split(".")[0] in ("BAR", "WARPSYNC")],
           "x5_bin": binner.bin(u, v)[0],
           "r1_strength": sd.SCOPES[r1["strength"]], "r1_syncs": r1["syncs"]}
    if cut_nops:
        mblocks = {b: [(pc, "WARPSYNC" if pc in cut_nops else o) for pc, o in ins]
                   for b, ins in blocks.items()}
        meng = sd.HBGraph(mblocks, edges, entry)
        mops = dict(ops)
        mops.update({pc: ("WARPSYNC", ["0xffffffff"]) for pc in cut_nops})
        rb = bob.CfgBinner(meng, mops).bin(u, v)
        mr1 = meng.ordered(v, u, observed, cur_read, anc_read)
        out.update({"rebin_nop_as_warpsync": rb[0], "rebin_detail": rb[1],
                    "r1_strength_nop_as_warpsync": sd.SCOPES[mr1["strength"]],
                    "r1_syncs_nop_as_warpsync": [hex(p) if isinstance(p, int) else p
                                                 for p in mr1["syncs"]]})
    return out, cut_nops + cut_syncs


def x1_facts(ls, u, v, key):
    agg = collections.Counter()
    shared_pairs = set()
    bases = collections.Counter()
    dist = collections.Counter()
    for kj, t in ls:
        agg["launches"] += 1
        ed = [e for e in t.get("edges", []) if e.get("ancient_pc") == u
              and e["current_pc"] == v and not e.get("cold_miss")]
        if ed:
            agg["edge_launches"] += 1
            for k, n in ed[0]["dist"].items():
                dist[k] += n
        for name, lst, a, b in (("hb_races", t.get("hb_races"), "a_pc", "b_pc"),
                                ("hb_races_sync_only", t.get("hb_races_sync_only"), 0, 1),
                                ("hb_sync_pass", t.get("hb_sync_pass"), 0, 1)):
            got = pair_in(lst, key, a, b)
            agg[f"{name}:{'absent' if got is None else got}"] += 1
        for r in t.get("hb_races") or ():
            if r.get("space") == "shared":
                shared_pairs.add((hex(r["a_pc"]), hex(r["b_pc"]), r["kind"], r["dist"]))
        hc = t.get("hb_stats", {}).get("hb_clock", {})
        vc, vs = hc.get("vc", {}), hc.get("vs", {})
        bases[(vc.get("bases"), vc.get("max_base"), vs.get("unique_bases"),
               hc.get("pending_barriers", {}).get("instances"))] += 1
    return {"counts": dict(agg), "edge_dist": dict(dist),
            "shared_race_pairs": sorted(shared_pairs),
            "hb_stats_vc_bases_maxbase_vs_bases_pending": [[list(k), n] for k, n in bases.items()]}


def oracle_pair(dot, kj, key):
    """-> (pair in races, pair in races_sync_only, the races_sync_only pc pairs with an end at u
    or v as 'a-b' strings)."""
    try:
        rep = ho.analyze(dot, kj)
    except sd.AlignmentError as e:                  # a TV check fired: reported, not hidden
        return (f"error:{str(e)[:120]}",) * 2 + ((),)
    touch = tuple(sorted(f"{a:#x}-{b:#x}" for a, b, _ in rep["races_sync_only"]
                         if a in key or b in key))
    return (pair_in(rep["races"], key), pair_in(rep["races_sync_only"], key), touch)


def instance_check(ev, u, v):
    """Every conflicting instance of the pc pair in one launch, straight from the records: an
    access at u by lane a, a later access at v by lane b != a, same block, same byte address
    (X5's `other` rows are WAW or RAW, so the access at u is a write). Taken for a's LATEST access
    at u before the access at v: a's earlier ones precede it in a's program order, so whatever
    orders the latest orders them. Same warp: is there a syncwarp record of that warp whose
    sync_mask holds a and b, strictly between the two records in trace (seq) order? Different
    warps: counted apart, with the number of barrier records in the launch."""
    ev = sorted(ev, key=lambda e: e["seq"])
    sw = collections.defaultdict(list)              # (block, warp) -> [(seq, mask)], seq order
    c = collections.Counter()
    for e in ev:
        if e.get("type") == "syncwarp":
            sw[(e["block"], e["warp"])].append((e["seq"], e["sync_mask"]))
        elif e.get("type") == "barrier":
            c["barrier_records"] += 1
    last_u = {}                                     # (block, addr) -> {(warp, lane): seq}
    for e in ev:
        if e.get("type") not in ("read", "write", "atomic"):
            continue
        if e["pc"] == u:
            for ln in e["lanes"]:
                last_u.setdefault((e["block"], ln["addr"]), {})[(e["warp"], ln["lane"])] = e["seq"]
        elif e["pc"] == v:
            for ln in e["lanes"]:
                b = ln["lane"]
                for (w, a), s0 in last_u.get((e["block"], ln["addr"]), {}).items():
                    if (w, a) == (e["warp"], b):
                        c["same_thread"] += 1
                        continue
                    if w != e["warp"]:
                        c["cross_warp"] += 1
                        continue
                    lst = sw[(e["block"], w)]
                    i = bisect.bisect_right(lst, (s0, 1 << 62))
                    ok = False
                    while i < len(lst) and lst[i][0] < e["seq"]:
                        if (lst[i][1] >> a) & 1 and (lst[i][1] >> b) & 1:
                            ok = True
                            break
                        i += 1
                    c["same_warp_syncwarp_between" if ok else "same_warp_NO_syncwarp_between"] += 1
    return c


def replay(dot, t, events, key, tmpdir):
    """hb_oracle.analyze on a copy of launch t whose hb_events are `events` (written to tmpdir)."""
    t2 = dict(t)
    t2["hb_events"] = events
    fd, path = tempfile.mkstemp(suffix=".json", dir=tmpdir)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(t2, f)
        return oracle_pair(dot, path, key)
    finally:
        os.unlink(path)


def event_facts(dot, ls, u, v, key, cut_pcs, shared_only=False):
    """shared_only: every oracle replay drops the trace's global-memory records first. The
    barrier-only clock (races_sync_only) takes no atomic join and a shared location's buckets
    hold only shared records, so its answer on a shared pc pair is unchanged; the vector clock
    then lacks the (ATOM) joins, so its `races` answer is reported but is not HbClock's. Used where
    the full replay exceeds node memory (the oracle's clocks grow with the atomic chains)."""
    agg = collections.Counter()
    census = collections.Counter()
    masks = collections.defaultdict(set)
    sizes = set()
    variants = [tuple(cut_pcs)] + ([(p,) for p in cut_pcs] if len(cut_pcs) > 1 else [])
    drop = {var: collections.Counter() for var in variants}
    touch = {var: collections.Counter() for var in [()] + variants}   # () = as recorded
    inst = collections.Counter()
    tmpdir = os.environ.get("TMPDIR", "/tmp")
    for kj, t in ls:
        ev = t["hb_events"]
        if shared_only:
            ev = [e for e in ev if e.get("space") != "global"]
        agg["launches"] += 1
        ic = instance_check(ev, u, v)
        inst.update(ic)
        inst["launches_with_an_instance"] += any(
            ic[k] for k in ("same_warp_syncwarp_between", "same_warp_NO_syncwarp_between",
                            "cross_warp"))
        bu, bv = set(), set()
        for e in ev:
            ty, pc = e.get("type"), e.get("pc")
            if ty in SYNC_TYPES and pc in cut_pcs:
                census[(hex(pc), ty)] += 1
                masks[(hex(pc), ty)].add(e.get("sync_mask", e.get("active_mask")))
            if pc in (u, v) and ty in ("read", "write", "atomic"):
                sizes.add(e.get("size"))
                tgt = bu if pc == u else bv
                tgt.update((e["block"], ln["addr"]) for ln in e["lanes"])
        same = bu & bv
        words_same_byte = {(b, a >> 2) for b, a in same}
        words_both = {(b, a >> 2) for b, a in bu} & {(b, a >> 2) for b, a in bv}
        agg["same_byte_launches"] += bool(same)
        agg["words_shared_only_by_different_bytes"] += len(words_both - words_same_byte)
        r, s, tp = replay(dot, t, ev, key, tmpdir) if shared_only else oracle_pair(dot, kj, key)
        agg[f"oracle_races:{r}"] += 1
        agg[f"oracle_sync_only:{s}"] += 1
        touch[()].update(tp)
        for var in variants:
            r2, s2, tp2 = replay(dot, t, [e for e in ev if not (e.get("type") in SYNC_TYPES
                                                               and e.get("pc") in var)], key, tmpdir)
            drop[var][f"races:{r2}"] += 1
            drop[var][f"sync_only:{s2}"] += 1
            touch[var].update(tp2)
    return {"shared_only": shared_only,
            "instances": dict(inst),
            "sync_only_pairs_at_u_or_v_launches": {
                ("recorded" if not var else "removed " + "+".join(hex(p) for p in var)): dict(c)
                for var, c in touch.items()},
            "counts": dict(agg), "access_sizes": sorted(x for x in sizes if x is not None),
            "sync_records_at_cut_pcs": {f"{pc} {ty}": n for (pc, ty), n in sorted(census.items())},
            "sync_masks_at_cut_pcs": {f"{pc} {ty}": sorted(f"{m:#x}" for m in ms)
                                      for (pc, ty), ms in sorted(masks.items())},
            "oracle_with_sync_records_removed": {
                "+".join(hex(p) for p in var): dict(c) for var, c in drop.items()}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shard", default="0/1", help="i/n: rows i, i+n, i+2n, ... only")
    ap.add_argument("--rows", help="comma-separated row indices (instead of --shard)")
    ap.add_argument("--shared-only", action="store_true",
                    help="oracle replays without the global-memory records (event_facts)")
    a = ap.parse_args()
    rows = [r for r in csv.DictReader(open(a.pairs)) if r["bin"] == "other"]
    si, sn = map(int, a.shard.split("/"))
    print(f"{len(rows)} rows in the `other` bin; shard {si}/{sn} rows {a.rows} "
          f"shared_only {a.shared_only}", flush=True)
    rows = [rows[int(i)] for i in a.rows.split(",")] if a.rows else rows[si::sn]
    parsed = {}
    with open(a.out, "w") as out:
        for r in rows:
            dotbase, mangled = r["kernel"].split("::", 1)
            u, v = int(r["anc_pc"], 16), int(r["cur_pc"], 16)
            key = frozenset((u, v))
            dot = f"{ROOT}/{r['store']}/{r['id']}/dots/{dotbase}"
            if dot not in parsed:
                parsed[dot] = sd.parse_dot(dot)
            kernels = parsed[dot]
            x1 = launches(f"{ROOT}/{r['store']}/{r['id']}/{r['mode']}", kernels, mangled)
            obs = sd.NONE
            for _, t in x1:
                for e in t.get("edges", []):
                    if e.get("ancient_pc") == u and e["current_pc"] == v and not e.get("cold_miss"):
                        obs = max(obs, sd._observed(e.get("dist", {}))[0])
            st, cut_pcs = static_facts(dot, mangled, u, v, r["race_type"], obs, parsed)
            rec = {"suite": r["suite"], "id": r["id"], "mode": r["mode"], "store": r["store"],
                   "kernel": r["kernel"], "u": r["anc_pc"], "v": r["cur_pc"],
                   "race_type": r["race_type"], "x5_detail": r["detail"],
                   "x1_dot_md5": md5(dot), "observed": sd.SCOPES[obs], "static": st,
                   "x1": x1_facts(x1, u, v, key)}
            # a kernel with cp.async: the store's dumps must carry X1's hb_async marker, which
            # decides whether the oracle models an LDGSTS as the issuing thread's async agent
            # (sync_dominance.dump_async_pcs); without it the copy replays as a plain write
            ops = [o for ins in kernels[mangled][0].values() for _, o in ins]
            x1_async = sorted({str(t.get("hb_async")) for _, t in x1}) \
                if any(o.split(".")[0] == "LDGSTS" for o in ops) else None
            rec["x1_hb_async"] = x1_async
            ev_store = None
            for s in EVENT_STORES:
                d = f"{ROOT}/{s}/{r['id']}"
                dd = f"{d}/dots/{dotbase}"
                if not os.path.exists(dd) or md5(dd) != rec["x1_dot_md5"]:
                    continue
                ls = launches(f"{d}/{r['mode']}", kernels, mangled)
                if x1_async is not None and \
                        sorted({str(t.get("hb_async")) for _, t in ls}) != x1_async:
                    rec.setdefault("events_stores_skipped_hb_async", []).append(s)
                    continue
                if ls and all(t.get("hb_events") for _, t in ls):
                    ev_store = s
                    rec["events_store"] = s
                    rec["events"] = event_facts(dot, ls, u, v, key, cut_pcs, a.shared_only)
                    break
            if ev_store is None:
                rec["events_store"] = None
            out.write(json.dumps(rec) + "\n")
            out.flush()
            e = rec.get("events", {})
            print(f"{r['id'][:70]:70s} {r['mode'][:6]} {r['anc_pc']}->{r['cur_pc']} "
                  f"cut={st['cut_nops'] + st['cut_syncs']} x1={rec['x1']['counts']} "
                  f"ev={ev_store} {e.get('sync_records_at_cut_pcs')} "
                  f"{e.get('counts')} {e.get('oracle_with_sync_records_removed')}", flush=True)


if __name__ == "__main__":
    main()

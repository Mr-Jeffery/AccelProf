#!/usr/bin/env python3
"""Host-level happens-before for host copies/sets and cross-stream kernels (T2 prototype;
the model is design/host_memcpy_model.md).

With YOSEMITE_HB_HOST_MEMCPY=1 the collector reports every host-side operation that orders
or touches device memory outside a kernel, and pc_dependency_analysis logs them in API order
to <dump>/host_ops.json, each launch tied to its kernel_<id>.json. `races(dump_dir)` replays
that log with vector clocks over streams plus the host's knowledge C_H (§2.1 of the model),
takes each monitored kernel's global-memory footprint from its hb_events, and returns every
pair of operations that access a common address, at least one writing, with neither ordered
before the other. It needs no GPU; both modes use it (a copy has no pc, so neither the static
leg nor the in-kernel engine is involved).

    python3 host_hb.py <dump dir>            # summary
    python3 host_hb.py <dump dir> --json     # the race records

Two readings of the synchronous API calls (design/host_memcpy_model.md §2.2): "spec" (the
verdict) follows the CUDA Runtime's documented synchronization -- a synchronous
`cudaMemcpy` from pageable host memory may return before its DMA completes, a synchronous
`cudaMemset` of device memory is asynchronous to the host, and non-blocking streams never
wait for the legacy stream; "practical" treats every synchronous copy/set as complete when
it returns. A race found under "spec" but not under "practical" is tagged spec_only.
"""
import argparse
import json
import os
import sys

H2H, H2D, D2H, D2D = 1, 2, 3, 4        # Sanitizer_MemcpyDirection
CU_STREAM_NON_BLOCKING = 0x1
UNKNOWN_FLAGS = 0xFFFFFFFF
LEGACY_PTRS = (0, 1)                    # NULL / cudaStreamLegacy as the op's CUstream
ACCESSING = ("memcpy", "memset", "launch")


def _join(a, b):
    out = dict(a)
    for k, v in b.items():
        if v > out.get(k, 0):
            out[k] = v
    return out


def _merge(ivs):
    """[(lo, hi)] -> sorted disjoint [(lo, hi)] (half-open)."""
    out = []
    for lo, hi in sorted(ivs):
        if out and lo <= out[-1][1]:
            if hi > out[-1][1]:
                out[-1] = (out[-1][0], hi)
        else:
            out.append((lo, hi))
    return out


def _overlap(a, b):
    """first address in both sorted disjoint interval lists, or None."""
    i = j = 0
    while i < len(a) and j < len(b):
        lo, hi = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
        if lo < hi:
            return lo
        if a[i][1] <= b[j][1]:
            i += 1
        else:
            j += 1
    return None


def _rows(base, nbytes, width, height, depth, pitch):
    """ranges of a copy/set side: height*depth rows of `width` bytes at `pitch` (2D/3D; the
    slice pitch is taken as pitch*height), else one [base, base+nbytes)."""
    rows = max(height, 1) * max(depth, 1)
    if rows > 1 and width and pitch:
        return _merge([(base + r * pitch, base + r * pitch + width) for r in range(rows)])
    return [(base, base + nbytes)] if nbytes else []


def kernel_footprint(kernel_json):
    """-> (writes, reads) sorted disjoint global-address intervals of one kernel dump, or
    None if it has no hb_events (not an HB trace). Atomics count as writes."""
    trace = json.loads(open(kernel_json).read())
    events = trace.get("hb_events")
    if events is None:
        return None
    w, r = [], []
    for e in events:
        if e.get("space") != "global" or e.get("type") not in ("read", "write", "atomic"):
            continue
        size = e.get("size") or 1
        dst = r if e["type"] == "read" else w
        for ln in e.get("lanes", ()):
            dst.append((ln["addr"], ln["addr"] + size))
    return _merge(w), _merge(r)


def _attribute(kernel_json, lo, hi, want_write):
    """first global access of the kernel overlapping [lo, hi) of the wanted kind -> (pc, tid)."""
    trace = json.loads(open(kernel_json).read())
    for e in sorted(trace.get("hb_events") or (), key=lambda e: e["seq"]):
        if e.get("space") != "global" or e.get("type") not in ("read", "write", "atomic"):
            continue
        if (e["type"] != "read") != want_write:
            continue
        size = e.get("size") or 1
        for ln in e.get("lanes", ()):
            if ln["addr"] < hi and ln["addr"] + size > lo:
                return e["pc"], (e["block"] << 10) | (e["warp"] << 5) | ln["lane"]
    return None, None


class _Op:
    __slots__ = ("rec", "seq", "kind", "stream", "index", "start", "W", "R", "kjson", "note")

    def __init__(self, rec):
        self.rec, self.seq, self.kind = rec, rec["seq"], rec["kind"]
        self.stream = self.index = self.start = None
        self.W = self.R = None
        self.kjson = self.note = None


def replay(ops, dump_dir, sync_api="spec", fp_cache=None):
    """-> (accessing ops with clocks and footprints, diagnostics). Implements §2.1-2.2;
    sync_api "practical" makes every synchronous copy/set block the host (module doc)."""
    fp_cache = {} if fp_cache is None else fp_cache
    flags, C, CH, n, clk_ev, pinned = {}, {}, {}, {}, {}, []
    diag = {"unmonitored_launches": 0, "launches_without_dump": 0, "launches_without_events": 0}

    def sid(rec):
        return rec["stream"] or ("ptr", rec.get("stream_ptr", 0))

    legacy = {}                                  # stream id -> is the legacy default stream

    def is_legacy(s):
        return legacy.get(s, False)

    def blocking(s):
        f = flags.get(s, UNKNOWN_FLAGS)
        return not is_legacy(s) and (f == UNKNOWN_FLAGS or not f & CU_STREAM_NON_BLOCKING)

    def issue(rec):
        s = sid(rec)
        legacy.setdefault(s, rec.get("stream_ptr", 0) in LEGACY_PTRS)
        start = _join(C.get(s, {}), CH)
        if is_legacy(s):         # waits for all earlier work in blocking streams
            for b in list(C):
                if b != s and blocking(b):
                    start = _join(start, C[b])
        elif blocking(s):        # waits for all earlier work in the legacy stream
            for b in list(C):
                if b != s and is_legacy(b):
                    start = _join(start, C[b])
        n[s] = n.get(s, 0) + 1
        C[s] = dict(start)
        C[s][s] = n[s]
        return s, n[s], start

    def is_pinned(addr):
        return any(lo <= addr < hi for lo, hi in pinned)

    out = []
    for rec in ops:
        k = rec["kind"]
        if k == "stream_create":
            flags[sid(rec)] = rec.get("flags", UNKNOWN_FLAGS)
        elif k == "host_alloc":
            pinned.append((rec["addr"], rec["addr"] + rec["size"]))
        elif k == "host_free":
            pinned = [(lo, hi) for lo, hi in pinned if lo != rec["addr"]]
        elif k == "event_record":
            s, _, _ = issue(rec)
            clk_ev[rec["event"]] = _join(C[s], CH)
        elif k == "stream_wait":
            s = sid(rec)
            legacy.setdefault(s, rec.get("stream_ptr", 0) in LEGACY_PTRS)
            C[s] = _join(C.get(s, {}), clk_ev.get(rec["event"], {}))
        elif k == "stream_sync":
            CH = _join(CH, C.get(sid(rec), {}))
        elif k == "event_sync":
            CH = _join(CH, clk_ev.get(rec["event"], {}))
        elif k == "ctx_sync":
            for c in C.values():
                CH = _join(CH, c)
        elif k in ACCESSING:
            op = _Op(rec)
            op.stream, op.index, op.start = issue(rec)
            if k == "memcpy":
                op.R = _rows(rec["src"], rec["size"], rec.get("width", 0), rec.get("height", 0),
                             rec.get("depth", 0), rec.get("src_pitch", 0))
                op.W = _rows(rec["dst"], rec["size"], rec.get("width", 0), rec.get("height", 0),
                             rec.get("depth", 0), rec.get("dst_pitch", 0))
                d = rec.get("direction", 0)
                blocking_copy = not rec.get("is_async") and (
                    sync_api == "practical" or d in (D2H, H2H) or (d == H2D and is_pinned(rec["src"])))
                if blocking_copy:                # §2.2: the host waits for completion
                    CH = _join(CH, C[op.stream])
            elif k == "memset":
                op.W = _rows(rec["dst"], rec.get("width", 0) * max(rec.get("height", 0), 1),
                             rec.get("width", 0), rec.get("height", 0), 0, rec.get("dst_pitch", 0))
                op.R = []
                if sync_api == "practical" and not rec.get("is_async"):
                    CH = _join(CH, C[op.stream])
            else:                                # launch
                kid = rec.get("kernel_id")
                if not rec.get("monitored") or kid is None:
                    diag["unmonitored_launches"] += 1
                    op.note = "unmonitored"
                else:
                    kj = os.path.join(dump_dir, f"kernel_{kid}.json")
                    if not os.path.exists(kj):
                        diag["launches_without_dump"] += 1
                        op.note = "no-dump"
                    else:
                        if kj not in fp_cache:
                            fp_cache[kj] = kernel_footprint(kj)
                        fp = fp_cache[kj]
                        if fp is None:
                            diag["launches_without_events"] += 1
                            op.note = "no-hb_events"
                        else:
                            op.W, op.R = fp
                            op.kjson = kj
            out.append(op)
    return out, diag


def _desc(op):
    d = {"seq": op.seq, "kind": op.kind, "stream": op.stream if not isinstance(op.stream, tuple)
         else f"ptr:{op.stream[1]}", "stream_index": op.index}
    r = op.rec
    if op.kind == "memcpy":
        d.update(direction={H2H: "H2H", H2D: "H2D", D2H: "D2H", D2D: "D2D"}.get(r.get("direction"), "?"),
                 is_async=bool(r.get("is_async")), src=r["src"], dst=r["dst"], size=r["size"])
    elif op.kind == "memset":
        d.update(dst=r["dst"], width=r.get("width"), height=r.get("height"))
    else:
        d.update(kernel_id=r.get("kernel_id"), kernel=r.get("kernel"))
    return d


def _pairs(acc):
    """-> [(x, y, race_type, first address)] over the unordered accessing pairs."""
    out = []
    for j, y in enumerate(acc):
        if y.W is None:
            continue
        for x in acc[:j]:
            if x.W is None or x.stream == y.stream:        # same stream: FIFO-ordered
                continue
            if y.start.get(x.stream, 0) >= x.index:        # x happens before y
                continue
            for rtype, a, b in (("WAW", x.W, y.W), ("RAW", x.W, y.R), ("WAR", x.R, y.W)):
                addr = _overlap(a, b)
                if addr is not None:
                    out.append((x, y, rtype, addr))
    return out


def races(dump_dir, host_ops=None):
    """-> {"races": [...], "diagnostics": {...}} for the dump directory (host_ops.json), or
    None when there is no host operation log. Races are the "spec" reading's; each carries
    spec_only = it disappears when synchronous copies/sets complete on return."""
    path = host_ops or os.path.join(dump_dir, "host_ops.json")
    if not os.path.exists(path):
        return None
    ops = json.loads(open(path).read())["host_ops"]
    cache = {}
    acc, diag = replay(ops, dump_dir, "spec", cache)
    practical = {(x.seq, y.seq, t) for x, y, t, _ in _pairs(replay(ops, dump_dir, "practical", cache)[0])}
    found = []
    for x, y, rtype, addr in _pairs(acc):
        rec = {"race_type": rtype, "addr": addr, "a": _desc(x), "b": _desc(y),
               "spec_only": (x.seq, y.seq, rtype) not in practical}
        for side, op, wants_write in (("a", x, rtype != "WAR"), ("b", y, rtype != "RAW")):
            if op.kjson:
                pc, tid = _attribute(op.kjson, addr, addr + 1, wants_write)
                rec[f"{side}_pc"], rec[f"{side}_tid"] = pc, tid
        found.append(rec)
    diag["spec_only"] = sum(r["spec_only"] for r in found)
    diag["accessing_ops"] = len(acc)
    diag["host_ops"] = len(ops)
    return {"races": found, "diagnostics": diag}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dump_dir")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    res = races(a.dump_dir)
    if res is None:
        print(f"{a.dump_dir}: no host_ops.json")
        return 1
    if a.json:
        print(json.dumps(res, indent=1))
        return 0
    print(f"{a.dump_dir}: {res['diagnostics']}")
    for r in res["races"]:
        def lab(d, pc):
            if d["kind"] == "launch":
                return f"kernel {d.get('kernel_id')} ({d.get('kernel')}) @pc {hex(pc) if pc is not None else '?'}"
            return f"{d['kind']} {d.get('direction', '')} #{d['seq']}"
        print(f"  {r['race_type']}{' (spec only)' if r['spec_only'] else ''} at {hex(r['addr'])}: {lab(r['a'], r.get('a_pc'))} "
              f"[stream {r['a']['stream']}] vs {lab(r['b'], r.get('b_pc'))} [stream {r['b']['stream']}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())

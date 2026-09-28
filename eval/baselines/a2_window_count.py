#!/usr/bin/env python3
"""T14 (CLAUDE.md C/T14; design/a2_flag.md): A2 in the tables -- the offline RMW window count
over the kept dumps and the re-score with the a2_uncertain flag. No GPU; BeeGFS is mounted on
the compute nodes only, so `count` and `rescore` run on `normal` nodes (setup/p_t14_*.sh).

An RMW's window is [its record, its thread's next record) in (seq, lane) order; a thread with no
next record keeps it open to the end of the kernel. Two RMWs on one location overlap when the
later one is recorded inside the earlier one's window (T13's definition, eval/NVBIT_SPIKE.md
section 4). Local records are no records (D14); seq is not assumed contiguous (pre-T3b dumps
have gaps where exits were dropped).

  count    --shard k/n [--store evcand]: per program and mode dump (vector-clock and
           scalar-clock where present): RMWs, same-location RMW pairs from different warps,
           how many overlap, how many of those lie on locations whose RMWs release or acquire
           (an RMW whose thread's previous or next record is a plain access to another
           location), same-warp overlaps, overlaps whose earlier window is open-ended, the
           order-uncertain successor edges of the brief, and the clusters (multi, and multi
           with a pair of members that are not morally strong) -> OUT/count/<id>.json.
  rescore  --shard k/n: every vector-clock kernel dump of T9's selection
           (eval/results/t9-rescore/selection.json) through this checkout's hb_oracle ->
           the store t14-after (hb_races with a2_uncertain, "hb_a2": 1; everything else
           symlinked); per kernel: DR records / instances / flagged, and whether the instance
           counts per (pc pair, kind, class, space) and the second clock equal T9's
           re-oracled dump (t9-after, record-level; compared up to 1 GB)
           -> OUT/rescore/<id>.json.
  t9keys   (normal node) for the re-scored kernels whose instance counts differ from T9's
           dump: same keys, same second clock, T9's count never above this one?
  tables   (login node) the per-suite tables of both, the verdict comparison of the two
           `parallel.py analyze` runs (per program and per row), -> eval/results/t14-a2/
           A2_TABLES.md + CSVs.
  handoffs --dots D.. -- K..: the Sanitizer's own inversion rate on the race-free lock of
           python/testdata/lock_contention_a2.cu, and engine == oracle on those traces
           (setup/t14_handoffs.sh runs it on a GPU node).
"""
import argparse
import csv
import glob
import json
import os
import re
import resource
import shutil
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, f"{APH}/python")
sys.path.insert(0, HERE)
import hb_modes  # noqa: E402

VC, SC = hb_modes.VECTOR_CLOCK, hb_modes.SCALAR_CLOCK
USER = os.environ.get("USER", "fzheng4")
STORES = f"/mnt/beegfs/{USER}/cuvein_traces"
OUT = f"/mnt/beegfs/{USER}/t14-a2"
AFTER = f"{STORES}/t14-after"
T9_AFTER = f"{STORES}/t9-after"
T9_SELECTION = f"{APH}/eval/results/t9-rescore/selection.json"
RES = f"{APH}/eval/results/t14-a2"


# ---------------------------------------------------------------- reading a dump

def read_dump(path):
    """-> (kernel dict, events list in seq order, marker dict). A collector dump has one
    hb_events record per line and is read line by line; anything else is parsed whole."""
    import orjson
    with open(path, "rb") as f:
        head = []
        for line in f:
            if line.startswith(b'  "nodes": [') or line.startswith(b'  "hb_events": ['):
                break
            head.append(line)
        else:
            line = b""
        try:
            header = orjson.loads(b"".join(head).rstrip().rstrip(b",") + b"}")
        except orjson.JSONDecodeError:
            header = None
        if header is None or "kernel" not in header:        # not the collector's layout
            f.seek(0)
            t = orjson.loads(f.read())
            ev = sorted(t.get("hb_events") or (), key=lambda e: e["seq"])
            return t.get("kernel", {}), ev, {k: t.get(k) for k in ("hb_exits", "hb_async")}
        while line and not line.startswith(b'  "hb_events": ['):
            line = f.readline()
        ev = []
        for line in f:
            s = line.strip()
            if s.startswith(b"]"):
                break
            ev.append(orjson.loads(s.rstrip(b",")))
        marks = {}
        for line in f:
            if line.startswith(b'  "hb_exits": 1'):
                marks["hb_exits"] = 1
            elif line.startswith(b'  "hb_async": 1'):
                marks["hb_async"] = 1
    if any(a["seq"] >= b["seq"] for a, b in zip(ev, ev[1:])):
        ev.sort(key=lambda e: e["seq"])
    return header["kernel"], ev, marks


_DOTS = {}


def rmw_scopes(dots, kernel_name):
    """{pc: atomic scope} of the kernel's CFG (sd.atomic_scope, as hb_oracle classifies)."""
    import sync_dominance as sd
    for dot in dots:
        if dot not in _DOTS:
            _DOTS[dot] = sd.parse_dot(dot)
        kernels = _DOTS[dot]
        try:
            m = sd.select_kernel(kernels, kernel_name)
        except sd.AlignmentError:
            continue
        blocks = kernels[m][0]
        return {pc: s for ins in blocks.values() for pc, op in ins
                if (s := sd.atomic_scope(op)) is not None}
    return None


# ---------------------------------------------------------------- the window count

class _Loc:
    """Per-location state of the window count (O(1) per RMW event)."""
    __slots__ = ("n", "open", "last_n_open", "last_wk", "ov", "ov_same", "ov_open",
                 "ov_same_open", "succ", "succ_unc", "succ_unc_xw", "sync", "size", "none",
                 "blk", "blocks", "clusters", "multi", "multi_members", "multi_mixed")

    def __init__(self):
        self.n = self.open = 0
        self.last_n_open = False      # the last RMW on loc still has its window open
        self.last_wk = None
        self.ov = self.ov_same = self.ov_open = self.ov_same_open = 0
        self.succ = self.succ_unc = self.succ_unc_xw = 0
        self.sync = False
        self.size, self.none, self.blk, self.blocks = 0, False, False, set()
        self.clusters = self.multi = self.multi_members = self.multi_mixed = 0

    def end_cluster(self):
        if self.size:
            self.clusters += 1
            if self.size > 1:
                self.multi += 1
                self.multi_members += self.size
                self.multi_mixed += self.none or (self.blk and len(self.blocks) > 1)
        self.size, self.none, self.blk, self.blocks = 0, False, False, set()


def count_kernel(ev, scope_of):
    """The window count of one kernel dump (see the module docstring). A window's overlaps are
    the RMWs issued on its location between its record and its thread's next record: the
    difference of the location's issue counter (and, for same-warp ones, the (location, warp)
    counter) between the two -- so the state is per location, per (location, warp) and per open
    window, never per RMW."""
    import sync_dominance as sd
    locs = {}                         # loc -> _Loc
    lw = defaultdict(int)             # (loc, warp key) -> RMWs issued so far
    open_w = {}                       # tid -> (loc, loc counter, (loc, warp) counter, warp key)
    last = {}                         # tid -> ("rmw" | "plain" | "sync", loc) of its last record

    def close(t, plain_loc):
        """t's next record closes t's open window; plain_loc = that record's location if it is
        a plain memory access (None otherwise)."""
        w = open_w.pop(t, None)
        if w is None:
            return
        loc, cn, cw, wk = w
        st = locs[loc]
        st.ov += st.n - cn
        st.ov_same += lw[(loc, wk)] - cw
        st.open -= 1
        if st.n == cn:                # no RMW on loc since: the last one's window is closed
            st.last_n_open = False
        if plain_loc is not None and plain_loc != loc:
            st.sync = True

    for e in ev:
        typ, block, warp = e["type"], e["block"], e["warp"]
        if e.get("space") == "local":
            continue
        base = (block << 10) | (warp << 5)
        if "lanes" not in e:          # exit, barrier, syncwarp, cp.async commit/wait
            m = e["sync_mask"] if typ == "syncwarp" else e.get("active_mask", 0)
            while m:
                k = (m & -m).bit_length() - 1
                m &= m - 1
                t = base | k
                if t in open_w:
                    close(t, None)
                last[t] = ("sync", None)
            continue
        pc, space = e["pc"], e["space"]
        sc = scope_of.get(pc)
        for ln in e["lanes"]:
            k, addr = ln["lane"], ln["addr"]
            t = base | k
            loc = ("shared", block, addr) if space == "shared" else (space, addr)
            if t in open_w:
                close(t, loc if sc is None else None)
            if sc is not None:
                st = locs.get(loc)
                if st is None:
                    st = locs[loc] = _Loc()
                prev = last.get(t)
                if prev is not None and prev[0] == "plain" and prev[1] != loc:
                    st.sync = True
                wk = t >> 5
                if st.n:
                    st.succ += 1
                    if st.last_n_open:
                        st.succ_unc += 1
                        st.succ_unc_xw += st.last_wk != wk
                if st.open == 0:      # every earlier window on loc closed: a new cluster
                    st.end_cluster()
                st.size += 1
                st.none = st.none or sc == sd.NONE
                st.blk = st.blk or sc == sd.BLOCK
                st.blocks.add(block)
                st.n += 1
                lw[(loc, wk)] += 1
                open_w[t] = (loc, st.n, lw[(loc, wk)], wk)
                st.open += 1
                st.last_n_open, st.last_wk = True, wk
            last[t] = ("rmw" if sc is not None else "plain", loc)
    for t, (loc, cn, cw, wk) in open_w.items():   # no next record: open to the end
        st = locs[loc]
        st.ov += st.n - cn
        st.ov_open += st.n - cn
        st.ov_same += lw[(loc, wk)] - cw
        st.ov_same_open += lw[(loc, wk)] - cw
    same = defaultdict(int)
    for (loc, _), n in lw.items():
        same[loc] += n * (n - 1) // 2
    c = Counter()
    for loc, st in locs.items():
        st.end_cluster()
        pairs = st.n * (st.n - 1) // 2 - same[loc]
        xw_ov = st.ov - st.ov_same
        c["rmw"] += st.n
        c["rmw_locs"] += 1
        c["sync_locs"] += st.sync
        c["xw_pairs"] += pairs
        c["xw_overlap"] += xw_ov
        c["xw_overlap_open"] += st.ov_open - st.ov_same_open
        c["sw_overlap"] += st.ov_same
        if st.sync:
            c["xw_pairs_sync"] += pairs
            c["xw_overlap_sync"] += xw_ov
            c["succ_uncertain_xw_sync"] += st.succ_unc_xw
        c["succ_edges"] += st.succ
        c["succ_uncertain"] += st.succ_unc
        c["succ_uncertain_xw"] += st.succ_unc_xw
        c["clusters"] += st.clusters
        c["multi"] += st.multi
        c["multi_members"] += st.multi_members
        c["multi_mixed"] += st.multi_mixed
    return c


def count_program(pdir):
    out = {}
    dots = sorted(glob.glob(f"{pdir}/dots/*.dot"))
    for mode in (VC, SC):
        mdir = hb_modes.resolve_dir(pdir, mode)
        kjs = sorted(glob.glob(f"{mdir}/kernel_*.json"))
        if not kjs:
            continue
        tot, errs, exits, nev = Counter(), [], 0, 0
        for kj in kjs:
            try:
                kern, ev, marks = read_dump(kj)
            except Exception as e:                      # noqa: BLE001 -- recorded
                errs.append(f"{os.path.basename(kj)}: {type(e).__name__}: {e}"[:200])
                continue
            if not ev:
                continue
            sc = rmw_scopes(dots, kern.get("kernel_name", ""))
            if sc is None:
                errs.append(f"{os.path.basename(kj)}: no CFG aligns")
                continue
            tot.update(count_kernel(ev, sc))
            tot["kernels"] += 1
            nev += len(ev)
            exits += bool(marks.get("hb_exits"))
        out[mode] = {**tot, "events": nev, "kernels_with_exits": exits, "errors": errs,
                     "kernel_files": len(kjs)}
    return out


def _forked(fn, arg, part, mem_gb, timeout):
    """fn(arg) in a child under an address-space and wall-clock cap; the child writes its
    result (a JSON dict) to `part` -> that dict, or {"error": ...}."""
    pid = os.fork()
    if pid == 0:
        lim = int(mem_gb * 1e9)
        resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
        try:
            res = fn(arg)
        except MemoryError:
            res = {"error": "oom"}
        except Exception as e:                          # noqa: BLE001 -- recorded
            res = {"error": f"{type(e).__name__}: {e}"[:400]}
        with open(part, "w") as f:
            json.dump(res, f)
        os._exit(0)
    t0, status = time.time(), None
    while True:
        done, status = os.waitpid(pid, os.WNOHANG)
        if done:
            break
        if time.time() - t0 > timeout:
            os.kill(pid, 9)
            os.waitpid(pid, 0)
            return {"error": f"timeout({timeout}s)"}
        time.sleep(0.5)
    try:
        with open(part) as f:
            res = json.load(f)
        os.remove(part)
        return res
    except (OSError, ValueError):
        return {"error": f"died(status={status})"}


def _shard(ids, spec):
    k, n = (int(x) for x in spec.split("/"))
    return [i for j, i in enumerate(sorted(ids)) if j % n == k]


def cmd_count(a):
    root = f"{STORES}/{a.store}"
    ids = [d for d in os.listdir(root) if os.path.isfile(f"{root}/{d}/meta.json")]
    if a.id:
        ids = [i for i in ids if i in a.id.split(",")]
    od = f"{OUT}/count-{a.tag or a.store}"
    os.makedirs(od, exist_ok=True)
    for j, _id in enumerate(_shard(ids, a.shard), 1):
        dst = f"{od}/{_id}.json"
        if os.path.exists(dst) and not a.force:
            continue
        t0 = time.time()
        res = _forked(count_program, f"{root}/{_id}", dst + ".part", a.mem_gb, a.timeout)
        res = {"id": _id, "pset": _id.split("-")[0], "store": a.store,
               "seconds": round(time.time() - t0, 1), **({"modes": res} if "error" not in res
                                                        else res)}
        with open(dst, "w") as f:
            json.dump(res, f)
        print(f"[{j}] {_id} {res.get('error', 'ok')} {res['seconds']}s", flush=True)


# ---------------------------------------------------------------- the re-score

def _pairs(races):
    """hb_races -> {(pc_lo, pc_hi, class): [instances, flagged]} (flagged None: no field)."""
    out = {}
    for r in races or ():
        a, b = r.get("a_pc"), r["b_pc"]
        k = (min(a, b), max(a, b), r.get("class", "DR")) if a is not None else (None, b, "DR")
        c = out.setdefault(k, [0, 0])
        c[0] += r.get("count", 1)
        if c[1] is not None:
            c[1] = c[1] + r["a2_uncertain"] if "a2_uncertain" in r else None
    return out


def _agg(races):
    """instances per (a_pc, b_pc, kind, class, space): T9's t9-after dumps hold record-level
    races (written before T9's aggregation commit), this oracle aggregated ones with a count."""
    out = Counter()
    for r in races or ():
        out[(r.get("a_pc"), r["b_pc"], r["kind"], r.get("class", "DR"), r["space"])] += \
            r.get("count", 1)
    return out


def rescore_program(info):
    import hb_oracle
    import orjson
    import sync_dominance as sd
    _id, pdir = info["id"], info["pdir"]
    dst = f"{AFTER}/{_id}"
    tmp = dst + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    for name in os.listdir(pdir):
        if name != VC:
            os.symlink(f"{pdir}/{name}", f"{tmp}/{name}")
    det = {"kernels": []}
    vdir = hb_modes.resolve_dir(pdir, VC)
    os.makedirs(f"{tmp}/{VC}")
    dots = sorted(glob.glob(f"{pdir}/dots/*.dot"))
    t9dir = f"{T9_AFTER}/{_id}/{VC}"
    for name in sorted(os.listdir(vdir)):
        src = f"{vdir}/{name}"
        if not (name.startswith("kernel_") and name.endswith(".json")):
            os.symlink(src, f"{tmp}/{VC}/{name}")
            continue
        t0 = time.time()
        with open(src, "rb") as f:
            trace = orjson.loads(f.read())
        k = {"file": name, "events": len(trace.get("hb_events") or ())}
        if not trace.get("hb_events"):
            k["skip"] = "no-hb_events"
            os.symlink(src, f"{tmp}/{VC}/{name}")
            det["kernels"].append(k)
            continue
        rep = err = None
        for strict in ("1", "0"):                      # the engine records a TV violation
            os.environ["YOSEMITE_HB_STRICT"] = strict   # and continues: so does the re-score
            for dot in dots:
                try:
                    rep = hb_oracle.analyze(dot, src)
                    break
                except sd.AlignmentError as e:
                    if str(e).startswith("TV-"):
                        err = str(e)
                        break
            if rep is not None or err is None:
                break
        os.environ.pop("YOSEMITE_HB_STRICT", None)
        if err:
            k["tv"] = err[:200]
        if rep is None:
            k["skip"] = "no-aligning-cfg"
            os.symlink(src, f"{tmp}/{VC}/{name}")
            det["kernels"].append(k)
            continue
        new = _pairs(rep["races"])
        dr = [r for r in rep["races"] if r["class"] == "DR"]
        k.update(kernel=trace["kernel"]["kernel_name"], records=len(rep["races"]),
                 dr_records=len(dr), dr_instances=sum(r["count"] for r in dr),
                 dr_flagged=sum(r["a2_uncertain"] for r in dr),
                 pairs=sorted([list(p[:2]), p[2], c] for p, c in new.items()),
                 seconds=round(time.time() - t0, 2))
        k["same_as_t9"] = None        # T9's re-oracled dump, compared up to a2 (<= 1 GB only)
        t9f = f"{t9dir}/{name}"
        if os.path.isfile(t9f) and os.path.getsize(t9f) <= 1 << 30:
            with open(t9f, "rb") as f:
                t9 = orjson.loads(f.read())
            k["same_as_t9"] = _agg(t9.get("hb_races")) == _agg(rep["races"]) and \
                t9.get("hb_races_sync_only") == (rep["races_sync_only"]
                                                 if trace.get("hb_races_sync_only") is not None
                                                 else None)
            del t9
        trace["hb_races"] = rep["races"]
        if trace.get("hb_races_sync_only") is not None:
            trace["hb_races_sync_only"] = rep["races_sync_only"]
        trace["hb_a2"] = 1
        trace["t14_rescore"] = {"from": src, "oracle": "hb_oracle.py (T14)"}
        with open(f"{tmp}/{VC}/{name}", "wb") as f:
            f.write(orjson.dumps(trace))
        det["kernels"].append(k)
        del trace, rep
    shutil.rmtree(dst, ignore_errors=True)
    os.rename(tmp, dst)
    return det


def cmd_rescore(a):
    sel = json.load(open(T9_SELECTION))["programs"]
    ids = [i for i, s in sel.items() if VC in s["modes"]
           and a.min_mb <= s["dump_mb"] < a.max_mb and (not a.id or i in a.id.split(","))]
    od = f"{OUT}/rescore"
    os.makedirs(od, exist_ok=True)
    os.makedirs(AFTER, exist_ok=True)
    for j, _id in enumerate(_shard(ids, a.shard), 1):
        dst = f"{od}/{_id}.json"
        if os.path.exists(dst) and not a.force:
            continue
        t0 = time.time()
        res = _forked(rescore_program, {"id": _id, "pdir": sel[_id]["pdir"]}, dst + ".part",
                      a.mem_gb, a.timeout)
        if "error" in res:
            shutil.rmtree(f"{AFTER}/{_id}.tmp", ignore_errors=True)
        res.update(id=_id, pset=sel[_id]["pset"], dump_mb=sel[_id]["dump_mb"],
                   seconds=round(time.time() - t0, 1))
        with open(dst, "w") as f:
            json.dump(res, f)
        print(f"[{j}] {_id} {res.get('error', 'ok')} {res['seconds']}s", flush=True)


def cmd_t9keys(a):
    """For every re-scored kernel whose instance counts differ from T9's re-oracled dump
    (same_as_t9 False): are the (a_pc, b_pc, kind, class, space) key sets and the second clock
    the same, and is T9's count never above this one? T9's t9-after dumps are record-level and
    hold each distinct record tuple once, the aggregated count counts repeats."""
    import orjson
    n = keys = sync = le = 0
    for p in sorted(glob.glob(f"{OUT}/rescore/*.json")):
        d = json.load(open(p))
        for k in d.get("kernels", []):
            if k.get("same_as_t9") is not False:
                continue
            f = k["file"]
            with open(f"{AFTER}/{d['id']}/{VC}/{f}", "rb") as fa:
                x = orjson.loads(fa.read())
            with open(f"{T9_AFTER}/{d['id']}/{VC}/{f}", "rb") as fb:
                y = orjson.loads(fb.read())
            kx, ky = _agg(x["hb_races"]), _agg(y["hb_races"])
            n += 1
            keys += set(kx) == set(ky)
            sync += x.get("hb_races_sync_only") == y.get("hb_races_sync_only")
            le += all(ky[q] <= kx[q] for q in ky)
            del x, y
    print(f"{n} kernels with differing instance counts: same key set {keys}, same second clock "
          f"{sync}, T9 count <= T14 count on every key {le}")


# ---------------------------------------------------------------- the Sanitizer's inversions

def cmd_handoffs(a):
    """python/testdata/lock_contention_a2.cu, kernel kcontend (race-free): every critical section
    (CS) is one plain read of data[0] after a successful CAS, and the sections run one at a time,
    so the order of their read records is the CS order (A2w). A hand-off CS_k -> CS_k+1 between
    two threads is recorded inverted -- the successful CAS before the unlock it read from --
    exactly when the two sections are unordered on the trace (T13's "S_k+1 recorded before E_k",
    measured without the values); the oracle's instances name the sections by (thread, epoch)."""
    import hb_oracle
    import sync_dominance as sd
    tot = Counter()
    for kj in a.traces:
        t = json.load(open(kj))
        if not t["kernel"]["kernel_name"].startswith("kcontend"):
            continue
        rep = None
        for dot in a.dots:
            try:
                rep = hb_oracle.analyze(dot, kj, records=True)
                break
            except sd.AlignmentError:
                continue
        rmw = {int(x, 16) for x in rep["atomic_pcs"]}
        ep, cs = defaultdict(lambda: 1), []
        for e in sorted(t["hb_events"], key=lambda e: e["seq"]):
            for ln in e.get("lanes", ()):
                tid = (e["block"] << 10) | (e["warp"] << 5) | ln["lane"]
                if e["pc"] in rmw:
                    ep[tid] += 1
                elif e["type"] == "read":
                    cs.append((tid, ep[tid]))
        recs = rep["a2_records"]      # [a_tid, a_pc, a_ep, b_tid, b_pc, b_ep, flagged, n]
        unordered = {(r[0], r[2], r[3], r[5]) for r in recs}
        unordered |= {(r[3], r[5], r[0], r[2]) for r in recs}
        c = Counter(sections=len(cs), adjacent=max(len(cs) - 1, 0),
                    instances=sum(r[7] for r in recs), flagged=sum(r[7] for r in recs if r[6]))
        if "hb_races" in t:           # vector-clock dump: the engine's records, the new field too
            key = lambda r: (r.get("a_pc"), r["b_pc"], r["kind"], r.get("class"), r["space"],
                             r.get("dist"), r.get("async"), r.get("count"), r.get("a2_uncertain"))
            c["engine_traces"] += 1
            c["engine_eq_oracle"] += {key(r) for r in t["hb_races"]} == \
                {key(r) for r in rep["races"]} and \
                t.get("hb_races_sync_only") == rep["races_sync_only"]
            c["engine_flagged"] += sum(r.get("a2_uncertain") or 0 for r in t["hb_races"])
        for x, y in zip(cs, cs[1:]):
            if x[0] != y[0]:
                c["cross_thread"] += 1
                c["inverted"] += (x[0], x[1], y[0], y[1]) in unordered
        print(f"{kj}: {dict(c)}", flush=True)
        tot.update(c)
    print("total", dict(tot))


# ---------------------------------------------------------------- tables (login node)

PSETS = ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P9")


def _load_csv(pattern, mode):
    order = {"RACE": 3, "CLEAN": 2, "TIMEOUT": 1, "ERROR": 0}
    runs = {}
    for p in sorted(glob.glob(pattern)):
        for r in csv.DictReader(open(p, newline="")):
            if hb_modes.canon(r.get("mode", ""), p) != mode:
                continue
            prev = runs.get(r["id"])
            if prev is None or order.get(r["verdict"], 0) > order.get(prev["verdict"], 0):
                runs[r["id"]] = r
    return runs


def cmd_tables(a):
    import make_tables as mt
    os.makedirs(RES, exist_ok=True)
    lines = ["# T14 -- A2 in the tables (generated by eval/baselines/a2_window_count.py tables)\n"]
    # --- window counts
    cnt = [json.load(open(p)) for p in sorted(glob.glob(f"{a.count_dir}/*.json"))]
    keys = ["kernels", "rmw", "rmw_locs", "sync_locs", "xw_pairs", "xw_overlap",
            "xw_overlap_open", "xw_pairs_sync", "xw_overlap_sync", "sw_overlap",
            "succ_edges", "succ_uncertain", "succ_uncertain_xw", "succ_uncertain_xw_sync",
            "clusters", "multi", "multi_members", "multi_mixed", "events", "kernels_with_exits"]
    rows = []
    for mode in (VC, SC):
        per, progs, with_ov, with_ov_sync, errs = defaultdict(Counter), Counter(), Counter(), \
            Counter(), Counter()
        for d in cnt:
            if "error" in d:
                errs[d["pset"]] += mode == VC
                continue
            m = d["modes"].get(mode)
            if m is None:
                continue
            ps = d["pset"]
            per[ps].update({k: m.get(k, 0) for k in keys})
            progs[ps] += 1
            with_ov[ps] += m.get("xw_overlap", 0) > 0
            with_ov_sync[ps] += m.get("xw_overlap_sync", 0) > 0
            errs[ps] += bool(m.get("errors"))
            rows.append({"id": d["id"], "pset": ps, "mode": mode,
                         **{k: m.get(k, 0) for k in keys}, "errors": len(m.get("errors", []))})
        lines.append(f"\n## Window count, {mode} dumps\n")
        lines.append("| suite | programs | with an overlap | with one on a sync location | RMWs | "
                     "cross-warp pairs | overlapping | % | of which the earlier window open-ended "
                     "| on sync locations: pairs / overlapping | same-warp overlaps | successor "
                     "edges: uncertain / cross-warp | multi clusters (mixed) | programs with a "
                     "read error |")
        lines.append("|" + "---|" * 14)
        tot = Counter()
        for ps in PSETS:
            if not progs[ps]:
                continue
            c = per[ps]
            tot.update(c)
            tot["programs"] += progs[ps]
            tot["with_ov"] += with_ov[ps]
            tot["with_ov_sync"] += with_ov_sync[ps]
            tot["errs"] += errs[ps]
            lines.append(_wrow(ps, progs[ps], with_ov[ps], with_ov_sync[ps], c, errs[ps]))
        lines.append(_wrow("**all**", tot["programs"], tot["with_ov"], tot["with_ov_sync"], tot,
                           tot["errs"]))
        failed = sorted(d["id"] for d in cnt if "error" in d)
        lines.append(f"\nNot counted (error / timeout): {len(failed)}"
                     + (": " + ", ".join(f"{i} ({next(d['error'] for d in cnt if d['id'] == i)})"
                                         for i in failed) if failed else ""))
    with open(f"{RES}/window_count.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "pset", "mode", *keys, "errors"])
        w.writeheader()
        w.writerows(rows)
    # --- the re-score: instance level
    rs = [json.load(open(p)) for p in sorted(glob.glob(f"{a.rescore_dir}/*.json"))]
    lines.append("\n## Re-score with the flag (vector-clock dumps of T9's selection, the T14 "
                 "oracle): DR instances and pc pairs\n")
    lines.append("| suite | programs | kernels with T9's instance counts / compared (`t9keys`: the "
                 "others) | DR "
                 "instances | flagged | % | DR pc pairs | every instance flagged | programs with "
                 "a flagged DR instance | SC instances / flagged | not re-scored |")
    lines.append("|" + "---|" * 11)
    tot = Counter()
    prog_rows, rs_rows = [], []
    for ps in PSETS:
        c = Counter()
        for d in rs:
            if d.get("pset") != ps:
                continue
            if "error" in d:
                c["err"] += 1
                continue
            ks = [k for k in d["kernels"] if "pairs" in k]
            if not ks:
                continue
            c["programs"] += 1
            c["same"] += sum(k.get("same_as_t9") is True for k in ks)
            c["cmp"] += sum(k.get("same_as_t9") is not None for k in ks)
            inst = sum(k["dr_instances"] for k in ks)
            fl = sum(k["dr_flagged"] for k in ks)
            c["inst"] += inst
            c["flag"] += fl
            pairs = defaultdict(lambda: [0, 0])
            for k in ks:
                for p, cls, (n, f) in k["pairs"]:
                    if cls == "DR":
                        pairs[tuple(p)][0] += n
                        pairs[tuple(p)][1] += f
                    else:
                        c["sc_inst"] += n
                        c["sc_flag"] += f or 0
            c["pairs"] += len(pairs)
            c["pairs_all"] += sum(f >= n for n, f in pairs.values())
            c["with_flag"] += fl > 0
            if fl:
                prog_rows.append((ps, d["id"], inst, fl, len(pairs),
                                  sum(f >= n for n, f in pairs.values())))
            rs_rows.append({"id": d["id"], "pset": ps, "kernels": len(ks), "dr_instances": inst,
                            "dr_flagged": fl, "dr_pairs": len(pairs),
                            "dr_pairs_all_flagged": sum(f >= n for n, f in pairs.values()),
                            "same_as_t9": sum(k.get("same_as_t9") is True for k in ks),
                            "compared_with_t9": sum(k.get("same_as_t9") is not None for k in ks),
                            "seconds": d.get("seconds")})
        if not (c["programs"] or c["err"]):
            continue
        tot.update(c)
        lines.append(_rrow(ps, c))
    lines.append(_rrow("**all**", tot))
    lines.append("\nPrograms with a flagged DR instance (instances / flagged / DR pc pairs / "
                 "pairs with every instance flagged):\n")
    lines.append("| suite | program | DR instances | flagged | DR pairs | all-flagged pairs |")
    lines.append("|---|---|---|---|---|---|")
    for r in sorted(prog_rows):
        lines.append("| " + " | ".join(map(str, r)) + " |")
    errs = sorted((d["id"], d["error"]) for d in rs if "error" in d)
    lines.append(f"\nNot re-scored: {len(errs)}" + (": " + ", ".join(f"{i} ({e})" for i, e in errs)
                                                   if errs else ""))
    with open(f"{RES}/rescore.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rs_rows[0]) if rs_rows else ["id"])
        w.writeheader()
        w.writerows(sorted(rs_rows, key=lambda r: r["id"]))
    # --- the oracle's cost: T9's re-score of the same dumps vs this one (wall seconds per program)
    t9d = {os.path.basename(p)[:-5]: json.load(open(p))
           for p in glob.glob(f"{a.t9_detail}/*.json")} if os.path.isdir(a.t9_detail) else {}
    pairs_s = [(t9d[r["id"]]["seconds"], r["seconds"]) for r in rs_rows
               if r["id"] in t9d and "error" not in t9d[r["id"]] and r["seconds"]]
    if pairs_s:
        s9, s14 = sum(x for x, _ in pairs_s), sum(y for _, y in pairs_s)
        big = [(x, y) for x, y in pairs_s if x >= 60]
        lines.append(f"\nOracle wall time, same dumps, programs both re-scores finished ({len(pairs_s)}): "
                     f"T9 {s9:.0f} s, T14 {s14:.0f} s (x{s14 / s9:.2f}); over the {len(big)} programs "
                     f"T9 needed >= 60 s for: x{sum(y for _, y in big) / max(sum(x for x, _ in big), 1):.2f} "
                     f"(max x{max((y / x for x, y in big), default=0):.2f}). Different nodes, one run each.")
    # --- verdicts: base code on t9-after vs this checkout on t14-after (vector-clock rows)
    base, new = _load_csv(a.base_csv, VC), _load_csv(a.new_csv, VC)
    man = {r["id"]: r for r in csv.DictReader(open(f"{APH}/eval/results/t9-rescore/manifest.t9.csv",
                                                     newline=""))}
    skip = {d["id"] for d in rs if "error" in d}
    scored = {d["id"] for d in rs if "error" not in d}   # programs with a re-scored VC dump
    both = sorted(set(base) & set(new) & scored)
    changed = [i for i in both if (base[i]["verdict"], base[i]["report_ids"],
                                   mt.report_classes(base[i])) !=
               (new[i]["verdict"], new[i]["report_ids"], mt.report_classes(new[i]))]
    t9 = _load_csv(a.t9_csv, VC)
    both9 = sorted(set(t9) & set(new) & scored)

    def rows(pattern, strict):            # per (id, rep): every row, not the best per program
        out = {}
        for p in sorted(glob.glob(pattern)):
            for r in csv.DictReader(open(p, newline="")):
                if hb_modes.canon(r.get("mode", ""), p) != VC or r["id"] not in scored or \
                        (r["verdict"] == "ERROR" and (r["id"], r["rep"]) in out):
                    continue
                note = re.sub(r";a2_uncertain=\d+:\d+", "", r["notes"] or "") if strict else \
                    mt.report_classes(r)
                out[(r["id"], r["rep"])] = (r["verdict"], r["reports_dedup"], r["report_ids"], note)
        return out
    rb, rn, r9 = rows(a.base_csv, True), rows(a.new_csv, True), rows(a.t9_csv, False)
    rn9 = {k: v[:3] + (mt.report_classes({"notes": v[3]}),) for k, v in rn.items()}
    rows_b = sorted(rb.keys() & rn.keys())
    rows_9 = sorted(r9.keys() & rn9.keys())
    rch_b = sorted({k[0] for k in rows_b if rb[k] != rn[k]})
    rch_9 = sorted({k[0] for k in rows_9 if r9[k] != rn9[k]})
    changed9 = [i for i in both9 if (t9[i]["verdict"], t9[i]["report_ids"],
                                     mt.report_classes(t9[i])) !=
                (new[i]["verdict"], new[i]["report_ids"], mt.report_classes(new[i]))]
    lines.append(f"\n## Verdicts (vector-clock rows of `parallel.py analyze` on the store t14-after)"
                 f"\n\nBase code (f127790) vs this checkout on the same dumps: {len(both)} programs "
                 f"compared (verdict, report ids, class note), {len(changed)} changed"
                 + (": " + ", ".join(changed) if changed else "") +
                 f"; left out: {len(set(new) - scored)} programs without a re-scored vector-clock "
                 f"dump ({len(skip)} of them re-scoring failed). Per row (id, rep; verdict, "
                 f"reports, report ids, notes without the a2 token): {len(rows_b)} rows compared, "
                 f"{sum(rb[k] != rn[k] for k in rows_b)} changed"
                 + (" (" + ", ".join(rch_b) + ")" if rch_b else "") + ".\n\n"
                 f"T9's committed re-score (T9 code on t9-after) vs this checkout on t14-after: "
                 f"{len(both9)} programs compared, {len(changed9)} changed"
                 + (": " + ", ".join(changed9) if changed9 else "") +
                 f"; per row (verdict, reports, report ids, class note): {len(rows_9)} rows "
                 f"compared, {sum(r9[k] != rn9[k] for k in rows_9)} changed"
                 + (" (" + ", ".join(rch_9) + ")" if rch_9 else "") + ".\n")
    lines.append("| suite | programs | RACE | Race alone RACE | a2-uncertain at Race alone: CLEAN "
                 "label / RACE label | at Race u Latent: CLEAN / RACE | programs with an "
                 "a2-uncertain report |")
    lines.append("|---|---|---|---|---|---|---|")
    tot = Counter()
    a2prog = []
    for ps in PSETS:
        c = Counter()
        for i in both:
            if not i.startswith(ps + "-"):
                continue
            r = new[i]
            c["n"] += 1
            c["race"] += r["verdict"] == "RACE"
            v1 = mt.race_alone_verdict(r)
            c["race1"] += v1 == "RACE"
            a2 = mt.report_a2(r)
            cls = mt.report_classes(r) or {}
            lab = man.get(i, {}).get("label", "")
            if a2 is None:
                continue
            c["any"] += a2[0] > 0
            if v1 == "RACE" and sum(cls.get(k, 0) for k in mt.RACE_CLASSES) <= a2[0]:
                c["r_" + lab] += 1
                a2prog.append((ps, i, lab, "Race alone" +
                               (" and Race u Latent" if r["verdict"] == "RACE" and
                                sum(n for k, n in cls.items() if k not in ("sc", "latent-sc"))
                                <= a2[1] else ""), r["notes"].split("classes=")[-1]))
            if r["verdict"] == "RACE" and \
                    sum(n for k, n in cls.items() if k not in ("sc", "latent-sc")) <= a2[1]:
                c["rl_" + lab] += 1
        if not c["n"]:
            continue
        tot.update(c)
        lines.append(f"| {ps} | {c['n']} | {c['race']} | {c['race1']} | {c['r_CLEAN']} / "
                     f"{c['r_RACE']} | {c['rl_CLEAN']} / {c['rl_RACE']} | {c['any']} |")
    lines.append(f"| **all** | {tot['n']} | {tot['race']} | {tot['race1']} | {tot['r_CLEAN']} / "
                 f"{tot['r_RACE']} | {tot['rl_CLEAN']} / {tot['rl_RACE']} | {tot['any']} |")
    lines.append("\nPrograms whose positive rests on a2-uncertain reports only:\n")
    lines.append("| suite | program | label | at | classes |")
    lines.append("|---|---|---|---|---|")
    for r in a2prog:
        lines.append("| " + " | ".join(r) + " |")
    text = "\n".join(lines) + "\n"
    open(f"{RES}/A2_TABLES.md", "w").write(text)
    print(text)


def _pct(a, b):
    return f"{100.0 * a / b:.2f}" if b else "-"


def _wrow(ps, n, wov, wsync, c, errs):
    return (f"| {ps} | {n} | {wov} | {wsync} | {c['rmw']} | {c['xw_pairs']} | {c['xw_overlap']} "
            f"| {_pct(c['xw_overlap'], c['xw_pairs'])} | {c['xw_overlap_open']} "
            f"| {c['xw_pairs_sync']} / {c['xw_overlap_sync']} | {c['sw_overlap']} "
            f"| {c['succ_uncertain']} / {c['succ_uncertain_xw']} of {c['succ_edges']} "
            f"| {c['multi']} ({c['multi_mixed']}) | {errs} |")


def _rrow(ps, c):
    return (f"| {ps} | {c['programs']} | {c['same']} / {c['cmp']} | {c['inst']} | {c['flag']} "
            f"| {_pct(c['flag'], c['inst'])} | {c['pairs']} | {c['pairs_all']} | {c['with_flag']} "
            f"| {c['sc_inst']} / {c['sc_flag']} | {c['err']} |")


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("count")
    c.add_argument("--store", default="evcand")
    c.add_argument("--tag", default="", help="output dir OUT/count-<tag> (default: the store)")
    c.add_argument("--shard", default="0/1")
    c.add_argument("--id", default="")
    c.add_argument("--mem-gb", type=float, default=60)
    c.add_argument("--timeout", type=int, default=7200)
    c.add_argument("--force", action="store_true")
    r = sub.add_parser("rescore")
    r.add_argument("--shard", default="0/1")
    r.add_argument("--id", default="")
    r.add_argument("--min-mb", type=float, default=0)
    r.add_argument("--max-mb", type=float, default=float("inf"))
    r.add_argument("--mem-gb", type=float, default=60)
    r.add_argument("--timeout", type=int, default=7200)
    r.add_argument("--force", action="store_true")
    t = sub.add_parser("tables")
    t.add_argument("--count-dir", default=f"{RES}/detail/count-evcand")   # copies of OUT/..
    t.add_argument("--rescore-dir", default=f"{RES}/detail/rescore")      # (detail/: gitignored)
    t.add_argument("--base-csv", default=f"{RES}/analyze-base/*.csv")
    t.add_argument("--new-csv", default=f"{RES}/analyze-t14/*.csv")
    t.add_argument("--t9-csv", default=f"{APH}/eval/results/t9-rescore/after/*.csv")
    t.add_argument("--t9-detail", default="/home/fzheng4/wt-T9/eval/results/t9-rescore/detail")
    h = sub.add_parser("handoffs")
    h.add_argument("--dots", nargs="+", required=True)
    h.add_argument("traces", nargs="+")
    sub.add_parser("t9keys")
    a = ap.parse_args()
    {"count": cmd_count, "rescore": cmd_rescore, "tables": cmd_tables,
     "handoffs": cmd_handoffs, "t9keys": cmd_t9keys}[a.cmd](a)


if __name__ == "__main__":
    main()

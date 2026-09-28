#!/usr/bin/env python3
"""T6 (c): Algorithm 1 of design/proof/hb_proof.tex, Detect(T, M), as an executable
reference, with the substitutions I1 and I2 of the code at 3331d35 (section 7) as switches.

  I1: tick before publish; the RMW's own entry carries the post-tick epoch.
  I2: one last write per location plus each thread's last read since that write, in place
      of the per-(thread, key) buckets; morally strong pairs are skipped (SC dropped).

Since T9 the code is Detect with I1 and I2 fixed: with both switches OFF, Detect(T, vec)
must equal hb_oracle.py's `races` (record pairs with their DR/SC class) on every trace and
Detect(T, sync) its `races_sync_only`; the switched-on runs show what I1 and I2 used to
cost on that trace. The other substitutions cannot differ on these dumps: no exit records
(I3), the trusting gate on both sides (I4), local records skipped on both sides (I5, D14),
no monitor here (I6), no cp.async records (I7, rejected).

    .env/bin/python design/algorithms_check.py [ARTIFACT_DIR ...]   (default: ScoR corpus)
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
import hb_oracle  # noqa: E402
import sync_dominance as sd  # noqa: E402


def ms(s1, b1, s2, b2):
    """Moral strength from the two records' strong scopes (None = weak) and blocks."""
    return s1 is not None and s2 is not None and (
        min(s1, s2) == sd.GRID or (min(s1, s2) == sd.BLOCK and b1 == b2))


def detect(events, block_tc, atom, coh, vec=True, i1=False, i2=False):
    """Detect(T, vec|sync) -> [(addr, prev_tid, prev_pc, tid, pc, class)]; class is DR/SC,
    or under I2 the oracle's kind label (atomic/WAW/RAW/WAR)."""
    clk = defaultdict(dict)                              # thread -> clock; own entry starts at 1
    get = lambda t, u: clk[t].get(u, 1 if u == t else 0)
    Bk = defaultdict(dict)                               # loc -> {(u, kind, scope): (epoch, pc)}
    W, R = {}, defaultdict(dict)                         # I2: loc -> last write / {u: last read}
    Ch, last, arrived, rep = {}, {}, defaultdict(set), []

    def sync(ts):                                        # procedure Sync
        J = {}
        for u in ts:
            for k in set(clk[u]) | {u}:
                J[k] = max(J.get(k, 0), get(u, k))
        for u in ts:
            clk[u] = {**J, u: J[u] + 1}

    def entries(loc, kind):                              # what Check inspects on loc
        if not i2:
            return [(u, k, ep, pc, s, "b") for (u, k, s), (ep, pc) in Bk[loc].items()]
        out = [(W[loc][0], "W", *W[loc][1:], "w")] if loc in W else []
        return out + ([(u, "R", ep, pc, s, "r") for u, (ep, pc, s) in R[loc].items()]
                      if kind != "R" else [])

    for e in sorted(events, key=lambda e: e["seq"]):
        typ, blk = e["type"], e["block"]
        if e.get("space") == "local":
            continue                                     # I5 (D14): outside the model
        if typ in ("syncwarp", "barrier"):
            m = e["sync_mask" if typ == "syncwarp" else "active_mask"]
            ts = [hb_oracle.tid_of(blk, e["warp"], k) for k in range(32) if (m >> k) & 1]
            if typ == "syncwarp":
                sync(ts)
                continue
            key = (blk, e["bar_index"])                  # instance assembly; exp = n or N (I3)
            arrived[key].update(ts)
            exp = e["thread_count"] or block_tc
            if not exp or len(arrived[key]) >= exp:
                sync(sorted(arrived.pop(key)))
            continue
        if typ.startswith("pipeline"):
            raise ValueError("cp.async records are outside the model (I7)")
        pc, s = e["pc"], coh.get(e["pc"])
        kind = "RMW" if pc in atom else "W" if typ == "write" else "R"
        for ln in e["lanes"]:
            t, a = hb_oracle.tid_of(blk, e["warp"], ln["lane"]), ln["addr"]
            loc = (e["space"], blk if e["space"] == "shared" else None, a)
            rmw = vec and kind == "RMW"
            if rmw:
                if loc in last and not ms(*last[loc], s, blk):
                    Ch.pop(loc, None)                    # chain broken
                for u, c in Ch.get(loc, {}).items():     # acquire (trusting gate, I4)
                    clk[t][u] = max(get(t, u), c)
            for u, pk, ep, ppc, ps, src in entries(loc, kind):   # procedure Check
                if u == t or (kind == "R" and pk == "R") or ep <= get(t, u):
                    continue
                strong = ms(ps, u >> 10, s, blk)
                if i2:
                    if strong:
                        continue                         # SC dropped
                    cls = "WAR" if src == "r" else {"RMW": "atomic", "W": "WAW", "R": "RAW"}[kind]
                elif strong and kind == pk == "RMW":
                    continue                             # two morally strong RMWs
                else:
                    cls = "SC" if strong else "DR"
                rep.append((a, u, ppc, t, pc, cls))
            if rmw and i1:
                clk[t][t] = get(t, t) + 1                # I1: tick before publish
            ep = get(t, t)
            if not i2:
                Bk[loc][(t, kind, s)] = (ep, pc)
            elif kind == "R":
                R[loc][t] = (ep, pc, s)
            else:
                W[loc], R[loc] = (t, ep, pc, s), {}
            if rmw:
                pub = Ch.setdefault(loc, {})             # publish ...
                for u in set(clk[t]) | {t}:
                    pub[u] = max(pub.get(u, 0), get(t, u))
                last[loc] = (s, blk)
                if not i1:
                    clk[t][t] = get(t, t) + 1            # ... then tick
    return rep


def pcs(rep):
    return Counter((min(r[2], r[4]), max(r[2], r[4])) for r in rep)


def tables(dots, trace):
    """(dot, atom, coh) for a dump: the aligning CFG, its RMW scopes and its coherent-access
    scopes under the current --strong-ldst policy (as hb_oracle.analyze derives them)."""
    for dot in dots:
        try:
            kernels = sd.parse_dot(dot)
            eng = sd.HBGraph(*kernels[sd.select_kernel(kernels, trace["kernel"]["kernel_name"])])
            break
        except sd.AlignmentError:
            continue
    else:
        raise sd.AlignmentError("no CFG aligns with the dump")
    policy = sd.strong_ldst_policy()
    atom = {pc: sc for pc, op in eng.pc_opcode.items() if (sc := sd.atomic_scope(op)) is not None}
    coh = {pc: sc for pc, op in eng.pc_opcode.items()
           if (sc := sd.coherent_scope(op, policy)) is not None}
    return dot, atom, coh


def reference(dots, trace_path, **switches):
    """Detect(T, vec) (switches off: the proof's reference) over one kernel dump."""
    trace = json.loads(Path(trace_path).read_text())
    _, atom, coh = tables(dots, trace)
    return detect(trace["hb_events"], trace["kernel"].get("block_thread_count"), atom, coh,
                  **switches)


def check(dots, trace_path):
    """One kernel dump -> dict of the comparisons (see the module docstring)."""
    trace = json.loads(Path(trace_path).read_text())
    dot, atom, coh = tables(dots, trace)
    oracle = hb_oracle.analyze(dot, trace_path, records=True)
    ev, tc = trace["hb_events"], trace["kernel"].get("block_thread_count")
    run = lambda **kw: detect(ev, tc, atom, coh, **kw)
    ref, ref_sync = run(), run(vec=False)
    o_vec = {tuple(r) for r in oracle["race_records"]}
    o_sync = Counter({(a, b): n for a, b, n in oracle["races_sync_only"]})
    pairs = lambda rep: {(r[0], r[1], r[2], r[3], r[4]) for r in rep}
    return {"events": len(ev), "oracle": len(o_vec),
            "vec_equal": set(ref) == o_vec, "sync_equal": pcs(ref_sync) == o_sync,
            "ref_pairs": len(pairs(ref)), "ref_sc": sum(r[5] == "SC" for r in set(ref)),
            "missed": sorted(set(pcs(ref)) - {(min(r[2], r[4]), max(r[2], r[4])) for r in o_vec}),
            "missed_i1": sorted(set(pcs(ref)) - set(pcs(run(i1=True)))),
            "missed_i2": sorted(set(pcs(ref)) - set(pcs(run(i2=True)))),
            "code_not_ref": sorted(pairs(o_vec) - pairs(ref)),
            "sync_missed": sorted(set(pcs(ref_sync)) - set(o_sync))}


def main(argv):
    dirs = [Path(a) for a in argv] or sorted(
        p for p in (ROOT / "ScoR/microbenchmarks/artifacts").iterdir() if p.is_dir())
    rows, bad = [], 0
    for d in dirs:
        dots = sorted(d.glob("**/*.dot"))
        for tr in sorted(d.glob("dependency_*/kernel_*.json")):
            r = check(dots, tr)
            bad += not (r["vec_equal"] and r["sync_equal"] and not r["code_not_ref"])
            rows.append((d.name + ("" if tr.name == "kernel_0.json" else "/" + tr.name), r))
    print(f"{'program':52} ev  orc ref  sc   oracle==ref  sync==  reference-only pc pairs "
          "(and which switch would lose them)")
    for name, r in rows:
        miss = ", ".join(f"{hex(a)}/{hex(b)}" for a, b in r["missed"])
        why = "".join(k[-2:] for k in ("missed_i1", "missed_i2") if r[k])
        print(f"{name:52} {r['events']:3d} {r['oracle']:3d} {r['ref_pairs']:3d} {r['ref_sc']:3d}"
              f"  {'yes' if r['vec_equal'] else 'NO':>12}  {'yes' if r['sync_equal'] else 'NO':>6}"
              f"  {miss or '-'}{' (' + why + ')' if why else ''}"
              f"{' SYNC-MISS ' + str(r['sync_missed']) if r['sync_missed'] else ''}"
              f"{' CODE-NOT-REF ' + str(r['code_not_ref']) if r['code_not_ref'] else ''}")
    print(f"{len(rows)} traces; {len(rows) - bad} with hb_oracle equal to Detect (switches off)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

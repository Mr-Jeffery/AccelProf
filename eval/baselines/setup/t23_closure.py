#!/usr/bin/env python3
"""T23 (eval/R3_CLOSURE.md): which recorded kernels can R3's location closure change, and which
verdicts does it move?

R3's gates ask "do these two atomic pcs touch one location?" of same_loc, the pc pairs of
observed atomic edges; T23 reads the connected components of that relation instead
(sync_dominance.HBGraph.same_location). The closure only adds pairs and the gates are used
negated, so a verdict can move only on a kernel where it adds a pair that names a CAS pc (every
gate query has a CAS on one side). `scan` finds those kernels from the trace's edges and the
CFG's opcodes alone, with the same alignment rule as sync_dominance.analyze; every other kernel's
verdicts are identical by construction. `diff` analyzes the others twice, with
$CUVEIN_R3_LOC_CLOSURE=0 (the pre-T23 rule) and with the closure, and lists every verdict that
moves with the closure pairs the gates consulted and, on a dump with hb_events, whether the
records show the two pcs on one address.

  t23_closure.py scan --store <dir> [--ids FILE] [--modes vector-clock,scalar-clock]
                      [--shard K/N] --out scan.jsonl
  t23_closure.py scan --rtraw-root <dir> --out scan.jsonl          # X4's <label>/<node>/{cfg,runK}
  t23_closure.py ids  scan.jsonl [...]                              # programs with a growth pair
  t23_closure.py diff scan.jsonl [...] --out moves.jsonl [--shard K/N]
  t23_closure.py scan-summary scan.jsonl [...]                      # counts per store
  t23_closure.py summary moves.jsonl [...]

A harness store is <store>/<id>/{dots/*.dot, <mode>/kernel_*.json} (parallel.py analyze's layout).
"""
import argparse
import glob
import itertools
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "python"))
import sync_dominance as sd  # noqa: E402

_ATOMIC_TEXT = ("ATOM", "RED.")        # cheap superset tests on a dot's text (atomic, CAS)


def _harness_tasks(store, ids, modes):
    store = Path(store)
    names = [ids_ for ids_ in ids] if ids else sorted(p.name for p in store.iterdir()
                                                       if (p / "dots").is_dir())
    for name in names:
        for mode in modes:
            kernels = sorted(glob.glob(f"{store}/{name}/{mode}/kernel_*.json"))
            if kernels:
                yield {"tag": store.name, "id": name, "mode": mode,
                       "dot_dir": f"{store}/{name}/dots", "kernels": kernels}


def _rtraw_tasks(root):
    root = Path(root)
    for lab in sorted(p for p in root.iterdir() if p.is_dir()):
        mode = "scalar-clock" if "scalar-clock" in lab.name else "vector-clock"
        for node in sorted(p for p in lab.iterdir() if (p / "cfg").is_dir()):
            kernels = sorted(glob.glob(f"{node}/run*/kernel_*.json"))
            if kernels:
                yield {"tag": root.name, "id": f"{lab.name}/{node.name}", "mode": mode,
                       "dot_dir": f"{node}/cfg", "kernels": kernels}


def _read_ids(path):
    return [ln.split()[0] for ln in Path(path).read_text().splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]


def _shard(tasks, spec):
    if not spec:
        return tasks
    k, n = map(int, spec.split("/"))
    return [t for i, t in enumerate(tasks) if i % n == k]


def _aligned(dots, trace):
    """(dot path, pc -> opcode) of the first dot that aligns, as analyze() does; None if none."""
    for dot, kernels in dots:
        try:
            mangled = sd.select_kernel(kernels, trace["kernel"]["kernel_name"])
        except sd.AlignmentError:
            continue
        pc_opcode = {pc: op for ins in kernels[mangled][0].values() for pc, op in ins}
        pcs = {n["pc"] for n in trace.get("nodes", [])} | {
            e[k] for e in trace.get("edges", []) for k in ("current_pc", "ancient_pc")
            if e.get(k) is not None}
        if all(pc in pc_opcode and sd.classify(pc_opcode[pc]) == "mem" for pc in pcs):
            return dot, pc_opcode, pcs
    return None


def scan_task(task):
    base = {k: task[k] for k in ("tag", "id", "mode")}
    dot_paths = sorted(glob.glob(f"{task['dot_dir']}/*.dot"))
    if not dot_paths:
        yield {**base, "status": "no-dot"}
        return
    texts = [Path(p).read_text(errors="replace") for p in dot_paths]
    if not any(t in tx for tx in texts for t in _ATOMIC_TEXT):
        yield {**base, "status": "no-atomic-opcode", "kernels": len(task["kernels"])}
        return
    if not any(".CAS" in tx for tx in texts):   # every gate query names a CAS pc: nothing can move
        yield {**base, "status": "no-cas-opcode", "kernels": len(task["kernels"])}
        return
    dots = []
    for p in dot_paths:
        try:
            dots.append((p, sd.parse_dot(p)))
        except sd.AlignmentError:      # a dot with no kernel cluster: analyze() skips it too
            continue
    for kj in task["kernels"]:
        rec = {**base, "kernel": os.path.basename(kj), "path": kj}
        try:
            trace = json.loads(Path(kj).read_text())
        except (OSError, ValueError) as ex:     # a partial / unreadable kernel JSON: recorded
            yield {**rec, "status": "error", "error": repr(ex)[:300]}
            continue
        al = _aligned(dots, trace)
        if al is None:
            yield {**rec, "status": "no-aligned-dot"}
            continue
        dot, pc_opcode, pcs = al
        atom = {pc for pc in pcs if sd.atomic_scope(pc_opcode[pc]) is not None}
        same_loc = set()
        for e in trace.get("edges", []):
            cur, anc = e["current_pc"], e.get("ancient_pc")
            if e.get("cold_miss") or anc is None or cur not in atom or anc not in atom:
                continue
            same_loc.add(frozenset((cur, anc)))
        classes = sd.HBGraph._location_classes(same_loc)
        groups = defaultdict(list)
        for pc, rep in classes.items():
            groups[rep].append(pc)
        cas = {pc for pc in atom if "CAS" in pc_opcode[pc].split(".")}
        growth = [(a, b) for m in groups.values() for a, b in itertools.combinations(sorted(m), 2)
                  if frozenset((a, b)) not in same_loc]
        yield {**rec, "status": "scanned", "dot": dot, "atomic_pcs": len(atom), "cas_pcs": len(cas),
               "same_loc_pairs": len([p for p in same_loc if len(p) == 2]),
               "growth": len(growth),
               "growth_cas": [[hex(a), hex(b)] for a, b in growth if a in cas or b in cas],
               "classes": [[hex(p) for p in sorted(m)] for m in groups.values() if len(m) > 1]}


def cmd_scan(a):
    if a.rtraw_root:
        tasks = list(_rtraw_tasks(a.rtraw_root))
    else:
        modes = a.modes.split(",")
        tasks = list(_harness_tasks(a.store, _read_ids(a.ids) if a.ids else None, modes))
    tasks = _shard(tasks, a.shard)
    n = errors = 0
    with open(a.out, "w") as out:
        for t in tasks:
            try:
                recs = list(scan_task(t))
            except Exception as ex:     # recorded, never swallowed: the summary counts them
                recs = [{**{k: t[k] for k in ("tag", "id", "mode")}, "status": "error",
                         "error": repr(ex)[:300]}]
            errors += sum(r["status"] == "error" for r in recs)
            for rec in recs:
                out.write(json.dumps(rec) + "\n")
                n += 1
            out.flush()
    print(f"scan: {len(tasks)} (program, mode) tasks, {n} records, {errors} errors -> {a.out}")


def _load_jsonl(paths):
    for p in paths:
        for ln in open(p):
            if ln.strip():
                yield json.loads(ln)


def cmd_ids(a):
    seen = defaultdict(set)
    for r in _load_jsonl(a.files):
        if r.get("growth_cas"):
            seen[r["tag"]].add(r["id"])
    for tag, ids in sorted(seen.items()):
        for i in sorted(ids):
            print(f"{tag}\t{i}")


def _loc_evidence(trace, pairs):
    """For each closure pair (hex, hex): True if some record shows the two pcs on one address,
    False if the dump has records and none does, None without records."""
    events = trace.get("hb_events")
    if not events:
        return {tuple(p): None for p in pairs}
    want = {int(x, 16) for p in pairs for x in p}
    at = defaultdict(set)
    for e in events:
        if e.get("pc") in want and "lanes" in e:
            for ln in e["lanes"]:
                at[e["pc"]].add((e["space"], e["block"] if e["space"] == "shared" else 0,
                                 ln["addr"]))
    return {tuple(p): bool(at[int(p[0], 16)] & at[int(p[1], 16)]) for p in pairs}


def _analyze(dot, kj, closure):
    os.environ["CUVEIN_R3_LOC_CLOSURE"] = "1" if closure else "0"
    try:
        return sd.analyze(dot, kj)
    finally:
        os.environ.pop("CUVEIN_R3_LOC_CLOSURE", None)


def cmd_diff(a):
    recs = [r for r in _load_jsonl(a.files) if r.get("growth_cas")]
    recs = _shard(recs, a.shard)
    n_moved = 0
    with open(a.out, "w") as out:
        for r in recs:
            head = {k: r[k] for k in ("tag", "id", "mode", "kernel", "path")}
            try:
                old, new = _analyze(r["dot"], r["path"], False), _analyze(r["dot"], r["path"], True)
            except Exception as ex:             # recorded, counted by `summary`
                out.write(json.dumps({**head, "anomaly": "analyze raised", "error": repr(ex)[:300]})
                          + "\n")
                continue
            ov, nv = old["verdicts"], new["verdicts"]
            if len(ov) != len(nv) or any((x["current_pc"], x["ancient_pc"]) !=
                                         (y["current_pc"], y["ancient_pc"])
                                         for x, y in zip(ov, nv)):
                out.write(json.dumps({**head, "anomaly": "verdict lists differ in shape",
                                      "old_n": len(ov), "new_n": len(nv)}) + "\n")
                continue
            moves = [(x, y) for x, y in zip(ov, nv)
                     if (x["verdict"], x["hb_class"], x["hb_chain"]) !=
                     (y["verdict"], y["hb_class"], y["hb_chain"])]
            fired = [v for v in nv if v.get("r3_loc_closure")]
            rec = {**head, "analyzed": True, "verdicts": len(ov), "moved": len(moves),
                   "closure_fired": len(fired),
                   "summary_old": old.get("summary"), "summary_new": new.get("summary")}
            if moves:
                trace = json.loads(Path(r["path"]).read_text())
                pairs = sorted({tuple(p[1:]) for _, y in moves for p in y.get("r3_loc_closure", [])})
                ev = _loc_evidence(trace, pairs)
                rec["moves"] = [{
                    "current_pc": x["current_pc_hex"], "ancient_pc": x["ancient_pc_hex"],
                    "race_type": x["race_type"], "space": x["space"],
                    "observed_distance": x["observed_distance"],
                    "event_candidate": x["event_candidate"],
                    "old": {k: x[k] for k in ("verdict", "hb_class", "hb_chain", "a2_uncertain")},
                    "new": {k: y[k] for k in ("verdict", "hb_class", "hb_chain", "a2_uncertain")},
                    "closure": y.get("r3_loc_closure"),
                    "same_address_in_records": [ev[tuple(p[1:])] for p in
                                                y.get("r3_loc_closure", [])],
                } for x, y in moves]
                n_moved += len(moves)
            out.write(json.dumps(rec) + "\n")
            out.flush()
    print(f"diff: {len(recs)} kernels analyzed twice, {n_moved} verdicts moved -> {a.out}")


def cmd_scansummary(a):
    by = defaultdict(Counter)
    for r in _load_jsonl(a.files):
        c = by[r["tag"]]
        c["records"] += 1
        c[r["status"]] += 1
        c["cas-kernels"] += bool(r.get("cas_pcs"))
        c["growth-kernels"] += bool(r.get("growth"))
        c["growth-with-a-CAS-kernels"] += bool(r.get("growth_cas"))
        if r["status"] != "scanned":
            c["tasks-" + r["status"]] += 0
    for tag, c in sorted(by.items()):
        print(tag + ": " + ", ".join(f"{k}={v}" for k, v in sorted(c.items()) if v))


def cmd_summary(a):
    kernels = moved_k = fired_k = moves = 0
    by = Counter()
    anomalies = []
    for r in _load_jsonl(a.files):
        if r.get("anomaly"):
            anomalies.append(r)
            continue
        kernels += 1
        fired_k += bool(r["closure_fired"])
        moved_k += bool(r["moved"])
        for m in r.get("moves", ()):
            moves += 1
            by[(r["mode"], m["old"]["verdict"], m["old"]["hb_class"], m["new"]["verdict"],
                m["new"]["hb_class"])] += 1
    print(f"kernels analyzed twice: {kernels}; closure fired in {fired_k}; "
          f"verdicts moved in {moved_k} kernels ({moves} verdict records); anomalies: "
          f"{len(anomalies)}")
    for (mode, ov, oc, nv, nc), n in sorted(by.items()):
        print(f"  {mode}: {ov}/{oc} -> {nv}/{nc}: {n}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("--store")
    s.add_argument("--rtraw-root")
    s.add_argument("--ids")
    s.add_argument("--modes", default="vector-clock,scalar-clock")
    s.add_argument("--shard")
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_scan)
    i = sub.add_parser("ids")
    i.add_argument("files", nargs="+")
    i.set_defaults(fn=cmd_ids)
    d = sub.add_parser("diff")
    d.add_argument("files", nargs="+")
    d.add_argument("--shard")
    d.add_argument("--out", required=True)
    d.set_defaults(fn=cmd_diff)
    ss = sub.add_parser("scan-summary")
    ss.add_argument("files", nargs="+")
    ss.set_defaults(fn=cmd_scansummary)
    m = sub.add_parser("summary")
    m.add_argument("files", nargs="+")
    m.set_defaults(fn=cmd_summary)
    a = ap.parse_args()
    if a.cmd == "scan" and not (a.store or a.rtraw_root):
        ap.error("scan needs --store or --rtraw-root")
    a.fn(a)


if __name__ == "__main__":
    main()

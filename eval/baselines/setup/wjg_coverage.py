#!/usr/bin/env python3
"""WARPSYNC join gap: how much of X1's final recording the measured records cover (read only).

  wjg_coverage.py --dir eval/results/wjg [--x1 final-2026-10] [--procs 16]

X1's stores keep aggregates only (no hb_events), so the census can only be taken on older
recordings. For every (program, mode) of X1's main store (<x1>/<id>/<mode>/ with a kernel JSON):
  same binary   some row of rows.csv with records, in a complete run directory (<id>/<mode>, not a
                timed-out run's <mode>-partial-repN), has the same program and mode and its program
                directory's dots include every dot md5 of X1's program
  partial only  the same, but only timed-out runs' partial dumps match
  other binary  rows with records exist for (program, mode), none with X1's dot md5s
  none          no row with records for (program, mode)
Static facts per X1 program, from its dots' text: instructions whose opcode is WARPSYNC, and
whether a CALL targets CUDA's out-of-line warpsync helper (`..._warpsync`). Writes
coverage.json and coverage.md.
"""
import argparse
import collections
import csv
import glob
import hashlib
import json
import multiprocessing as mp
import os
import re

ROOT = "/mnt/beegfs/fzheng4/cuvein_traces"
# an instruction inside a dot label: `0150:\ \ \ NOP\ ;` (spaces escaped), optional predicate
INSTR = re.compile(r"([0-9a-f]{4,}):(?:\\ )+(@!?U?P[T0-9]+(?:\\ )+)?([A-Z][A-Z0-9_.]*)")


def dot_facts(path):
    b = open(path, "rb").read()
    txt = b.decode(errors="replace")
    ops = collections.Counter(m.group(3).split(".")[0] for m in INSTR.finditer(txt))
    return {"md5": hashlib.md5(b).hexdigest(), "warpsync": ops.get("WARPSYNC", 0),
            "helper_call": bool(re.search(r"CALL[^;]*warpsync", txt)),
            "nop": ops.get("NOP", 0), "bar": ops.get("BAR", 0)}


def prog_dots(pdir):
    return {os.path.basename(d): dot_facts(d) for d in sorted(glob.glob(f"{pdir}/dots/*.dot"))}


def store_root(tag):
    if tag.startswith("home:"):
        return f"/mnt/beegfs/fzheng4/home_archive/eval_baselines/{tag[5:]}"
    if tag.startswith("other:"):
        return f"/mnt/beegfs/fzheng4/{tag[6:]}"
    return f"{ROOT}/{tag}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--x1", default="final-2026-10")
    ap.add_argument("--procs", type=int, default=16)
    a = ap.parse_args()
    x1root = f"{ROOT}/{a.x1}"
    x1 = {}
    for pdir in sorted(glob.glob(f"{x1root}/*/")):
        pid = os.path.basename(pdir.rstrip("/"))
        modes = [m for m in ("vector-clock", "scalar-clock") if glob.glob(f"{pdir}{m}/kernel_*.json")]
        x1[pid] = modes
    rows = [r for r in csv.DictReader(open(f"{a.dir}/rows.csv")) if int(r.get("with_records") or 0) > 0]
    pdirs = sorted({f"{store_root(r['store'])}/{r['id']}" for r in rows} | {f"{x1root}/{p}" for p in x1})
    with mp.Pool(a.procs) as pool:
        facts = dict(zip(pdirs, pool.map(prog_dots, pdirs, chunksize=4)))
    rec = collections.defaultdict(list)            # (id, mode) -> [(store, complete?, md5 set)]
    for r in rows:
        mode = r["mode"]
        base = mode.split("-partial-rep")[0]
        if base not in ("vector-clock", "scalar-clock") or r["rundir"] != f"{r['id']}/{mode}":
            continue
        md5s = {f["md5"] for f in facts[f"{store_root(r['store'])}/{r['id']}"].values()}
        rec[(r["id"], base)].append((r["store"], "-partial-rep" not in mode, md5s))
    out, tab = [], collections.defaultdict(collections.Counter)
    for pid, modes in x1.items():
        xf = facts[f"{x1root}/{pid}"]
        xm = {f["md5"] for f in xf.values()}
        ws = sum(f["warpsync"] for f in xf.values())
        helper = any(f["helper_call"] for f in xf.values())
        for mode in modes:
            cands = rec.get((pid, mode), [])
            same = [s for s, comp, m in cands if comp and xm and xm <= m]
            part = [s for s, comp, m in cands if not comp and xm and xm <= m]
            cls = "same binary" if same else "partial only" if part else \
                  "other binary" if cands else "none"
            out.append({"id": pid, "mode": mode, "class": cls, "stores": same or part,
                        "warpsync_instrs": ws, "helper_call": helper, "dots": len(xf)})
            suite = pid.split("-", 1)[0]
            tab[(suite, mode)][cls] += 1
            tab[(suite, mode)]["programs"] += 1
            tab[(suite, mode)]["with WARPSYNC"] += ws > 0
            tab[(suite, mode)]["with WARPSYNC, not covered"] += ws > 0 and cls != "same binary"
            tab[(suite, mode)]["helper call"] += helper
    json.dump(out, open(f"{a.dir}/coverage.json", "w"), indent=0)
    L = ["| suite | mode | X1 programs | same binary | partial only | other binary | none | "
         "with a WARPSYNC instruction | ... of them not covered (same binary) | with a warpsync-helper CALL |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    tot = collections.Counter()
    for (suite, mode), c in sorted(tab.items()):
        tot.update(c)
        L.append(f"| {suite} | {mode} | {c['programs']} | {c['same binary']} | {c['partial only']} | "
                 f"{c['other binary']} | {c['none']} | {c['with WARPSYNC']} | "
                 f"{c['with WARPSYNC, not covered']} | {c['helper call']} |")
    L.append(f"| **all** | both | {tot['programs']} | {tot['same binary']} | {tot['partial only']} | "
             f"{tot['other binary']} | {tot['none']} | {tot['with WARPSYNC']} | "
             f"{tot['with WARPSYNC, not covered']} | {tot['helper call']} |")
    open(f"{a.dir}/coverage.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()

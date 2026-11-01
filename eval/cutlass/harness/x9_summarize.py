#!/usr/bin/env python3
"""X9 step 4 roll-up: read every pair file eval/results/cutlass/pairs/<flavor>/<id>.json (per-kernel sub-ids <parent>__kNNN
and the gate ids), map each to its family (manifest `target` of the parent id), and
  - count pair statuses per family (CONFIRMED / BARRIER-ORDERED / RECLASSIFIED / ON-ONLY);
  - ON-ONLY anywhere = subset violation (scalar-clock reports a pair collector-only mode does not): listed first, exit 3;
  - dedupe reported pairs by (family, space, innermost CUTLASS-tree frame of a, of b) (unordered), keeping per group:
    statuses, pairs, kernels, kernel classes (cutlass::gemm::kernel::<Class> from the mangled name), race types,
    verdicts, sample SASS, full frame stacks of one representative, parent ids.
A t5400 pair file replaces nothing: main and t5400 ids are disjoint (t5400 = main timeouts re-recorded).
Writes <out>/summary.json, <out>/groups.tsv, <out>/families.tsv.
usage: x9_summarize.py [--out eval/results/cutlass/summary]"""
import argparse, collections, csv, glob, json, os, re, sys
W = "/home/fzheng4/wt-x9"
ap = argparse.ArgumentParser()
ap.add_argument("--out", default=f"{W}/eval/results/cutlass/summary")
a = ap.parse_args()
fam = {r["id"]: r["target"] for r in csv.DictReader(open(f"{W}/eval/cutlass/manifest_cutlass.csv", newline=""))}
SRC = "/mnt/beegfs/fzheng4/cutlass/src/cutlass-v4.8.1/"
short = lambda f: f["file"].replace(SRC, "") + ":" + str(f["line"])
def cframe(frames, pc):
    """innermost frame inside the CUTLASS tree (CUDA headers such as cuda_fp16.hpp / atomic functions skipped)."""
    if not frames:
        return f"pc{pc}"
    return short(next((x for x in frames if x["file"].startswith(SRC)), frames[0]))
def kclass(m):
    i = m.find("kernel")
    mm = re.match(r"(\d+)", m[i + 6:]) if i >= 0 else None
    return m[i + 6 + len(mm.group(1)): i + 6 + len(mm.group(1)) + int(mm.group(1))] if mm else m[:40]
fams = collections.defaultdict(collections.Counter)
groups = {}
files = errs = 0
onlys = []
for fl in ("main", "t5400"):
    for p in sorted(glob.glob(f"{W}/eval/results/cutlass/pairs/{fl}/*.json")):
        sid = os.path.basename(p)[:-5]
        parent = sid.split("__k")[0]
        f = fam.get(parent, "?")
        try:
            d = json.load(open(p))
        except ValueError:
            errs += 1; continue
        files += 1
        fams[f]["files"] += 1
        for st, n in (d.get("status_counts") or {}).items():
            fams[f][st] += n
        for q in d.get("pairs") or ():
            st = q.get("status")
            if st == "ON-ONLY":
                onlys.append((fl, sid, q["space"], q["a_pc"], q["b_pc"]))
            if st in ("-", None):
                continue
            fa, fb = cframe(q.get("frames_a"), q["a_pc"]), cframe(q.get("frames_b"), q["b_pc"])
            key = (f, q["space"]) + tuple(sorted((fa, fb)))
            g = groups.setdefault(key, dict(status=collections.Counter(), pairs=0, kernels=set(), classes=set(),
                                            rt=set(), verdicts=set(), sass=set(), parents=set(), rep=None))
            g["status"][st] += 1; g["pairs"] += 1; g["kernels"].add(q["kid"]); g["classes"].add(kclass(q["kernel"]))
            half = q["on"] if q["on"].get("verdicts") else q["off"]
            g["rt"].update(half.get("rt") or ()); g["verdicts"].update(half.get("verdicts") or ())
            g["sass"].add((q.get("sass_a"), q.get("sass_b"))); g["parents"].add(f"{fl}:{parent}")
            if g["rep"] is None:
                g["rep"] = dict(sid=sid, a_pc=q["a_pc"], b_pc=q["b_pc"], frames_a=[short(x) for x in q.get("frames_a") or ()],
                                frames_b=[short(x) for x in q.get("frames_b") or ()], on=q["on"], off=q["off"])
os.makedirs(a.out, exist_ok=True)
gl = sorted(groups.items(), key=lambda kv: (kv[0][0], -kv[1]["pairs"]))
out = dict(files=files, unreadable=errs, on_only=onlys, families={k: dict(v) for k, v in fams.items()},
           groups=[dict(family=k[0], space=k[1], a=k[2], b=k[3], status=dict(g["status"]), pairs=g["pairs"],
                        kernels=len(g["kernels"]), classes=sorted(g["classes"]), race_types=sorted(g["rt"]),
                        verdicts=sorted(g["verdicts"]), sass=sorted(map(list, g["sass"]))[:6], parents=sorted(g["parents"]),
                        rep=g["rep"]) for k, g in gl])
json.dump(out, open(f"{a.out}/summary.json", "w"), indent=1)
with open(f"{a.out}/groups.tsv", "w") as t:
    t.write("family\tspace\tframe_a\tframe_b\tpairs\tkernels\tstatus\tclasses\trace_types\tverdicts\n")
    for g in out["groups"]:
        t.write("\t".join(map(str, (g["family"], g["space"], g["a"], g["b"], g["pairs"], g["kernels"],
                                    ";".join(f"{k}={v}" for k, v in sorted(g["status"].items())), ";".join(g["classes"]),
                                    ";".join(g["race_types"]), ";".join(g["verdicts"])))) + "\n")
with open(f"{a.out}/families.tsv", "w") as t:
    cols = ["files", "CONFIRMED", "BARRIER-ORDERED", "RECLASSIFIED", "ON-ONLY"]
    t.write("family\t" + "\t".join(cols) + "\tgroups\n")
    for f, c in sorted(fams.items()):
        t.write(f + "\t" + "\t".join(str(c.get(x, 0)) for x in cols) + f"\t{sum(1 for g in out['groups'] if g['family'] == f)}\n")
print(f"{files} pair files ({errs} unreadable), {len(out['groups'])} groups, ON-ONLY {len(onlys)} -> {a.out}")
print(open(f"{a.out}/families.tsv").read())
sys.exit(3 if onlys else 0)

#!/usr/bin/env python3
"""X13: numbers for eval/PER_KERNEL_TABLES.md (sections 2, 3, 4) from eval/results/per-kernel/*.csv."""
import collections, csv, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
D = f"{APH}/eval/results/per-kernel"
suite = lambda b: "P9" if b.startswith("hecbench:") else re.search(r"/bin/(P[0-9I]+)/", b).group(1)
nk = lambda s: s.replace(" ", "")
# inventory
cub = collections.defaultdict(set)
for r in csv.DictReader(open(f"{D}/cubin_kernels.csv")):
    if r["status"] == "ok" and r["is_entry"] == "1" and "/native/" not in r["exe"]:
        cub[r["exe"]].add(nk(r["demangled"]))
launched = collections.defaultdict(set)
for r in csv.DictReader(open(f"{D}/inventory.csv")):
    if int(r["launches"]) > 0:
        launched[r["binary"]].add(nk(r["kernel"]))
rows = []
for b, ks in launched.items():
    exe = b if not b.startswith("hecbench:") else f"/home/fzheng4/AccelProf/eval/baselines/bin/P9/{b.split(':')[1]}-cuda"
    rows.append((suite(b), b, len(cub.get(exe, ())), len(ks)))
agg = collections.defaultdict(lambda: collections.Counter())
for s, b, nc, nl in rows:
    agg[s][(nc, nl)] += 1
print("## inventory: suite -> (in_cubin, launched): binaries")
for s in sorted(agg): print(s, dict(sorted(agg[s].items())))
print("binaries with launched < cubin entries:")
for s, b, nc, nl in sorted(rows):
    if nl != nc and s != "PI": print("  ", s, os.path.basename(b), "cubin", nc, "launched", nl)
print("PI binaries with launched != cubin:", sum(1 for s, b, nc, nl in rows if s == "PI" and nl != nc))
# verdicts
lab = {}
for r in csv.DictReader(open(f"{D}/labels.csv")):
    lab[(r["binary"], r["kernel"])] = r["label"]
ver = []
for f in ("kernel_verdicts_curace.csv", "kernel_verdicts_baselines.csv"):
    for r in csv.DictReader(open(f"{D}/{f}")):
        ver.append(r)
# curace details
cd = {}
for r in csv.DictReader(open(f"{D}/curace.csv")):
    cd[(r["binary"], r["mode"], r["kernel"])] = r
bl = collections.defaultdict(list)
for r in csv.DictReader(open(f"{D}/baselines.csv")):
    bl[(r["tool"], r["binary"], r["kernel"])].append(r["reported_locations"])
fp = []
for r in ver:
    L = lab.get((r["binary"], r["kernel"]), "")
    if r["verdict"] == "RACE" and L == "CLEAN":
        mode = r["mode"] or ""
        detail = ""
        if r["tool"] == "cuvein":
            x = cd.get((r["binary"], mode, r["kernel"]))
            detail = (x["pairs"] + " | " + x["classes"]) if x else ""
        else:
            detail = ";".join(sorted(set(bl.get((r["tool"], r["binary"], r["kernel"]), []))))[:200]
        fp.append([suite(r["binary"]), r["tool"], mode, r["binary"], r["kernel"], detail])
with open(f"{D}/fp_kernels.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["suite", "tool", "mode", "binary", "kernel", "pc_pairs_or_lines | classes"]); w.writerows(fp)
c = collections.Counter((x[0], x[1] + ("/" + x[2] if x[2] else "")) for x in fp)
print("## reports in race-free kernels: (suite, tool/mode) -> kernels")
for k, v in sorted(c.items()): print(k, v)
ct = collections.Counter(x[1] + ("/" + x[2] if x[2] else "") for x in fp)
print("TOTAL per tool/mode:", dict(ct))
# split by whether the binary is race-free labelled or racy-binary kernel
bl_lab = {}
for r in csv.DictReader(open(f"{D}/kernel_verdicts_curace.csv")):
    bl_lab[r["binary"]] = r["binary_label"]
inracy = collections.Counter(x[1] + ("/" + x[2] if x[2] else "") for x in fp if bl_lab.get(x[3]) == "RACE")
print("of which in a kernel of a RACY-labelled binary:", dict(inracy))
# missed racy kernels in a binary the tool reported
byb = collections.defaultdict(dict)
for r in ver:
    byb[(r["tool"], r["mode"], r["binary"])][r["kernel"]] = r["verdict"]
miss = []
for (t, m, b), kv in byb.items():
    if any(v == "RACE" for v in kv.values()):
        for k, v in kv.items():
            if lab.get((b, k)) == "RACE" and v != "RACE":
                miss.append([suite(b), t, m, b, k, v])
with open(f"{D}/missed_kernels.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["suite", "tool", "mode", "binary", "kernel", "verdict"]); w.writerows(miss)
cm = collections.Counter((x[0], x[1] + ("/" + x[2] if x[2] else "")) for x in miss)
print("## racy kernels missed in a binary the tool reported: (suite, tool/mode) -> kernels")
for k, v in sorted(cm.items()): print(k, v)
print("TOTAL:", dict(collections.Counter(x[1] + ("/" + x[2] if x[2] else "") for x in miss)))
# never launched cubin kernels
nl = [(suite(b), os.path.basename(b), len(cub[b] - launched.get(b, set()))) for b in launched if suite(b) != "P9" and cub.get(b, set()) - launched.get(b, set())]
print("never-launched (cubin entry not launched) non-HeCBench binaries:", len(nl), nl[:12])
for p in ("atomicCAS", "dxtc2", "knn", "tridiagonal", "expdist", "overlap", "fpc", "gpp", "crs", "mr"):
    b = f"hecbench:{p}"
    exe = f"/home/fzheng4/AccelProf/eval/baselines/bin/P9/{p}-cuda"
    print("HeCBench", p, "cubin", len(cub.get(exe, ())), "launched", len(launched.get(b, ())), "not launched:", sorted(cub.get(exe, set()) - launched.get(b, set()))[:4])

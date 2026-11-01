#!/usr/bin/env python3
"""X9 harness: keep in <store>/<id>/dots only the CFG dots that can align a recorded kernel, move the rest to
<store>/<id>/dots_pruned/ (a CUTLASS unit-test binary carries one cubin per translation unit, 14-36 dots of up to tens of MB,
and the alignment stage parses them in order for every new kernel name: 3.6 s for a median dot, > 90 s for the largest).
A dot is kept iff one of its `subgraph cluster_<mangled>` names demangles (c++filt) to a recorded kernel_name, whitespace
removed -- the exact-match branch of sync_dominance.select_kernel. When some recorded kernel name matches no dot by that
rule, nothing is pruned (select_kernel's fallback branch could then pick a dot) and the id is reported.
Idempotent; writes dots_pruned/PRUNED.json {kept, pruned, unmatched}.
usage: x9_prune_dots.py <store>/<id>"""
import glob, json, os, re, shutil, subprocess, sys
idir = sys.argv[1]
norm = lambda s: re.sub(r"\s+", "", s)
names = set()
for kj in glob.glob(f"{idir}/scalar-clock/kernel_*.json"):
    with open(kj) as f:
        head = f.read(1 << 20)
    m = re.search(r'"kernel_name"\s*:\s*"((?:[^"\\]|\\.)*)"', head)
    if m:
        names.add(norm(json.loads(f'"{m.group(1)}"')))
    else:
        names.add(norm(json.load(open(kj))["kernel"]["kernel_name"]))
dots = sorted(glob.glob(f"{idir}/dots/*.dot"))
pd = f"{idir}/dots_pruned"
keep, matched = [], set()
for d in dots:
    txt = open(d, errors="replace").read()
    cl = sorted(set(re.findall(r'subgraph\s+"?cluster_([A-Za-z0-9_$.]+)', txt)))
    dm = subprocess.run(["c++filt"], input="\n".join(cl), capture_output=True, text=True).stdout.splitlines() if cl else []
    hit = {norm(x) for x in dm} & names
    if hit:
        keep.append(d); matched |= hit
unmatched = sorted(names - matched)
if unmatched or not keep:
    print(f"prune: {os.path.basename(idir)}: {len(unmatched)} recorded kernel name(s) match no dot exactly; nothing pruned")
    sys.exit(0)
os.makedirs(pd, exist_ok=True)
pruned = [d for d in dots if d not in keep]
for d in pruned:
    shutil.move(d, f"{pd}/{os.path.basename(d)}")
prev = json.load(open(f"{pd}/PRUNED.json")) if os.path.exists(f"{pd}/PRUNED.json") else {"pruned": []}
json.dump({"kept": [os.path.basename(d) for d in keep],
           "pruned": sorted(set(prev["pruned"]) | {os.path.basename(d) for d in pruned}),
           "kernel_names": len(names), "rule": "cluster name demangles to a recorded kernel_name"},
          open(f"{pd}/PRUNED.json", "w"), indent=1)
print(f"prune: {os.path.basename(idir)}: {len(names)} kernel names, kept {len(keep)} dot(s), pruned {len(pruned)}")

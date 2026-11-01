#!/usr/bin/env python3
"""X9 harness: split one whole-binary recording <store>/<id> into per-kernel sub-stores <store>/<id>__kNNN, one per
recorded kernel name, so that step 4 analyzes each kernel against only the dot(s) it can align (a whole CUTLASS test
binary records 3-272 kernel names over 14-84 cubins; the alignment stage parses the dots in order for every new kernel
name, > 25 min per name on the unpruned gate stores).
A sub-store holds symlinks: scalar-clock/kernel_*.json of that kernel name, dots/<dot> for every dot one of whose
`subgraph cluster_<mangled>` names demangles (c++filt) to that kernel name, whitespace removed (the exact-match branch of
sync_dominance.select_kernel; the rule x9_prune_dots.py uses and the X9 gate checked against unpruned analysis: identical
pairs and verdicts). A kernel name no dot matches exactly keeps every dot (select_kernel's fallback branch could pick any).
meta.json is copied with "id" set to the sub-id and "x9_split" = {parent, kernel_name, dots, launches}.
Rows for the sub-ids (the parent's manifest row, id and `kernel` replaced) are written to --manifest-out (replacing
earlier rows of the same parent). Idempotent.
usage: x9_split.py --store S --id ID --manifest M --manifest-out MK"""
import argparse, csv, glob, json, os, re, shutil, subprocess

ap = argparse.ArgumentParser()
ap.add_argument("--store", required=True)
ap.add_argument("--id", required=True)
ap.add_argument("--manifest", required=True)
ap.add_argument("--manifest-out", required=True)
a = ap.parse_args()
norm = lambda s: re.sub(r"\s+", "", s)
idir = f"{a.store}/{a.id}"
byname = {}
for kj in sorted(glob.glob(f"{idir}/scalar-clock/kernel_*.json")):
    with open(kj) as f:
        head = f.read(1 << 20)
    m = re.search(r'"kernel_name"\s*:\s*"((?:[^"\\]|\\.)*)"', head)
    name = json.loads(f'"{m.group(1)}"') if m else json.load(open(kj))["kernel"]["kernel_name"]
    byname.setdefault(name, []).append(kj)
dotnames = {}
dots = sorted(glob.glob(f"{idir}/dots/*.dot"))
for d in dots:
    txt = open(d, errors="replace").read()
    cl = sorted(set(re.findall(r'subgraph\s+"?cluster_([A-Za-z0-9_$.]+)', txt)))
    dm = subprocess.run(["c++filt"], input="\n".join(cl), capture_output=True, text=True).stdout.splitlines() if cl else []
    dotnames[d] = {norm(x) for x in dm}
rows = list(csv.DictReader(open(a.manifest, newline="")))
cols = list(rows[0].keys())
parent = next(r for r in rows if r["id"] == a.id)
meta = json.load(open(f"{idir}/meta.json"))
for old in glob.glob(f"{idir}__k*"):
    shutil.rmtree(old)
new = []
for i, (name, kjs) in enumerate(sorted(byname.items())):
    sid = f"{a.id}__k{i:03d}"
    sdir = f"{a.store}/{sid}"
    hit = [d for d in dots if norm(name) in dotnames[d]]
    use = hit or dots
    for sub in ("scalar-clock", "dots"):
        os.makedirs(f"{sdir}/{sub}", exist_ok=True)
    for kj in kjs:
        os.symlink(os.path.realpath(kj), f"{sdir}/scalar-clock/{os.path.basename(kj)}")
    for d in use:
        os.symlink(os.path.realpath(d), f"{sdir}/dots/{os.path.basename(d)}")
    sm = dict(meta, id=sid, x9_split=dict(parent=a.id, kernel_name=name, launches=len(kjs),
                                          dots=[os.path.basename(d) for d in use], exact_dot_match=bool(hit)))
    json.dump(sm, open(f"{sdir}/meta.json", "w"))
    r = dict(parent, id=sid, kernel=name[:2000])
    new.append(r)
    print(f"{sid}\t{len(kjs)} launches\t{len(use)} dot(s){'' if hit else ' (no exact match: all dots)'}\t{name[:150]}")
mrows = list(csv.DictReader(open(a.manifest_out, newline=""))) if os.path.exists(a.manifest_out) else []
mrows = [r for r in mrows if not r["id"].startswith(a.id + "__k")] + new
with open(a.manifest_out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(mrows)
print(f"split: {a.id}: {len(byname)} kernel names, {sum(len(v) for v in byname.values())} launches, {len(dots)} dots")

#!/usr/bin/env python3
"""X11 stage A: build a run tree of the artifact's native HeCBench binaries and a manifest for
parallel.py. Layout mirrors the artifact's cwd ($HECBENCH_PATH/src/<app>-cuda, inputs at ../<x>-sycl/data).
  python x11_mktree.py TREE [app,app,...]   (needs /mnt/beegfs; no GPU)"""
import csv, hashlib, json, os, shutil, sys
TREE = sys.argv[1]
AP = "/home/fzheng4/AccelProf"
SC = f"{AP}/eval/baselines/setup/tools/supercollider/supercollider-artifacts"
CORP = os.path.realpath(f"{AP}/eval/baselines/corpora/HeCBench/src")
FIELDS = ["id", "pset", "program", "build", "input", "exe", "args", "stdin", "shared_mem", "label",
          "arrays_to_wrap", "monitored_kernels", "reps", "timeout"]
sub = json.load(open(f"{SC}/scripts/hecbench/benchmarks/artifact_subset.json"))["benchmarks"]
only = sys.argv[2].split(",") if len(sys.argv) > 2 and sys.argv[2] else list(sub)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
rows = []
for app in only:
    cfg = sub[app]
    d = f"{TREE}/src/{app}-cuda"
    os.makedirs(d, exist_ok=True)
    src = f"{SC}/bin/hecbench/native/{app}"
    exe = f"{d}/{app}"
    if not os.path.exists(exe) or sha(exe) != sha(src):
        shutil.copy2(src, exe)
    assert sha(exe) == sha(src)
    rows.append(dict(id=f"X11-{app}", pset="P9", program=f"{app}-cuda", build="sc-native",
                     input="sc-artifact", exe=exe, args=" ".join(cfg.get("args", [])), stdin="",
                     shared_mem=0, label="RACE" if cfg.get("racy") else "CLEAN", arrays_to_wrap="",
                     monitored_kernels="", reps=1, timeout=84600))
    print(app, sha(exe)[:16], flush=True)
for dd in ("dxtc2-sycl",):
    link = f"{TREE}/src/{dd}"
    if not os.path.lexists(link):
        os.symlink(f"{CORP}/{dd}", link)
with open(f"{TREE}/manifest.csv", "w", newline="") as f:
    w = csv.DictWriter(f, FIELDS)
    w.writeheader()
    w.writerows(rows)

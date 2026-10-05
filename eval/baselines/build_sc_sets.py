#!/usr/bin/env python3
"""Build the two program sets that mirror SuperCollider's (PLDI'26) artifact, so the
other detectors can be run on exactly the programs SuperCollider ships instrumented.

SuperCollider is a pass inside NVIDIA's proprietary `ptxas`; the artifact (Zenodo
10.5281/zenodo.19058944) cannot instrument new programs -- it only ships
pre-instrumented binaries for cuHadron (= our P6), 99 original-Indigo tests and 10
HeCBench apps. This script compiles those same programs from the same sources with
OUR recipe (-lineinfo --cudart shared, sm_89) for cuVein / iGUARD / compute-sanitizer:

  P8  Indigo, SuperCollider's 99-test subset. Sources: the HiRace SC24 artifact's
      indigo/indigo_sources/<pattern>/<test>.cu (the artifact's binaries embed that
      path), include dir indigo/indigo_include. Label = the artifact's own ground
      truth (gen_table_indigo_detection.py): RACE if the name has "Bug" and not
      "boundsBug"; CLEAN if no "Bug"; boundsBug tests are excluded (label '').
  P9  HeCBench, SuperCollider's 10-app subset, with the artifact's args and its
      racy/race-free flag (scripts/hecbench/benchmarks/artifact_subset.json) as the
      label (source: the SuperCollider paper's Table 1, not an independent oracle).

Writes bin/P8|P9/manifest_rows.csv (mk_manifest.rows_cloned reads them). Needs nvcc.
  BASELINE_SM=89 .env/bin/python eval/baselines/build_sc_sets.py
"""
import csv
import glob
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blib

SC = f"{HERE}/setup/tools/supercollider/supercollider-artifacts"
HIRACE = f"{HERE}/setup/tools/HiRace/indigo"
HEC = f"{HERE}/corpora/HeCBench/src"
BIN = f"{HERE}/bin"
SM = os.environ.get("BASELINE_SM", "89")
# The artifact's subset JSON lists no args for `mr`, but the public HeCBench mr-cuda
# exits with a usage message without <repeat>; use its Makefile `run:` default for
# OUR build (the artifact's own binary runs argument-less and is left as shipped).
NEEDS_MAKEFILE_ARGS = {"mr": "100"}
FIELDS = ["id", "pset", "program", "build", "input", "exe", "args", "stdin",
          "shared_mem", "label", "arrays_to_wrap", "monitored_kernels", "reps", "timeout"]


def _p2_graph():
    for r in csv.DictReader(open(f"{HERE}/manifest.csv", newline="")):
        if r["pset"] == "P2":
            return r["args"].split()[0]
    g = sorted(glob.glob(f"{HIRACE}/input/*.egr"))
    return g[0] if g else ""


def sc_label(name):
    if "boundsBug" in name:
        return ""                       # excluded by the artifact's ground truth
    return "RACE" if "Bug" in name else "CLEAN"


def build_p8(env):
    os.makedirs(f"{BIN}/P8", exist_ok=True)
    graph = _p2_graph()
    rows, ok = [], 0
    tests = sorted(glob.glob(f"{SC}/bin/indigo/instrumented/*/*.out"))
    for t in tests:
        pat = os.path.basename(os.path.dirname(t))
        name = os.path.basename(t)[:-4]
        src = f"{HIRACE}/indigo_sources/{pat}/{name}.cu"
        exe = f"{BIN}/P8/{name}"
        if os.path.exists(src):
            r = subprocess.run(["nvcc", "-O3", f"-arch=sm_{SM}", "-lineinfo", "--cudart",
                                "shared", "-ccbin", "/usr/bin/g++", "-I",
                                f"{HIRACE}/indigo_include", "-o", exe, src],
                               env=env, stderr=subprocess.PIPE)
            if not os.path.exists(exe):
                print(f"  FAIL {name}: {r.stderr.decode()[-160:]}")
        ok += os.path.exists(exe)
        rows.append(dict(id=f"P8-{name}", pset="P8", program=name, build="default",
                         input=os.path.basename(graph).split("_")[0] + "-100n", exe=exe,
                         args=f"{graph} 256 4", stdin="", shared_mem=0,
                         label=sc_label(name), arrays_to_wrap="",
                         monitored_kernels=pat, reps=3, timeout=600))
    _write("P8", rows)
    print(f"P8: {ok}/{len(tests)} built, labels: "
          f"RACE={sum(r['label']=='RACE' for r in rows)} "
          f"CLEAN={sum(r['label']=='CLEAN' for r in rows)} "
          f"excluded(boundsBug)={sum(r['label']=='' for r in rows)}")


def build_p9(env):
    os.makedirs(f"{BIN}/P9", exist_ok=True)
    sub = json.load(open(f"{SC}/scripts/hecbench/benchmarks/artifact_subset.json"))["benchmarks"]
    rows, ok = [], 0
    for app, cfg in sub.items():
        d = f"{HEC}/{app}-cuda"
        exe = f"{BIN}/P9/{app}-cuda"
        if os.path.isdir(d):
            subprocess.run(["make", "clean"], cwd=d, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            r = subprocess.run(["make", f"ARCH=sm_{SM}", "CC=nvcc",
                                "EXTRA_CFLAGS=-ccbin /usr/bin/g++ -lineinfo --cudart shared"],
                               cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            if r.returncode == 0 and os.path.exists(f"{d}/main"):
                shutil.copy(f"{d}/main", exe)
            else:
                print(f"  FAIL {app}: {r.stderr.decode()[-200:]}")
        ok += os.path.exists(exe)
        args = " ".join(cfg.get("args", []))
        if not args and app in NEEDS_MAKEFILE_ARGS:
            args = NEEDS_MAKEFILE_ARGS[app]
        rows.append(dict(id=f"P9-{app}-cuda", pset="P9", program=f"{app}-cuda",
                         build="default", input="sc-artifact", exe=exe,
                         args=args, stdin="", shared_mem=0,
                         label="RACE" if cfg.get("racy") else "CLEAN", arrays_to_wrap="",
                         monitored_kernels="", reps=3, timeout=1200))
    _write("P9", rows)
    print(f"P9: {ok}/{len(sub)} built")


def _write(ps, rows):
    with open(f"{BIN}/{ps}/manifest_rows.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    env = blib.base_env(blib.resolve_cuda_home())
    build_p8(env)
    build_p9(env)

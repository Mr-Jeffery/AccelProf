#!/usr/bin/env python3
"""Generate + compile the Indigo3 corpora (P1 sample, P3 race-free graph codes).

Indigo3 ships .idg templates; generate_all_codes.py (CPU-only) expands them to
.cu. This wraps that pipeline for the baseline harness:

  P1: enable bug:{nobug,RaceBug,SyncBug} in codeGen/configure.txt, generate CUDA
      for the graph algos, keep the mk_e1 sample (programs whose only active
      planted bug is RaceBug/SyncBug, plus nobug), compile each TWICE --
      default (cuda::atomic relaxed) and -DSLOWER_ATOMIC (RMW; lib/cuda_atomic.h:43)
      -- over 2 .egr inputs. Writes bin/P1/manifest_rows.csv.
  P3: the nobug CC/MIS/MST codes (race-free), compiled once, on the torus100
      input. Writes bin/P3/manifest_rows.csv. (GC/graph-coloring is not in
      Indigo3's algo set; recorded in Blockers.)

Generation/sampling run on the login node; --compile needs a GPU node (nvcc).

  .env/bin/python eval/baselines/build_indigo.py --stage sample     # login node
  srun ... .env/bin/python eval/baselines/build_indigo.py --stage compile --pset P1,P3
"""
import argparse
import csv
import glob
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blib

I3 = f"{HERE}/corpora/Indigo3Suite"
GEN = f"{I3}/generatedCodes/CUDA"
LIB = f"{I3}/lib"
BIN = f"{HERE}/bin"
PY = f"{blib.APH}/.env/bin/python"
P1_ALGOS = ["cc", "mis", "mst", "bfs", "sssp", "pr", "tc"]
P3_ALGOS = ["cc", "mis", "mst"]
# two graph inputs (the '2 inputs'): small torus100 + a larger torus
GRAPHS = [f"{I3}/inputs/undirect2dim_rand_torus_100n_400e.egr",
          f"{I3}/inputs/undirect4dim_rand_torus_1296n_10368e.egr"]
P1_SAMPLE = 100


def active_bugs(cu):
    return {t for t in os.path.basename(cu)[:-3].split("_")
            if t.endswith("Bug") and not t.startswith("No")}


def _configure(bug_line):
    """Rewrite codeGen/configure.txt's `bug:` line (the suite's own knob)."""
    cfg = f"{I3}/codeGen/configure.txt"
    txt = open(cfg).read()
    txt = re.sub(r"(?m)^(\s*bug:\s*).*$", r"\g<1>" + bug_line, txt)
    open(cfg, "w").write(txt)


def generate(algos, bug_line):
    _configure(bug_line)
    for a in algos:
        subprocess.run([PY, "generate_all_codes.py", "cuda", a], cwd=I3,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def sample_p1():
    """mk_e1 rule: keep nobug + programs whose only active bug is RaceBug/SyncBug.
    Stratify: interleave the nobug and race/sync pools so the 100-sample carries
    both false-positive (nobug, X1) and true-positive (racy, X2) programs rather
    than the first-N-sorted (which is all-nobug). Deterministic."""
    nobug, racy = [], []
    for cu in sorted(glob.glob(f"{GEN}/*/*.cu")):
        ab = active_bugs(cu)
        if not ab:
            nobug.append(cu)
        elif ab <= {"RaceBug", "SyncBug"}:
            racy.append(cu)
    out, i = [], 0
    while len(out) < P1_SAMPLE and (i < len(nobug) or i < len(racy)):
        if i < len(nobug):
            out.append(nobug[i])
        if i < len(racy) and len(out) < P1_SAMPLE:
            out.append(racy[i])
        i += 1
    return out[:P1_SAMPLE]


def rows_for(cu_list, pset, builds, graphs, label_fn):
    rows = []
    for cu in cu_list:
        prog = os.path.basename(cu)[:-3]
        for build in builds:
            for g in graphs:
                m = re.search(r"(\d+)n_", os.path.basename(g))
                tag = (m.group(1) + "n") if m else os.path.splitext(os.path.basename(g))[0]
                exe = f"{BIN}/{pset}/{prog}__{build}"
                rows.append(dict(
                    id=f"{pset}-{prog}-{build}-{tag}", pset=pset, program=prog,
                    build=build, input=tag, exe=exe,
                    args=f"{g} 1 0 1", stdin="",
                    shared_mem=0, label=label_fn(cu), arrays_to_wrap="label;nstat",
                    monitored_kernels="", reps=3, timeout=600, src=cu))
    return rows


def write_rows(pset, rows):
    os.makedirs(f"{BIN}/{pset}", exist_ok=True)
    fields = ["id", "pset", "program", "build", "input", "exe", "args", "stdin",
              "shared_mem", "label", "arrays_to_wrap", "monitored_kernels",
              "reps", "timeout"]
    with open(f"{BIN}/{pset}/manifest_rows.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in fields})
    return rows


def sample_stage():
    generate(P1_ALGOS, "{all}")   # nobug + hasbug; RaceBug/SyncBug via option:{all}
    p1 = rows_for(sample_p1(), "P1", ["default", "slower_atomic"], GRAPHS,
                  lambda cu: "RACE" if active_bugs(cu) & {"RaceBug", "SyncBug"} else "CLEAN")
    write_rows("P1", p1)
    generate(P3_ALGOS, "{nobug}")
    p3src = [cu for cu in sorted(glob.glob(f"{GEN}/*/*.cu"))
             if not active_bugs(cu) and any(x in cu.upper() for x in ("CC-", "MIS-", "MST-"))][:12]
    p3 = rows_for(p3src, "P3", ["default"], GRAPHS[:1], lambda cu: "CLEAN")
    write_rows("P3", p3)
    print(f"P1 sample rows={len(p1)} (progs={len(p1)//4}), P3 rows={len(p3)}")


def compile_stage(psets):
    """Compile ONLY the sampled generated codes directly (nvcc -O3 -arch -I lib --
    the suite's own command; a CUDA-13 removed-API patch to lib/*_cuda.h clockRate
    is applied separately). Compiling all ~6000 generated variants is infeasible;
    we compile the ~100 P1 sample + a few P3. sm from BASELINE_SM."""
    sm = os.environ.get("BASELINE_SM", "89")
    env = blib.base_env(blib.resolve_cuda_home())
    numn = re.compile(r"(\d+)n_")

    def gtag(g):
        m = numn.search(os.path.basename(g))
        return (m.group(1) + "n") if m else "g"

    def compile_one(cu, exe, defines=()):
        # --cudart shared is REQUIRED so accelprof's LD_PRELOADed compute-sanitizer
        # resolves cudart (static-cudart binaries exit rc=1 under accelprof).
        subprocess.run(["nvcc", "-O3", f"-arch=sm_{sm}", "-lineinfo",
                        "--cudart", "shared", *defines, "-I", LIB, "-o", exe, cu],
                       env=env, stderr=subprocess.PIPE)
        return os.path.exists(exe)

    if "P1" in psets:
        os.makedirs(f"{BIN}/P1", exist_ok=True)
        # two build axes (task): default = atomicRead/Write via cuda::atomic relaxed;
        # slower_atomic = -DSLOWER_ATOMIC (RMW atomics, lib/cuda_atomic.h:43).
        builds = (("default", ()), ("slower_atomic", ("-DSLOWER_ATOMIC",)))
        rows, nok = [], 0
        for cu in sample_p1():
            prog = os.path.basename(cu)[:-3]
            lab = "RACE" if active_bugs(cu) & {"RaceBug", "SyncBug"} else "CLEAN"
            for build, defs in builds:
                exe = f"{BIN}/P1/{prog}__{build}"
                if not compile_one(cu, exe, defs):
                    continue
                nok += 1
                for g in GRAPHS:
                    rows.append(dict(id=f"P1-{prog}-{build}-{gtag(g)}", pset="P1",
                        program=prog, build=build, input=gtag(g), exe=exe,
                        args=f"{g} 1 0 1", stdin="", shared_mem=0, label=lab,
                        arrays_to_wrap="label;nstat", monitored_kernels="",
                        reps=3, timeout=600))
        write_rows("P1", rows)
        print(f"P1: compiled {nok} binaries -> {len(rows)} rows")

    if "P3" in psets:
        os.makedirs(f"{BIN}/P3", exist_ok=True)
        cus = [cu for cu in sorted(glob.glob(f"{GEN}/*/*.cu"))
               if not active_bugs(cu)
               and any(a in cu.upper() for a in ("CC-", "MIS-", "MST-"))][:60]
        mrows, nok = [], 0
        for cu in cus:
            prog = os.path.basename(cu)[:-3]
            exe = f"{BIN}/P3/{prog}"
            if not compile_one(cu, exe):
                continue
            nok += 1
            g = GRAPHS[0]
            mrows.append(dict(id=f"P3-{prog}-{gtag(g)}", pset="P3", program=prog,
                build="racefree", input=gtag(g), exe=exe, args=f"{g} 1 0 1",
                stdin="", shared_mem=0, label="CLEAN", arrays_to_wrap="",
                monitored_kernels="", reps=3, timeout=600))
        write_rows("P3", mrows)
        print(f"P3: compiled {nok} progs -> {len(mrows)} rows")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["sample", "compile"], required=True)
    ap.add_argument("--pset", default="P1,P3")
    a = ap.parse_args()
    if not os.path.isdir(I3):
        sys.exit("Indigo3Suite not cloned — run fetch_corpora.sh")
    if a.stage == "sample":
        sample_stage()
    else:
        compile_stage(a.pset.split(","))


if __name__ == "__main__":
    main()

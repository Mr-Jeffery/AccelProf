#!/usr/bin/env python3
"""Build the benchmark corpora at sm_86 with -lineinfo, into eval/baselines/bin/<Pn>.

Reuses the flag choices of eval/build_{scor,cuhadron,ecl,hecbench}.py but resolves
a real CUDA_HOME (blib) instead of their stale hardcoded spack path, and adds
-lineinfo so pc->source-line mapping (nvdisasm --print-line-info) and racecheck's
analysis report both have source lines. Records a per-target status row in
eval/results/baselines-build.csv. Must run on a GPU node (needs nvcc).

  srun -p rtx3060ti -N1 -n1 -t 04:00:00 bash -c \
    'source eval/baselines/gpu_env.sh; $PY eval/baselines/build_corpora.py --pset P6'
"""
import argparse
import csv
import glob
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blib

APH = blib.APH
BIN = f"{HERE}/bin"
INPUTS = f"{HERE}/inputs"
CORPORA = f"{HERE}/corpora"
SCOR_BENCHES = ["1dconv", "graph-coloring", "graph-connectivity",
                "matrix-multiplication", "reduction", "rule-110", "uts"]
CUHADRON_SKIP = {"multigpu"}
STATUS = []
SM = os.environ.get("BASELINE_SM", "86")   # target compute capability (e.g. 86, 89)


def _stat(pset, target, ok, err=""):
    STATUS.append(dict(pset=pset, target=target, status="ok" if ok else "FAIL",
                       err=("" if ok else err[-200:].strip())))
    print(f"  {'ok  ' if ok else 'FAIL'} {pset} {target}"
          + ("" if ok else f": {err[-160:].strip()}"))


def build_p4(env):
    os.makedirs(f"{BIN}/P4", exist_ok=True)
    os.makedirs(INPUTS, exist_ok=True)
    subprocess.run([f"{APH}/.env/bin/python", f"{APH}/eval/gen_scor_input.py",
                    "--out", INPUTS], stdout=subprocess.DEVNULL)
    bdir = f"{APH}/ScoR/benchmarks"
    nvcc = "nvcc -ccbin /usr/bin/g++"
    # --cudart shared is REQUIRED: accelprof LD_PRELOADs the compute-sanitizer
    # backend, which can only resolve cudart symbols if the app links it
    # dynamically. The ScoR bench Makefiles use a literal `nvcc $(ARCH) ...` with
    # no NVCC/flag var, so we smuggle --cudart shared + -lineinfo through ARCH
    # (static-cudart binaries otherwise exit rc=1 under accelprof -> no kernel JSON).
    arch = f"ARCH=-arch=sm_{SM} --cudart shared -lineinfo"
    for b in SCOR_BENCHES:
        d = f"{bdir}/{b}"
        if not os.path.isdir(d):
            _stat("P4", b, False, "no source dir"); continue
        for racey, tag in ((0, "norace"), (1, "racy")):
            subprocess.run(["make", "clean"], cwd=d, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            cmd = ["make", arch, f"NVCC={nvcc}"]
            if racey:
                cmd.append("RACEY=1")
            r = subprocess.run(cmd, cwd=d, env=env, stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE)
            # the per-dir Makefile builds a binary named after the dir
            cand = [p for p in (f"{d}/{b}", *glob.glob(f"{d}/{b}*"))
                    if os.path.isfile(p) and os.access(p, os.X_OK)]
            if r.returncode == 0 and cand:
                shutil.copy(cand[0], f"{BIN}/P4/{b}_{tag}")
                _stat("P4", f"{b}_{tag}", True)
            else:
                _stat("P4", f"{b}_{tag}", False, r.stderr.decode())


def build_p5(env):
    os.makedirs(f"{BIN}/P5", exist_ok=True)
    mdir = f"{APH}/ScoR/microbenchmarks"
    subprocess.run(["make", "clean"], cwd=mdir, env=env,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    r = subprocess.run(["make", "-j4",
                        f"NVCC_FLAGS=-arch=sm_{SM} -lineinfo --cudart shared",
                        "NVCC=nvcc -ccbin /usr/bin/g++"],
                       cwd=mdir, env=env, stdout=subprocess.DEVNULL,
                       stderr=subprocess.PIPE)
    built = glob.glob(f"{mdir}/bin/*")
    _stat("P5", f"microbenchmarks({len(built)})", len(built) > 0, r.stderr.decode())
    # canary (loose root file) -> bin/P5/canary
    canary = f"{APH}/canary_pc_level_false_negative.cu"
    if os.path.exists(canary):
        r = subprocess.run(["nvcc", f"-arch=sm_{SM}", "-lineinfo", "--cudart", "shared",
                            "-ccbin", "/usr/bin/g++", canary, "-o", f"{BIN}/P5/canary"],
                           env=env, stderr=subprocess.PIPE)
        _stat("P5", "canary", os.path.exists(f"{BIN}/P5/canary"), r.stderr.decode())


def _cuhadron_reqs(cdir):
    """{category: (min_arch, min_gpus)} from test_requirements.txt."""
    reqs = {}
    try:
        for ln in open(f"{cdir}/test_requirements.txt"):
            p = ln.split()
            if len(p) >= 3 and not p[0].startswith("#"):
                reqs[p[0]] = (int(p[1]), int(p[2]))
    except (OSError, ValueError):
        pass
    return reqs


def build_p6(env, arch=None, ngpu=1):
    arch = arch if arch is not None else int(SM)
    """Compile each cuHadron .cu directly with nvcc -- the shipped Makefile's
    `$(shell awk ...)` on line 32 does not parse under GNU Make 4.2.1, and the
    .cu files are self-contained (only cuda_runtime.h/stdio.h). We honor
    test_requirements.txt: categories needing a higher arch or >1 GPU are skipped
    and recorded (task: cuHadron bulkcpy/dsmem need sm_90, multigpu needs 2 GPUs)."""
    os.makedirs(f"{BIN}/P6", exist_ok=True)
    cdir = f"{APH}/cuHadron"
    reqs = _cuhadron_reqs(cdir)
    for cu in sorted(glob.glob(f"{cdir}/*/*.cu")):
        cat = os.path.basename(os.path.dirname(cu))
        name = os.path.basename(cu)[:-3]
        min_arch, min_gpus = reqs.get(cat, (80, 1))
        if min_arch > arch:
            _stat("P6", f"{cat}/{name}", False, f"needs sm_{min_arch} (skipped at sm_{arch})")
            continue
        if min_gpus > ngpu:
            _stat("P6", f"{cat}/{name}", False, f"needs {min_gpus} GPUs (skipped)")
            continue
        for suffix, fixed in (("racy", 0), ("fixed", 1)):
            out = f"{BIN}/P6/{cat}__{name}__{suffix}.sm86.out"
            cmd = ["nvcc", f"-arch=sm_{arch}", "-lineinfo", "--cudart", "shared",
                   "-ccbin", "/usr/bin/g++", "-I", cdir, "-I", f"{cdir}/{cat}"]
            if fixed:
                cmd.append("-DFIXED")
            cmd += [cu, "-o", out]
            r = subprocess.run(cmd, env=env, stderr=subprocess.PIPE)
            _stat("P6", f"{cat}/{name}/{suffix}", os.path.exists(out), r.stderr.decode())


def build_p3(env):
    ecl = f"{CORPORA}/ECL-suite"
    if not os.path.isdir(ecl):
        _stat("P3", "ECL-suite", False, "not cloned (run fetch_corpora.sh)"); return
    os.makedirs(f"{BIN}/P3", exist_ok=True)
    lib = f"{ecl}/library"
    for s in sorted(glob.glob(f"{ecl}/src/racefree/egr-input/**/*.cu", recursive=True)):
        name = os.path.basename(s)[:-3]
        out = f"{BIN}/P3/{name}"
        r = subprocess.run([ "nvcc", f"-arch=sm_{SM}", "-lineinfo", "-ccbin",
                            "/usr/bin/g++", "-I", lib, "-O3", s, "-o", out],
                           env=env, stderr=subprocess.PIPE)
        _stat("P3", name, os.path.exists(out), r.stderr.decode())


def build_p7(env, apps):
    src = f"{CORPORA}/HeCBench/src"
    if not os.path.isdir(src):
        _stat("P7", "HeCBench", False, "not cloned (run fetch_corpora.sh)"); return
    os.makedirs(f"{BIN}/P7", exist_ok=True)
    for app in apps:
        d = f"{src}/{app}"
        if not os.path.isdir(d):
            _stat("P7", app, False, "no app dir"); continue
        subprocess.run(["make", "clean"], cwd=d, env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        r = subprocess.run(["make", f"ARCH=sm_{SM}", "CC=nvcc",
                            "EXTRA_CFLAGS=-ccbin /usr/bin/g++ -lineinfo --cudart shared"], cwd=d,
                           env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        prog = f"{d}/main"
        if r.returncode == 0 and os.path.exists(prog):
            shutil.copy(prog, f"{BIN}/P7/{app}")
            _stat("P7", app, True)
        else:
            _stat("P7", app, False, r.stderr.decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pset", default="P4,P5,P6,P3,P7")
    ap.add_argument("--arch", default=SM, help="compute capability, e.g. 86 or 89")
    ap.add_argument("--hecbench-apps",
                    default="nbody-cuda,mandelbrot-cuda,bitonic-sort-cuda")
    a = ap.parse_args()
    globals()["SM"] = a.arch
    cuda = blib.resolve_cuda_home()
    env = blib.base_env(cuda)
    psets = set(a.pset.split(","))
    if "P4" in psets: build_p4(env)
    if "P5" in psets: build_p5(env)
    if "P6" in psets: build_p6(env)
    if "P3" in psets: build_p3(env)
    if "P7" in psets: build_p7(env, a.hecbench_apps.split(","))
    os.makedirs(blib.RESULTS_DIR, exist_ok=True)
    out = f"{blib.RESULTS_DIR}/baselines-build.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["pset", "target", "status", "err"])
        w.writeheader()
        w.writerows(STATUS)
    ok = sum(s["status"] == "ok" for s in STATUS)
    print(f"build: {ok}/{len(STATUS)} ok -> {out}")


if __name__ == "__main__":
    main()

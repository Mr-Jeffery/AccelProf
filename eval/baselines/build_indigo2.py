#!/usr/bin/env python3
"""Generate + compile P2 = original Indigo (IndigoSuite, ISPASS'22): a stratified
60-kernel sample (half race-free, half with a planted race/atomic/sync bug).

IndigoSuite/Generators/generate_suite.py expands .idg templates (per configure.txt)
into <out>/CUDA/*.cu, graph inputs into <out>/inputs/*.egr, headers into
<out>/include/. We generate, glob the results, stratify-sample 60, and compile with
the same recipe as Indigo3 (nvcc -O3 -arch -lineinfo --cudart shared -I <include>),
applying the CUDA-13 clockRate->0 patch if the headers hit the removed API. Writes
bin/P2/manifest_rows.csv (mk_manifest.rows_cloned reads it). CPU-only for
generate+compile; run happens later via parallel.py.

  BASELINE_SM=89 .env/bin/python eval/baselines/build_indigo2.py --stage all
"""
import argparse
import csv
import glob
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blib

I2 = f"{HERE}/corpora/IndigoSuite"
GENDIR = f"{I2}/Generators"
BIN = f"{HERE}/bin"
PY = f"{blib.APH}/.env/bin/python"
P2_SAMPLE = 60
# IndigoSuite planted-bug option tokens (configure.txt): a program is racy if its
# generated name carries one of these as an active option.
BUG_TOKENS = ("race", "atomicBug", "syncBug", "boundsBug")


def _is_racy(name):
    # a program is racy if its generated name carries any bug token; the baseline
    # nobug variant carries none. IndigoSuite uses atomicBug/guardBug/boundsBug/
    # syncBug/race etc., so match any "*Bug" token or the literal "race".
    toks = name.split("_")
    return any(t.endswith("Bug") for t in toks) or "race" in name.lower() \
        or any(t.lower() in name.lower() for t in BUG_TOKENS)


def _patch_clockrate():
    """Same CUDA-13 removed-API fix as Indigo3, if IndigoSuite headers use it."""
    for h in glob.glob(f"{GENDIR}/**/*.h", recursive=True):
        try:
            if "clockRate" in open(h, errors="ignore").read():
                subprocess.run(["sed", "-i",
                                r"s/[A-Za-z_]*\.memoryClockRate/0/g; s/[A-Za-z_]*\.clockRate/0/g",
                                h])
        except OSError:
            pass


def generate():
    # configure for both nobug and hasbug over all patterns/options
    cfg = f"{GENDIR}/configure.txt"
    if os.path.exists(cfg):
        txt = open(cfg).read()
        txt = re.sub(r"(?m)^(\s*bug:\s*).*$", r"\g<1>{all}", txt)
        open(cfg, "w").write(txt)
    subprocess.run([PY, "generate_suite.py"], cwd=GENDIR)
    _patch_clockrate()


def _generated_cu():
    # generated tree is <out>/CUDA/<pattern>/<variant>.cu (one level below CUDA)
    return sorted(glob.glob(f"{GENDIR}/**/CUDA/**/*.cu", recursive=True))


def _includes():
    incs = []
    for d in glob.glob(f"{GENDIR}/**/include", recursive=True):
        incs += ["-I", d]
    incs += ["-I", f"{GENDIR}/graph_include", "-I", f"{GENDIR}/sources_include"]
    return incs


def compile_stage():
    sm = os.environ.get("BASELINE_SM", "89")
    env = blib.base_env(blib.resolve_cuda_home())
    cus = _generated_cu()
    # graphs live at <out>/inputs/<pattern>/*.egr; pick a mid-size one (50-500 nodes)
    allg = sorted(glob.glob(f"{GENDIR}/**/inputs/**/*.egr", recursive=True))
    def nodes(g):
        m = re.search(r"(\d+)n", os.path.basename(g))
        return int(m.group(1)) if m else 0
    mid = [g for g in allg if 50 <= nodes(g) <= 500]
    graphs = mid or allg
    if not cus or not graphs:
        print(f"P2: no generated codes ({len(cus)}) or graphs ({len(allg)}) -- "
              f"generation failed; P2 stays blocked")
        return
    graph = graphs[0]
    nobug = [c for c in cus if not _is_racy(os.path.basename(c)[:-3])]
    racy = [c for c in cus if _is_racy(os.path.basename(c)[:-3])]
    # stratified: 30 + 30 interleaved
    sample, i = [], 0
    while len(sample) < P2_SAMPLE and (i < len(nobug) or i < len(racy)):
        if i < len(racy):
            sample.append((racy[i], "RACE"))
        if i < len(nobug) and len(sample) < P2_SAMPLE:
            sample.append((nobug[i], "CLEAN"))
        i += 1
    os.makedirs(f"{BIN}/P2", exist_ok=True)
    incs = _includes()
    rows, nok = [], 0
    numn = re.compile(r"(\d+)")
    m = numn.search(os.path.basename(graph))
    tag = (m.group(1) + "n") if m else "g"
    for cu, lab in sample:
        prog = os.path.basename(cu)[:-3]
        exe = f"{BIN}/P2/{prog}"
        subprocess.run(["nvcc", "-O3", f"-arch=sm_{sm}", "-lineinfo",
                        "--cudart", "shared", *incs, "-o", exe, cu],
                       env=env, stderr=subprocess.PIPE)
        if not os.path.exists(exe):
            continue
        nok += 1
        rows.append(dict(id=f"P2-{prog}", pset="P2", program=prog,
            build="default", input=tag, exe=exe, args=f"{graph} 256 4", stdin="",
            shared_mem=0, label=lab, arrays_to_wrap="", monitored_kernels="",
            reps=3, timeout=600))
    fields = ["id", "pset", "program", "build", "input", "exe", "args", "stdin",
              "shared_mem", "label", "arrays_to_wrap", "monitored_kernels",
              "reps", "timeout"]
    with open(f"{BIN}/P2/manifest_rows.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in fields})
    print(f"P2: compiled {nok}/{len(sample)} -> {len(rows)} rows "
          f"(racy={sum(1 for _, l in sample if l == 'RACE')})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["generate", "compile", "all"], default="all")
    a = ap.parse_args()
    if not os.path.isdir(I2):
        sys.exit("IndigoSuite not cloned -- run fetch_corpora.sh")
    if a.stage in ("generate", "all"):
        generate()
    if a.stage in ("compile", "all"):
        compile_stage()


if __name__ == "__main__":
    main()

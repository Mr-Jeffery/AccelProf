#!/usr/bin/env python3
"""Generate the single shared manifest.csv that every baseline tool consumes.

One row per (program, input, build-variant). Enumerated from source, so it can be
regenerated on the login node without a GPU; exe paths point at where
build_corpora.py deposits binaries (eval/baselines/bin/<Pn>/...). Runners check
existence at run time.

Coverage:
  P4 ScoR apps        (present)  7 benches x {norace,racy} x {small,large}
  P5 ScoR micro       (present)  ScoR/microbenchmarks/src/*.cu  + canary
  P6 cuHadron         (present)  category/*.cu x {racy(FIXED=0), fixed(FIXED=1)}
  P1 Indigo3          (clone)    from corpora/Indigo3   -- only if present
  P2 Indigo (orig)    (clone)    from corpora/Indigo    -- only if present
  P3 ECL CC/GC/MIS/MST(clone)    from corpora/ECL-suite -- only if present
  P7 HeCBench         (clone)    from corpora/HeCBench  -- only if present

Missing corpora simply contribute no rows here; fetch_corpora.sh + build_corpora.py
record their status, and make_tables.py surfaces them as Blockers.

    .env/bin/python eval/baselines/mk_manifest.py            # -> eval/baselines/manifest.csv
"""
import csv
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.dirname(os.path.dirname(HERE))
BIN = f"{HERE}/bin"
INPUTS = f"{HERE}/inputs"
CORPORA = f"{HERE}/corpora"

FIELDS = ["id", "pset", "program", "build", "input", "exe", "args", "stdin",
          "shared_mem", "label", "arrays_to_wrap", "monitored_kernels",
          "reps", "timeout"]

SCOR_BENCHES = ["1dconv", "graph-coloring", "graph-connectivity",
                "matrix-multiplication", "reduction", "rule-110", "uts"]
# device arrays each ScoR app's shared-data accesses touch (for HiRace wrapping);
# determined from the *_kernel.cu shared-data declarations.
SCOR_ARRAYS = {
    "1dconv": "in;out", "graph-coloring": "color;randoms",
    "graph-connectivity": "label;changed", "matrix-multiplication": "A;B;C",
    "reduction": "sdata;g_odata", "rule-110": "cells;next", "uts": "stack;count",
}


def _src_uses_shared(paths):
    for p in paths:
        try:
            if "__shared__" in open(p, errors="ignore").read():
                return 1
        except OSError:
            pass
    return 0


def rows_p4():
    out = []
    bdir = f"{APH}/ScoR/benchmarks"
    for b in SCOR_BENCHES:
        srcs = glob.glob(f"{bdir}/{b}/*.cu") + glob.glob(f"{bdir}/{b}/*.cuh")
        sm = _src_uses_shared(srcs)
        for variant, label in (("norace", "CLEAN"), ("racy", "RACE")):
            for size in ("small", "large"):
                out.append(dict(
                    id=f"P4-{b}-{variant}-{size}", pset="P4", program=b,
                    build=variant, input=size,
                    exe=f"{BIN}/P4/{b}_{variant}", args="",
                    stdin=f"{INPUTS}/{b}.{size}.in", shared_mem=sm, label=label,
                    arrays_to_wrap=SCOR_ARRAYS.get(b, ""), monitored_kernels="",
                    reps=3, timeout=600))
    return out


def rows_p5():
    out = []
    src = f"{APH}/ScoR/microbenchmarks/src"
    for f in sorted(glob.glob(f"{src}/*.cu")):
        name = os.path.basename(f)[:-3]
        label = "CLEAN" if name.startswith("norace") else "RACE"
        out.append(dict(
            id=f"P5-{name}", pset="P5", program=name, build="default",
            input="default", exe=f"{APH}/ScoR/microbenchmarks/bin/{name}",
            args="", stdin="", shared_mem=_src_uses_shared([f]), label=label,
            arrays_to_wrap="", monitored_kernels="", reps=3, timeout=300))
    canary = f"{APH}/canary_pc_level_false_negative.cu"
    if os.path.exists(canary):
        out.append(dict(
            id="P5-canary", pset="P5", program="canary_pc_level_false_negative",
            build="default", input="default", exe=f"{BIN}/P5/canary",
            args="", stdin="", shared_mem=0, label="RACE",
            arrays_to_wrap="data;flag", monitored_kernels="kmain",
            reps=3, timeout=300))
    return out


# cuHadron categories needing sm_90 (excluded at sm_86; recorded as blocker-note)
CUHADRON_SM90 = {"bulkcpy", "dsmem"}
CUHADRON_SKIP = {"multigpu"}  # needs 2 GPUs


def rows_p6():
    out = []
    root = f"{APH}/cuHadron"
    for cu in sorted(glob.glob(f"{root}/*/*.cu")):
        cat = os.path.basename(os.path.dirname(cu))
        if cat in CUHADRON_SKIP:
            continue
        name = os.path.basename(cu)[:-3]
        sm = _src_uses_shared([cu]) or int("shared" in name or cat in CUHADRON_SM90)
        note = "needs-sm90" if cat in CUHADRON_SM90 else ""
        for variant, fixed in (("racy", 0), ("fixed", 1)):
            # false_positives category is race-free even in the racy build
            if variant == "fixed" or cat == "false_positives":
                label = "CLEAN"
            else:
                label = "RACE"
            out.append(dict(
                id=f"P6-{cat}-{name}-{variant}", pset="P6",
                program=f"{cat}/{name}", build=variant + (f"[{note}]" if note else ""),
                input="default",
                exe=f"{BIN}/P6/{cat}__{name}__{variant}.sm86.out", args="",
                stdin="", shared_mem=sm, label=label, arrays_to_wrap="",
                monitored_kernels="", reps=3, timeout=300))
    return out


def rows_cloned():
    """P1/P2/P3/P7 rows, only when the cloned corpus + built binaries exist."""
    out = []
    # P1 Indigo3 / P2 Indigo / P3 ECL(graph codes): build_indigo.py writes a
    # manifest_rows.csv per set (bin/<Pn>/manifest_rows.csv).
    # PI (build_indigo_full.py) = all 590 IndigoSuite codes; it replaced the two
    # partial Indigo-original sets P2 (60-code sample) and P8 (SuperCollider's 99),
    # which are subsets of it. Their old result rows stay in eval/results/.
    for ps in ("P1", "PI", "P3", "P7", "P9"):
        extra = f"{BIN}/{ps}/manifest_rows.csv"
        if os.path.exists(extra):
            with open(extra, newline="") as f:
                out.extend(dict(r) for r in csv.DictReader(f))
    return out


def main():
    rows = rows_p4() + rows_p5() + rows_p6() + rows_cloned()
    path = f"{HERE}/manifest.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    by = {}
    for r in rows:
        by[r["pset"]] = by.get(r["pset"], 0) + 1
    print(f"{len(rows)} rows -> {path}")
    for ps in sorted(by):
        print(f"  {ps}: {by[ps]}")


if __name__ == "__main__":
    main()

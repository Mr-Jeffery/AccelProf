#!/usr/bin/env python3
"""Build PI = the WHOLE original Indigo suite (IndigoSuite 1.3 CUDA, 590 codes), the one
Indigo-original program set every detector is run on. It replaces the two earlier
partial sets: P2 (our stratified 60-code sample) and P8 (SuperCollider's 99 tests) --
both are subsets of these 590 codes (9 in common), and the HiRace SC24 artifact's
indigo/indigo_sources is byte-for-byte (modulo whitespace/comments) the same 590 files
our corpora/IndigoSuite generator emits (checked 590/590).

Sources: the HiRace artifact's copies, because each has its HiRace-instrumented twin
next to it (indigo/indigo_hirace_sources/<pattern>/<pattern>_hirace<suffix>.cu):

  bin/PI/<code>          uninstrumented, OUR recipe (-O3 sm_89 -lineinfo --cudart shared)
                         -> cuVein / compute-sanitizer / iGUARD / native timing
  bin/PI_hirace/<code>   the artifact's instrumented twin, same recipe + the artifact's
                         own flags (-DRACECHECK -I src/hirace)  -> HiRace

Inputs (7 per code -> 4130 manifest rows, id PI-<code>-<graph>):
  * the six graphs + launch of the HiRace artifact's `make table1`
    (indigo/input/*.egr, 256 threads/block x 1024 blocks)
  * SuperCollider's input (DAG_100n_100e.egr, 256 x 4): the only input its
    pre-instrumented binaries are shipped for.
Label = both artifacts' ground truth (HiRace scripts/gen_table1.py, SuperCollider
gen_table_indigo_detection.py): RACE if the name has "Bug" and not "boundsBug"; CLEAN if
no "Bug"; boundsBug codes are excluded (label '').

Writes bin/PI/manifest_rows.csv (mk_manifest.rows_cloned reads it) and
bin/PI/build_status.csv. Needs nvcc; parallel (--jobs).
  BASELINE_SM=89 .env/bin/python eval/baselines/build_indigo_full.py --jobs 16
"""
import argparse
import csv
import glob
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blib
from build_sc_sets import sc_label, FIELDS

HIRACE = f"{HERE}/setup/tools/HiRace"
SRC = f"{HIRACE}/indigo/indigo_sources"
HSRC = f"{HIRACE}/indigo/indigo_hirace_sources"
BIN = f"{HERE}/bin"
SM = os.environ.get("BASELINE_SM", "89")
SC_GRAPH = f"{HERE}/corpora/IndigoSuite/Generators/IndigoSuite_1.3/inputs/DAG/DAG_100n_100e.egr"
SC_BINS = f"{HERE}/setup/tools/supercollider/supercollider-artifacts/bin/indigo/instrumented"


def inputs():
    """[(tag, graph path, 'tpb blocks')]: HiRace Table-1 graphs at 256x1024 + SC's at 256x4."""
    out = [(os.path.basename(g)[:-4], g, "256 1024")
           for g in sorted(glob.glob(f"{HIRACE}/indigo/input/*.egr"))]
    out.append((os.path.basename(SC_GRAPH)[:-4], SC_GRAPH, "256 4"))
    return out


def twin(pattern, code):
    """<pattern><suffix> -> <pattern>_hirace<suffix>.cu"""
    return f"{HSRC}/{pattern}/{pattern}_hirace{code[len(pattern):]}.cu"


def _nvcc(src, exe, extra, env):
    if os.path.exists(exe) and os.path.getmtime(exe) >= os.path.getmtime(src):
        return ""
    r = subprocess.run(["nvcc", "-O3", f"-arch=sm_{SM}", "-lineinfo", "--cudart", "shared",
                        "-ccbin", "/usr/bin/g++", *extra, "-o", exe, src],
                       env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return "" if os.path.exists(exe) else (r.stderr.decode(errors="replace")[-300:] or "nvcc failed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--no-compile", action="store_true", help="manifest rows only")
    a = ap.parse_args()
    env = blib.base_env(blib.resolve_cuda_home())
    os.makedirs(f"{BIN}/PI", exist_ok=True)
    os.makedirs(f"{BIN}/PI_hirace", exist_ok=True)
    codes = []
    for s in sorted(glob.glob(f"{SRC}/*/*.cu")):
        pat = os.path.basename(os.path.dirname(s))
        codes.append((pat, os.path.basename(s)[:-3], s))
    status = {}

    def build(item):
        pat, code, s = item
        e1 = _nvcc(s, f"{BIN}/PI/{code}", ["-I", f"{HIRACE}/indigo/indigo_include"], env)
        t = twin(pat, code)
        e2 = (_nvcc(t, f"{BIN}/PI_hirace/{code}", ["-DRACECHECK", "-I", f"{HIRACE}/src/hirace"], env)
              if os.path.exists(t) else "no-hirace-twin")
        return code, e1, e2

    if not a.no_compile:
        with ThreadPoolExecutor(max_workers=a.jobs) as ex:
            for n, (code, e1, e2) in enumerate(ex.map(build, codes), 1):
                status[code] = (e1, e2)
                if e1 or e2:
                    print(f"  FAIL {code}: plain={e1[-120:]!r} hirace={e2[-120:]!r}", flush=True)
                if n % 50 == 0:
                    print(f"  built {n}/{len(codes)}", flush=True)
        with open(f"{BIN}/PI/build_status.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["code", "plain_ok", "hirace_ok", "plain_err", "hirace_err"])
            for code, (e1, e2) in sorted(status.items()):
                w.writerow([code, int(not e1), int(not e2), e1.replace("\n", " | "), e2.replace("\n", " | ")])
    sc = {os.path.basename(p)[:-4] for p in glob.glob(f"{SC_BINS}/*/*.out")}
    rows = []
    for pat, code, _ in codes:
        for tag, g, launch in inputs():
            rows.append(dict(id=f"PI-{code}-{tag}", pset="PI", program=code,
                             build="sc-subset" if (code in sc and g == SC_GRAPH) else "default",
                             input=tag, exe=f"{BIN}/PI/{code}", args=f"{g} {launch}", stdin="",
                             shared_mem=0, label=sc_label(code), arrays_to_wrap="",
                             monitored_kernels=pat, reps=3, timeout=600))
    with open(f"{BIN}/PI/manifest_rows.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    okp = sum(os.path.exists(f"{BIN}/PI/{c}") for _, c, _ in codes)
    okh = sum(os.path.exists(f"{BIN}/PI_hirace/{c}") for _, c, _ in codes)
    print(f"PI: {len(codes)} codes, plain built {okp}, hirace twins built {okh}, "
          f"{len(rows)} manifest rows ({len(inputs())} inputs); labels per code: "
          f"RACE={sum(sc_label(c) == 'RACE' for _, c, _ in codes)} "
          f"CLEAN={sum(sc_label(c) == 'CLEAN' for _, c, _ in codes)} "
          f"excluded={sum(sc_label(c) == '' for _, c, _ in codes)}; "
          f"SuperCollider-subset rows: {sum(r['build'] == 'sc-subset' for r in rows)}")


if __name__ == "__main__":
    main()

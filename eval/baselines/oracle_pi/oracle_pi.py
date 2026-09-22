#!/usr/bin/env python3
"""Input-level ground truth for the Indigo-original suite (PI): does the planted bug produce
an unordered conflicting access pair ON THIS INPUT?  (The suite's label is per code.)

Each code is compiled unmodified for the CPU against shim/indigo_cuda.h (the source is piped
through sed only to drop `typedef int data_t;`, replaced by an access-logging int) and run
with the manifest row's graph and launch geometry under 3 thread schedules (forward,
reverse, shuffled). CONFLICT if any schedule shows two different threads touching one
location, >=1 write, not both atomic, with no barrier / warp collective between them.
Source-level: a store the compiler elides is still a write here.

  $PY eval/baselines/oracle_pi/oracle_pi.py [--jobs 16] -> eval/results/baselines-pi-oracle.csv
"""
import argparse, csv, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.abspath(f"{HERE}/../../..")
SRC = f"{HERE}/../corpora/IndigoSuite/Generators/IndigoSuite_1.3/CUDA"
BIN = f"{HERE}/bin"


def build(pat, code):
    out = f"{BIN}/{code}"
    if os.path.exists(out):
        return ""
    src = open(f"{SRC}/{pat}/{code}.cu").read().replace("typedef int data_t;", "", 1)
    p = subprocess.run(["g++", "-O1", "-w", "-x", "c++", "-I", f"{HERE}/shim", "-o", out, "-"],
                       input=src, text=True, capture_output=True)
    return p.stderr[-300:] if p.returncode else ""


def run(m):
    pat, code = m["monitored_kernels"], m["program"]
    err = build(pat, code)
    res = dict(id=m["id"], code=code, graph=m["input"], label=m["label"], oracle="", pairs="", example="", notes="")
    if err:
        res.update(oracle="BUILD-ERROR", notes=err.replace("\n", " | ")); return res
    verdicts, pairs, ex = [], 0, ""
    for seed in (0, 1, 7):
        try:
            p = subprocess.run([f"{BIN}/{code}", *m["args"].split(), str(seed)], capture_output=True, text=True, timeout=1800)
        except subprocess.TimeoutExpired:
            verdicts.append("TIMEOUT"); continue
        line = next((l for l in p.stdout.splitlines() if l.startswith("ORACLE")), "")
        f = line.split()
        if len(f) < 3:
            verdicts.append(f"ERROR(rc={p.returncode})"); continue
        verdicts.append(f[1])
        n = int(f[2].split("=")[1])
        if n > pairs:
            pairs, ex = n, " ".join(f[6:])
    res["oracle"] = "CONFLICT" if "CONFLICT" in verdicts else verdicts[0] if len(set(verdicts)) == 1 else "/".join(verdicts)
    res["pairs"], res["example"], res["notes"] = pairs, ex, "schedules=" + ",".join(verdicts)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--inputs", default="DAG_5n_5e,counterDAG_5n_5e,DAG_100n_100e",
                    help="graphs to check (default: the three on which any detector's FNs on racy codes "
                         "concentrate; the >=200-vertex graphs emulate 256k fibers and take minutes per run)")
    ap.add_argument("--out", default=f"{APH}/eval/results/baselines-pi-oracle.csv")
    a = ap.parse_args()
    os.makedirs(BIN, exist_ok=True)
    rows = [m for m in csv.DictReader(open(f"{HERE}/../manifest.csv"))
            if m["pset"] == "PI" and m["label"].upper() in ("RACE", "CLEAN")
            and (not a.inputs or m["input"] in a.inputs.split(","))]
    codes = sorted({(m["monitored_kernels"], m["program"]) for m in rows})
    with ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(lambda c: build(*c), codes))
    with ThreadPoolExecutor(a.jobs) as ex:
        out = list(ex.map(run, rows))
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
    import collections
    print(collections.Counter((r["label"].upper(), r["oracle"]) for r in out))
    print(f"{len(out)} rows -> {a.out}")


if __name__ == "__main__":
    main()

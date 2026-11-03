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
import argparse, csv, os, subprocess, sys, time
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


TMO = 1800      # seconds per schedule run (--timeout)
NA = False      # --na: a row with an unfinished schedule is ORACLE-N/A instead of TIMEOUT / ERROR


def run(m):
    pat, code = m["monitored_kernels"], m["program"]
    err = build(pat, code)
    res = dict(id=m["id"], code=code, graph=m["input"], label=m["label"], oracle="", pairs="", example="", notes="")
    if err:
        res.update(oracle="BUILD-ERROR", notes=err.replace("\n", " | ")); return res
    verdicts, pairs, ex = [], 0, ""
    for seed in (0, 1, 7):
        try:
            p = subprocess.run([f"{BIN}/{code}", *m["args"].split(), str(seed)], capture_output=True, text=True, timeout=TMO)
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
    if NA and "CONFLICT" not in verdicts and any(v not in ("NO-CONFLICT",) for v in verdicts):
        res["oracle"] = "ORACLE-N/A"      # a schedule did not finish (time / memory): no verdict, launch not shrunk
        res["notes"] = "schedules=" + ",".join(verdicts)
        return res
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
    ap.add_argument("--build", default="", help="only manifest rows with this build tag (X8: sc-subset = the 99 shipped codes)")
    ap.add_argument("--shard", default="", help="k/n over the sorted row ids")
    ap.add_argument("--timeout", type=int, default=1800, help="seconds per schedule run")
    ap.add_argument("--na", action="store_true", help="unfinished row -> ORACLE-N/A (never shrinks the launch)")
    a = ap.parse_args()
    os.makedirs(BIN, exist_ok=True)
    rows = [m for m in csv.DictReader(open(f"{HERE}/../manifest.csv"))
            if m["pset"] == "PI" and m["label"].upper() in ("RACE", "CLEAN")
            and (not a.inputs or m["input"] in a.inputs.split(","))
            and (not a.build or m["build"] == a.build)]
    global TMO, NA
    TMO, NA = a.timeout, a.na
    if a.shard:
        k, n = (int(x) for x in a.shard.split("/"))
        rows = [m for i, m in enumerate(sorted(rows, key=lambda r: r["id"])) if i % n == k]
    codes = sorted({(m["monitored_kernels"], m["program"]) for m in rows})
    with ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(lambda c: build(*c), codes))
    out = []
    FIELDS = ["id", "code", "graph", "label", "oracle", "pairs", "example", "notes"]
    with open(a.out, "w", newline="") as fh, ThreadPoolExecutor(a.jobs) as ex:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader()
        from concurrent.futures import as_completed
        for f in as_completed([ex.submit(run, m) for m in rows]):     # written as they finish
            r = f.result(); out.append(r); w.writerow(r); fh.flush()
    import collections
    print(collections.Counter((r["label"].upper(), r["oracle"]) for r in out))
    print(f"{len(out)} rows -> {a.out}")


if __name__ == "__main__":
    main()

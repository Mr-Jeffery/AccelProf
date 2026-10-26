#!/usr/bin/env python3
"""M2 / figure 1d: every pair verdict record of the kept recordings of the fig1d variants, plus the
SASS of the kernel and the pc -> source-line map. Analysis only: sync_dominance.analyze is run on the
store's kernel_*.json and dots (what parallel.py analyze runs); nothing here changes a verdict.

  fig1d_pairs.py --store <store dir> --bin <dir of the executables> --out <json> ID:EXE [ID:EXE ...]
"""
import argparse
import glob
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault("CUVEIN_HOME", str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[1] / "eval" / "baselines"))
import blib                                  # noqa: E402
sys.path.insert(0, blib.PYDIR)
sys.path.insert(0, f"{blib.APH}/eval")
import sync_dominance as sd                  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--store", required=True)
ap.add_argument("--bin", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("items", nargs="+")
a = ap.parse_args()
env = blib.base_env(blib.resolve_cuda_home())
out = {}
for item in a.items:
    pid, exe = item.split(":")
    rec = {"exe": exe, "modes": {}}
    cubdir = f"{a.out}.cubins/{exe}"
    scope, cubs = blib.extract(os.path.realpath(f"{a.bin}/{exe}"), cubdir, env)
    pcmap = {}
    for c in cubs:
        pcmap.update(blib.pc_line_map(c, env))
    rec["pc_line"] = {hex(k): v for k, v in sorted(pcmap.items())}
    rec["sass"] = subprocess.run(["cuobjdump", "-sass", f"{a.bin}/{exe}"], env=env, capture_output=True,
                                 text=True).stdout
    for mode in ("vector-clock", "scalar-clock"):
        d = Path(os.path.realpath(f"{a.store}/{pid}/{mode}"))
        dots = sorted(glob.glob(f"{d.parent}/dots/*.dot"))
        verdicts = []
        for kj in sorted(glob.glob(f"{d}/kernel_*.json")):
            for dot in dots:
                try:
                    rep = sd.analyze(dot, kj)
                except sd.AlignmentError:
                    continue
                for v in rep["verdicts"]:
                    verdicts.append(dict(v, _kernel=rep["kernel"]["mangled"], _kj=os.path.basename(kj)))
                break
        rec["modes"][mode] = {"dir": str(d), "n_kernel_json": len(glob.glob(f"{d}/kernel_*.json")),
                              "verdicts": verdicts}
    out[pid] = rec
Path(a.out).write_text(json.dumps(out, indent=1, default=str))
for pid, rec in out.items():
    for mode, m in rec["modes"].items():
        print(pid, mode, "kernel_json", m["n_kernel_json"], "verdict records", len(m["verdicts"]))

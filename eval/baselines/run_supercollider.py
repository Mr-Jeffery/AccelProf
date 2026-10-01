#!/usr/bin/env python3
"""B6 -- SuperCollider (PLDI'26, NVIDIA) runner into the unified baseline schema.

SuperCollider is a redundant-read pass inside NVIDIA's proprietary `ptxas`; its
artifact (Zenodo 10.5281/zenodo.19058944) ships NO compiler, only pre-instrumented
binaries + the runtime `lib64/librc-release.so` (enabled with
CUDA_INJECTION64_PATH). So it can only be measured on the programs it ships:
  P6  cuHadron      bin/cuhadron/{instrumented,fixed}/<cat>/<test>.all.out
  P8  Indigo (99)   bin/indigo/instrumented/<pattern>/<test>.out
  P9  HeCBench (10) bin/hecbench/instrumented-balanced/<app>
Manifest rows of those sets are mapped onto the artifact binary of the SAME program
(the other detectors run our own build of the same source). Native wall comes from
the artifact's own uninstrumented binary (bin/*/native), run the same way, so the
slowdown is instrumented-vs-native of the same build.

The binaries need GLIBC 2.34 (Ubuntu 22.04); the cluster is EL8, so every run goes
through `singularity exec --nv ubuntu2204.sif` (the artifact's supported setup is a
Docker image of the same base). Detection is probabilistic, and the artifact's own
protocol is 5 attempts per program (N_SC_RUNS=5): default --reps 5, RACE if any
attempt reports. Markers (kick_the_tires.sh): "RACECHECKER ENGAGED" = runtime
attached; "RACE CONDITIONS DETECTED" = race; per report
"In function <f> at <file>:<line>" / "Type : ...". Must run on a GPU node.

  $PY eval/baselines/run_supercollider.py --pset P6,P8,P9 --shard 0/16
"""
import argparse
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blib

ROOT = f"{HERE}/setup/tools/supercollider"
SC = f"{ROOT}/supercollider-artifacts"
SIF = os.environ.get("SC_SIF", f"{ROOT}/ubuntu2204.sif")
LIB = f"{SC}/lib64/librc-release.so"
SING = os.environ.get("SINGULARITY_BIN", "/opt/ohpc/pub/libs/singularity/3.7.1/bin/singularity")
HEC = f"{HERE}/corpora/HeCBench/src"
_REP = re.compile(r"In function (\S+?)(?: at (\S+?):(\d+))?\s*\n\s*Type\s*:\s*([^\n]+)"
                  r"(?:\n\s*PC offset\s*:\s*(\S+))?")
_N = re.compile(r"(\d+)\s+RACE CONDITIONS DETECTED")


def _load_cuh_req():
    req = {}
    try:
        for ln in open(f"{blib.APH}/cuHadron/test_requirements.txt"):
            p = ln.split()
            if len(p) >= 3 and not p[0].startswith("#"):
                req[p[0]] = (int(p[1]), int(p[2]))
    except (OSError, ValueError):
        pass
    return req


_CUH_REQ = _load_cuh_req()
_CC = []


def _cc():
    """device compute capability as an int (8.9 -> 89), cached."""
    if not _CC:
        import subprocess
        try:
            o = subprocess.run(["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"],
                               capture_output=True, text=True, timeout=30).stdout.split()[0]
            _CC.append(int(o.replace(".", "")))
        except Exception:
            _CC.append(0)
    return _CC[0]


def _shard(items, shard):
    if not shard:
        return items
    k, n = (int(x) for x in shard.split("/"))
    return [it for i, it in enumerate(items) if i % n == k]


def sc_binaries(m):
    """manifest row -> (instrumented, native) artifact binaries, or (None, None)."""
    ps, prog = m["pset"], m["program"]
    if ps == "P6":
        cat, name = prog.split("/", 1)
        sub = "fixed" if m["build"].startswith("fixed") else "instrumented"
        return (f"{SC}/bin/cuhadron/{sub}/{cat}/{name}.all.out",
                f"{SC}/bin/cuhadron/native/{cat}/{name}.all.out")
    # PI = the whole Indigo-original suite; SuperCollider ships binaries only for its
    # 99-test subset and only its own input (build_indigo_full.py tags those rows
    # build=sc-subset). P8 = the retired stand-alone copy of that subset.
    if ps == "P8" or (ps == "PI" and m["build"] == "sc-subset"):
        pat = m["monitored_kernels"]
        return (f"{SC}/bin/indigo/instrumented/{pat}/{prog}.out",
                f"{SC}/bin/indigo/native/{pat}/{prog}.out")
    if ps == "P9":
        app = prog[:-5] if prog.endswith("-cuda") else prog
        return (f"{SC}/bin/hecbench/instrumented-balanced/{app}",
                f"{SC}/bin/hecbench/native/{app}")
    return None, None


def parse(text):
    """dedup on (location, kind); location = file:line when the binary has line info,
    else function+pc-offset."""
    reps, lines = [], set()
    for fn, f, ln, typ, pc in _REP.findall(text):
        kind = ("W-clobbered" if "WROTE" in typ else "R-clobbered" if "READ" in typ
                else re.sub(r"\W+", "-", typ.strip())[:24])
        loc = f"{os.path.basename(f)}:{ln}" if f else f"{fn}+{pc or '?'}"
        key = f"{loc}:{kind}"
        if key not in reps:
            reps.append(key)
        if f:
            lines.add(f"{os.path.basename(f)}:{ln}")
    return reps, lines


def run_one(m, cuda, reps, logroot):
    common = dict(id=m["id"], pset=m["pset"], program=m["program"], build=m["build"],
                  input=m["input"], tool="supercollider")
    inst, nat = sc_binaries(m)
    if not inst or not os.path.exists(inst):
        return [blib.row(**common, verdict="ERROR",
                         notes="not-shipped-instrumented (artifact has no binary for this program)")]
    # cuHadron categories carry a minimum compute capability / GPU count
    # (cuHadron/test_requirements.txt); the artifact's own scripts SKIP a test the
    # GPU cannot exhibit (bulkcpy/dsmem need sm_90, multigpu 2 GPUs). Running it
    # anyway yields a meaningless CLEAN, so it is recorded as unsupported instead.
    if m["pset"] == "P6":
        need = _CUH_REQ.get(m["program"].split("/", 1)[0])
        if need and (need[0] > _cc() or need[1] > 1):
            return [blib.row(**common, verdict="ERROR",
                             notes=f"unsupported-on-this-gpu: needs sm_{need[0]} x{need[1]} GPU(s); "
                                   f"have sm_{_cc()} (artifact skips it too)")]
    args = [a for a in m["args"].split() if a] if m["args"] else []
    cwd = os.path.dirname(inst)
    app_src = f"{HEC}/{m['program']}"
    if m["pset"] == "P9" and os.path.isdir(app_src):
        cwd = app_src                     # ../dxtc2-sycl/data/... resolve from here
    # clean env for the container: the host LD_LIBRARY_PATH (CUDA 13.3 / torch libs
    # built for EL8) must not leak into the Ubuntu 22.04 userland
    nenv = {k: v for k, v in os.environ.items() if k not in ("LD_LIBRARY_PATH", "LD_PRELOAD")}
    env = dict(nenv)
    env["SINGULARITYENV_CUDA_INJECTION64_PATH"] = LIB
    env["CUDA_INJECTION64_PATH"] = LIB
    pre = [SING, "exec", "--nv", SIF]
    logd = f"{logroot}/{m['id']}"
    os.makedirs(logd, exist_ok=True)
    man_timeout = int(m["timeout"] or 300)
    # native = artifact's own uninstrumented build, same container, no injection
    # One discarded warm-up (first container start on a node is cold: image page-in,
    # driver init), then best of 3 -- otherwise a cold native vs warm tool runs makes
    # the instrumented binary look faster than native.
    native = None
    if os.path.exists(nat):
        blib.run_timed([*pre, nat, *args], nenv, cwd, man_timeout)
        for k in range(3):
            w, _, nrc, to = blib.run_timed([*pre, nat, *args], nenv, cwd, man_timeout,
                                           stderr_path=f"{logd}/native{k}.txt")
            if not to and isinstance(w, (int, float)):
                native = w if native is None else min(native, w)
    timeout = min(max(int(10 * native), 120), 1200) if native else man_timeout
    rows = []
    for rep in range(1, reps + 1):
        outp = f"{logd}/sc_rep{rep}.txt"
        wall, peak, rc, to = blib.run_timed([*pre, inst, *args], env, cwd, timeout,
                                            poll_mem=True, stderr_path=outp)
        base = dict(**common, rep=rep, wall_s=wall,
                    native_wall_s=native if native is not None else "",
                    peak_mb=round(peak / 1024.0, 1) if peak else "", rc=rc)
        if to:
            rows.append(blib.row(**base, verdict="TIMEOUT", notes=f"timeout={timeout}s"))
            continue
        try:
            text = open(outp, errors="replace").read()
        except OSError:
            text = ""
        if "RACECHECKER ENGAGED" not in text:
            tail = blib.tail_text(outp, 3, 200).replace(",", ";").replace("\n", " | ")
            rows.append(blib.row(**base, verdict="ERROR", notes=f"runtime-not-attached;rc={rc};{tail}"))
            continue
        reps_, lines = parse(text)
        n = _N.search(text)
        racy = "RACE CONDITIONS DETECTED" in text
        rows.append(blib.row(**base, verdict="RACE" if racy else "CLEAN",
                             reports_dedup=len(reps_), report_ids=" ".join(reps_)[:2000],
                             report_lines=" ".join(sorted(lines)),
                             notes=(f"sc_races={n.group(1)}" if n else "") + (f";rc={rc}" if rc else "")))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=f"{HERE}/manifest.csv")
    ap.add_argument("--pset", default="P6,P8,P9")
    ap.add_argument("--id", default="")
    ap.add_argument("--shard", default="")
    ap.add_argument("--reps", type=int, default=5, help="artifact protocol: 5 attempts")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    for need in (LIB, SIF, SING):
        if not os.path.exists(need):
            sys.stderr.write(f"BLOCKER: SuperCollider prerequisite missing: {need}. "
                             f"Run setup/supercollider_setup.sh. Not simulating.\n")
            sys.exit(3)
    cuda = blib.resolve_cuda_home()
    psets = set(a.pset.split(",")) if a.pset else None
    ids = set(a.id.split(",")) if a.id else None
    rows = [m for m in blib.read_manifest(a.manifest)
            if (not psets or m["pset"] in psets) and (not ids or m["id"] in ids)]
    # of the whole Indigo-original suite only the artifact's 99-test subset on its own
    # input has binaries; the other PI rows are not runnable (no row, shown as "-")
    rows = [m for m in rows if m["pset"] != "PI" or m["build"] == "sc-subset"]
    rows = _shard(rows, a.shard)
    tag = a.shard.replace("/", "_") if a.shard else "all"
    path = a.out or f"{blib.RESULTS_DIR}/baselines-supercollider-shard{tag}.csv"
    logroot = f"/mnt/local/{os.environ.get('USER', 'u')}/sc_logs"
    try:
        os.makedirs(logroot, exist_ok=True)
    except OSError:
        logroot = f"{HERE}/setup/build_logs/sc_logs"
        os.makedirs(logroot, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=blib.COLUMNS)
        w.writeheader()
        for i, m in enumerate(rows, 1):
            print(f"[{i}/{len(rows)}] {m['id']}", flush=True)
            try:
                for r in run_one(m, cuda, a.reps, logroot):
                    w.writerow(r)
            except Exception as e:
                w.writerow(blib.row(id=m["id"], pset=m["pset"], program=m["program"],
                                    build=m["build"], input=m["input"], tool="supercollider",
                                    verdict="ERROR", notes=f"{type(e).__name__}:{e}"))
            fh.flush()
    print(f"supercollider: {len(rows)} program(s) -> {path}")


if __name__ == "__main__":
    main()

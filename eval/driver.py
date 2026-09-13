#!/usr/bin/env python3
"""Batch driver for the cuVein race eval.

Runs each program in a manifest end-to-end: cubin/CFG extraction + atomic-scope
sidecar, then three timed configs (native / trace-only / full engine), then the
verdict aggregator -> one CSV row. All orchestration is subprocess with an
explicit env dict (no shell source/export), so it runs from a worktree session.

Success is detected by the engine dependency dir + kernel JSONs, not accelprof's
exit code (its timing tail can exit nonzero while the tool succeeded).

    conda run -p /home/fzheng4/AccelProf/.env python eval/driver.py MANIFEST.json
"""
import glob
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import types
from pathlib import Path

import aggregate  # same dir

# CUVEIN_HOME selects which checkout's bin/, lib/, .env/ and python/ run (a worktree
# with lib/build/.env symlinked to the main checkout is a full runtime mirror).
APH = os.environ.get("CUVEIN_HOME", "/home/fzheng4/AccelProf")
CUDA_HOME = "/home/fzheng4/spack/opt/spack/linux-zen2/cuda-12.9.0-owxskbbrhugkzflau7xe3gyqnvdqlfyw"
PY310LIB = "/home/fzheng4/AccelProf/.claude/worktrees/fix+multiwarp-barrier-hb/py310/lib"
PYDIR = f"{APH}/python"
SIDECAR = f"{PYDIR}/atomic_scope_sidecar.py"


def base_env():
    e = os.environ.copy()
    e["ACCEL_PROF_HOME"] = APH
    e["CUDA_HOME"] = CUDA_HOME
    e["CUDA_PATH"] = CUDA_HOME
    e["PATH"] = f"{APH}/bin:{CUDA_HOME}/bin:" + e.get("PATH", "")
    e["LD_LIBRARY_PATH"] = (f"{CUDA_HOME}/compute-sanitizer:{PY310LIB}:"
                            + e.get("LD_LIBRARY_PATH", ""))
    # drop any HB knobs inherited from the shell
    for k in ("YOSEMITE_HB_TRACE", "YOSEMITE_HB_NO_ENGINE", "YOSEMITE_ATOMIC_SCOPE_FILE"):
        e.pop(k, None)
    return e


def _descendants(root):
    """pids of root + all descendants (single /proc scan)."""
    kids = {}
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            with open(f"/proc/{d}/stat") as f:
                ppid = int(f.read().split(") ", 1)[1].split()[1])
            kids.setdefault(ppid, []).append(int(d))
        except (OSError, IndexError, ValueError):
            pass
    out, stack = [], [root]
    while stack:
        p = stack.pop()
        out.append(p)
        stack.extend(kids.get(p, []))
    return out


def _rss_kb(pids):
    tot = 0
    for p in pids:
        try:
            with open(f"/proc/{p}/status") as f:
                for ln in f:
                    if ln.startswith("VmRSS:"):
                        tot += int(ln.split()[1])
                        break
        except OSError:
            pass
    return tot


def run_timed(cmd, env, cwd, timeout, reps=1, poll_mem=False, stdin_path=None):
    """-> (min_wall_s, peak_rss_kb, rc, ok). Wall = min over reps; peak from a
    /proc poller over the whole subtree when poll_mem (the engine run)."""
    best, peak, rc, ok = None, 0, None, True
    for _ in range(reps):
        stop = threading.Event()
        local_peak = [0]
        fin = open(stdin_path, "rb") if stdin_path else subprocess.DEVNULL
        t0 = time.perf_counter()
        try:
            # own session/process group so a timeout kills the whole tree —
            # accelprof is a bash wrapper; killing only it orphans the sanitizer-
            # instrumented child (multi-GB RSS via libtorch), which otherwise
            # accumulates across runs until the host OOMs.
            p = subprocess.Popen(cmd, env=env, cwd=cwd, stdin=fin,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  start_new_session=True)
        except OSError:
            if stdin_path:
                fin.close()
            return "NA", 0, 127, False
        if poll_mem:
            def poll():
                while not stop.is_set():
                    local_peak[0] = max(local_peak[0], _rss_kb(_descendants(p.pid)))
                    time.sleep(0.1)
            th = threading.Thread(target=poll, daemon=True)
            th.start()
        def _killtree():
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
                p.kill()
        try:
            rc = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            _killtree(); p.wait(); rc = 124; ok = False
        _killtree()  # reap any lingering grandchildren even on clean exit
        stop.set()
        if stdin_path:
            fin.close()
        wall = round(time.perf_counter() - t0, 3)
        if best is None or wall < best:
            best = wall
        peak = max(peak, local_peak[0])
    return best, peak, rc, ok


def extract(exe_abs, cubindir):
    """cubin -> CFG dots -> atomic-scope sidecar. Returns scope-file path or ''."""
    shutil.rmtree(cubindir, ignore_errors=True)
    os.makedirs(cubindir)
    env = base_env()
    subprocess.run(["cuobjdump", "-xelf", "all", exe_abs], cwd=cubindir, env=env,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cubs = glob.glob(f"{cubindir}/*.cubin") or glob.glob(f"{cubindir}/*.elf")
    for c in cubs:
        dot = os.path.splitext(c)[0] + ".dot"
        with open(dot, "w") as f:
            subprocess.run(["nvdisasm", "-bbcfg", "-poff", c], stdout=f,
                           stderr=subprocess.DEVNULL, env=env)
    scope = f"{cubindir}/atomic_scope.txt"
    dots = glob.glob(f"{cubindir}/*.dot")
    if dots:
        r = subprocess.run([sys.executable, SIDECAR, *dots, "-o", scope],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if r.returncode == 0 and os.path.exists(scope):
            return scope
    return ""


def run_program(pg, csv, detail_dir):
    exe_abs = os.path.realpath(pg["exe"])
    exe_dir = os.path.dirname(exe_abs)
    exe_base = os.path.basename(exe_abs)
    name = os.path.splitext(exe_base)[0]
    args = [str(a) for a in pg.get("args", [])]
    timeout = pg.get("timeout", 300)
    reps = pg.get("reps", 3)
    tag = pg.get("input", "")
    stdin_path = pg.get("stdin")

    def blank_row(note):
        ns = types.SimpleNamespace(python_dir=PYDIR, depdir="/nonexistent",
            cubindir="/nonexistent", log="", suite=pg["suite"], program=pg["program"],
            variant=pg.get("variant", ""), label=pg.get("label", ""), input=tag,
            csv=csv, notes_extra=note)
        aggregate.emit_row(ns)

    if not (os.path.exists(exe_abs) and os.access(exe_abs, os.X_OK)):
        print(f"  MISSING/non-exec exe: {exe_abs}")
        blank_row("missing-exe")
        return

    cubindir = f"{exe_dir}/{name}_eval_cubins"
    scope = extract(exe_abs, cubindir)

    # 1) native
    tn, _, rcn, _ = run_timed([exe_abs, *args], base_env(), exe_dir, timeout, reps,
                              stdin_path=stdin_path)
    # 2) trace-only (dump, engine skipped) — throwaway depdir
    for d in glob.glob(f"{exe_dir}/dependency_{exe_base}_*"):
        shutil.rmtree(d, ignore_errors=True)
    te_env = base_env(); te_env["YOSEMITE_HB_TRACE"] = "1"
    if scope:
        te_env["YOSEMITE_ATOMIC_SCOPE_FILE"] = scope
    tr_env = dict(te_env); tr_env["YOSEMITE_HB_NO_ENGINE"] = "1"
    # accelprof derives its log/output name as ${EXECUTABLE#./}; an absolute path
    # breaks that (writes to a nonexistent dir, app never runs). Pass ./<base> and
    # rely on cwd=exe_dir (matches getall.sh).
    accel = ["accelprof", "-t", "pc_dependency_analysis", "-n", "1",
             f"./{exe_base}", *args]
    tt, _, rct, _ = run_timed(accel, tr_env, exe_dir, timeout, 1, stdin_path=stdin_path)
    for d in glob.glob(f"{exe_dir}/dependency_{exe_base}_*"):
        shutil.rmtree(d, ignore_errors=True)
    # 3) full engine — keep depdir, poll memory
    ten, peak, rce, _ = run_timed(accel, te_env, exe_dir, timeout, 1, poll_mem=True,
                                  stdin_path=stdin_path)
    deps = sorted(glob.glob(f"{exe_dir}/dependency_{exe_base}_*"), key=os.path.getmtime)
    depdir = deps[-1] if deps else ""
    log = f"{exe_dir}/{exe_base}.accelprof.log"

    kjs = glob.glob(f"{depdir}/kernel_*.json") if depdir else []
    print(f"  [{pg['program']}/{pg.get('variant','')}] "
          f"native={tn}s trace={tt}s engine={ten}s peak={round(peak/1024,1)}MB "
          f"kernels={len(kjs)} rc(n/t/e)={rcn}/{rct}/{rce}")

    if not kjs:
        blank_row(f"no-engine-output(rc={rce})")
        return

    ns = types.SimpleNamespace(
        python_dir=PYDIR, depdir=depdir, cubindir=cubindir, log=log,
        suite=pg["suite"], program=pg["program"], variant=pg.get("variant", ""),
        label=pg.get("label", ""), input=tag,
        t_native=tn, t_trace=tt, t_engine=ten, peak_kb=peak,
        racecheck=pg.get("racecheck", ""), oracle=pg.get("oracle", False),
        oracle_max_events=pg.get("oracle_max_events", 300000),
        expect_pcs=pg.get("expect_pcs", ""), csv=csv,
        assume_warp_lockstep=pg.get("assume_warp_lockstep", False),
        detail=(f"{detail_dir}/{pg['program']}__{pg.get('variant','')}__{tag}.json"
                if detail_dir else ""))
    aggregate.emit_row(ns)


def main():
    man = json.loads(Path(sys.argv[1]).read_text())
    csv = man["csv"]
    detail_dir = man.get("detail_dir", "")
    if detail_dir:
        os.makedirs(detail_dir, exist_ok=True)
    os.makedirs(os.path.dirname(csv), exist_ok=True)
    progs = man["programs"]
    print(f"driver: {len(progs)} program(s) -> {csv}")
    for i, pg in enumerate(progs, 1):
        print(f"[{i}/{len(progs)}] {pg['suite']} {pg['program']} {pg.get('variant','')}")
        try:
            run_program(pg, csv, detail_dir)
        except Exception as e:
            print(f"  ERROR {type(e).__name__}: {e}")
    print("driver: done")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Phase 4 scale-evaluation harness.

Runs one app binary through the HB pipeline and records the metrics microbenchmarks
cannot surface:
  - event count (len hb_events)
  - engine hb_races: deduped count AND grouped-by-(a_pc,b_pc) pair count
  - TV violations (Phase 1) reported by the engine
  - coherence profile size (atomic addresses; longest per-address order)
  - wall time A/B: scalar-clock (dump only) vs vector-clock (dump + engine), via
    YOSEMITE_HB_MODE (engine cost = t_vector_clock_s - t_scalar_clock_s)
  - exact VC oracle: verdict + peak RSS + wall, WHERE IT FITS. Above a bound the exact
    O(threads) oracle is not run -- the row is then flagged vector_clock_only_unverified
    (UNVERIFIED against the oracle), never silently. The engine remains the only verdict there.

The harness reuses getall.sh to produce the (CFG .dot, atomic-scope sidecar, trace) tuple,
then re-runs accelprof directly for the A/B timing.

Usage: python scale_harness.py <binary> [-- app args...] [--tag NAME] [--oracle-cap-events N]
"""
import argparse
import hb_modes  # same dir: vector-clock / scalar-clock
import json
import os
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path

import hb_oracle as ho
import sync_dominance as sd

_ROOT = Path(__file__).resolve().parents[1]


def _run(cmd, cwd, env=None, timeout=None):
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    return time.time() - t0, p


def _accelprof_env(sidecar, mode):
    env = dict(os.environ)
    env["ACCEL_PROF_HOME"] = str(_ROOT)
    env["PATH"] = f"{_ROOT}/bin:" + env.get("PATH", "")
    env["YOSEMITE_HB_TRACE"] = "1"
    if sidecar and Path(sidecar).exists():
        env["YOSEMITE_ATOMIC_SCOPE_FILE"] = str(sidecar)
    hb_modes.require_collector_support(str(_ROOT))   # a pre-T8 library ignores YOSEMITE_HB_MODE
    env.pop(hb_modes.LEGACY_ENV, None)      # an inherited pre-T8 switch would flip the mode
    env.update(hb_modes.collector_env(mode))
    return env


def _dedup_races(races):
    seen = set()
    for r in races:
        seen.add((r["addr"], r["a_tid"], r.get("a_pc"), r["b_tid"], r["b_pc"], r["kind"]))
    return seen


def _pc_pairs(races):
    return {(r.get("a_pc"), r["b_pc"], r["kind"]) for r in races}


def analyze_app(binary, app_args, tag, oracle_cap_events):
    binary = Path(binary).resolve()
    idir = binary.parent
    base = binary.name

    # 1) CFG + sidecar via getall.sh. NOTE getall.sh does NOT forward app args to
    # accelprof, so its trace is the default-arg run; we ignore it and run accelprof
    # ourselves WITH the app args below. The CFG/sidecar are arg-independent.
    getall_env = dict(os.environ)
    getall_env.setdefault("ACCEL_PROF_HOME", str(_ROOT))
    subprocess.run(["bash", str(_ROOT / "getall.sh"), str(binary), *app_args],
                   cwd=_ROOT, capture_output=True, timeout=3600, env=getall_env)
    ext = idir / f"{binary.stem}_extracted_cubins"
    sidecar = ext / "atomic_scope.txt"
    dots = sorted(ext.glob("*.dot"))
    if not dots:
        return {"tag": tag, "error": "no CFG produced (build/GPU/cuobjdump failed)"}

    # 2) The analyzed trace: run accelprof (vector-clock) WITH the app args, timed. Snapshot
    # dep dirs before/after so we analyze exactly this run's trace, not getall's.
    run_cmd = ["accelprof", "-v", "-t", "pc_dependency_analysis", "-n", "1", f"./{base}", *app_args]
    before = set(idir.glob(f"dependency_{base}_*"))
    t_engine, _ = _run(run_cmd, cwd=idir, env=_accelprof_env(sidecar, hb_modes.VECTOR_CLOCK), timeout=7200)
    new = sorted(set(idir.glob(f"dependency_{base}_*")) - before)
    if not new:
        return {"tag": tag, "error": "no trace produced (accelprof vector-clock run failed)"}
    dep = new[-1]
    traces = sorted(dep.glob("kernel_*.json"))
    # scalar-clock (dump-only) time (engine cost = vector-clock - scalar-clock), same args.
    t_dump, _ = _run(run_cmd, cwd=idir, env=_accelprof_env(sidecar, hb_modes.SCALAR_CLOCK), timeout=7200)

    rows = []
    for tf in traces:
        d = json.loads(tf.read_text())
        events = len(d.get("hb_events", []))
        eng_races = d.get("hb_races", [])
        cp = d.get("coherence_profile", {})
        grid = d["kernel"].get("grid_dim"); block = d["kernel"].get("block_dim")
        threads = (d["kernel"].get("grid_cta_count", 0)
                   * d["kernel"].get("block_thread_count", 0))
        row = {
            "tag": tag, "kernel": d["kernel"]["kernel_name"], "trace": tf.name,
            "grid": grid, "block": block, "threads": threads, "events": events,
            "vector_clock_races_dedup": len(_dedup_races(eng_races)),
            "vector_clock_race_pc_pairs": len(_pc_pairs(eng_races)),
            "tv_violation": d.get("tv_violation"),
            "atomic_addrs": len(cp),
            "max_coherence_len": max((v["len"] for v in cp.values()), default=0),
            "t_scalar_clock_s": round(t_dump, 3), "t_vector_clock_s": round(t_engine, 3),
            "t_vector_clock_delta_s": round(t_engine - t_dump, 3),
        }
        # 3) Exact VC oracle where it fits.
        if events == 0:
            row["oracle"] = "n/a (no hb_events)"
        elif events > oracle_cap_events:
            row["oracle"] = f"SKIPPED (events {events} > cap {oracle_cap_events})"
            row["vector_clock_only_unverified"] = True
        else:
            report, peak_kb, t_orc, err = _run_oracle_subprocess(dots, tf)
            if err:
                row["oracle"] = f"FAILED ({err})"
                row["vector_clock_only_unverified"] = True
            else:
                orc = _dedup_races(report["races"])
                eng = _dedup_races(eng_races)
                row["oracle_races_dedup"] = len(orc)
                row["vector_clock_eq_oracle"] = (eng == orc)
                row["oracle_peak_rss_mb"] = round(peak_kb / 1024, 1)
                row["oracle_wall_s"] = round(t_orc, 3)
                row["vector_clock_only_unverified"] = False
        rows.append(row)
    return {"tag": tag, "rows": rows}


def _run_oracle_subprocess(dots, trace):
    """Run the oracle in a child so we can read its peak RSS; return (report, peak_kb,
    wall, err). Tries each dot until one aligns."""
    script = (
        "import json,sys,resource,time\n"
        "sys.path.insert(0, %r)\n"
        "import hb_oracle as ho, sync_dominance as sd\n"
        "dots=%r; tf=%r\n"
        "t0=time.time(); rep=None\n"
        "for dot in dots:\n"
        "    try: rep=ho.analyze(dot, tf); break\n"
        "    except sd.AlignmentError: continue\n"
        "if rep is None: print('ERR:no-align'); sys.exit(3)\n"
        "peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss\n"
        "json.dump({'races':rep['races'],'peak_kb':peak,'wall':time.time()-t0}, open(%r,'w'))\n"
    ) % (str(_ROOT / "python"), [str(x) for x in dots], str(trace), str(trace) + ".oracle.json")
    try:
        t0 = time.time()
        p = subprocess.run([sys.executable, "-c", script], capture_output=True,
                           text=True, timeout=1800)
        if p.returncode != 0:
            return None, 0, 0, (p.stdout + p.stderr).strip()[:200] or "nonzero exit"
        out = json.loads(Path(str(trace) + ".oracle.json").read_text())
        return {"races": out["races"]}, out["peak_kb"], out["wall"], None
    except subprocess.TimeoutExpired:
        return None, 0, 0, "oracle timeout (1800s)"
    except Exception as exc:  # noqa
        return None, 0, 0, str(exc)[:200]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("binary")
    ap.add_argument("app_args", nargs="*")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--oracle-cap-events", type=int, default=2_000_000)
    ap.add_argument("-o", "--output", type=Path)
    args = ap.parse_args(argv)
    tag = args.tag or Path(args.binary).stem
    result = analyze_app(args.binary, args.app_args, tag, args.oracle_cap_events)
    txt = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(txt + "\n")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())

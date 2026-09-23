#!/usr/bin/env python3
"""B5 -- cuVein runner, both modes, into the unified baseline schema.

Two modes, distinct verdict surfaces (this is what X6/canary probes):
  vector-clock  YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=vector-clock -> verdict from the
                C++ HbEngine's `hb_races` in kernel_N.json crossed with the static leg.
  scalar-clock  YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=scalar-clock -> dump only; verdict
                from the sync_dominance static leg + offline barrier-only pass.

Invocation of the detector is reused verbatim from eval/driver.py:
  accelprof -t pc_dependency_analysis -n 1 ./<exe> <args>   (cwd = exe dir)
Verdict/report parsing reuses python/sync_dominance.py and eval/aggregate.py's
dedup key -- nothing in the detector/oracle is modified.

Overhead is re-measured here: a native (no-LD_PRELOAD) baseline plus the tool wall
for the same binary+args. Reports are pcs, each mapped to a source line via
blib.pc_line_map (nvdisasm --print-line-info).

Must run on a GPU node (srun). Example:
  srun -p rtx3060ti -N1 -n1 -t 04:00:00 \
    .env/bin/python eval/baselines/run_cuvein.py --pset P6 --confirm
"""
import argparse
import glob
import json
import os
import shutil
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blib

sys.path.insert(0, blib.PYDIR)          # python/ : sync_dominance, hb_oracle
sys.path.insert(0, f"{blib.APH}/eval")  # eval/   : aggregate (dedup key)
import sync_dominance as sd  # noqa: E402
import aggregate as agg      # noqa: E402
import host_hb               # noqa: E402  (T2: host copies / cross-stream kernels)


def _analyze_reports(depdir, cubindir):
    """Run sync_dominance.analyze over the dump and dedup RACE verdicts on
    (unordered pc pair, space). Used for BOTH modes: analyze derives the verdict
    from the trace edges, and when the dump carries the C++ engine's hb_races
    (vector-clock mode) it crosses them in via _hb_class -- so the vector-clock dump
    can flag a statically-ordered pair the engine observed racing (e.g. the canary),
    while the scalar-clock dump yields the static-leg verdict (+ the offline
    barrier-only pass) and misses it. That is exactly the vector-clock vs
    scalar-clock surface the task compares.

    -> (ids, pcs_set, raw_verdicts). This branch's analyze(dot, trace) takes no
    assume_warp_lockstep kwarg (that lives only on the eval branch). Only
    AlignmentError is swallowed (wrong dot -> next); other exceptions propagate so
    a real failure is an ERROR row, not a silent CLEAN."""
    dots = sorted(glob.glob(f"{cubindir}/*.dot"))
    ded = {}
    for kj in sorted(glob.glob(f"{depdir}/kernel_*.json")):
        rep = None
        for dot in dots:
            try:
                rep = sd.analyze(dot, kj)
                break
            except sd.AlignmentError:
                continue
        if rep is None:
            continue
        for v in rep["verdicts"]:
            if v["verdict"] == "RACE":
                ded.setdefault(agg._dedup_key(v), v)
    ids, pcs_all, raw = [], set(), []
    for k, v in sorted(ded.items(), key=lambda kv: kv[0]):
        a, b, space = k
        ids.append(f"{space}:{hex(a)}-{hex(b)}:{v.get('race_type', '')}")
        pcs_all.update((a, b))
        raw.append({"a_pc": a, "b_pc": b, "space": space,
                    "race_type": v.get("race_type"), "strength": v.get("strength"),
                    "hb_class": v.get("hb_class"), "hb_chain": v.get("hb_chain")})
    ids_h, raw_h = _host_reports(depdir)
    return ids + ids_h, pcs_all | {r[p] for r in raw_h for p in ("a_pc", "b_pc") if r[p] is not None}, \
        raw + raw_h


def _host_label(d, pc):
    if d["kind"] == "launch":
        return f"k{d.get('kernel_id')}@{hex(pc) if pc is not None else '?'}"
    return f"{d['kind']}{d.get('direction', '')}#{d['seq']}"


def _host_reports(depdir):
    """T2 (YOSEMITE_HB_HOST_MEMCPY=1; python/host_hb.py, design/host_memcpy_model.md): races
    between host copies/sets and kernels, or kernels on two streams, that no stream order,
    event or host synchronize orders. Present only when the dump carries host_ops.json.
    Report id global:host:<A>-<B>:<type> (A/B = memcpyH2D#<seq>, memset#<seq> or
    k<kernel>@<pc>); raw records carry "host" (a copy/set side has no pc: a_pc/b_pc None),
    and the pc-pair classifiers skip them. hb_class "host-spec-only" = a race only under the
    CUDA Runtime's documented synchronization (a synchronous copy/set that may not have
    completed when it returned; host_hb.py), "host" otherwise. Deduped on (A, B, type)."""
    res = host_hb.races(depdir)
    if not res:
        return [], []
    ids, raw, seen = [], [], set()
    for r in res["races"]:
        a, b = _host_label(r["a"], r.get("a_pc")), _host_label(r["b"], r.get("b_pc"))
        if (a, b, r["race_type"]) in seen:
            continue
        seen.add((a, b, r["race_type"]))
        ids.append(f"global:host:{a}-{b}:{r['race_type']}")
        raw.append({"a_pc": r.get("a_pc"), "b_pc": r.get("b_pc"), "space": "global",
                    "race_type": r["race_type"], "strength": "none",
                    "hb_class": "host-spec-only" if r["spec_only"] else "host",
                    "hb_chain": None, "host": {"a": r["a"], "b": r["b"], "addr": r["addr"]}})
    return ids, raw


def run_one(mrow, modes, cuda, writer, confirm_dir):
    exe = mrow["exe"]
    exe_dir = os.path.dirname(exe)
    base = os.path.basename(exe)
    args = [a for a in mrow["args"].split() if a] if mrow["args"] else []
    stdin = mrow["stdin"] or None
    reps = int(mrow["reps"] or 3)
    man_timeout = int(mrow["timeout"] or 600)
    common = dict(id=mrow["id"], pset=mrow["pset"], program=mrow["program"],
                  build=mrow["build"], input=mrow["input"], tool="cuvein")

    if not (os.path.exists(exe) and os.access(exe, os.X_OK)):
        writer.writerow(blib.row(**common, mode="", verdict="ERROR",
                                 notes="missing-exe"))
        return

    # 1) native baseline (no LD_PRELOAD): min wall over reps
    nenv = blib.base_env(cuda)
    native, native_rc = None, 0
    for _ in range(reps):
        w, _, rc, to = blib.run_timed([exe, *args], nenv, exe_dir,
                                      man_timeout, stdin_path=stdin)
        native_rc = max(native_rc, rc or 0)
        if not to and isinstance(w, (int, float)):
            native = w if native is None else min(native, w)
    # "10x native or 20 min": read as up to 20 min (vector-clock runs 3-218x native,
    # so a literal 10x cap kills it on ~0.1s-native programs). Floor 120s, cap 1200s.
    tool_timeout = min(max(int(10 * native), 120), 1200) if native else man_timeout

    # 2) extract cubins/CFG/scope + pc->line map (once)
    cubindir = f"{exe_dir}/{os.path.splitext(base)[0]}_eval_cubins"
    scope, cubs = blib.extract(os.path.realpath(exe), cubindir, nenv)
    pcmap = {}
    for c in cubs:
        pcmap.update(blib.pc_line_map(c, nenv))

    def lines_for(pcs):
        got = sorted({pcmap[p] for p in pcs if p in pcmap})
        return ";".join(got)

    accel = ["accelprof", "-t", "pc_dependency_analysis", "-n", "1",
             f"./{base}", *args]

    for mode in modes:
        env = blib.base_env(cuda, hb_trace=True, hb_mode=mode, scope_file=scope or None)
        for rep in range(1, reps + 1):
            for d in glob.glob(f"{exe_dir}/dependency_{base}_*"):
                shutil.rmtree(d, ignore_errors=True)
            wall, peak, rc, to = blib.run_timed(accel, env, exe_dir, tool_timeout,
                                                poll_mem=True, stdin_path=stdin)
            deps = sorted(glob.glob(f"{exe_dir}/dependency_{base}_*"),
                          key=os.path.getmtime)
            depdir = deps[-1] if deps else ""
            kjs = glob.glob(f"{depdir}/kernel_*.json") if depdir else []
            notes = ""
            raw = []
            if to:
                verdict, ids, pcs = "TIMEOUT", [], set()
            elif not kjs:
                verdict, ids, pcs = "ERROR", [], set()
                notes = f"no-kernel-json(rc={rc})"
            else:
                # rc != native rc: the app died under the tool (accelprof returns 1,
                # e.g. an OOM-killed engine run) and the dump holds only the kernels
                # finished before that. A race it shows is a race; it is never CLEAN.
                complete = rc == native_rc
                try:
                    ids, pcs, raw = _analyze_reports(depdir, cubindir)
                except ValueError:
                    if complete:
                        raise
                    ids, pcs, raw = [], set(), []
                verdict = "RACE" if ids else "CLEAN"
                if not complete:
                    notes = f"partial(rc={rc};nkernels={len(kjs)})"
                    if not ids:
                        verdict = "ERROR"
                        notes = f"incomplete-trace(rc={rc};nkernels={len(kjs)})"
            writer.writerow(blib.row(
                **common, mode=mode, rep=rep, verdict=verdict,
                reports_dedup=len(ids), report_ids=" ".join(ids),
                report_lines=lines_for(pcs),
                wall_s=wall, native_wall_s=native if native is not None else "",
                peak_mb=round(peak / 1024.0, 1) if peak else "",
                rc=rc, notes=notes))
            # confirmation detail: rep 1 only, full report objects for classify
            if confirm_dir and rep == 1 and kjs and not to and verdict != "ERROR":
                Path(f"{confirm_dir}/{mrow['id']}__cuvein__{mode}.json").write_text(
                    json.dumps({"id": mrow["id"], "tool": "cuvein", "mode": mode,
                                "verdict": verdict, "report_ids": ids,
                                "pcs": sorted(pcs), "lines": lines_for(pcs),
                                "raw": raw, "scope_file": scope,
                                "pc_lines": {str(k): v for k, v in pcmap.items()
                                             if k in pcs}}, indent=2))
    # tidy trace dirs (bulky)
    for d in glob.glob(f"{exe_dir}/dependency_{base}_*"):
        shutil.rmtree(d, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=f"{HERE}/manifest.csv")
    ap.add_argument("--pset", default="", help="comma list filter, e.g. P4,P6")
    ap.add_argument("--mode", default=",".join(blib.hb_modes.MODES),
                    help="comma list of vector-clock,scalar-clock")
    ap.add_argument("--id", default="", help="run only these ids (comma list)")
    ap.add_argument("--confirm", action="store_true",
                    help="write a confirmation-run detail JSON per program (rep 1)")
    a = ap.parse_args()
    cuda = blib.resolve_cuda_home()   # raises on the login node
    psets = set(a.pset.split(",")) if a.pset else None
    ids = set(a.id.split(",")) if a.id else None
    modes = list(blib.hb_modes.parse_modes(a.mode))
    confirm_dir = f"{HERE}/confirm" if a.confirm else ""
    if confirm_dir:
        os.makedirs(confirm_dir, exist_ok=True)
    writer, fh, path = blib.open_results("cuvein")
    n = 0
    try:
        for mrow in blib.read_manifest(a.manifest):
            if psets and mrow["pset"] not in psets:
                continue
            if ids and mrow["id"] not in ids:
                continue
            n += 1
            print(f"[{n}] {mrow['id']}")
            try:
                run_one(mrow, modes, cuda, writer, confirm_dir)
                fh.flush()
            except Exception as e:
                writer.writerow(blib.row(
                    id=mrow["id"], pset=mrow["pset"], program=mrow["program"],
                    build=mrow["build"], input=mrow["input"], tool="cuvein",
                    verdict="ERROR", notes=f"{type(e).__name__}:{e}"))
                fh.flush()
    finally:
        fh.close()
    print(f"cuvein: {n} program(s) -> {path}")


if __name__ == "__main__":
    main()

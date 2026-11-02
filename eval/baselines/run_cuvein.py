#!/usr/bin/env python3
"""B5 -- cuVein runner, both modes, into the unified baseline schema.

Two modes, distinct verdict surfaces (this is what X6/canary probes):
  vector-clock  YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=vector-clock -> verdict from the
                C++ HbClock's `hb_races` in kernel_N.json crossed with the static leg.
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
import contextlib
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


def analysis_workers(n=None):
    """X7: the verdict step's pool size: n if given (>= 1), else $CUVEIN_ANALYSIS_WORKERS, else
    the cores this process may run on (os.sched_getaffinity: the node's cores in a whole-node
    job). 1 = the serial loop."""
    if n is None:
        n = os.environ.get("CUVEIN_ANALYSIS_WORKERS") or None
    if n is None:
        try:
            n = len(os.sched_getaffinity(0))
        except (AttributeError, OSError):
            n = os.cpu_count() or 1
    return max(int(n), 1)


def graph_cache_enabled(cache=None):
    """X7: the static-graph cache (sync_dominance.graph_cache) for one analysis: on unless
    cache=False or $CUVEIN_GRAPH_CACHE=0 (the pre-X7 path: every launch parses and builds)."""
    if cache is None:
        cache = os.environ.get("CUVEIN_GRAPH_CACHE", "1") != "0"
    return bool(cache)


def _kernel_report(kj, dots):
    """One kernel JSON's report, as the serial loop computes it: the first .dot (in sorted
    order) that aligns with it, or None if none does. Only the two keys the merge reads are
    kept (rep["gate_policy"], rep["verdicts"])."""
    for dot in dots:
        try:
            rep = sd.analyze(dot, kj)
        except sd.AlignmentError:
            continue
        return {"gate_policy": rep.get("gate_policy"), "verdicts": rep["verdicts"]}
    return None


def _pool_task(kj, dots):
    """_kernel_report in a pool worker. An exception comes back as data, so the parent
    re-raises one of the same type and message at this kernel's place in the order: pickled
    as itself (its own __reduce__: OSError keeps errno and filename), except a
    JSONDecodeError, whose pickle would carry the whole document -- it travels as its
    message and positions (its str() is its message)."""
    try:
        return ("OK", _kernel_report(kj, dots))
    except json.JSONDecodeError as e:
        return ("JDE", (e.args, e.msg, e.pos, e.lineno, e.colno))
    except Exception as e:   # noqa: BLE001 -- re-raised by the parent, in order
        return ("EXC", e)


def _reraise(tag, payload):
    if tag == "JDE":
        args, msg, pos, lineno, colno = payload
        e = json.JSONDecodeError.__new__(json.JSONDecodeError)
        e.args, e.msg, e.doc, e.pos, e.lineno, e.colno = args, msg, "", pos, lineno, colno
        raise e
    raise payload


class AnalysisWorkerDied(RuntimeError):
    """X7: a pool worker of the verdict step vanished (killed: OOM, signal)."""


def _kernel_reports(kjs, dots, workers, cached):
    """Yield _kernel_report(kj) for each kernel JSON in the order given, inside the
    static-graph cache when `cached`: inline when one worker (or one kernel JSON), else from a
    fork pool of `workers` processes whose results are consumed in input order
    (ProcessPoolExecutor.map), so the caller's merge sees the reports exactly as the serial
    loop produces them. With a pool and the cache, every .dot is parsed here once before the
    fork and the workers inherit the parsed graphs (each worker builds the static HBGraph of a
    (dot, kernel) it meets once). The pool's processes are children of this one (a capped
    analysis counts them, parallel._analyze_capped); on an exception they are killed at once,
    as the serial loop would stop there."""
    with (sd.graph_cache() if cached else contextlib.nullcontext()):
        if workers <= 1 or len(kjs) <= 1:
            for kj in kjs:
                yield _kernel_report(kj, dots)
            return
        if cached:
            for dot in dots:          # parsed once here, inherited by the forked workers
                try:
                    sd.parse_dot(dot)
                except Exception:     # noqa: BLE001 -- not cached: the worker that needs
                    pass              # this .dot raises it where the serial loop would
        import multiprocessing
        from concurrent.futures import ProcessPoolExecutor
        from concurrent.futures.process import BrokenProcessPool
        ex = ProcessPoolExecutor(max_workers=min(workers, len(kjs)),
                                 mp_context=multiprocessing.get_context("fork"))
        done = False
        try:
            for tag, payload in ex.map(_pool_task, kjs, [dots] * len(kjs)):
                if tag != "OK":
                    _reraise(tag, payload)
                yield payload
            done = True
        except BrokenProcessPool as e:
            raise AnalysisWorkerDied(f"analysis pool worker died: {e}") from None
        finally:
            if not done:              # stop now: kill the workers still judging
                for p in list((getattr(ex, "_processes", None) or {}).values()):
                    try:
                        p.kill()
                    except Exception:  # noqa: BLE001
                        pass
            ex.shutdown(wait=True, cancel_futures=True)


def _analyze_reports(depdir, cubindir, workers=None, cache=None):
    """Run sync_dominance.analyze over the dump and dedup RACE verdicts on
    (unordered pc pair, space). Used for BOTH modes: analyze derives the verdict
    from the trace edges, and when the dump carries HbClock's hb_races
    (vector-clock mode) it crosses them in via _hb_class -- so the vector-clock dump
    can flag a statically-ordered pair HbClock observed racing (e.g. the canary),
    while the scalar-clock dump yields the static-leg verdict (+ the offline
    barrier-only pass) and misses it. That is exactly the vector-clock vs
    scalar-clock surface the task compares.

    -> (ids, pcs_set, raw_verdicts). ids/pcs are the RACE reports (a latent pair is a
    RACE: the Race u Latent operating point, D2). raw holds them with their
    `matrix_class` (the verdict-matrix class before judge's relabels, of the pair's
    strongest RACE verdict over the kernels: model_bug > structural > race (scalar-clock,
    no class) > latent) and, after them, the SC reports (`"verdict": "SC"`: unordered
    strong conflicts, informational, never in ids; T9/D12) -- split_raw() separates them,
    classes_note() counts them. This branch's analyze(dot, trace) takes no
    assume_warp_lockstep kwarg (that lives only on the eval branch). Only
    AlignmentError is swallowed (wrong dot -> next); other exceptions propagate so
    a real failure is an ERROR row, not a silent CLEAN.

    X7 (eval/VERDICT_PARALLEL.md): workers = the pool that judges the kernel JSONs
    (analysis_workers(): None = the node's cores, 1 = the serial loop); the merge below reads
    their reports in the serial loop's order (sorted kernel_*.json names), so the result is
    the serial one. cache = the static-graph cache (graph_cache_enabled(): on unless
    $CUVEIN_GRAPH_CACHE=0); with a pool, the parent parses every .dot once before forking
    and the workers inherit the parsed graphs."""
    dots = sorted(glob.glob(f"{cubindir}/*.dot"))
    kjs = sorted(glob.glob(f"{depdir}/kernel_*.json"))
    workers = analysis_workers(workers)
    cached = graph_cache_enabled(cache)
    ded, cls, ded_sc = {}, {}, {}
    mbug = set()   # keys with a model_bug annotation (R1 contradicted by hb_races; DR or SC)
    policies = set()   # T16: the chain-edge policy the dumps' hb_races were computed under
    a2s = {}   # T14: key -> [race of this run, some unflagged, latent, flagged without R3, flag seen]
    for rep in _kernel_reports(kjs, dots, workers, cached):   # streamed, in kjs order
        if rep is None:
            continue
        if rep.get("gate_policy"):
            policies.add(rep["gate_policy"])
        for v in rep["verdicts"]:
            k = agg._dedup_key(v)
            if v.get("model_bug") or v.get("hb_class") == "model_bug":
                mbug.add(k)
            if v["verdict"] == "RACE":
                ded.setdefault(k, v)
                c = v.get("matrix_class", v.get("hb_class")) or "race"
                if _CLASS_RANK.get(c, 2) > _CLASS_RANK.get(cls.get(k), -1):
                    cls[k] = c
                s = a2s.setdefault(k, [False, False, False, False, False])
                f = v.get("a2_uncertain")
                s[4] = s[4] or f is not None
                if c in ("structural", "model_bug"):
                    s[0] = True
                    s[1] = s[1] or f is not True
                    s[3] = s[3] or (f is True and c == "structural" and not v.get("hb_chain"))
                elif c == "latent":
                    s[2] = True
            elif v["verdict"] == "SC":
                ded_sc.setdefault(k, v)
    ids, pcs_all, raw = [], set(), []
    for k, v in sorted(ded.items(), key=lambda kv: kv[0]):
        a, b, space = k
        ids.append(f"{space}:{hex(a)}-{hex(b)}:{v.get('race_type', '')}")
        pcs_all.update((a, b))
        raw.append({"a_pc": a, "b_pc": b, "space": space,
                    "race_type": v.get("race_type"), "strength": v.get("strength"),
                    "hb_class": v.get("hb_class"), "hb_chain": v.get("hb_chain"),
                    "matrix_class": cls[k], "conflict_class": v.get("conflict_class"),
                    "a2": _a2_status(a2s[k]), "model_bug": k in mbug})
    for k, v in sorted((k, v) for k, v in ded_sc.items() if k not in ded):
        a, b, space = k
        raw.append({"a_pc": a, "b_pc": b, "space": space, "verdict": "SC",
                    "race_type": v.get("race_type"), "strength": v.get("strength"),
                    "hb_class": v.get("hb_class"), "hb_chain": v.get("hb_chain"),
                    "matrix_class": v.get("matrix_class"), "conflict_class": "SC",
                    "model_bug": k in mbug})
    ids_h, raw_h = _host_reports(depdir)
    # T16: a certain-policy dump set is noted on every report (classes_note reads it off raw);
    # a mixed set (some kernels under each policy) is noted as such and is never the paper's
    if policies:
        pol = next(iter(policies)) if len(policies) == 1 else "mixed"
        for r in raw:
            r["gate_policy"] = pol
    return ids + ids_h, pcs_all | {r[p] for r in raw_h for p in ("a_pc", "b_pc") if r[p] is not None}, \
        raw + raw_h


# strength of a RACE report's class for the per-pair dedup (the pair counts as a race of
# this run if any of its verdicts is one)
_CLASS_RANK = {"latent": 0, "race": 1, "structural": 2, "model_bug": 3}


def _a2_status(s):
    """T14 (design/a2_flag.md): one deduped RACE report's A2 exposure from its verdicts'
    pair-level flags -- None (no flag in the dumps, or no race of this run), 'robust' (some DR
    instance unflagged), 'race' (A2-uncertain at the Race-alone point only: at Race u Latent
    it stays a positive -- it also has a latent verdict, or a flagged pair no R1/R3
    certificate orders, which reordered would be Latent), 'both' (uncertain at both points)."""
    race, some_unflagged, latent, alt_latent, seen = s
    if not seen or not race:
        return None
    if some_unflagged:
        return "robust"
    return "race" if latent or alt_latent else "both"


def split_raw(raw):
    """_analyze_reports' raw -> (RACE reports, SC reports)."""
    return ([r for r in raw if r.get("verdict") != "SC"],
            [r for r in raw if r.get("verdict") == "SC"])


def classes_note(raw):
    """`classes=<class>:<n>,...` over the deduped reports (D2): the RACE reports by their
    pre-relabel matrix class (latent = the Latent tier; race = scalar-clock, which cannot
    tell Race from Latent; host = T2 host reports), the SC reports as sc / latent-sc.
    make_tables derives the Race-alone operating point from it. '' if there are none."""
    n = {}
    for r in raw:
        c = r.get("matrix_class") or ("host" if r.get("host") else "race")
        n[c] = n.get(c, 0) + 1
    note = "classes=" + ",".join(f"{c}:{k}" for c, k in sorted(n.items())) if n else ""
    # T14: `;a2_uncertain=<k>:<m>` -- k RACE reports A2-uncertain at Race alone, m of them at
    # Race u Latent too (_a2_status); only when the dumps carry the flag (vector-clock, T14+)
    a2 = [r.get("a2") for r in raw if r.get("verdict") != "SC"]
    if note and any(x is not None for x in a2):
        note += (f";a2_uncertain={sum(x in ('race', 'both') for x in a2)}"
                 f":{sum(x == 'both' for x in a2)}")
    # `;model_bug=<n>`: deduped reports (RACE or SC) carrying the model_bug annotation -- R1
    # claims every-schedule order and hb_races contradicts it; the report's verdict is its
    # class's (an SC one is a Strong conflict)
    nb = sum(bool(r.get("model_bug")) for r in raw)
    if note and nb:
        note += f";model_bug={nb}"
    # T16: `;gate_policy=certain` when the dumps' hb_races were computed under the certain clock
    # (sync_dominance.dump_policy_of); the recorded policy, today's default, is not noted, so
    # every existing row reads as recorded. make_tables keys the "Race (sound)" column on it.
    pol = {r.get("gate_policy") for r in raw if r.get("gate_policy")}
    if note and pol and pol != {"recorded"}:
        note += f";gate_policy={'mixed' if len(pol) > 1 else next(iter(pol))}"
    return note


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


def run_one(mrow, modes, cuda, writer, confirm_dir, cap=1200):
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
    # so a literal 10x cap kills it on ~0.1s-native programs). Floor 120s, cap 1200s unless
    # --timeout-cap is passed (X1: 5,400 s); the cap goes into every row's notes (cap=<s>).
    tool_timeout = min(max(int(10 * native), 120), cap) if native else man_timeout

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
            raw, raw_sc = [], []
            if to:
                verdict, ids, pcs = "TIMEOUT", [], set()
            elif not kjs:
                verdict, ids, pcs = "ERROR", [], set()
                notes = f"no-kernel-json(rc={rc})"
            else:
                # rc != native rc: the app died under the tool (accelprof returns 1,
                # e.g. an OOM-killed vector-clock run) and the dump holds only the kernels
                # finished before that. A race it shows is a race; it is never CLEAN.
                complete = rc == native_rc
                try:
                    ids, pcs, raw = _analyze_reports(depdir, cubindir)
                except ValueError:
                    if complete:
                        raise
                    ids, pcs, raw = [], set(), []
                verdict = "RACE" if ids else "CLEAN"
                cnote = classes_note(raw)
                raw, raw_sc = split_raw(raw)
                if cnote:
                    notes = cnote
                if not complete:
                    notes = f"partial(rc={rc};nkernels={len(kjs)})" + (f";{cnote}" if cnote else "")
                    if not ids:
                        verdict = "ERROR"
                        notes = f"incomplete-trace(rc={rc};nkernels={len(kjs)})"
            notes = f"cap={cap};{notes}"
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
                                "raw": raw, "raw_sc": raw_sc, "scope_file": scope,
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
    ap.add_argument("--timeout-cap", dest="timeout_cap", type=int, default=1200,
                    help="maximum tool timeout in s, min(max(10x native, 120), cap) "
                         "(default 1200; recorded as cap=<s> in the row's notes)")
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
                run_one(mrow, modes, cuda, writer, confirm_dir, cap=a.timeout_cap)
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

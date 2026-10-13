#!/usr/bin/env python3
"""T12 (CLAUDE.md section C, step 4): measure the instance gate and the R3 amendments on the kept
stores before wiring them, no GPU.

The base is T10's re-scored store `t10-after` (the evcand + full-2026-09-22 selection of
eval/results/t10-rescore/selection.json, whose vector-clock dumps carry `hb_races` from the T10
oracle under the trusting gate). Three analyses of the same programs:

  before   t10-after, this checkout with CUVEIN_R3_TRACE_RELEASE=0 CUVEIN_R3_BEFORE_ACQUIRE=0
           (= the pre-T12 verdict layer by construction: the region release point, the region
           CAS-section test, no write-before-lock decline) -- the trusting-gate `hb_races`
  r3only   t10-after, this checkout's defaults: R3's trace release point, fenced() in the
           CAS-section test, the write-before-lock decline -- still trusting `hb_races`
  after    t12-after (the same dumps re-scored by the gated oracle), this checkout's defaults

The gate governs (ATOM) edges only, so a program with no atomic RMW pc in any kernel re-scores
identically under it (its t12-after entry is a symlink to t10-after); R3 needs an atomic too.

  prepare  per program: affected iff some kernel of some dot has an RMW pc -> selection; the
           AFTER store t12-after (unaffected: symlink to the t10-after dir).
  oracle   --shard k/n: every affected program's vector-clock dumps through hb_oracle.py under
           the instance gate (strong-ldst token) -> t12-after/<id>/vector-clock/ and a detail
           JSON per program (old and new pc pairs with their classes, the gate counters).
  tables   race-set deltas (details) and the verdict deltas before -> r3only -> after.

    .env/bin/python eval/baselines/t12_rescore.py prepare               (a normal node)
    W=<wt> sbatch --array=0-15 eval/baselines/setup/p_t12_rescore.sh     (oracle shards)
    W=<wt> WHICH=before|r3only|after IDFILE=... sbatch --array=0-31 eval/baselines/setup/p_t12_analyze.sh
    .env/bin/python eval/baselines/t12_rescore.py tables                (login node)
"""
import argparse
import csv
import glob
import json
import os
import resource
import shutil
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, f"{APH}/python")
sys.path.insert(0, HERE)
import hb_modes  # noqa: E402

VC, SCM = hb_modes.VECTOR_CLOCK, hb_modes.SCALAR_CLOCK
BEEGFS = f"/mnt/beegfs/{os.environ.get('USER', 'fzheng4')}/cuvein_traces"
BASE = f"{BEEGFS}/t10-after"
AFTER = f"{BEEGFS}/t12-after"
T10 = f"{APH}/eval/results/t10-rescore"
OUT = f"{APH}/eval/results/t12-rescore"
MANIFEST = f"{APH}/eval/results/t9-rescore/manifest.t9.csv"
SELECTION = f"{OUT}/selection.json"


def rmw_ops(dots):
    """Counter of the RMW opcodes over every kernel of the dots (empty: the gate is moot)."""
    import sync_dominance as sd
    out = Counter()
    for dot in dots:
        try:
            kernels = sd.parse_dot(dot)
        except sd.AlignmentError:
            continue
        for _m, (blocks, _e, _en) in kernels.items():
            for ins in blocks.values():
                for _pc, op in ins:
                    if sd.atomic_scope(op) is not None:
                        out[op] += 1
    return out


def cmd_prepare(a):
    t10 = json.load(open(f"{T10}/selection.json"))["programs"]
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(AFTER, exist_ok=True)
    sel, t0 = {}, time.time()
    for n, (_id, s) in enumerate(sorted(t10.items()), 1):
        src = f"{BASE}/{_id}"
        rec = {"pset": s["pset"], "modes": s["modes"], "dump_mb": s["dump_mb"],
               "src": os.path.realpath(src)}
        if not os.path.isdir(src):
            rec["skip"] = "no-t10-after-dir"
            sel[_id] = rec
            continue
        ops = rmw_ops(sorted(glob.glob(f"{src}/dots/*.dot")))
        rec["affected"] = bool(ops)
        rec["rmw_ops"] = dict(ops)
        dst = f"{AFTER}/{_id}"
        if not ops and not os.path.lexists(dst):
            os.symlink(rec["src"], dst)
        sel[_id] = rec
        if n % 50 == 0:
            print(f"[{n}/{len(t10)}] {time.time() - t0:.0f}s", flush=True)
    json.dump({"base": BASE, "after": AFTER, "programs": sel}, open(SELECTION, "w"), indent=1)
    aff = sorted(i for i, r in sel.items() if r.get("affected"))
    with open(f"{OUT}/ids_affected.txt", "w") as f:
        f.write("".join(i + "\n" for i in aff))
    print(f"{len(sel)} programs, {len(aff)} affected ({Counter(sel[i]['pset'] for i in aff)}), "
          f"{sum('skip' in r for r in sel.values())} skipped -> {SELECTION}")


def _pairs(races):
    """hb_races -> {(pc_lo, pc_hi): {class: records}}"""
    out = defaultdict(Counter)
    for r in races or ():
        x, y = r.get("a_pc"), r["b_pc"]
        k = (min(x, y), max(x, y)) if x is not None else (None, y)
        out[k][r.get("class", "DR")] += r.get("count", 1)
    return out


def _rescore_program(_id, rec):
    import hb_oracle
    import sync_dominance as sd
    src, dst = rec["src"], f"{AFTER}/{_id}"
    tmp = dst + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    for name in os.listdir(src):
        if name != VC:
            os.symlink(os.path.realpath(f"{src}/{name}"), f"{tmp}/{name}")
    det = {"id": _id, "pset": rec["pset"], "src": src, "kernels": []}
    if VC in rec["modes"] and os.path.isdir(f"{src}/{VC}"):
        vdir = f"{src}/{VC}"
        os.makedirs(f"{tmp}/{VC}")
        dots = sorted(glob.glob(f"{src}/dots/*.dot"))
        for name in sorted(os.listdir(vdir)):
            path = f"{vdir}/{name}"
            if not (name.startswith("kernel_") and name.endswith(".json")):
                os.symlink(os.path.realpath(path), f"{tmp}/{VC}/{name}")
                continue
            t0 = time.time()
            trace = json.load(open(path))
            k = {"file": name, "events": len(trace.get("hb_events") or ())}
            if not trace.get("hb_events"):
                k["skip"] = "no-hb_events"
                os.symlink(os.path.realpath(path), f"{tmp}/{VC}/{name}")
                det["kernels"].append(k)
                continue
            rep = err = None
            for strict in ("1", "0"):          # a TV violation: re-run as the engine continues
                os.environ["YOSEMITE_HB_STRICT"] = strict
                for dot in dots:
                    try:
                        rep = hb_oracle.analyze(dot, path, strong_ldst="token", gate="instance")
                        break
                    except sd.AlignmentError as e:
                        if str(e).startswith("TV-"):
                            err = str(e)
                            break
                if rep is not None or err is None:
                    break
            os.environ.pop("YOSEMITE_HB_STRICT", None)
            if err:
                k["tv"] = err[:200]
            if rep is None:
                k["skip"] = "no-aligning-cfg"
                os.symlink(os.path.realpath(path), f"{tmp}/{VC}/{name}")
                det["kernels"].append(k)
                continue
            old, new = _pairs(trace.get("hb_races")), _pairs(rep["races"])
            so_old = {tuple(p[:2]) for p in trace.get("hb_races_sync_only") or ()}
            so_new = {tuple(p[:2]) for p in rep["races_sync_only"]}
            k.update(kernel=trace["kernel"]["kernel_name"],
                     old_pairs=sorted([list(p), dict(c)] for p, c in old.items()),
                     new_pairs=sorted([list(p), dict(c)] for p, c in new.items()),
                     sync_changed=sorted(so_old ^ so_new), gate=rep["summary"].get("gate", {}),
                     seconds=round(time.time() - t0, 2))
            trace["hb_races"] = rep["races"]
            if trace.get("hb_races_sync_only") is not None:
                trace["hb_races_sync_only"] = rep["races_sync_only"]
            trace["hb_gate"] = "instance"
            trace["t12_rescore"] = {"from": path, "oracle": "hb_oracle.py (T12, instance gate)"}
            with open(f"{tmp}/{VC}/{name}", "w") as f:
                json.dump(trace, f)
            det["kernels"].append(k)
            del trace, rep
    if os.path.lexists(dst):
        if os.path.islink(dst):
            os.remove(dst)
        else:
            shutil.rmtree(dst)
    os.rename(tmp, dst)
    return det


def cmd_oracle(a):
    sel = json.load(open(SELECTION))["programs"]
    ids = sorted(i for i, r in sel.items() if r.get("affected")
                 and (not a.id or i in a.id.split(",")))
    # big dumps last, so a shard's small programs are not stuck behind them
    ids.sort(key=lambda i: (sel[i]["dump_mb"] > 2000, i))
    k, n = (int(x) for x in a.shard.split("/"))
    ids = [i for j, i in enumerate(ids) if j % n == k]
    det_dir = f"{OUT}/detail"
    os.makedirs(det_dir, exist_ok=True)
    for j, _id in enumerate(ids, 1):
        out = f"{det_dir}/{_id}.json"
        if os.path.exists(out) and not a.force:
            continue
        print(f"[{j}/{len(ids)}] {_id} ({sel[_id]['dump_mb']} MB)", flush=True)
        t0 = time.time()
        part = out + ".part"
        pid = os.fork()
        if pid == 0:                           # child: cap memory, rescore, write the detail
            lim = int(a.mem_gb * 1e9)
            resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
            try:
                det = _rescore_program(_id, sel[_id])
            except MemoryError:
                det = {"id": _id, "error": "oracle-oom"}
            except Exception as e:             # noqa: BLE001 -- recorded, not swallowed
                det = {"id": _id, "error": f"{type(e).__name__}: {e}"[:400]}
            with open(part, "w") as f:
                json.dump(det, f)
            os._exit(0)
        status = None
        while True:
            done, status = os.waitpid(pid, os.WNOHANG)
            if done:
                break
            if time.time() - t0 > a.timeout:
                os.kill(pid, 9)
                os.waitpid(pid, 0)
                status = "timeout"
                break
            time.sleep(0.5)
        if status == "timeout":
            det = {"id": _id, "error": f"oracle-timeout({a.timeout}s)"}
        else:
            try:
                det = json.load(open(part))
            except (OSError, ValueError):
                det = {"id": _id, "error": f"oracle-died(status={status})"}
        if os.path.exists(part):
            os.remove(part)
        det.update(pset=sel[_id]["pset"], dump_mb=sel[_id]["dump_mb"],
                   seconds=round(time.time() - t0, 1))
        if "error" in det:
            shutil.rmtree(f"{AFTER}/{_id}.tmp", ignore_errors=True)
        json.dump(det, open(out, "w"))
        print(f"   -> {det.get('error', 'ok')} {det['seconds']}s", flush=True)


# ---------------------------------------------------------------- tables (login node)

_ORDER = {"RACE": 3, "CLEAN": 2, "TIMEOUT": 1, "ERROR": 0}


def _load_csv(pattern):
    """(id, mode) -> row; reps collapse RACE > CLEAN > TIMEOUT > ERROR (make_tables)."""
    runs = {}
    for p in sorted(glob.glob(pattern)):
        for r in csv.DictReader(open(p, newline="")):
            key = (r["id"], hb_modes.canon(r.get("mode", ""), p))
            prev = runs.get(key)
            if prev is None or _ORDER.get(r["verdict"], 0) > _ORDER.get(prev["verdict"], 0):
                runs[key] = r
    return runs


def _suite_table(L, man, runs_by_name, ra, mt):
    """Per suite and mode: TP/FN/FP/TN at Race u Latent and at Race alone, per analysis."""
    names = list(runs_by_name)
    L.append("| pset | mode | " + " | ".join(f"{n}: RuL TP/FN/FP/TN, RA TP/FN/FP/TN, sc R/C"
                                             for n in names) + " |")
    L.append("|---|---|" + "---|" * len(names))
    agg = defaultdict(lambda: {n: Counter() for n in names})
    keys = set().union(*(set(r) for r in runs_by_name.values()))
    for key in keys:
        lab = man.get(key[0], {}).get("label", "")
        if lab not in ("RACE", "CLEAN") or key[1] not in (VC, SCM):
            continue
        ps = man.get(key[0], {}).get("pset", "?")
        for n, runs in runs_by_name.items():
            r = runs.get(key)
            if r is None:
                continue
            c = agg[(ps, key[1])][n]
            for op, v in (("rl", r.get("verdict")), ("ra", ra(r))):
                if v in ("RACE", "CLEAN"):
                    c[op + {("RACE", "RACE"): "_tp", ("RACE", "CLEAN"): "_fn",
                            ("CLEAN", "RACE"): "_fp", ("CLEAN", "CLEAN"): "_tn"}[(lab, v)]] += 1
            cls = mt.report_classes(r) or {}
            if cls.get("sc") or cls.get("latent-sc"):
                c["sc_" + lab] += 1
    q = lambda c, op: "/".join(str(c[f"{op}_{x}"]) for x in ("tp", "fn", "fp", "tn"))
    for (ps, m), c in sorted(agg.items()):
        L.append(f"| {ps} | {m} | " + " | ".join(
            f"{q(c[n], 'rl')}, {q(c[n], 'ra')}, {c[n]['sc_RACE']}/{c[n]['sc_CLEAN']}"
            for n in names) + " |")


def _deltas(L, man, sel, b_runs, a_runs, title, ra, mt):
    L.append(f"\n## {title}\n")
    moves, rows = Counter(), []
    for key in sorted(set(b_runs) | set(a_runs)):
        b, f = b_runs.get(key) or {}, a_runs.get(key) or {}
        vb, vf = b.get("verdict", "-"), f.get("verdict", "-")
        cb = (mt.report_classes(b) or {}) if b else {}
        cf = (mt.report_classes(f) or {}) if f else {}
        moves[(key[1], vb, vf)] += 1
        if vb != vf or cb != cf or ra(b) != ra(f):
            rows.append(dict(mode=key[1], id=key[0], label=man.get(key[0], {}).get("label", ""),
                             vb=vb, vf=vf, rab=ra(b), raf=ra(f), cb=cb, cf=cf))
    L.append("| mode | before | after | programs |")
    L.append("|---|---|---|---|")
    for (m, vb, vf), n in sorted(moves.items()):
        L.append(f"| {m} | {vb} | {vf} | {n} |")
    both = [r for r in rows if "-" not in (r["vb"], r["vf"])]
    for op_name, gb, ga in (("Race u Latent", "vb", "vf"), ("Race alone", "rab", "raf")):
        tp_gain = [r for r in both if r["label"] == "RACE" and r[gb] != "RACE" and r[ga] == "RACE"]
        tp_lost = [r for r in both if r["label"] == "RACE" and r[gb] == "RACE" and r[ga] != "RACE"]
        fp_new = [r for r in both if r["label"] == "CLEAN" and r[gb] != "RACE" and r[ga] == "RACE"]
        fp_gone = [r for r in both if r["label"] == "CLEAN" and r[gb] == "RACE" and r[ga] != "RACE"]
        L.append(f"\n### {op_name}: TPs gained {len(tp_gain)}, TPs lost {len(tp_lost)}, "
                 f"new FPs {len(fp_new)}, FPs removed {len(fp_gone)}\n")
        for t, rs in (("TPs lost", tp_lost), ("FPs removed", fp_gone), ("TPs gained", tp_gain),
                      ("New FPs", fp_new)):
            if rs:
                L.append(f"{t}: " + ", ".join(f"{r['id']} ({r['mode']})" for r in rs) + "\n")
    L.append("\n| mode | program | label | verdict | Race alone | classes before | classes after |")
    L.append("|---|---|---|---|---|---|---|")
    fmt = lambda c: " ".join(f"{k}={v}" for k, v in sorted(c.items()) if v) or "-"
    for r in rows:
        L.append(f"| {r['mode']} | {r['id']} | {r['label']} | {r['vb']} -> {r['vf']} | "
                 f"{r['rab']} -> {r['raf']} | {fmt(r['cb'])} | {fmt(r['cf'])} |")


def cmd_tables(a):
    import make_tables as mt
    man = {r["id"]: r for r in csv.DictReader(open(MANIFEST, newline=""))}
    sel = json.load(open(SELECTION))["programs"]
    dets = {os.path.basename(p)[:-5]: json.load(open(p))
            for p in glob.glob(f"{OUT}/detail/*.json")}
    aff = sorted(i for i, r in sel.items() if r.get("affected"))
    ra = lambda r: mt.race_alone_verdict({"verdict": r.get("verdict", "-"),
                                          "notes": r.get("notes", "")}) if r else "-"
    L = ["# T12 re-score tables (generated by eval/baselines/t12_rescore.py tables)\n"]
    L.append(f"{len(aff)} of {len(sel)} programs have an RMW pc in some kernel "
             f"({', '.join(f'{p}: {n}' for p, n in sorted(Counter(sel[i]['pset'] for i in aff).items()))}); "
             f"the rest are symlinked (the gate and R3 need an atomic).\n")
    # --- race-set deltas and gate counters
    L.append("## Race-set deltas (vector-clock dumps, pc pairs: trusting gate -> instance gate)\n")
    L.append("| pset | program | RMW records | rel=0 | acq=0 | held | held reported | pairs before "
             "| pairs after | new DR | new SC | lost | DR->SC | SC->DR |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    tot, errs = Counter(), []
    for _id in aff:
        d = dets.get(_id)
        if d is None or "error" in d:
            errs.append((_id, d.get("error") if d else "no detail"))
            continue
        ks = [k for k in d["kernels"] if "old_pairs" in k]
        if not ks:
            continue
        g = Counter()
        for k in ks:
            g.update(k.get("gate", {}))
        side = lambda s: {(k["file"], tuple(p)): set(c) for k in ks for p, c in k[s]}
        old, new = side("old_pairs"), side("new_pairs")
        cls = lambda m, key: "DR" if "DR" in m.get(key, ()) else ("SC" if key in m else None)
        row = Counter(rmw=g["rmw"], rel0=g["rel0"], acq0=g["acq0"], held=g["held"],
                      hrep=g["held_reported"], pb=len(old), pa=len(new),
                      ndr=sum(1 for x in new if x not in old and cls(new, x) == "DR"),
                      nsc=sum(1 for x in new if x not in old and cls(new, x) == "SC"),
                      lost=sum(1 for x in old if x not in new),
                      dr_sc=sum(1 for x in old if x in new and cls(old, x) == "DR" and cls(new, x) == "SC"),
                      sc_dr=sum(1 for x in old if x in new and cls(old, x) == "SC" and cls(new, x) == "DR"))
        tot.update(row)
        if row["pa"] != row["pb"] or row["ndr"] or row["nsc"] or row["lost"] or row["dr_sc"] \
                or row["sc_dr"]:
            L.append(f"| {sel[_id]['pset']} | {_id} | " + " | ".join(
                str(row[c]) for c in ("rmw", "rel0", "acq0", "held", "hrep", "pb", "pa", "ndr",
                                      "nsc", "lost", "dr_sc", "sc_dr")) + " |")
    L.append("| **all affected** | | " + " | ".join(
        str(tot[c]) for c in ("rmw", "rel0", "acq0", "held", "hrep", "pb", "pa", "ndr", "nsc",
                              "lost", "dr_sc", "sc_dr")) + " |")
    L.append(f"\nPrograms without a race-set change are left out of the table. Oracle errors / not "
             f"re-scored: {len(errs)}" + (" -- " + "; ".join(f"{i}: {e}" for i, e in errs) if errs else "")
             + ".\n")
    # --- verdicts
    runs = {n: _load_csv(f"{OUT}/{n}/*.csv") for n in ("before", "r3only", "after")}
    runs = {n: r for n, r in runs.items() if r}
    L.append("## Per suite (affected programs, labelled; RuL = Race u Latent, RA = Race alone, "
             "sc = programs with an SC report, labelled RACE / CLEAN)\n")
    _suite_table(L, man, runs, ra, mt)
    if "before" in runs and "r3only" in runs:
        _deltas(L, man, sel, runs["before"], runs["r3only"],
                "Verdict deltas, before -> r3only (R3 amendments alone, trusting hb_races)", ra, mt)
    if "r3only" in runs and "after" in runs:
        _deltas(L, man, sel, runs["r3only"], runs["after"],
                "Verdict deltas, r3only -> after (the instance gate's hb_races)", ra, mt)
    if "before" in runs and "after" in runs:
        _deltas(L, man, sel, runs["before"], runs["after"],
                "Verdict deltas, before -> after (all of T12)", ra, mt)
    open(f"{OUT}/T12_RESCORE_TABLES.md", "w").write("\n".join(L) + "\n")
    print(f"-> {OUT}/T12_RESCORE_TABLES.md")


def cmd_review(a):
    """The rebase review's verdict moves on t12-after: `after` (the pre-rebase detector, the 464
    programs with an RMW) -> `r1old` (the review's code with CUVEIN_R1_LOOP_SCOPE=1
    CUVEIN_R3_LANDING=0: the model_bug annotation alone) -> `final` (defaults: + R1's same-pc fix
    + R3's landing decline), the last two over all 594 programs."""
    import make_tables as mt
    man = {r["id"]: r for r in csv.DictReader(open(MANIFEST, newline=""))}
    sel = json.load(open(SELECTION))["programs"]
    ra = lambda r: mt.race_alone_verdict({"verdict": r.get("verdict", "-"),
                                          "notes": r.get("notes", "")}) if r else "-"
    runs = {n: _load_csv(f"{OUT}/{n}/*.csv") for n in ("after", "r1old", "final")}
    L = ["# T12 rebase review: verdict moves (generated by eval/baselines/t12_rescore.py review)\n",
         "Store t12-after (kept dumps; the gated oracle's hb_races, unchanged by the rebase: T5b "
         "touched the engine only). `after` = the pre-rebase detector (464 programs with an RMW); "
         "`r1old` = the review's code with the R1 same-pc form and the pre-T12 landing rule "
         "(CUVEIN_R1_LOOP_SCOPE=1 CUVEIN_R3_LANDING=0), i.e. the model_bug annotation alone; "
         "`final` = defaults. Programs whose analysis hit the 4 h cap or failed identically on "
         "both sides appear as unchanged ERROR/TIMEOUT rows.\n",
         "## Per suite (labelled; RuL = Race u Latent, RA = Race alone, sc = programs with an SC "
         "report, labelled RACE / CLEAN)\n"]
    _suite_table(L, man, {"r1old": runs["r1old"], "final": runs["final"]}, ra, mt)
    aff = {k: v for k, v in runs["r1old"].items() if sel.get(k[0], {}).get("affected")}
    _deltas(L, man, sel, runs["after"], aff,
            "Verdict deltas, after -> r1old (the model_bug annotation; the 464 programs with an RMW)",
            ra, mt)
    _deltas(L, man, sel, runs["r1old"], runs["final"],
            "Verdict deltas, r1old -> final (R1 certifies no same-pc pair; R3 declines a landing "
            "on the unlock; all programs)", ra, mt)
    mb = [(k, mt.report_model_bug(r)) for k, r in sorted(runs["final"].items()) if mt.report_model_bug(r)]
    L.append("\n## model_bug annotations left (final)\n")
    L.append("\n".join(f"- {k[0]} ({k[1]}): {n}" for k, n in mb) if mb else "none")
    open(f"{OUT}/T12_REVIEW_TABLES.md", "w").write("\n".join(L) + "\n")
    print(f"-> {OUT}/T12_REVIEW_TABLES.md")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare")
    sub.add_parser("review")
    o = sub.add_parser("oracle")
    o.add_argument("--shard", default="0/1")
    o.add_argument("--id", default="")
    o.add_argument("--timeout", type=int, default=14400)
    o.add_argument("--mem-gb", type=float, default=170)
    o.add_argument("--force", action="store_true")
    sub.add_parser("tables")
    a = ap.parse_args(argv)
    {"prepare": cmd_prepare, "oracle": cmd_oracle, "tables": cmd_tables, "review": cmd_review}[a.cmd](a)
    return 0


if __name__ == "__main__":
    sys.exit(main())

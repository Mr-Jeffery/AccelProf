#!/usr/bin/env python3
"""T16 (CLAUDE.md section C, steps 3-4; eval/CERTAIN_CLOCK.md): re-score the kept stores under
both chain-edge policies of hb_oracle.py, no GPU.

Two sets of dumped programs:
  main   T12's selection (eval/results/t12-rescore/selection.json): the evcand/full-2026-09-22
         vector-clock dumps as re-oracled by T12 under the instance gate (store t12-after, 594
         programs; recorded before T3b, so a thread's LAST RMW has an open-ended window);
  exits  the dumps HbClock recorded after T3b with exit records -- stores t19-parity (66
         programs, the d67ed41 runtime) and t12-eval-t12rb (62, ScoR P4/P5, the T12 runtime);
         t19-parity wins when a program is in both.
A program with no RMW pc in any kernel (T12's `affected` = False) re-scores identically under
the two policies (the policy governs (ATOM) edges only): its AFTER entry is a symlink.

  prepare  the selection (per program: src, pset, dump_mb, affected, set) and the id lists for
           `parallel.py analyze`.
  oracle   --set main|exits --shard k/n: every affected program's vector-clock dumps through
           hb_oracle.py under `recorded` and under `certain` (strong-ldst token, the dump's gate)
           in a child under a wall-clock and address-space cap -> the AFTER store
           t16-certain[-exits]/<id>/vector-clock/ (hb_races replaced by the certain clock's,
           hb_gate_policy = certain, hb_chain) and a detail JSON per program: per kernel the
           stored, recorded and certain pc-pair sets with classes, counts and a2_uncertain, the
           chain counters under both policies, whether oracle(recorded) == the stored hb_races
           (parity of the default policy with T12's / HbClock's), and the invariant
           Rep_certain >= Rep_recorded (a violation is a bug, not a result).
  tables   eval/results/t16-rescore/T16_RESCORE_TABLES.md: parity, the invariant, the chain
           edges refused per suite (with the open-ended share), the race-set deltas, and the
           verdict deltas recorded -> certain (the "Race (sound)" column) from the
           `parallel.py analyze` CSVs of both stores.

    .env/bin/python eval/baselines/t16_rescore.py prepare                     (a normal node)
    W=<wt> SET=main  sbatch --array=0-23 eval/baselines/setup/p_t16_rescore.sh  (oracle shards)
    W=<wt> SET=exits sbatch --array=0-3  eval/baselines/setup/p_t16_rescore.sh
    W=<wt> SET=main  WHICH=recorded|certain sbatch --array=0-31 eval/baselines/setup/p_t16_analyze.sh
    W=<wt> SET=exits WHICH=recorded|certain sbatch --array=0-3  eval/baselines/setup/p_t16_analyze.sh
    .env/bin/python eval/baselines/t16_rescore.py tables                      (login node)
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
SETS = {
    "main": dict(base=[f"{BEEGFS}/t12-after"], after=f"{BEEGFS}/t16-certain",
                 manifest=f"{APH}/eval/results/t9-rescore/manifest.t9.csv",
                 selection=f"{APH}/eval/results/t12-rescore/selection.json"),
    "exits": dict(base=[f"{BEEGFS}/t19-parity", f"{BEEGFS}/t12-eval-t12rb"],
                  after=f"{BEEGFS}/t16-certain-exits", recorded=f"{BEEGFS}/t16-recorded-exits",
                  manifest=f"{HERE}/manifest.csv", selection=None),
}
# selection.json: {"programs": {set: {id: {...}}}} -- a program can be in both sets
OUT = f"{APH}/eval/results/t16-rescore"
SELECTION = f"{OUT}/selection.json"
POLICIES = ("recorded", "certain")


def rmw_ops(dots):
    """Counter of the RMW opcodes over every kernel of the dots (empty: the policy is moot)."""
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


# ---------------------------------------------------------------- prepare

def _dump_mb(pdir):
    return round(sum(os.path.getsize(p) for p in glob.glob(f"{pdir}/{VC}/kernel_*.json")) / 1e6, 1)


def cmd_prepare(a):
    os.makedirs(OUT, exist_ok=True)
    sel, t0 = {"main": {}, "exits": {}}, time.time()
    # main: T12's selection, re-pointed at t12-after (the dumps as T12 re-oracled them)
    t12 = json.load(open(SETS["main"]["selection"]))["programs"]
    base = SETS["main"]["base"][0]
    for _id, s in sorted(t12.items()):
        src = f"{base}/{_id}"
        if not os.path.isdir(src):
            continue
        sel["main"][_id] = dict(set="main", src=src, pset=s["pset"], modes=s["modes"],
                                dump_mb=s.get("dump_mb", _dump_mb(src)),
                                affected=bool(s.get("affected")), rmw_ops=s.get("rmw_ops", {}))
    man = {r["id"]: r for r in csv.DictReader(open(SETS["exits"]["manifest"], newline=""))}
    for base in SETS["exits"]["base"]:
        for _id in sorted(os.listdir(base)):
            src = f"{base}/{_id}"
            if _id in sel["exits"] or not os.path.isdir(f"{src}/{VC}") \
                    or not os.path.isfile(f"{src}/meta.json"):
                continue
            kjs = glob.glob(f"{src}/{VC}/kernel_*.json")
            if not kjs:
                continue
            has_events = any(b'"hb_events"' in open(k, "rb").read(1 << 20) for k in kjs[:3])
            if not has_events:        # a no-dump recording: aggregates only, nothing to replay
                continue
            ops = rmw_ops(sorted(glob.glob(f"{src}/dots/*.dot")))
            meta = json.load(open(f"{src}/meta.json"))
            sel["exits"][_id] = dict(set="exits", src=src,
                                     pset=man.get(_id, {}).get("pset", meta.get("pset", "?")),
                                     modes=[m for m in (VC, SCM) if os.path.isdir(f"{src}/{m}")],
                                     dump_mb=_dump_mb(src), affected=bool(ops), rmw_ops=dict(ops),
                                     store=os.path.basename(base))
    json.dump({"created": time.strftime("%Y-%m-%d %H:%M:%S"), "programs": sel},
              open(SELECTION, "w"), indent=1)
    for which in SETS:
        ids = sorted(sel[which])
        open(f"{OUT}/ids_{which}.txt", "w").write("\n".join(ids) + "\n")
        aff = [i for i in ids if sel[which][i]["affected"]]
        print(f"{which}: {len(ids)} programs, {len(aff)} with an RMW pc (re-scored), "
              f"{sum(sel[which][i]['dump_mb'] for i in aff):.0f} MB of vector-clock dumps")
    print(f"selection -> {SELECTION} ({time.time() - t0:.0f}s)")


# ---------------------------------------------------------------- oracle

def _pairs(races):
    """hb_races -> {(pc_lo, pc_hi): {class: [count, a2_uncertain]}}"""
    out = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for r in races or ():
        x, y = r.get("a_pc"), r["b_pc"]
        k = (min(x, y), max(x, y)) if x is not None else (None, y)
        c = out[k][r.get("class", "DR")]
        c[0] += r.get("count", 1)
        c[1] += r.get("a2_uncertain", 0)
    return out


def _key(r):
    return (r.get("a_pc"), r["b_pc"], r["kind"], r.get("class"), r["space"], r.get("dist"),
            r.get("async"), r.get("count"), r.get("a2_uncertain"))


def _agg(races):
    c = Counter()
    for r in races or ():
        c[(r.get("a_pc"), r["b_pc"], r["kind"], r.get("class"), r["space"], r.get("dist"),
           r.get("async"))] += r.get("count", 1)
    return c


def _run_oracle(dots, path, policy):
    import hb_oracle
    import sync_dominance as sd
    rep = err = None
    for strict in ("1", "0"):          # a TV violation: re-run as HbClock continues
        os.environ["YOSEMITE_HB_STRICT"] = strict
        for dot in dots:
            try:
                rep = hb_oracle.analyze(dot, path, strong_ldst="token", gate_policy=policy)
                break
            except sd.AlignmentError as e:
                if str(e).startswith("TV-"):
                    err = str(e)
                    break
        if rep is not None or err is None:
            break
    os.environ.pop("YOSEMITE_HB_STRICT", None)
    return rep, err


def _rescore_program(_id, rec):
    after = SETS[rec["set"]]["after"]
    src, dst = rec["src"], f"{after}/{_id}"
    tmp = dst + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    for name in os.listdir(src):
        if name != VC:
            os.symlink(os.path.realpath(f"{src}/{name}"), f"{tmp}/{name}")
    det = {"id": _id, "set": rec["set"], "pset": rec["pset"], "src": src, "kernels": []}
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
            k = {"file": name, "events": len(trace.get("hb_events") or ()),
                 "exits": bool(trace.get("hb_exits")), "gate": trace.get("hb_gate")}
            if not trace.get("hb_events"):
                k["skip"] = "no-hb_events"
                os.symlink(os.path.realpath(path), f"{tmp}/{VC}/{name}")
                det["kernels"].append(k)
                continue
            reps = {}
            for policy in POLICIES:
                rep, err = _run_oracle(dots, path, policy)
                if err:
                    k["tv"] = err[:200]
                if rep is None:
                    break
                reps[policy] = rep
            if len(reps) < 2:
                k["skip"] = "no-aligning-cfg"
                os.symlink(os.path.realpath(path), f"{tmp}/{VC}/{name}")
                det["kernels"].append(k)
                continue
            rec_, cer = reps["recorded"], reps["certain"]
            stored = trace.get("hb_races")
            ar, ac = _agg(rec_["races"]), _agg(cer["races"])
            k.update(kernel=trace["kernel"]["kernel_name"],
                     stored_eq_recorded={_key(r) for r in stored or ()} == {_key(r) for r in rec_["races"]},
                     stored_policy=trace.get("hb_gate_policy"),
                     superset=all(ac.get(x, 0) >= n for x, n in ar.items())
                     and rec_["races_sync_only"] == cer["races_sync_only"],
                     stored_pairs=sorted([list(p), {c: v for c, v in d.items()}]
                                         for p, d in _pairs(stored).items()),
                     rec_pairs=sorted([list(p), {c: v for c, v in d.items()}]
                                      for p, d in _pairs(rec_["races"]).items()),
                     cer_pairs=sorted([list(p), {c: v for c, v in d.items()}]
                                      for p, d in _pairs(cer["races"]).items()),
                     rec_chain=rec_["chain"], cer_chain=cer["chain"],
                     seconds=round(time.time() - t0, 2))
            trace["hb_races"] = cer["races"]
            trace["hb_gate_policy"] = "certain"
            trace["hb_chain"] = cer["chain"]
            trace["t16_rescore"] = {"from": path, "oracle": "hb_oracle.py (T16, --gate-policy certain)"}
            with open(f"{tmp}/{VC}/{name}", "w") as f:
                json.dump(trace, f)
            det["kernels"].append(k)
            del trace, reps, rec_, cer
    if os.path.lexists(dst):
        if os.path.islink(dst):
            os.remove(dst)
        else:
            shutil.rmtree(dst)
    os.rename(tmp, dst)
    return det


def cmd_oracle(a):
    sel = json.load(open(SELECTION))["programs"][a.set]
    after = SETS[a.set]["after"]
    os.makedirs(after, exist_ok=True)
    ids = sorted(i for i in sel if not a.id or i in a.id.split(","))
    # unaffected programs: symlink to the base (identical under both policies); the exits set
    # also gets one recorded-side store (its dumps come from two stores)
    recorded = SETS[a.set].get("recorded")
    if recorded:
        os.makedirs(recorded, exist_ok=True)
    for i in ids:
        if not sel[i]["affected"] and not os.path.lexists(f"{after}/{i}"):
            os.symlink(sel[i]["src"], f"{after}/{i}")
        if recorded and not os.path.lexists(f"{recorded}/{i}"):
            os.symlink(sel[i]["src"], f"{recorded}/{i}")
    ids = [i for i in ids if sel[i]["affected"]]
    ids.sort(key=lambda i: (sel[i]["dump_mb"] > 2000, i))   # big dumps last
    k, n = (int(x) for x in a.shard.split("/"))
    ids = [i for j, i in enumerate(ids) if j % n == k]
    det_dir = f"{OUT}/detail-{a.set}"
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
        det.update(set=a.set, pset=sel[_id]["pset"], dump_mb=sel[_id]["dump_mb"],
                   seconds=round(time.time() - t0, 1))
        if "error" in det:
            shutil.rmtree(f"{after}/{_id}.tmp", ignore_errors=True)
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


def _pct(a, b):
    return f"{100.0 * a / b:.1f} %" if b else "-"


def cmd_tables(a):
    import make_tables as mt
    allsel = json.load(open(SELECTION))["programs"]
    mans = {w: {r["id"]: r for r in csv.DictReader(open(SETS[w]["manifest"], newline=""))} for w in SETS}
    L = ["# T16 re-score: the certain clock on the kept stores\n",
         f"Generated {time.strftime('%Y-%m-%d %H:%M')} by `eval/baselines/t16_rescore.py tables` from "
         f"the program details and the `parallel.py analyze` CSVs under `{os.path.relpath(OUT, APH)}/`.\n"]
    for which in SETS:
        sel = allsel[which]
        dets = {os.path.basename(p)[:-5]: json.load(open(p))
                for p in glob.glob(f"{OUT}/detail-{which}/*.json")}
        ids = sorted(sel)
        aff = [i for i in ids if sel[i]["affected"]]
        done = [i for i in aff if i in dets and "error" not in dets[i]]
        errs = {i: dets[i]["error"] for i in aff if i in dets and "error" in dets[i]}
        L.append(f"\n## Set `{which}`: {len(ids)} programs, {len(aff)} with an RMW pc, "
                 f"{len(done)} re-scored, {len(errs)} failed, {len(aff) - len(done) - len(errs)} pending\n")
        if errs:
            L.append("Failed: " + ", ".join(f"`{i}` ({e})" for i, e in sorted(errs.items())) + "\n")
        # parity + invariant
        par_bad, inv_bad, kern, kern_ex = [], [], 0, 0
        chain = defaultdict(lambda: Counter())
        added = defaultdict(lambda: Counter())
        moved = []
        for i in done:
            d = dets[i]
            for k in d["kernels"]:
                if "skip" in k:
                    continue
                kern += 1
                kern_ex += bool(k.get("exits"))
                if not k["stored_eq_recorded"]:
                    par_bad.append((i, k["file"]))
                if not k["superset"]:
                    inv_bad.append((i, k["file"]))
                ps = d["pset"]
                for key, v in k["cer_chain"].items():
                    chain[ps][key] += v
                chain[ps]["kernels"] += 1
                rp = {tuple(p): c for p, c in k["rec_pairs"]}
                cp = {tuple(p): c for p, c in k["cer_pairs"]}
                for p, c in cp.items():
                    for cls, (n, f) in c.items():
                        n0, f0 = rp.get(p, {}).get(cls, [0, 0])
                        if n > n0:
                            added[ps]["instances"] += n - n0
                            added[ps]["flagged"] += f - f0
                            added[ps][f"pairs_{cls}"] += p not in rp or cls not in rp[p]
                            if p not in rp or cls not in rp[p]:
                                moved.append((i, k["file"], p, cls, n - n0, f - f0))
        L.append(f"- Kernels re-scored: {kern} ({kern_ex} with exit records).")
        L.append(f"- **Parity of the default policy**: oracle(recorded) == the stored hb_races on "
                 f"{kern - len(par_bad)} of {kern} kernels" + (f"; differs on: " + ", ".join(
                     f"`{i}`/{f}" for i, f in par_bad[:20]) + (" ..." if len(par_bad) > 20 else "")
                     if par_bad else " (**proved-in-effect**)."))
        L.append(f"- **Invariant Rep_certain >= Rep_recorded**: holds on {kern - len(inv_bad)} of {kern} "
                 f"kernels" + (f"; **VIOLATED** on: " + ", ".join(f"`{i}`/{f}" for i, f in inv_bad[:20])
                               if inv_bad else " (**proved-in-effect**)."))
        L.append("\n### Chain edges per suite (vector-clock dumps; the certain policy's counters)\n")
        L.append("Chain edges = morally strong successor pairs r -> q on one location (the edges the "
                 "recorded clock takes). `uncertain` = r's window still open at q (refused by the certain "
                 "clock); `cross-warp` = the uncertain edges between RMWs of different warps, the quantity "
                 "`eval/A2_WINDOWS.md` reports as 12.6 M of 29.9 M successor edges (42 %) over the evcand "
                 "dumps (the lanes of one warp instruction always overlap); `open-ended` = the releaser's "
                 "window never closed before the kernel's end (on a dump without exit records every "
                 "thread's last RMW); `unsafe` = disjoint windows but a possible coherence intermediate "
                 "not morally strong with the edge (refused as well).\n")
        L.append("| pset | kernels | chain edges | uncertain (windows overlap) | % | cross-warp | % | "
                 "open-ended | unsafe | refused | refused % |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|")
        tot = Counter()
        for ps in sorted(chain):
            c = chain[ps]
            tot.update(c)
            L.append(f"| {ps} | {c['kernels']} | {c['edges']:,} | {c['uncertain']:,} | "
                     f"{_pct(c['uncertain'], c['edges'])} | {c['xwarp']:,} | {_pct(c['xwarp'], c['edges'])} | "
                     f"{c['open']:,} | {c['unsafe']:,} | {c['refused']:,} | {_pct(c['refused'], c['edges'])} |")
        c = tot
        L.append(f"| **all** | {c['kernels']} | {c['edges']:,} | {c['uncertain']:,} | "
                 f"{_pct(c['uncertain'], c['edges'])} | {c['xwarp']:,} | {_pct(c['xwarp'], c['edges'])} | "
                 f"{c['open']:,} | {c['unsafe']:,} | {c['refused']:,} | {_pct(c['refused'], c['edges'])} |")
        L.append("\n### Reports the certain clock adds (pc pairs / instances beyond the recorded clock)\n")
        L.append("| pset | new DR pc pairs | new SC pc pairs | added instances | of which a2_uncertain |")
        L.append("|---|---|---|---|---|")
        for ps in sorted(added):
            c = added[ps]
            L.append(f"| {ps} | {c['pairs_DR']} | {c['pairs_SC']} | {c['instances']:,} | "
                     f"{c['flagged']:,} ({_pct(c['flagged'], c['instances'])}) |")
        # verdicts
        man = mans[which]
        runs = {w: _load_csv(f"{OUT}/{which}-{w}/*.csv") for w in POLICIES}
        if all(runs.values()):
            L.append(f"\n### Verdicts: recorded -> certain (`parallel.py analyze`, this checkout)\n")
            L.append("Race alone under `certain` is the **Race (sound)** column; FP / TP as "
                     "programs over the labelled ones (ERROR/TIMEOUT excluded).\n")
            L.append("| pset | mode | R u L FP / TP (recorded) | R u L FP / TP (certain) | "
                     "Race alone FP / TP (recorded) | **Race (sound)** FP / TP | labelled CLEAN / RACE |")
            L.append("|---|---|---|---|---|---|---|")
            agg = defaultdict(Counter)
            diff = []
            for (i, m), r in sorted(runs["recorded"].items()):
                if i not in sel:
                    continue
                c = runs["certain"].get((i, m))
                lab = man.get(i, {}).get("label", "")
                if c is None or lab not in ("RACE", "CLEAN"):
                    continue
                if r["verdict"] in ("ERROR", "TIMEOUT") or c["verdict"] in ("ERROR", "TIMEOUT"):
                    continue
                ps = sel[i]["pset"]
                k = agg[(ps, m)]
                k["lab_" + lab] += 1
                ra_r, ra_c = mt.race_alone_verdict(r), mt.race_alone_verdict(c)
                for tag, v in (("rl_rec", r["verdict"]), ("rl_cer", c["verdict"]),
                               ("ra_rec", ra_r), ("ra_cer", ra_c)):
                    if v == "RACE":
                        k[tag + ("_tp" if lab == "RACE" else "_fp")] += 1
                if r["verdict"] != c["verdict"] or ra_r != ra_c:
                    diff.append((ps, m, i, lab, r["verdict"], c["verdict"], ra_r, ra_c,
                                 mt.report_classes(r) or {}, mt.report_classes(c) or {}))
            for (ps, m), k in sorted(agg.items()):
                L.append(f"| {ps} | {hb_modes.SHORT.get(m, m)} | {k['rl_rec_fp']} / {k['rl_rec_tp']} | "
                         f"{k['rl_cer_fp']} / {k['rl_cer_tp']} | {k['ra_rec_fp']} / {k['ra_rec_tp']} | "
                         f"**{k['ra_cer_fp']} / {k['ra_cer_tp']}** | {k['lab_CLEAN']} / {k['lab_RACE']} |")
            L.append(f"\n### Programs whose verdict differs between the policies ({len(diff)})\n")
            L.append("| pset | mode | program | label | R u L | Race alone | classes recorded | classes certain |")
            L.append("|---|---|---|---|---|---|---|---|")
            fmt = lambda c: " ".join(f"{k}={v}" for k, v in sorted(c.items()) if v) or "-"
            for ps, m, i, lab, vr, vcer, rr, rc, cr, cc in diff:
                L.append(f"| {ps} | {hb_modes.SHORT.get(m, m)} | `{i}` | {lab} | {vr} -> {vcer} | "
                         f"{rr} -> {rc} | {fmt(cr)} | {fmt(cc)} |")
        else:
            L.append("\n_Verdict CSVs not present yet for both policies "
                     f"(`{OUT}/{which}-recorded`, `{OUT}/{which}-certain`)._")
        L.append(f"\n### New pc pairs under certain, by program ({len(moved)})\n")
        L.append("| program | kernel | pc pair | class | instances | a2_uncertain |")
        L.append("|---|---|---|---|---|---|")
        for i, f, p, cls, n, fl in moved[:400]:
            L.append(f"| `{i}` | {f} | {hex(p[0]) if p[0] is not None else '-'} / {hex(p[1])} | {cls} | {n} | {fl} |")
        if len(moved) > 400:
            L.append(f"\n_... {len(moved) - 400} more in the detail JSONs._")
    out = f"{OUT}/T16_RESCORE_TABLES.md"
    open(out, "w").write("\n".join(L) + "\n")
    print(f"wrote {out}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare")
    o = sub.add_parser("oracle")
    o.add_argument("--set", choices=list(SETS), default="main")
    o.add_argument("--shard", default="0/1")
    o.add_argument("--id", default="")
    o.add_argument("--timeout", type=int, default=14400)
    o.add_argument("--mem-gb", type=float, default=110)
    o.add_argument("--force", action="store_true")
    sub.add_parser("tables")
    a = ap.parse_args(argv)
    {"prepare": cmd_prepare, "oracle": cmd_oracle, "tables": cmd_tables}[a.cmd](a)


if __name__ == "__main__":
    main()

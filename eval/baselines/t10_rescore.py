#!/usr/bin/env python3
"""T10 (CLAUDE.md section C, step 3): re-score the kept stores with the strength column, no GPU.

The base is T9's re-scored store `t9-after` (the evcand + full-2026-09-22 selection of
eval/results/t9-rescore/selection.json): its vector-clock dumps carry the `hb_races` /
`hb_races_sync_only` the installed engine writes (the T9 oracle under the pre-T10 default
policy `generic`), so T9's AFTER rows (eval/results/t9-rescore/after/) are the BEFORE of T10.
The strength policy enters the oracle and sync_dominance only through the per-pc table
sd.coherent_scope(op, policy); a program whose opcodes give the same table under `generic`
and `token` therefore re-scores identically by construction.

  prepare  per program: the pcs whose strength/scope differ between `generic` and `token`
           (every kernel of every dot, pydot-parsed as the oracle parses them) -> selection
           with an `affected` flag; the AFTER store t10-after: an unaffected program is a
           symlink to its t9-after dir, an affected one is re-scored by `oracle`.
  oracle   --shard k/n: every affected program's vector-clock dumps through hb_oracle.py under
           `token` -> t10-after/<id>/vector-clock/ (everything else symlinked to t9-after) and a
           detail JSON per program (old and new pc pairs with their classes).
  tables   the race-set deltas (details) and the verdict deltas (BEFORE = T9's AFTER rows,
           AFTER = `parallel.py analyze` of t10-after with this checkout), labels from T9's
           manifest; programs, operating points (Race u Latent, Race alone) and the SC column.

    .env/bin/python eval/baselines/t10_rescore.py prepare          (a normal node)
    sbatch --array=0-7 eval/baselines/setup/p_t10_rescore.sh       (oracle shards)
    sbatch --array=0-31 eval/baselines/setup/p_t10_analyze.sh      (AFTER analysis)
    .env/bin/python eval/baselines/t10_rescore.py tables           (login node)
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
BASE = f"{BEEGFS}/t9-after"
AFTER = f"{BEEGFS}/t10-after"
T9 = f"{APH}/eval/results/t9-rescore"
OUT = f"{APH}/eval/results/t10-rescore"
MANIFEST = f"{T9}/manifest.t9.csv"
SELECTION = f"{OUT}/selection.json"
POLICIES = ("generic", "token")


# ---------------------------------------------------------------- prepare

def strength_diff(dots):
    """[(dot, kernel, pc, opcode, generic scope, token scope)] for every memory pc of every
    kernel whose strong scope differs between the two policies (None = weak)."""
    import sync_dominance as sd
    out = []
    for dot in dots:
        try:
            kernels = sd.parse_dot(dot)
        except sd.AlignmentError:
            continue
        for mangled, (blocks, _, _) in kernels.items():
            for ins in blocks.values():
                for pc, op in ins:
                    if sd.classify(op) != "mem":
                        continue
                    g, t = (sd.coherent_scope(op, p) for p in POLICIES)
                    if g != t:
                        out.append((os.path.basename(dot), mangled, pc, op, g, t))
    return out


def cmd_prepare(a):
    t9 = json.load(open(f"{T9}/selection.json"))["programs"]
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(AFTER, exist_ok=True)
    sel, t0 = {}, time.time()
    for n, (_id, s) in enumerate(sorted(t9.items()), 1):
        src = f"{BASE}/{_id}"
        rec = {"pset": s["pset"], "modes": s["modes"], "dump_mb": s["dump_mb"], "src": src}
        if not os.path.isdir(src):
            rec["skip"] = "no-t9-after-dir"    # T9's oracle did not finish (4 P1 1296n)
            sel[_id] = rec
            continue
        diff = strength_diff(sorted(glob.glob(f"{src}/dots/*.dot")))
        rec["affected"] = bool(diff)
        rec["diff_pcs"] = len(diff)
        rec["diff_ops"] = dict(Counter(op for *_, op, _g, _t in diff))
        dst = f"{AFTER}/{_id}"
        if not diff and not os.path.lexists(dst):
            os.symlink(src, dst)
        sel[_id] = rec
        if n % 50 == 0:
            print(f"[{n}/{len(t9)}] {time.time() - t0:.0f}s", flush=True)
    json.dump({"base": BASE, "after": AFTER, "policies": POLICIES, "programs": sel},
              open(SELECTION, "w"), indent=1)
    aff = sorted(i for i, r in sel.items() if r.get("affected"))
    print(f"{len(sel)} programs, {len(aff)} affected ({Counter(sel[i]['pset'] for i in aff)}), "
          f"{sum('skip' in r for r in sel.values())} skipped -> {SELECTION}")


# ---------------------------------------------------------------- oracle

def _pairs(races):
    """hb_races -> {(pc_lo, pc_hi): {class: records}}"""
    out = defaultdict(Counter)
    for r in races or ():
        a, b = r.get("a_pc"), r["b_pc"]
        k = (min(a, b), max(a, b)) if a is not None else (None, b)
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
                        rep = hb_oracle.analyze(dot, path, strong_ldst="token")
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
                     sync_old=len(so_old), sync_new=len(so_new),
                     sync_only_old=sorted(so_old - so_new), sync_only_new=sorted(so_new - so_old),
                     seconds=round(time.time() - t0, 2))
            trace["hb_races"] = rep["races"]
            if trace.get("hb_races_sync_only") is not None:
                trace["hb_races_sync_only"] = rep["races_sync_only"]
            trace["t10_rescore"] = {"from": path, "oracle": "hb_oracle.py (T10, token)"}
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


def cmd_tables(a):
    import make_tables as mt
    man = {r["id"]: r for r in csv.DictReader(open(MANIFEST, newline=""))}
    sel = json.load(open(SELECTION))["programs"]
    dets = {os.path.basename(p)[:-5]: json.load(open(p))
            for p in glob.glob(f"{OUT}/detail/*.json")}
    L = []
    aff = sorted(i for i, r in sel.items() if r.get("affected"))
    ops = Counter()
    for i in aff:
        ops.update(sel[i]["diff_ops"])
    L.append("## Programs whose strength table differs between `generic` and `token`\n")
    L.append(f"{len(aff)} of {len(sel)} selected programs "
             f"({', '.join(f'{p}: {n}' for p, n in sorted(Counter(sel[i]['pset'] for i in aff).items()))}); "
             f"skipped (no t9-after dir): {sum('skip' in r for r in sel.values())}. The opcodes "
             f"whose strength changes, with their pc count over those programs' dots: "
             + ", ".join(f"`{o}` {n}" for o, n in ops.most_common()) + ".\n")
    # --- race-set deltas (affected programs' vector-clock dumps)
    L.append("## Race-set deltas (vector-clock dumps, pc pairs: T9 oracle under `generic` vs "
             "T10 oracle under `token`)\n")
    L.append("| pset | program | pairs | DR before | DR after | SC before | SC after | DR -> SC | "
             "SC -> DR | lost | gained | sync pairs +/- |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    tot = Counter()
    for _id in aff:
        d = dets.get(_id)
        if d is None or "error" in d:
            L.append(f"| {sel[_id]['pset']} | {_id} | {d and d.get('error') or 'no vector-clock dump'} "
                     "| | | | | | | | | |")
            continue
        ks = [k for k in d["kernels"] if "old_pairs" in k]
        if not ks:
            L.append(f"| {sel[_id]['pset']} | {_id} | no vector-clock dump | | | | | | | | | |")
            continue
        cl = lambda side, c: {(k["file"], tuple(p)) for k in ks for p, cc in k[side] if cc.get(c)}
        odr, osc, ndr, nsc = cl("old_pairs", "DR"), cl("old_pairs", "SC"), cl("new_pairs", "DR"), \
            cl("new_pairs", "SC")
        allp = odr | osc | ndr | nsc
        row = Counter(pairs=len(allp), dr_b=len(odr), dr_a=len(ndr), sc_b=len(osc - odr),
                      sc_a=len(nsc - ndr), dr_sc=len(odr - ndr & nsc), sc_dr=len((osc - odr) & ndr),
                      lost=len((odr | osc) - (ndr | nsc)), gained=len((ndr | nsc) - (odr | osc)),
                      sp=sum(len(k["sync_only_new"]) for k in ks),
                      sm=sum(len(k["sync_only_old"]) for k in ks))
        tot.update(row)
        L.append(f"| {sel[_id]['pset']} | {_id} | {row['pairs']} | {row['dr_b']} | {row['dr_a']} | "
                 f"{row['sc_b']} | {row['sc_a']} | {row['dr_sc']} | {row['sc_dr']} | {row['lost']} | "
                 f"{row['gained']} | +{row['sp']}/-{row['sm']} |")
    L.append(f"| **all** | | {tot['pairs']} | {tot['dr_b']} | {tot['dr_a']} | {tot['sc_b']} | "
             f"{tot['sc_a']} | {tot['dr_sc']} | {tot['sc_dr']} | {tot['lost']} | {tot['gained']} | "
             f"+{tot['sp']}/-{tot['sm']} |")
    # --- verdict deltas
    before, after = _load_csv(a.before), _load_csv(a.after)
    skip = {i for i, r in sel.items() if "skip" in r} | set(a.exclude.split(",") if a.exclude else ())
    L.append("\n## Verdict deltas (BEFORE = T9's AFTER rows: the pre-T10 detector on t9-after; "
             "AFTER = this checkout on t10-after)\n")
    L.append(f"Left out: {', '.join(sorted(skip)) or 'none'}.\n")
    moves, rows = Counter(), []
    ra = lambda r: mt.race_alone_verdict({"verdict": r.get("verdict", "-"),
                                          "notes": r.get("notes", "")}) if r else "-"
    for key in sorted(set(before) | set(after)):
        if key[0] in skip:
            continue
        b, f = before.get(key) or {}, after.get(key) or {}
        vb, vf = b.get("verdict", "-"), f.get("verdict", "-")
        lab = man.get(key[0], {}).get("label", "")
        cb, cf = (mt.report_classes(b) or {}) if b else {}, (mt.report_classes(f) or {}) if f else {}
        moves[(key[1], vb, vf)] += 1
        if vb != vf or b.get("report_ids") != f.get("report_ids") or cb != cf:
            rows.append(dict(mode=key[1], id=key[0], label=lab, vb=vb, vf=vf, rab=ra(b), raf=ra(f),
                             nb=len((b.get("report_ids") or "").split()),
                             nf=len((f.get("report_ids") or "").split()), cb=cb, cf=cf,
                             aff=bool(sel.get(key[0], {}).get("affected"))))
    L.append("| mode | before | after | programs |")
    L.append("|---|---|---|---|")
    for (m, vb, vf), n in sorted(moves.items()):
        L.append(f"| {m} | {vb} | {vf} | {n} |")
    # --- per pset and mode: the two operating points and the SC column, before -> after
    L.append("\n### Per suite (labelled programs; TP / FN / FP / TN at Race u Latent and at Race "
             "alone; `sc` = programs with at least one SC report, informational, D2)\n")
    L.append("| pset | mode | programs | Race u Latent TP/FN/FP/TN | Race alone TP/FN/FP/TN | "
             "sc programs (labelled RACE / CLEAN) |")
    L.append("|---|---|---|---|---|---|")
    agg = defaultdict(lambda: {s: Counter() for s in ("b", "a")})
    for key in set(before) | set(after):
        if key[0] in skip or key[1] not in (VC, SCM):
            continue
        lab = man.get(key[0], {}).get("label", "")
        if lab not in ("RACE", "CLEAN"):
            continue
        ps = man.get(key[0], {}).get("pset", "?")
        for s, src in (("b", before), ("a", after)):
            r = src.get(key)
            if r is None:
                continue
            c = agg[(ps, key[1])][s]
            c["n"] += 1
            for op, v in (("rl", r.get("verdict")), ("ra", ra(r))):
                if v not in ("RACE", "CLEAN"):
                    c[f"{op}_other"] += 1
                    continue
                c[op + {("RACE", "RACE"): "_tp", ("RACE", "CLEAN"): "_fn",
                        ("CLEAN", "RACE"): "_fp", ("CLEAN", "CLEAN"): "_tn"}[(lab, v)]] += 1
            cls = mt.report_classes(r) or {}
            if cls.get("sc") or cls.get("latent-sc"):
                c["sc_" + lab] += 1
    q = lambda c, op: "/".join(str(c[f"{op}_{x}"]) for x in ("tp", "fn", "fp", "tn"))
    for (ps, m), c in sorted(agg.items()):
        b, f = c["b"], c["a"]
        L.append(f"| {ps} | {m} | {b['n']} -> {f['n']} | {q(b, 'rl')} -> {q(f, 'rl')} | "
                 f"{q(b, 'ra')} -> {q(f, 'ra')} | {b['sc_RACE']}/{b['sc_CLEAN']} -> "
                 f"{f['sc_RACE']}/{f['sc_CLEAN']} |")
    missing = [r for r in rows if "-" in (r["vb"], r["vf"])]
    L.append(f"\nRows present on one side only (not compared below): {len(missing)}"
             + (" -- " + ", ".join(f"{r['id']} ({r['mode']}: {r['vb']} -> {r['vf']})"
                                  for r in missing) if missing else "") + ".\n")
    both = [r for r in rows if "-" not in (r["vb"], r["vf"])]
    for op_name, get_b, get_a in (("Race u Latent (the harness verdict)", "vb", "vf"),
                                  ("Race alone", "rab", "raf")):
        tp_gain = [r for r in both if r["label"] == "RACE" and r[get_b] != "RACE" and r[get_a] == "RACE"]
        tp_lost = [r for r in both if r["label"] == "RACE" and r[get_b] == "RACE" and r[get_a] != "RACE"]
        fp_new = [r for r in both if r["label"] == "CLEAN" and r[get_b] != "RACE" and r[get_a] == "RACE"]
        fp_gone = [r for r in both if r["label"] == "CLEAN" and r[get_b] == "RACE" and r[get_a] != "RACE"]
        L.append(f"\n### {op_name}: TPs gained {len(tp_gain)}, TPs lost {len(tp_lost)}, new FPs "
                 f"{len(fp_new)}, FPs removed {len(fp_gone)}\n")
        for title, rs in (("TPs lost", tp_lost), ("FPs removed", fp_gone), ("TPs gained", tp_gain),
                          ("New FPs", fp_new)):
            if rs:
                L.append(f"{title}: " + ", ".join(f"{r['id']} ({r['mode']})" for r in rs) + "\n")
    L.append("\nEvery (program, mode) whose verdict, report set or class counts moved "
             "(classes from the harness's `classes=` note, before -> after):\n")
    L.append("| mode | program | label | verdict | Race alone | #report ids | classes before | "
             "classes after | strength table differs |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    fmt = lambda c: " ".join(f"{k}={v}" for k, v in sorted(c.items())) or "-"
    for r in both:
        L.append(f"| {r['mode']} | {r['id']} | {r['label']} | {r['vb']} -> {r['vf']} | "
                 f"{r['rab']} -> {r['raf']} | {r['nb']} -> {r['nf']} | {fmt(r['cb'])} | "
                 f"{fmt(r['cf'])} | {'yes' if r['aff'] else 'NO'} |")
    unaffected_moved = [r for r in both if not r["aff"]]
    L.append(f"\nRows that moved on a program whose strength table does not differ: "
             f"{len(unaffected_moved)}" + (" -- " + ", ".join(f"{r['id']} ({r['mode']})"
                                                             for r in unaffected_moved)
                                          if unaffected_moved else "") + ".\n")
    text = "\n".join(L) + "\n"
    open(f"{OUT}/T10_RESCORE_TABLES.md", "w").write(text)
    print(text)


def cmd_check_before(a):
    """T9's AFTER rows vs the f127790 detector's rows (p_t10_before.sh) on the same t9-after
    dumps, for the ids the latter ran: verdict, report ids and class counts per (id, mode)."""
    import make_tables as mt

    def rows(pattern):                 # (id, mode, rep) -> row, no collapsing of reps
        out = {}
        for p in sorted(glob.glob(pattern)):
            for r in csv.DictReader(open(p, newline="")):
                out[(r["id"], hb_modes.canon(r.get("mode", ""), p), r.get("rep", ""))] = r
        return out
    t9, cur = rows(a.before), rows(a.current)
    keys = sorted(k for k in cur if k[1] in (VC, SCM))
    diff = []
    for k in keys:
        b, c = t9.get(k), cur[k]
        if b is None:
            diff.append((k, "missing in T9's rows"))
            continue
        for col in ("verdict", "report_ids"):
            if (b.get(col) or "") != (c.get(col) or ""):
                diff.append((k, f"{col}: {b.get(col)} -> {c.get(col)}"))
        if (mt.report_classes(b) or {}) != (mt.report_classes(c) or {}):
            diff.append((k, f"classes: {mt.report_classes(b)} -> {mt.report_classes(c)}"))
    for k, d in diff:
        print(f"DIFF {k[0]} {k[1]}: {d}")
    print(f"{len(keys)} (id, mode, rep) rows of the f127790 detector on t9-after; {len(diff)} differ "
          f"from T9's AFTER rows")


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare")
    o = sub.add_parser("oracle")
    o.add_argument("--shard", default="0/1")
    o.add_argument("--timeout", type=int, default=14400)
    o.add_argument("--mem-gb", type=float, default=170)
    o.add_argument("--id", default="")
    o.add_argument("--force", action="store_true")
    t = sub.add_parser("tables")
    t.add_argument("--before", default=f"{T9}/after/baselines-cuvein-shard*.csv")
    t.add_argument("--after", default=f"{OUT}/after/baselines-cuvein-shard*.csv")
    t.add_argument("--exclude", default="", help="ids left out of the verdict comparison")
    c = sub.add_parser("check-before")
    c.add_argument("--before", default=f"{T9}/after/baselines-cuvein-shard*.csv")
    c.add_argument("--current", default=f"{OUT}/before-affected/baselines-cuvein-shard*.csv")
    a = ap.parse_args()
    {"prepare": cmd_prepare, "oracle": cmd_oracle, "tables": cmd_tables,
     "check-before": cmd_check_before}[a.cmd](a)


if __name__ == "__main__":
    main()

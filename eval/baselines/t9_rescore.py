#!/usr/bin/env python3
"""T9 (CLAUDE.md section C, step 6): re-score the kept BeeGFS stores with the T9 detector,
no GPU. The vector-clock dumps were recorded by the pre-T9 engine: their `hb_races` /
`hb_races_sync_only` are the old engine's (= the old oracle's, the parity invariant). The
new engine would have written what the new hb_oracle.py computes on the same trace (the
T9 parity invariant), so the re-score replaces those two keys with the new oracle's output
and re-runs the verdict layer; scalar-clock dumps need no replay (the offline pass is
recomputed by the new sync_dominance.analyze).

  prepare  select the programs (latent_census.select_sources over its DEFAULT_STORES: the
           later store wins, per program the store of its vector-clock dump), build the
           BEFORE store (per program: meta.json + symlinks to dots/ and the mode dirs) and a
           manifest (manifest.csv + the evcand / pre-PI manifests for dropped ids) for
           `parallel.py analyze`.
  oracle   --shard k/n: per program, in a child under a wall-clock and address-space cap:
           the new hb_oracle over every vector-clock kernel dump -> the AFTER store (the
           rewritten dumps; everything else symlinked) and a detail JSON with, per kernel,
           the old (recorded) and new race sets at pc-pair level with their DR/SC class,
           the second clock's pairs before/after, events and time. A TV violation is
           re-run with YOSEMITE_HB_STRICT=0, as the engine records and continues.
  tables   the race-set deltas (from the details) and the verdict deltas (the BEFORE and
           AFTER `parallel.py analyze` CSVs), labels from the same manifest.

    .env/bin/python eval/baselines/t9_rescore.py prepare            (a normal node)
    sbatch --array=0-15 eval/baselines/setup/p_t9_rescore.sh        (oracle shards)
    ... parallel.py analyze BEFORE with the 1a3aea5 code, AFTER with this checkout's ...
    .env/bin/python eval/baselines/t9_rescore.py tables             (login node)
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
import latent_census as lc  # noqa: E402

VC, SC = hb_modes.VECTOR_CLOCK, hb_modes.SCALAR_CLOCK
BEEGFS = lc.BEEGFS
BEFORE = f"{BEEGFS}/t9-before"
AFTER = f"{BEEGFS}/t9-after"
OUT = f"{APH}/eval/results/t9-rescore"
MANIFEST = f"{OUT}/manifest.t9.csv"
SELECTION = f"{OUT}/selection.json"


# ---------------------------------------------------------------- prepare

def cmd_prepare(a):
    src, why = lc.select_sources(lc.DEFAULT_STORES)
    per = {}                                   # id -> pdir: the vector-clock dump's store wins
    for (_id, mode), s in sorted(src.items()):
        if mode == VC or _id not in per:
            per[_id] = s["pdir"]
    os.makedirs(OUT, exist_ok=True)
    for root in (BEFORE, AFTER):
        os.makedirs(root, exist_ok=True)
    for _id, pdir in per.items():
        d = f"{BEFORE}/{_id}"
        if not os.path.exists(d):
            os.symlink(pdir, d)
    sel = {_id: {"pdir": pdir, "modes": [m for m in (VC, SC) if (_id, m) in src],
                 "dump_mb": max(src[(_id, m)]["dump_mb"] for m in (VC, SC) if (_id, m) in src),
                 "pset": next(src[(_id, m)]["pset"] for m in (VC, SC) if (_id, m) in src)}
           for _id, pdir in per.items()}
    json.dump({"stores": lc.DEFAULT_STORES, "programs": sel,
               "not_selected": {f"{i}|{m}": w for (i, m), w in why.items()}},
              open(SELECTION, "w"), indent=1)
    # manifest: current rows, then the older manifests for ids the current one dropped
    rows, cols = {}, None
    for p in (f"{HERE}/manifest.csv", f"{HERE}/setup/manifest.evcand.csv",
              f"{HERE}/manifest.pre-PI.csv"):
        with open(p, newline="") as f:
            rd = csv.DictReader(f)
            cols = cols or rd.fieldnames
            for r in rd:
                if r["id"] in per and r["id"] not in rows:
                    rows[r["id"]] = {c: r.get(c, "") for c in cols}
    with open(MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for _id in sorted(rows):
            w.writerow(rows[_id])
    print(f"{len(per)} programs ({sum(VC in s['modes'] for s in sel.values())} with a "
          f"vector-clock dump), {len(rows)} in the manifest -> {SELECTION}, {MANIFEST}")


# ---------------------------------------------------------------- oracle

def _pairs(races):
    """hb_races -> {(pc_lo, pc_hi): {class: records}}"""
    out = defaultdict(Counter)
    for r in races or ():
        a, b = r.get("a_pc"), r["b_pc"]
        k = (min(a, b), max(a, b)) if a is not None else (None, b)
        out[k][r.get("class", "DR")] += 1
    return out


def _rescore_program(_id, info):
    import hb_oracle
    import sync_dominance as sd
    pdir = info["pdir"]
    dst = f"{AFTER}/{_id}"
    tmp = dst + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    for name in os.listdir(pdir):
        if name != VC:
            os.symlink(f"{pdir}/{name}", f"{tmp}/{name}")
    det = {"id": _id, "pset": info["pset"], "pdir": pdir, "kernels": []}
    if VC in info["modes"]:
        vdir = hb_modes.resolve_dir(pdir, VC)
        os.makedirs(f"{tmp}/{VC}")
        dots = sorted(glob.glob(f"{pdir}/dots/*.dot"))
        for name in sorted(os.listdir(vdir)):
            src = f"{vdir}/{name}"
            if not (name.startswith("kernel_") and name.endswith(".json")):
                os.symlink(src, f"{tmp}/{VC}/{name}")
                continue
            t0 = time.time()
            trace = json.load(open(src))
            k = {"file": name, "events": len(trace.get("hb_events") or ())}
            if not trace.get("hb_events"):
                k["skip"] = "no-hb_events"
                os.symlink(src, f"{tmp}/{VC}/{name}")
                det["kernels"].append(k)
                continue
            rep = err = None
            for strict in ("1", "0"):
                os.environ["YOSEMITE_HB_STRICT"] = strict
                for dot in dots:
                    try:
                        rep = hb_oracle.analyze(dot, src)
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
                os.symlink(src, f"{tmp}/{VC}/{name}")
                det["kernels"].append(k)
                continue
            old, new = _pairs(trace.get("hb_races")), _pairs(rep["races"])
            so_old = {(a, b) for a, b, _ in trace.get("hb_races_sync_only") or ()}
            so_new = {(a, b) for a, b, _ in rep["races_sync_only"]}
            k.update(kernel=trace["kernel"]["kernel_name"],
                     old_records=len(trace.get("hb_races") or ()),
                     new_records=len(rep["races"]),
                     old_pairs=sorted([list(p), dict(c)] for p, c in old.items()),
                     new_pairs=sorted([list(p), dict(c)] for p, c in new.items()),
                     sync_old=len(so_old), sync_new=len(so_new),
                     sync_only_old=sorted(so_old - so_new), sync_only_new=sorted(so_new - so_old),
                     had_sync=trace.get("hb_races_sync_only") is not None,
                     local_events=sum(e.get("space") == "local" for e in trace["hb_events"]),
                     seconds=round(time.time() - t0, 2))
            trace["hb_races"] = rep["races"]
            if trace.get("hb_races_sync_only") is not None:
                trace["hb_races_sync_only"] = rep["races_sync_only"]
            trace["t9_rescore"] = {"from": src, "oracle": "hb_oracle.py (T9)"}
            with open(f"{tmp}/{VC}/{name}", "w") as f:
                json.dump(trace, f)
            det["kernels"].append(k)
            del trace, rep
    shutil.rmtree(dst, ignore_errors=True)
    os.rename(tmp, dst)
    return det


def cmd_oracle(a):
    sel = json.load(open(SELECTION))["programs"]
    ids = sorted(i for i, s in sel.items()
                 if a.min_mb <= s["dump_mb"] < a.max_mb and (not a.id or i in a.id.split(",")))
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
        if "error" in det:                     # no re-scored vector-clock dump: none in AFTER
            shutil.rmtree(f"{AFTER}/{_id}.tmp", ignore_errors=True)
        json.dump(det, open(out, "w"))
        print(f"   -> {det.get('error', 'ok')} {det['seconds']}s", flush=True)


# ---------------------------------------------------------------- tables
# (below this line: login node, no BeeGFS needed)

def _load_csv(path):
    runs = {}
    for p in sorted(glob.glob(path)):
        for r in csv.DictReader(open(p, newline="")):
            mode = hb_modes.canon(r.get("mode", ""), p)
            key = (r["id"], mode)
            prev = runs.get(key)
            # reps collapse as make_tables.load_runs does: RACE > CLEAN > TIMEOUT > ERROR
            order = {"RACE": 3, "CLEAN": 2, "TIMEOUT": 1, "ERROR": 0}
            if prev is None or order.get(r["verdict"], 0) > order.get(prev["verdict"], 0):
                runs[key] = r
    return runs


def cmd_tables(a):
    sys.path.insert(0, HERE)
    import make_tables as mt
    man = {r["id"]: r for r in csv.DictReader(open(MANIFEST, newline=""))}
    dets = {os.path.basename(p)[:-5]: json.load(open(p))
            for p in glob.glob(f"{OUT}/detail/*.json")}
    lines = []
    # --- race-set deltas (vector-clock dumps, pc-pair level)
    per_ps = defaultdict(Counter)
    prog_rows = []
    for _id, d in sorted(dets.items()):
        ps = d.get("pset")
        c = per_ps[ps]
        if "error" in d:
            c["error:" + d["error"].split("(")[0]] += 1
            continue
        ks = [k for k in d["kernels"] if "old_pairs" in k]
        if not ks:
            c["no-vc-dump"] += 1
            continue
        c["programs"] += 1
        old = {tuple(p) for k in ks for p, _ in k["old_pairs"]}
        new_dr = {tuple(p) for k in ks for p, cl in k["new_pairs"] if cl.get("DR")}
        new_sc = {tuple(p) for k in ks for p, cl in k["new_pairs"] if cl.get("SC") and not cl.get("DR")}
        gained, lost = new_dr - old, old - new_dr - new_sc
        s_new = sum(len(k["sync_only_new"]) for k in ks)
        s_lost = sum(len(k["sync_only_old"]) for k in ks)
        loc = sum(k.get("local_events", 0) for k in ks)
        tv = [k["tv"] for k in d["kernels"] if k.get("tv")]
        c["old_pairs"] += len(old)
        c["new_dr_pairs"] += len(new_dr)
        c["new_sc_pairs"] += len(new_sc)
        c["dr_gained"] += len(gained)
        c["lost"] += len(lost)
        c["sync_pairs_gained"] += s_new
        c["sync_pairs_lost"] += s_lost
        c["with_local_events"] += bool(loc)
        c["tv"] += bool(tv)
        c["old_records"] += sum(k["old_records"] for k in ks)
        c["new_records"] += sum(k["new_records"] for k in ks)
        if gained or lost or new_sc or s_new or s_lost:
            prog_rows.append((ps, _id, len(old), len(new_dr), len(new_sc), sorted(gained)[:4],
                              sorted(lost)[:4], s_new, s_lost))
    lines.append("## Race-set deltas (vector-clock dumps: recorded engine vs T9 oracle, pc pairs)\n")
    keys = ["programs", "old_pairs", "new_dr_pairs", "new_sc_pairs", "dr_gained", "lost",
            "sync_pairs_gained", "sync_pairs_lost", "old_records", "new_records",
            "with_local_events", "tv"]
    errs = sorted({k for c in per_ps.values() for k in c if k.startswith(("error:", "no-vc"))})
    lines.append("| pset | " + " | ".join(keys + errs) + " |")
    lines.append("|" + "---|" * (len(keys) + len(errs) + 1))
    tot = Counter()
    for ps in sorted(per_ps, key=str):
        tot.update(per_ps[ps])
        lines.append(f"| {ps} | " + " | ".join(str(per_ps[ps][k]) for k in keys + errs) + " |")
    lines.append("| **all** | " + " | ".join(str(tot[k]) for k in keys + errs) + " |")
    lines.append("\nPrograms whose pc-pair sets moved (old = recorded engine pairs; DR/SC = the "
                 "T9 oracle's classes; first four pairs shown):\n")
    lines.append("| pset | program | old | new DR | new SC-only | DR gained | lost | sync+ | sync- |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    hx = lambda ps: ", ".join(f"{p[0]:#x}/{p[1]:#x}" if p[0] is not None else f"-/{p[1]:#x}" for p in ps)
    for r in prog_rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {hx(r[5])} | {hx(r[6])} "
                     f"| {r[7]} | {r[8]} |")
    # --- verdict deltas
    before, after = _load_csv(a.before), _load_csv(a.after)
    lines.append("\n## Verdict deltas (parallel.py analyze: BEFORE = 1a3aea5 code on the "
                 "recorded dumps, AFTER = T9 code on the re-scored dumps)\n")
    moves = Counter()
    rows = []
    for key in sorted(set(before) | set(after)):
        b, f = before.get(key), after.get(key)
        vb, vf = (b or {}).get("verdict", "-"), (f or {}).get("verdict", "-")
        lab = man.get(key[0], {}).get("label", "")
        cb = mt.report_classes(f) if f else None
        ra = mt.race_alone_verdict({"verdict": vf, "notes": (f or {}).get("notes", "")}) \
            if f else None
        moves[(key[1], vb, vf)] += 1
        if vb != vf or (b or {}).get("report_ids") != (f or {}).get("report_ids"):
            ib = set(((b or {}).get("report_ids") or "").split())
            iff = set(((f or {}).get("report_ids") or "").split())
            rows.append((key[1], key[0], lab, vb, vf, ra, len(ib), len(iff),
                         sorted(iff - ib)[:3], sorted(ib - iff)[:3], cb))
    lines.append("| mode | before | after | programs |")
    lines.append("|---|---|---|---|")
    for (m, vb, vf), n in sorted(moves.items()):
        lines.append(f"| {m} | {vb} | {vf} | {n} |")
    tp_gain = [r for r in rows if r[2] == "RACE" and r[3] != "RACE" and r[4] == "RACE"]
    tp_lost = [r for r in rows if r[2] == "RACE" and r[3] == "RACE" and r[4] != "RACE"]
    fp_new = [r for r in rows if r[2] == "CLEAN" and r[3] != "RACE" and r[4] == "RACE"]
    fp_gone = [r for r in rows if r[2] == "CLEAN" and r[3] == "RACE" and r[4] != "RACE"]
    for title, rs in (("True positives gained", tp_gain), ("True positives lost", tp_lost),
                      ("New false positives", fp_new), ("False positives removed", fp_gone)):
        lines.append(f"\n**{title}: {len(rs)}**" + ("" if not rs else ":\n"))
        if rs:
            lines.append("| mode | program | label | before | after | Race alone | classes |")
            lines.append("|---|---|---|---|---|---|---|")
            for r in rs:
                lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[10]} |")
    lines.append("\nEvery program whose verdict or report set moved:\n")
    lines.append("| mode | program | label | before | after | Race alone | #ids b/a | ids added | ids removed | classes |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]}/{r[7]} "
                     f"| {' '.join(r[8])} | {' '.join(r[9])} | {r[10]} |")
    text = "\n".join(lines) + "\n"
    open(f"{OUT}/T9_RESCORE_TABLES.md", "w").write(text)
    print(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare")
    o = sub.add_parser("oracle")
    o.add_argument("--shard", default="0/1")
    o.add_argument("--min-mb", type=float, default=0)
    o.add_argument("--max-mb", type=float, default=float("inf"))
    o.add_argument("--timeout", type=int, default=3600)
    o.add_argument("--mem-gb", type=float, default=60)
    o.add_argument("--id", default="")
    o.add_argument("--force", action="store_true")
    t = sub.add_parser("tables")
    t.add_argument("--before", default=f"{OUT}/before/baselines-cuvein-shard*.csv")
    t.add_argument("--after", default=f"{OUT}/after/baselines-cuvein-shard*.csv")
    a = ap.parse_args()
    {"prepare": cmd_prepare, "oracle": cmd_oracle, "tables": cmd_tables}[a.cmd](a)


if __name__ == "__main__":
    main()

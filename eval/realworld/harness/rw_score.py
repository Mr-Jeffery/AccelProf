#!/usr/bin/env python3
"""T21b steps 3-5: score the attributed runs against the pre-registered oracles (bc71082) and write
eval/results/realworld_t21c/recall.csv, eval/results/realworld_t21c/recall_summary.json and eval/realworld/triage_queue.md.

  rw_score.py [--results eval/results/realworld_t21c] [--manifest eval/realworld/manifest_t21c.csv] [--write]

Per target x variant x mode (x component for DR+SC targets): buggy -> DETECTED | DETECTED-AS-<class> | MISSED(+cause m1-m4);
fixed -> CLEAN-FOR-PAIR | RESIDUAL-AS-EXPECTED | STILL-REPORTED. The matching rule is the brief's: the two pcs of a reported
pair attribute (inlined frames included) to the oracle's two sites, +-2 lines, either order. Oracles are read, never edited;
the hand-derived pair table is eval/realworld/recall_pairs.json. Facts only: a value that was not obtained is empty."""
import argparse, csv, fnmatch, glob, json, os, re, sys
from collections import defaultdict, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
MODES = ("vector-clock", "scalar-clock")
TOL = 2


def hits(frames, ranges, tol=TOL):
    for fr in frames or ():
        base = os.path.basename(fr["file"])
        for pat, l0, l1 in ranges:
            if fnmatch.fnmatch(base, pat) and l0 - tol <= fr["line"] <= l1 + tol:
                return True
    return False


def match(r, p):
    tol = p.get("tol", TOL)
    fa, fb = r.get("a_frames"), r.get("b_frames")
    return (hits(fa, p["A"], tol) and hits(fb, p["B"], tol)) or (hits(fb, p["A"], tol) and hits(fa, p["B"], tol))


def rclass(r):
    return "SC" if (r.get("verdict") == "SC" or r.get("conflict_class") == "SC") else "DR"


def fl(frames, n=2):
    return " <- ".join(f"{os.path.basename(f['file'])}:{f['line']}" for f in (frames or [])[:n]) or "(no line info)"


def strong(r):
    return any(".STRONG" in (r.get(k) or "") for k in ("a_op", "b_op"))


def rep_str(r):
    return (f"{r.get('kernel') or r.get('mangled')[:60]} | pcs {hex(r['a_pc'])}/{hex(r['b_pc'])} | {r['space']} {r.get('race_type')} | "
            f"{rclass(r)} ({r['verdict']}, matrix {r.get('matrix_class')}, a2 {r.get('a2')}) | "
            f"A {fl(r.get('a_frames'))} [{r.get('a_op')}] | B {fl(r.get('b_frames'))} [{r.get('b_op')}]")


def load(path):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return None


def read_csv_rows(resdir, id_):
    p = f"{resdir}/baselines-cuvein-shard{id_}-all.csv"
    out = {}
    if os.path.exists(p):
        for r in csv.DictReader(open(p, newline="")):
            out[r["mode"]] = r
    return out


def racecheck(id_):
    p = f"{WT}/eval/realworld/racecheck/{id_}.txt"
    if not os.path.exists(p):
        return ""
    txt = open(p, errors="replace").read()
    if "racecheck n/a" in txt[:200]:
        return "n/a (global memory)"
    m = re.findall(r"RACECHECK SUMMARY: (\d+) hazards? displayed \((\d+) errors?, (\d+) warnings?\)", txt)
    if m:
        d, e, w = m[-1]
        m2 = re.findall(r"(\d+) errors?, (\d+) warnings? in total|(\d+) errors?, (\d+) warnings?", txt)
        return f"{e} errors, {w} warnings (displayed {d})"
    return "see file"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=f"{WT}/eval/results/realworld_t21c")
    ap.add_argument("--manifest", default=f"{WT}/eval/realworld/manifest_t21c.csv")
    ap.add_argument("--pairs", default=f"{WT}/eval/realworld/recall_pairs.json")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--exclude", default="", help="comma list of manifest ids or targets left unscored (T21c: colmap-new-1,lightgbm-new-1,lightgbm-new-2)")
    a = ap.parse_args()
    spec_all = json.load(open(a.pairs))
    man = {r["id"]: r for r in csv.DictReader(open(a.manifest, newline=""))}
    pats = {}
    for l in open(f"{WT}/eval/realworld/targets.jsonl"):
        d = json.loads(l)
        pats[d["id"]] = d
    excl = {x for x in a.exclude.split(",") if x}
    brows = [(i, r["target"]) for i, r in man.items()
             if r["variant"] == "buggy" and i not in excl and r["target"] not in excl]    # T21c: one scored row per buggy manifest id
    try:
        tvd = json.load(open(f"{a.results}/tv_violation.json"))      # harness/scan_tv.py (fact only; changes no outcome)
    except (OSError, ValueError):
        tvd = {}
    rows, queue_miss, queue_fixed, others = [], [], [], []
    detail = {}
    for bid, t in brows:
        spec = spec_all[t]
        orc = json.load(open(f"{WT}/eval/realworld/oracle/{t}.json"))
        exp_class = orc["expected_class"]
        manb = man[bid]
        pr = pats[t]
        for flavor, resdir in (("main", a.results), ("certain", f"{a.results}/certain"), ("vc5400", f"{a.results}/vc5400")):
            for variant in ("buggy", "fixed"):
                id_ = bid if variant == "buggy" else f"{t}-fixed"
                if variant == "fixed" and (id_ not in man or bid != f"{t}-buggy"):
                    continue                  # T21c: candidates have no fixed row (except llamacpp-open-2)
                att = load(f"{resdir}/attrib/{id_}.json")
                csvr = read_csv_rows(resdir, id_)
                if att is None and not csvr:
                    continue
                modes = MODES if flavor == "main" else (("scalar-clock",) if flavor.endswith("-sc") else ("vector-clock",))
                for mode in modes:
                    cr = csvr.get(mode, {})
                    am = (att or {}).get("modes", {}).get(mode)
                    if not cr and am is None:
                        continue              # T21c: mode not run (vector-clock skipped on Jeffery's instruction): no row
                    status = cr.get("verdict", "")        # RACE | CLEAN | TIMEOUT | ERROR | ''
                    base = dict(id=id_, target=t, variant=variant, mode=mode, flavor=flavor, wave=manb["wave"], route=manb["route"],
                                pattern=pr.get("pattern", ""), expected_class=exp_class, run_verdict=status,
                                wall_s=cr.get("wall_s", ""), native_wall_s=cr.get("native_wall_s", ""), rc=cr.get("rc", ""),
                                n_race=(am or {}).get("n_race", ""), n_sc=(am or {}).get("n_sc", ""),
                                racecheck=racecheck(id_), tv_violation=tvcell(tvd.get(f"{flavor}/{id_}/{mode}")), open_decision=spec.get("open_decision") or "")
                    reps = (am or {}).get("reports", [])
                    ok_run = status in ("RACE", "CLEAN") and am is not None
                    if variant == "buggy":
                        comps = OrderedDict()
                        for cl in ("DR", "SC"):
                            if cl in exp_class.split("+"):
                                ps = [p for p in spec["pairs"] if p["cls"] == cl and
                                      (p["role"] in ("primary", "family") or (cl == "SC" and exp_class == "DR+SC"))]
                                comps[cl] = ps
                        for cl, ps in comps.items():
                            row = dict(base, component=cl)
                            if not ok_run:
                                if "no-kernel-json" in (cr.get("notes") or ""):
                                    row.update(outcome="VOID", miss_cause="first run void: no kernel launched (driver args defect, re-queued)",
                                               matched="", operating_point="", a2="", strong_token="")
                                else:
                                    row.update(outcome="MISSED", miss_cause=f"m4: {status or 'no run'} ({(cr.get('notes') or '')[:160]})",
                                               matched="", operating_point="", a2="", strong_token="")
                                    queue_miss.append(dict(row, kind="MISSED", evidence=[], kernel_seen=""))
                            else:
                                inc, oth, which = [], [], []
                                for r in reps:
                                    for p in ps:
                                        if match(r, p):
                                            (inc if rclass(r) == cl else oth).append((r, p))
                                            break
                                if inc:
                                    r0, p0 = inc[0]
                                    exact = any(p["role"] == "primary" for _, p in inc)
                                    pts = {("latent" if r.get("matrix_class") == "latent" else "race") for r, _ in inc}
                                    if mode == "scalar-clock":
                                        op = "scalar-clock (one point)"
                                    elif cl == "SC":
                                        op = "SC report (informational class)"
                                    else:
                                        op = "Race" if "race" in pts else "Race u Latent only"
                                    a2s = sorted({str(r.get("a2")) for r, _ in inc})
                                    row.update(outcome="DETECTED" + ("" if exact else " (family)"),
                                               matched="; ".join(sorted({p["name"] for _, p in inc})), operating_point=op,
                                               a2=",".join(a2s), strong_token="yes" if any(strong(r) for r, _ in inc) else "no",
                                               miss_cause="")
                                elif oth:
                                    r0, p0 = oth[0]
                                    row.update(outcome=f"DETECTED-AS-{rclass(r0)}", matched=p0["name"],
                                               operating_point="", a2=str(r0.get("a2")),
                                               strong_token="yes" if any(strong(r) for r, _ in oth) else "no", miss_cause="")
                                    queue_miss.append(dict(row, kind="DETECTED-AS", reports=[rep_str(r) for r, _ in oth]))
                                else:
                                    # miss: propose a cause from the evidence the attribution kept
                                    ev, cause = [], ""
                                    ksn = am.get("kernel_seen", 0) if am else 0
                                    sv = [v for v in am.get("site_verdicts", [])
                                          if any(hits(v["cur_frames"], p["A"]) and hits(v["anc_frames"], p["B"]) or
                                                 hits(v["cur_frames"], p["B"]) and hits(v["anc_frames"], p["A"]) for p in ps)]
                                    if not ksn:
                                        cause = (f"m1 (proposed): the oracle's kernel ({att.get('oracle_kernel_substr')}) is not among the "
                                                 f"{am.get('n_kernel_jsons')} traced kernels")
                                    elif sv:
                                        ords = [v for v in sv if v.get("verdict") == "ORDERED"]
                                        if ords:
                                            v0 = ords[0]
                                            cause = (f"m2 (proposed): the pair was judged ORDERED ({v0.get('hb_class')}; ordering_syncs "
                                                     f"{v0.get('ordering_syncs')}; hb_chain {v0.get('hb_chain')})")
                                        else:
                                            cause = "m3? (proposed): verdicts exist for the sites but none is a report: " + \
                                                    ", ".join(sorted({f"{v.get('verdict')}/{v.get('hb_class')}" for v in sv}))
                                        ev = sv[:6]
                                    else:
                                        sk = am.get("site_skipped") or {}
                                        cause = ("m1/m3 (proposed): no verdict between the oracle's sites; skipped edges there: "
                                                 f"{sk}" if sk else "m1/m3 (proposed): no verdict and no skipped edge between the oracle's sites "
                                                 "(the conflicting instance did not run, or the pair is outside the model)")
                                    row.update(outcome="MISSED", miss_cause=cause, matched="", operating_point="", a2="", strong_token="")
                                    ov = (spec.get("miss_cause") or {}).get(id_)      # T21c: hand-checked cause from recall_pairs.json; the automatic proposal is kept
                                    if ov:
                                        row["miss_cause"] = f"{ov} [scorer's automatic proposal: {cause}]"
                                    queue_miss.append(dict(row, kind="MISSED", evidence=ev, kernel_seen=ksn))
                            rows.append(row)
                    else:  # fixed
                        fx = spec.get("fixed", {})
                        row = dict(base, component="")
                        if not ok_run:
                            row.update(outcome="VOID" if "no-kernel-json" in (cr.get("notes") or "") else "NOT-SCORED", miss_cause=f"m4: {status or 'no run'} ({(cr.get('notes') or '')[:160]})", matched="",
                                       operating_point="", a2="", strong_token="")
                        else:
                            eq = [(r, p) for r in reps for p in fx.get("equiv", []) if match(r, p)]
                            rs = [(r, p) for r in reps for p in fx.get("residual", []) if match(r, p)]
                            kn = [(r, p) for r in reps for p in spec.get("both_builds", []) if match(r, p)]
                            if eq:
                                oc = "STILL-REPORTED"
                            elif rs:
                                oc = "RESIDUAL-AS-EXPECTED" if fx.get("oracle") == "residual" else "STILL-REPORTED"
                            else:
                                oc = "CLEAN-FOR-PAIR"
                            matched = "; ".join(sorted({p["name"] for _, p in eq + rs}))
                            row.update(outcome=oc, matched=matched, operating_point="", a2="", miss_cause="",
                                       strong_token="yes" if any(strong(r) for r, _ in eq + rs) else "no")
                            row["also_residual"] = "yes" if (eq and rs) else ""
                            if oc in ("STILL-REPORTED", "RESIDUAL-AS-EXPECTED"):
                                queue_fixed.append(dict(row, kind=oc, oracle_fixed=fx.get("oracle"),
                                                        reports=[rep_str(r) for r, _ in eq + rs]))
                        rows.append(row)
                    # reports no spec pair explains: the T21c queue
                    known = []
                    for p in spec.get("pairs", []) + spec.get("both_builds", []) + fx_all(spec):
                        known.append(p)
                    for r in reps:
                        if not any(match(r, p) for p in known):
                            others.append(dict(id=id_, target=t, variant=variant, mode=mode, flavor=flavor, kernel=r.get("kernel"),
                                               a_pc=hex(r["a_pc"]), b_pc=hex(r["b_pc"]), cls=rclass(r), verdict=r["verdict"],
                                               matrix_class=r.get("matrix_class"), space=r["space"], race_type=r.get("race_type"),
                                               a=fl(r.get("a_frames")), b=fl(r.get("b_frames")), a_op=r.get("a_op"), b_op=r.get("b_op")))
    # Opus triage (triage_opus.md, 7eb1eb9): cccl-1 "other" reports are artifacts of the syncwarp record defect (trace sync_mask 0xffffffff for a
    # __syncwarp(0x3fffff)); they leave T21c's queue and are kept in other_reports_removed.csv with the reason.
    removed = [dict(o, reason="cccl-1: artifact of the syncwarp-record defect (Opus triage 7eb1eb9, item 1)") for o in others if o["target"] == "cccl-1"]
    others = [o for o in others if o["target"] != "cccl-1"]
    # amrex-1: final m4 (Jeffery's decision; the long-cap pass was not run, see REALWORLD.md 2.6)
    for r in rows:
        if r["target"] == "amrex-1" and r["flavor"] == "main" and r["variant"] == "buggy" and r["miss_cause"].startswith("m4"):
            r["miss_cause"] += " [FINAL m4: decision, long-cap pass not run]"
    # ---- outputs
    cols = ["id", "target", "variant", "mode", "flavor", "component", "wave", "route", "pattern", "expected_class", "run_verdict", "n_race", "n_sc",
            "outcome", "matched", "operating_point", "a2", "strong_token", "miss_cause", "also_residual", "open_decision",
            "wall_s", "native_wall_s", "rc", "racecheck", "tv_violation"]
    if a.write:
        os.makedirs(a.results, exist_ok=True)
        with open(f"{a.results}/recall.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        with open(f"{a.results}/other_reports.csv", "w", newline="") as fh:
            oc = ["id", "target", "variant", "mode", "flavor", "kernel", "a_pc", "b_pc", "cls", "verdict", "matrix_class", "space", "race_type",
                  "a", "b", "a_op", "b_op"]
            w = csv.DictWriter(fh, fieldnames=oc)
            w.writeheader()
            for r in others:
                w.writerow(r)
        with open(f"{a.results}/other_reports_removed.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=oc + ["reason"])
            w.writeheader()
            for r in removed:
                w.writerow(r)
        json.dump(dict(queue_miss=queue_miss, queue_fixed=queue_fixed), open(f"{a.results}/triage_inputs.json", "w"), indent=1, default=str)
    print(f"removed from other queue: {len(removed)};")
    print(f"rows {len(rows)}; misses/detected-as {len(queue_miss)}; fixed to triage {len(queue_fixed)}; other reports {len(others)}")
    return rows, queue_miss, queue_fixed, others


def tvcell(q):
    return "" if q is None else f"{q['n_tv_violation']}/{q['n_kernel_jsons']}"


def fx_all(spec):
    fx = spec.get("fixed", {})
    return list(fx.get("equiv", [])) + list(fx.get("residual", []))


if __name__ == "__main__":
    main()

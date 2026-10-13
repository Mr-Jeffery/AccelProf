#!/usr/bin/env python3
"""X2 -- the sound column (eval/FINAL_CERTAIN.md): checks over the two recordings of
setup/p_final_certain.sh (P4 + P5, vector-clock, no-dump; one leg under
YOSEMITE_HB_GATE_POLICY=certain, one under =recorded, same node, same job).

  check      step 2. Every vector-clock kernel JSON of a store carries hb_gate_policy=<policy>
             and every hb_races record gate_policy=<policy>; every meta.json asked for <policy>;
             every vector-clock row of the leg's CSVs notes gate_policy=certain (certain leg) or
             carries no gate_policy note (recorded leg). Exit 1 on any violation.
               final_certain.py check --store <store> --results <dir> --policy certain|recorded
  invariant  step 3. Per program: the certain run's reported pc-pair set (Race u Strong
             conflict: confirm-detail reports of class structural/model_bug, SC reports of class
             sc) must contain the recorded run's (eval/CERTAIN_CLOCK.md section 1; there it holds
             on the same trace, here between two recordings made alike, so a violation is a
             detector bug or a schedule difference and is listed either way). Also: the same at
             Race u Latent (every report, latent and latent-sc included); the verdicts at Race
             alone and Race u Latent under both policies (make_tables' own functions); the pairs
             the certain clock adds, with their class; and, from the certain store's kernel JSONs,
             whether every instance of an added pair is a2_uncertain (it must be:
             CERTAIN_CLOCK.md section 1, "what the certain clock adds is the flagged population").
             For pairs both runs report: the unflagged instance counts under each (equal on one
             trace by T16's tests; across two recordings a difference is the schedule).
               final_certain.py invariant --certain-store S1 --recorded-store S2
                   --certain-confirm C1 --recorded-confirm C2 --certain-results R1
                   --recorded-results R2 --out <dir>
Reads only; the kernel JSONs are on BeeGFS (compute nodes), the rest in home.
"""
import argparse
import csv
import glob
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_tables as mt  # noqa: E402  (load_runs, race_alone_verdict: the tables' own reading)

VC = mt.VC
RACE_CLS = {"structural", "model_bug"}      # a race of this run (vector-clock), D2
SC_CLS = {"sc"}                             # an unordered strong conflict of this run
LATENT_CLS = {"latent", "latent-sc"}


def _space(s):
    return (s or "").split("/")[0]


def _kernel_jsons(store, pid):
    return sorted(glob.glob(f"{store}/{pid}/{VC}/kernel_*.json"))


def _programs(store):
    return sorted(os.path.basename(os.path.dirname(m)) for m in glob.glob(f"{store}/*/meta.json"))


# ---------------------------------------------------------------- step 2
def cmd_check(a):
    bad = []
    nprog = nker = nrec = 0
    chain = defaultdict(int)
    nstats = 0      # kernel JSONs carrying HB_STATS (YOSEMITE_HB_STATS=1 writes `hb_stats` into each)
    for pid in _programs(a.store):
        meta = json.load(open(f"{a.store}/{pid}/meta.json"))
        nprog += 1
        if meta.get("hb_gate_policy") != a.policy:
            bad.append(f"{pid}: meta.json hb_gate_policy={meta.get('hb_gate_policy')!r}")
        if meta.get("hb_dump") not in (False, 0):
            bad.append(f"{pid}: meta.json hb_dump={meta.get('hb_dump')!r} (expected no-dump)")
        for kj in _kernel_jsons(a.store, pid):
            nker += 1
            try:
                j = json.load(open(kj))
            except ValueError as e:
                bad.append(f"{pid}/{os.path.basename(kj)}: unreadable ({e})")
                continue
            if j.get("hb_gate_policy") != a.policy:
                bad.append(f"{pid}/{os.path.basename(kj)}: hb_gate_policy={j.get('hb_gate_policy')!r}")
            st = (j.get("hb_stats") or {}).get("hb_clock")
            if st is not None:
                nstats += 1
                if st.get("gate_policy") != a.policy:
                    bad.append(f"{pid}/{os.path.basename(kj)}: hb_stats gate_policy={st.get('gate_policy')!r}")
            if "hb_events" in j:
                bad.append(f"{pid}/{os.path.basename(kj)}: carries hb_events (expected no-dump)")
            for r in j.get("hb_races") or ():
                nrec += 1
                if r.get("gate_policy") != a.policy:
                    bad.append(f"{pid}/{os.path.basename(kj)}: hb_races record gate_policy="
                               f"{r.get('gate_policy')!r} ({r.get('a_pc')}-{r.get('b_pc')})")
            for k, v in (j.get("hb_chain") or {}).items():
                chain[k] += v
    rows = [r for f in sorted(glob.glob(f"{a.results}/*.csv")) for r in csv.DictReader(open(f))]
    vrows = [r for r in rows if r.get("mode") == VC]
    by_verdict = defaultdict(int)
    for r in vrows:
        by_verdict[r["verdict"]] += 1
        notes = r.get("notes") or ""
        if a.policy == "certain" and not re.search(r"(^|;)gate_policy=certain(;|$)", notes):
            bad.append(f"row {r['id']} rep {r.get('rep')} {r['verdict']}: notes lack gate_policy=certain "
                       f"({notes[:100]})")
        if a.policy == "recorded" and "gate_policy=" in notes:
            bad.append(f"row {r['id']} rep {r.get('rep')}: recorded leg notes carry a gate_policy "
                       f"({notes[:100]})")
    other = [r for r in rows if r.get("mode") != VC]
    print(f"check {a.store} policy={a.policy}: {nprog} programs, {nker} vector-clock kernel JSONs, "
          f"{nrec} hb_races records; {len(vrows)} vector-clock rows {dict(by_verdict)}"
          f"{f', {len(other)} rows of another mode' if other else ''}; "
          f"HB_STATS (hb_stats.hb_clock) in {nstats} of {nker} kernel JSONs; hb_chain summed {dict(chain)}")
    for b in bad:
        print("  VIOLATION", b)
    print(f"check: {len(bad)} violations")
    sys.exit(1 if bad else 0)


# ---------------------------------------------------------------- step 3
def _confirm(cdir, pid):
    p = f"{cdir}/{pid}__cuvein__{VC}.json"
    return json.load(open(p)) if os.path.exists(p) else None


def _pairs(conf):
    """{(a_pc, b_pc, space): (verdict-set, matrix_class, conflict_class)} of a confirm detail."""
    out = {}
    for r in (conf.get("raw") or []) + (conf.get("raw_sc") or []):
        if r.get("a_pc") is None or r.get("b_pc") is None:
            continue      # T2 host reports: no pc pair
        a, b = sorted((r["a_pc"], r["b_pc"]))
        k = (a, b, _space(r.get("space")))
        out[k] = (r.get("matrix_class") or ("sc" if r.get("verdict") == "SC" else "race"),
                  r.get("conflict_class") or ("SC" if r.get("verdict") == "SC" else ""))
    return out


def _instances(store, pid):
    """{(a_pc, b_pc, space): [count, a2_uncertain, {class: count}]} over the program's
    vector-clock kernel JSONs (the hb_races aggregates)."""
    inst = defaultdict(lambda: [0, 0, defaultdict(int)])
    for kj in _kernel_jsons(store, pid):
        for r in json.load(open(kj)).get("hb_races") or ():
            if r.get("a_pc") is None or r.get("b_pc") is None:
                continue
            a, b = sorted((r["a_pc"], r["b_pc"]))
            x = inst[(a, b, _space(r.get("space")))]
            n = int(r.get("count", 1))
            x[0] += n
            x[1] += int(r.get("a2_uncertain", 0))
            x[2][r.get("class", "DR")] += n
    return inst


def _chain(store, pid):
    c = defaultdict(int)
    for kj in _kernel_jsons(store, pid):
        for k, v in (json.load(open(kj)).get("hb_chain") or {}).items():
            c[k] += v
    return c


def _fmt_pair(k):
    return f"{k[2]}:{hex(k[0])}-{hex(k[1])}"


def cmd_invariant(a):
    cr, _ = mt.load_runs(sorted(glob.glob(f"{a.certain_results}/*.csv")), shards=True)
    rr, _ = mt.load_runs(sorted(glob.glob(f"{a.recorded_results}/*.csv")), shards=True)
    man = mt.load_manifest()
    ids = sorted({k[0] for k in cr} | {k[0] for k in rr})
    os.makedirs(a.out, exist_ok=True)
    per, added_rows, viol = [], [], []
    tot = defaultdict(int)
    for pid in ids:
        rc_ = cr.get((pid, "cuvein-certain", VC))
        rv = rr.get((pid, "cuvein", VC))
        rec = dict(id=pid, pset=man.get(pid, {}).get("pset", pid.split("-")[0]),
                   label=man.get(pid, {}).get("label", ""),
                   recorded=rv["verdict"] if rv else "—", certain=rc_["verdict"] if rc_ else "—",
                   recorded_race_alone=(mt.race_alone_verdict(rv) or "n/a") if rv else "—",
                   certain_race_alone=(mt.race_alone_verdict(rc_) or "n/a") if rc_ else "—")
        cc, cv = _confirm(a.certain_confirm, pid), _confirm(a.recorded_confirm, pid)
        if rc_ is None and (pid, "cuvein", VC) in cr:
            rec["note"] = "certain row without gate_policy=certain"
        if cc is None or cv is None:
            rec.update(status="not-comparable",
                       note=rec.get("note") or f"no confirm detail ({'certain' if cc is None else ''}"
                                               f"{' ' if cc is None and cv is None else ''}"
                                               f"{'recorded' if cv is None else ''})")
            per.append(rec)
            tot["not-comparable"] += 1
            continue
        if cc.get("gate_policy") != "certain" or cv.get("gate_policy", "recorded") != "recorded":
            viol.append(f"{pid}: confirm gate_policy certain-side={cc.get('gate_policy')!r} "
                        f"recorded-side={cv.get('gate_policy')!r}")
        pc, pv = _pairs(cc), _pairs(cv)
        core_c = {k for k, (m, _) in pc.items() if m in RACE_CLS | SC_CLS}
        core_v = {k for k, (m, _) in pv.items() if m in RACE_CLS | SC_CLS}
        lost = sorted(core_v - core_c)            # the invariant: must be empty
        lost_all = sorted(set(pv) - set(pc))      # the same at Race u Latent
        added = sorted(core_c - core_v)
        ic, iv = _instances(a.certain_store, pid), _instances(a.recorded_store, pid)
        unflag_added = 0
        for k in added:
            n, f, by = ic.get(k, [0, 0, {}])
            unflag_added += n - f
            added_rows.append(dict(id=pid, pair=_fmt_pair(k), certain_class=pc[k][0],
                                   conflict=pc[k][1] or "/".join(sorted(by)),
                                   recorded_class=pv[k][0] if k in pv else "—",
                                   instances=n, a2_uncertain=f, all_flagged=n > 0 and f == n,
                                   classes=";".join(f"{c}:{v}" for c, v in sorted(by.items()))))
        common = core_c & core_v
        unfl_diff = sum((ic.get(k, [0, 0])[0] - ic.get(k, [0, 0])[1])
                        != (iv.get(k, [0, 0])[0] - iv.get(k, [0, 0])[1]) for k in common)
        ch = _chain(a.certain_store, pid)
        rec.update(status="VIOLATION" if lost else "ok",
                   rep_recorded=len(core_v), rep_certain=len(core_c), added=len(added),
                   added_dr=sum(pc[k][0] in RACE_CLS for k in added),
                   added_sc=sum(pc[k][0] in SC_CLS for k in added),
                   added_unflagged_instances=unflag_added, lost=len(lost), lost_r_u_l=len(lost_all),
                   common_unflagged_differ=unfl_diff,
                   chain_edges=ch.get("edges", 0), chain_refused=ch.get("refused", 0),
                   chain_uncertain=ch.get("uncertain", 0), chain_unsafe=ch.get("unsafe", 0),
                   chain_open=ch.get("open", 0))
        if lost:
            viol.append(f"{pid}: recorded reports not reported under certain: "
                        + ", ".join(f"{_fmt_pair(k)} ({pv[k][0]})" for k in lost))
        if lost_all and not lost:
            viol.append(f"{pid}: (Race u Latent) recorded reports absent under certain: "
                        + ", ".join(f"{_fmt_pair(k)} ({pv[k][0]})" for k in lost_all))
        per.append(rec)
        tot["comparable"] += 1
        tot["added"] += len(added)
        tot["added_unflagged_instances"] += unflag_added
        tot["violations"] += bool(lost)
        tot["moved_race_alone"] += rec["recorded_race_alone"] != rec["certain_race_alone"]
        tot["moved_r_u_l"] += rec["recorded"] != rec["certain"]
    cols = ["id", "pset", "label", "status", "recorded", "certain", "recorded_race_alone",
            "certain_race_alone", "rep_recorded", "rep_certain", "added", "added_dr", "added_sc",
            "added_unflagged_instances", "lost", "lost_r_u_l", "common_unflagged_differ",
            "chain_edges", "chain_uncertain", "chain_refused", "chain_unsafe", "chain_open", "note"]
    with open(f"{a.out}/per_program.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in per:
            w.writerow(r)
    acols = ["id", "pair", "certain_class", "conflict", "recorded_class", "instances",
             "a2_uncertain", "all_flagged", "classes"]
    with open(f"{a.out}/added_pairs.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=acols)
        w.writeheader()
        for r in added_rows:
            w.writerow(r)
    print(f"invariant: {tot['comparable']} programs comparable, {tot['not-comparable']} not; "
          f"violations (Race u Strong conflict) {tot['violations']}; added pc pairs {tot['added']} "
          f"({sum(r['all_flagged'] for r in added_rows)} with every instance a2_uncertain, "
          f"{tot['added_unflagged_instances']} unflagged instances); verdicts moved: Race alone "
          f"{tot['moved_race_alone']}, Race u Latent {tot['moved_r_u_l']}")
    for v in viol:
        print("  VIOLATION" if "(Race u Latent)" not in v else "  NOTE", v)
    print("\n| program | label | Race alone recorded | Race alone certain | R u L recorded | R u L certain "
          "| Race u SC pairs rec / cert | added (DR / SC) | added unflagged inst. | chain edges refused / total |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in per:
        if r.get("status") == "not-comparable":
            print(f"| {r['id']} | {r['label']} | {r['recorded_race_alone']} | {r['certain_race_alone']} "
                  f"| {r['recorded']} | {r['certain']} | — | — | — | — ({r.get('note', '')}) |")
            continue
        print(f"| {r['id']} | {r['label']} | {r['recorded_race_alone']} | {r['certain_race_alone']} "
              f"| {r['recorded']} | {r['certain']} | {r['rep_recorded']} / {r['rep_certain']} "
              f"| {r['added']} ({r['added_dr']} / {r['added_sc']}) | {r['added_unflagged_instances']} "
              f"| {r['chain_refused']:,} / {r['chain_edges']:,} |")
    sys.exit(1 if tot["violations"] else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("check")
    c.add_argument("--store", required=True)
    c.add_argument("--results", required=True)
    c.add_argument("--policy", required=True, choices=("certain", "recorded"))
    i = sp.add_parser("invariant")
    for k in ("certain-store", "recorded-store", "certain-confirm", "recorded-confirm",
              "certain-results", "recorded-results", "out"):
        i.add_argument(f"--{k}", required=True)
    a = ap.parse_args()
    {"check": cmd_check, "invariant": cmd_invariant}[a.cmd](a)


if __name__ == "__main__":
    main()

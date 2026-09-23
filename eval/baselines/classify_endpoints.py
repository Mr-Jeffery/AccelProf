#!/usr/bin/env python3
"""Disagreement classifier for the baseline comparison.

Two tools disagree on a program when their RACE/CLEAN verdicts differ. For every
disagreement this emits one row per involved report pair, classified as:
  category  : weak-vs-weak | weak-vs-strong | strong-vs-strong | RMW-vs-RMW | unresolved
  mechanism : barrier | warp-lockstep | fence-chain | none
plus which tool's verdict matches the PTX 8.7.1 definition of a data race
(conflict AND not causality-ordered AND not morally-strong) and which matches the
suite label.

Endpoint strength/RMW come from the atomic-scope sidecar the detector already
produces (YOSEMITE_ATOMIC_SCOPE_FILE = `<pc> <scope>`, scope in
none/warp/block/grid; the file lists exactly the ATOM/ATOMG/ATOMS/RED RMW pcs).
  - RMW endpoint            : pc present in the scope file
  - morally-strong endpoint : scope >= block (block/grid)
  - weak endpoint           : plain access or relaxed atomic (absent / scope none)
Mechanism/strength of the *pair* come from the sync_dominance verdict object
captured in the confirmation-run JSON (strength, syncs, hb_chain, hb_class).

Consumes the confirmation JSONs written by run_cuvein.py --confirm, the reduced
per-tool verdicts (from eval/results/baselines-*.csv), and the manifest labels.
Writes eval/results/baselines-disagreements.csv. Runs anywhere (no GPU).

    .env/bin/python eval/baselines/classify_endpoints.py
"""
import csv
import glob
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.dirname(os.path.dirname(HERE))
RES = f"{APH}/eval/results"

import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "python"))
import hb_modes  # noqa: E402  (vector-clock / scalar-clock; legacy names accepted with a warning)
VC, SC = hb_modes.VECTOR_CLOCK, hb_modes.SCALAR_CLOCK
CONFIRM = f"{HERE}/confirm"
SCOPE_ORD = {"none": 0, "warp": 1, "block": 2, "grid": 3}


def load_scope(path):
    """atomic_scope.txt -> {pc(int): scope_name}. Empty when no file / no atomics."""
    m = {}
    if not path or not os.path.exists(path):
        return m
    for ln in open(path):
        p = ln.split()
        if len(p) >= 2:
            try:
                pc = int(p[0], 0)
            except ValueError:
                continue
            sc = p[1].lower()
            m[pc] = sc if sc in SCOPE_ORD else ("block" if sc in ("2",) else
                    "grid" if sc in ("3",) else "none")
    return m


def endpoint_kind(pc, scope):
    """-> 'rmw' | 'strong' | 'weak'. rmw = in scope file (ATOM/RED); strong = scope
    >= block; else weak (plain / relaxed atomic)."""
    if pc in scope:
        return "rmw" if SCOPE_ORD.get(scope[pc], 0) >= SCOPE_ORD["block"] else "weak"
    return "weak"


def pair_category(ka, kb):
    ks = {ka, kb}
    if ka == "rmw" and kb == "rmw":
        return "RMW-vs-RMW"
    strongish = {"rmw", "strong"}
    if ka in strongish and kb in strongish:
        return "strong-vs-strong"
    if ka in strongish or kb in strongish:
        return "weak-vs-strong"
    return "weak-vs-weak"


def mechanism(raw):
    """barrier | warp-lockstep | fence-chain | none from the sd verdict object."""
    if not raw:
        return "none"
    if raw.get("hb_chain"):
        return "fence-chain"
    if raw.get("syncs"):
        return "barrier"
    hc = (raw.get("hb_class") or "")
    if "warp" in hc:
        return "warp-lockstep"
    return "none"


def classify_report(rep_raw, scope):
    a, b = rep_raw.get("a_pc"), rep_raw.get("b_pc")
    if a is None or b is None:
        return "unresolved", mechanism(rep_raw)
    ka = endpoint_kind(a, scope)
    kb = endpoint_kind(b, scope)
    return pair_category(ka, kb), mechanism(rep_raw)


# Only tools that claim a RACE/CLEAN verdict take part in race disagreements.
# memcheck/synccheck/initcheck rows reuse the schema's RACE column as "FLAGGED"
# for their own error class and are excluded here.
RACE_TOOLS = {"cuvein", "racecheck", "hirace", "iguard", "supercollider"}


def load_reduced():
    """(id,tool,mode) -> verdict, collapsing reps (any RACE => RACE)."""
    per = defaultdict(list)
    meta = {}
    for path in glob.glob(f"{RES}/baselines-*.csv"):
        tool = os.path.basename(path)[len("baselines-"):-4]
        if tool in ("build", "disagreements", "p7-selection", "diagnose") or "-shard" in tool:
            continue
        rd = csv.DictReader(open(path, newline=""))
        if not {"id", "program", "verdict"} <= set(rd.fieldnames or []):
            continue                      # not a per-run result file
        for r in rd:
            t = r.get("tool") or tool
            if t not in RACE_TOOLS:
                continue
            per[(r["id"], t, hb_modes.canon(r.get("mode", ""), path))].append(r["verdict"])
            meta[r["id"]] = r["program"]
    red = {}
    for k, vs in per.items():
        red[k] = "RACE" if "RACE" in vs else ("CLEAN" if "CLEAN" in vs else vs[0])
    return red, meta


def load_labels():
    m = {}
    p = f"{HERE}/manifest.csv"
    if os.path.exists(p):
        for r in csv.DictReader(open(p, newline="")):
            m[r["id"]] = r.get("label", "")
    return m


def main():
    red, prog = load_reduced()
    labels = load_labels()
    # confirmation raw reports per (id, toolmode)
    confirm = {}
    for f in glob.glob(f"{CONFIRM}/*.json"):
        d = json.loads(open(f).read())
        d["mode"] = hb_modes.canon(d.get("mode", ""), CONFIRM)
        confirm[(d["id"], f"{d['tool']}:{d['mode']}")] = d

    # group verdicts per id across tool-columns
    byid = defaultdict(dict)
    for (i, tool, mode), v in red.items():
        if i not in labels:
            continue        # retired program sets (P2/P8 -> PI): rows kept in the CSVs, not compared
        byid[i][(tool, mode)] = v

    rows = []
    for i, tv in byid.items():
        # tool order, then the harness's mode order (vector-clock before scalar-clock,
        # as engine sorted before trace-only): tool_a/tool_b stay where they were
        cols = sorted(tv.items(), key=lambda kv: (kv[0][0], _mode_rank(kv[0][1])))
        for a in range(len(cols)):
            for b in range(a + 1, len(cols)):
                (ta, ma), va = cols[a]
                (tb, mb), vb = cols[b]
                if {va, vb} != {"RACE", "CLEAN"}:
                    continue                       # only true RACE/CLEAN splits
                # pick a confirmation report set from whichever side reported RACE
                race_side = (ta, ma) if va == "RACE" else (tb, mb)
                key = (i, f"{race_side[0]}:{race_side[1]}")
                d = confirm.get(key)
                scope = load_scope(d.get("scope_file")) if d else {}
                raws = (d.get("raw") or []) if d else []
                lab = labels.get(i, "")
                if not raws:
                    rows.append(dict(program=prog.get(i, i),
                        tool_a=f"{ta}/{ma}".rstrip("/"), verdict_a=va,
                        tool_b=f"{tb}/{mb}".rstrip("/"), verdict_b=vb,
                        category="unresolved", mechanism="none",
                        ptx_871_match=_ptx_match("unresolved", "none", va, vb, ta, ma, tb, mb),
                        suite_label_match=_label_match(lab, va, vb, ta, ma, tb, mb),
                        report="(no confirmation report captured)"))
                    continue
                for rr in raws:
                    cat, mech = classify_report(rr, scope)
                    rows.append(dict(program=prog.get(i, i),
                        tool_a=f"{ta}/{ma}".rstrip("/"), verdict_a=va,
                        tool_b=f"{tb}/{mb}".rstrip("/"), verdict_b=vb,
                        category=cat, mechanism=mech,
                        ptx_871_match=_ptx_match(cat, mech, va, vb, ta, ma, tb, mb),
                        suite_label_match=_label_match(lab, va, vb, ta, ma, tb, mb),
                        report=f"{rr.get('space')}:{hex(rr['a_pc'])}-{hex(rr['b_pc'])}"
                               f":{rr.get('race_type')}"))
    out = f"{RES}/baselines-disagreements.csv"
    fields = ["program", "tool_a", "verdict_a", "tool_b", "verdict_b", "category",
              "mechanism", "ptx_871_match", "suite_label_match", "report"]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} disagreement report-rows -> {out}")


def _mode_rank(m):
    return hb_modes.MODES.index(m) if m in hb_modes.MODES else -1


def _tname(t, m):
    return f"{t}/{m}".rstrip("/")


def _ptx_match(cat, mech, va, vb, ta, ma, tb, mb):
    """Which tool matches PTX 8.7.1 (a real race = conflict, not causality-ordered,
    not morally-strong). A morally-strong pair (RMW-vs-RMW / strong-vs-strong at
    scope) is NOT a race per PTX; anything ordered by barrier/fence-chain is
    causality-ordered and NOT a race. Otherwise it IS a race."""
    if cat in ("RMW-vs-RMW", "strong-vs-strong") or mech in ("barrier", "fence-chain"):
        ptx = "CLEAN"
    elif cat == "unresolved":
        return "unresolved"
    else:
        ptx = "RACE"
    win = _tname(ta, ma) if va == ptx else _tname(tb, mb)
    return f"{win} (PTX={ptx})"


def _label_match(lab, va, vb, ta, ma, tb, mb):
    tgt = "RACE" if lab == "RACE" else "CLEAN" if lab == "CLEAN" else ""
    if not tgt:
        return "no-label"
    win = _tname(ta, ma) if va == tgt else _tname(tb, mb)
    return f"{win} (label={tgt})"


if __name__ == "__main__":
    main()

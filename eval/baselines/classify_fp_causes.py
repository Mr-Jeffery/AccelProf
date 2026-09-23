#!/usr/bin/env python3
"""Attribute every cuVein false-positive report to a root cause -> baselines-fp-causes.csv.

Input: the manifest (label CLEAN = race-free program), the per-program confirmation
details (confirm/<id>__cuvein__<mode>.json: deduped RACE reports with pcs + hb_class)
and the kept mismatch traces (traces_keep/<id>/: CFG dots + engine kernel JSONs). For
each report of a race-free program the two racing pcs are looked up in the CFG and
each endpoint is typed from its SASS opcode:

  atom     ATOM/ATOMG/ATOMS/RED                       atomic RMW (atomicAdd/Exch/CAS/Min)
  seq      MEMBAR;ERRBAR;CCTL.* ; LD|ST.*.STRONG.*    fenced strong ld/st (cuda::atomic
                                                      seq_cst load/store, or a manual
                                                      __threadfence + volatile access)
  strong   LD|ST.*.STRONG.* without the fence idiom   cuda::atomic relaxed load/store, or
                                                      a volatile access
  plain    any other LD*/ST*                          ordinary access

`seq`/`strong` endpoints also carry the opcode FORM: generic (`LD`/`ST`, what the
cuda::atomic builtins lower to) vs spaced (`LDG/STG/LDS/STS`, what a volatile pointer
access lowers to). The report is then assigned one cause:

  RC1-atomic-ldst     both endpoints are language-level atomics (atom, or generic-form
                      seq/strong) and at least one is a load/store: the atomic model
                      only knows RMW opcodes, so cuda::atomic load/store looks plain
  RC3-attribution     vector-clock mode only: hb_class says the pair raced, but no engine
                      hb_races record names this pc pair (subset pair matching marks
                      every pair sharing a pc with a same-pc race) -- or model_bug
  RC2-latent          not raced dynamically (hb_class latent) and no static proof:
                      barrier-in-loop / lock idioms the PC-level rules cannot certify
  RC5-volatile        a spaced-form STRONG endpoint (ScoR volatile handshake data; F1)
  RC4-samepc-waw      same-pc plain write-write that did race: idempotent-write candidate
  other               anything else (plain-vs-plain / plain-vs-atomic that did race)

Writes eval/results/baselines-fp-causes.csv (one row per report) and prints the
per-program-set roll-up: report counts per cause and, per program, the SET of causes
(a program is fixed only when every cause in its set is). No GPU needed.
"""
import argparse
import collections
import csv
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.dirname(os.path.dirname(HERE))
RES = f"{APH}/eval/results"

import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "python"))
import hb_modes  # noqa: E402  (vector-clock / scalar-clock; legacy names accepted with a warning)
VC, SC = hb_modes.VECTOR_CLOCK, hb_modes.SCALAR_CLOCK
_ATOM = ("ATOM", "ATOMG", "ATOMS", "RED")
_MEM = re.compile(r"^(U?LD|U?ST|ATOM|RED)")


def parse_dot(path):
    """-> {cluster: [(pc, opcode)] sorted by pc}; regex parse (no pydot needed)."""
    txt = open(path, errors="replace").read()
    out = {}
    parts = re.split(r'subgraph "cluster_([^"]*)"', txt)
    for i in range(1, len(parts), 2):
        ins = {}
        for lab in re.findall(r'\[label="\{(.*?)\}"\]', parts[i + 1], flags=re.S):
            for line in lab.split("\\l"):
                line = re.sub(r"^\|?<[a-z0-9]+>", "", line).replace("\\ ", " ")
                m = re.match(r"^\s*([0-9a-f]{4,8}):\s+(.*?)\s*;?\s*$", line)
                if not m or not m.group(2).split():
                    continue
                toks = m.group(2).split()
                op = toks[1] if toks[0].startswith("@") and len(toks) > 1 else toks[0]
                ins[int(m.group(1), 16)] = op.rstrip(";")
        out[parts[i]] = sorted(ins.items())
    return out


def endpoint(ins, idx):
    """-> (kind, form, opcode) for the instruction at ins[idx]."""
    op = ins[idx][1]
    parts = op.split(".")
    if parts[0] in _ATOM:
        return "atom", "", op
    if "STRONG" in parts:
        prev = [ins[j][1] for j in range(max(0, idx - 3), idx)]
        fenced = (len(prev) == 3 and prev[0].startswith("MEMBAR")
                  and prev[1].startswith("ERRBAR") and prev[2].startswith("CCTL"))
        form = "generic" if parts[0] in ("LD", "ST") else "spaced"
        return ("seq" if fenced else "strong"), form, op
    return "plain", "", op


def lookup(dotmap, a, b):
    for ins in dotmap.values():
        idx = {pc: i for i, (pc, _) in enumerate(ins)}
        if a in idx and b in idx and _MEM.match(ins[idx[a]][1]) and _MEM.match(ins[idx[b]][1]):
            return endpoint(ins, idx[a]), endpoint(ins, idx[b])
    return None


def engine_pairs(idir):
    """Exact raced pc pairs from the kept vector-clock dumps (the HbEngine's hb_races).
    A WAR record on this branch has a_pc null: keep it as (None, writer_pc). -> set, or
    None if no dump was kept."""
    kjs = glob.glob(f"{hb_modes.resolve_dir(idir, VC)}/kernel_*.json")
    if not kjs:
        return None
    pairs = set()
    for kj in kjs:
        try:
            races = json.load(open(kj)).get("hb_races") or []
        except (OSError, ValueError):
            continue
        for r in races:
            pairs.add((r.get("a_pc"), r.get("b_pc")))
    return pairs


def engine_confirms(pairs, a, b, race_type):
    if (a, b) in pairs or (b, a) in pairs:
        return True
    # WAR with an unknown reader pc: the writer must be in the pair and the report
    # must be a read/write pair.
    return race_type in ("WAR", "RAW") and any(x is None and w in (a, b) for x, w in pairs)


def cause_of(ea, eb, hb_class, same_pc, mode, confirmed):
    def atomicish(e):
        return e[0] == "atom" or (e[0] in ("seq", "strong") and e[1] == "generic")
    if atomicish(ea) and atomicish(eb) and not (ea[0] == "atom" and eb[0] == "atom"):
        return "RC1-atomic-ldst"
    if mode == VC and (hb_class == "model_bug" or
                             (hb_class == "structural" and confirmed is False)):
        return "RC3-attribution"
    if any(e[1] == "spaced" for e in (ea, eb)):
        return "RC5-volatile"
    # scalar-clock has no dynamic class: a same-pc plain write-write is the idempotent-
    # write candidate there too (the engine confirms these race; barriers don't order them)
    if same_pc and ea[0] == "plain" and (hb_class == "structural" or mode == SC):
        return "RC4-samepc-waw"
    if hb_class in ("latent", None):
        return "RC2-latent"
    return "other"


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--manifest", default=f"{HERE}/manifest.csv")
    ap.add_argument("--confirm", default=f"{HERE}/confirm")
    ap.add_argument("--traces", default=f"{HERE}/traces_keep")
    ap.add_argument("--out", default=f"{RES}/baselines-fp-causes.csv")
    a = ap.parse_args()

    man = {r["id"]: r for r in csv.DictReader(open(a.manifest))}
    rows, nodots = [], collections.Counter()
    def _order(f):   # (id, harness mode order): vector-clock rows before scalar-clock, as before T8
        i, _, m = os.path.basename(f)[:-len(".json")].rpartition("__cuvein__")
        m = hb_modes.LEGACY.get(m, m)
        return (i, hb_modes.MODES.index(m) if m in hb_modes.MODES else len(hb_modes.MODES))
    for f in sorted(glob.glob(f"{a.confirm}/*__cuvein__*.json"), key=_order):
        j = json.load(open(f))
        j["mode"] = hb_modes.canon(j["mode"], a.confirm)
        m = man.get(j["id"])
        if not m or m["label"] != "CLEAN" or j["verdict"] != "RACE":
            continue
        idir = f"{a.traces}/{j['id']}"
        dotmap = {}
        for d in glob.glob(f"{idir}/dots/*.dot"):
            dotmap.update(parse_dot(d))
        if not dotmap:
            nodots[(m["pset"], j["mode"])] += 1
            continue
        pairs = engine_pairs(idir) if j["mode"] == VC else None
        for r in j["raw"]:
            hit = lookup(dotmap, r["a_pc"], r["b_pc"])
            if hit is None:
                ea = eb = ("?", "", "?")
            else:
                ea, eb = hit
            confirmed = None if pairs is None else \
                engine_confirms(pairs, r["a_pc"], r["b_pc"], r.get("race_type"))
            rows.append({
                "id": j["id"], "pset": m["pset"], "mode": j["mode"],
                "a_pc": hex(r["a_pc"]), "b_pc": hex(r["b_pc"]), "space": r["space"],
                "race_type": r.get("race_type"), "hb_class": r.get("hb_class") or "",
                "op_a": ea[2], "op_b": eb[2],
                "kind_a": ea[0] + (f"/{ea[1]}" if ea[1] else ""),
                "kind_b": eb[0] + (f"/{eb[1]}" if eb[1] else ""),
                "engine_confirmed": "" if confirmed is None else int(confirmed),
                "cause": "unmapped" if hit is None else
                         cause_of(ea, eb, r.get("hb_class"), r["a_pc"] == r["b_pc"],
                                  j["mode"], confirmed),
            })

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["id"])
        w.writeheader()
        w.writerows(rows)

    for mode in hb_modes.MODES:
        sel = [r for r in rows if r["mode"] == mode]
        print(f"\n=== {mode}: reports per cause")
        c = collections.Counter((r["pset"], r["cause"]) for r in sel)
        for (pset, cause), n in sorted(c.items()):
            progs = len({r["id"] for r in sel if r["pset"] == pset and r["cause"] == cause})
            print(f"  {pset}  {cause:18s} {n:5d} reports in {progs:3d} programs")
        print(f"=== {mode}: FP programs by the set of causes they contain")
        per = collections.defaultdict(set)
        for r in sel:
            per[(r["pset"], r["id"])].add(r["cause"])
        c = collections.Counter((pset, " + ".join(sorted(s))) for (pset, _), s in per.items())
        for (pset, key), n in sorted(c.items()):
            print(f"  {pset}  {n:3d} programs : {key}")
    if nodots:
        print("\nFP programs without kept dots (not classified):", dict(nodots))
    print(f"\n{len(rows)} reports -> {a.out}")


if __name__ == "__main__":
    main()

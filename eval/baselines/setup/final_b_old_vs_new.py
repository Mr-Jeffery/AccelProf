#!/usr/bin/env python3
"""X1b: collapsed cuVein verdicts per suite and mode, X1's merged file against X1b's merged file
(RACE > CLEAN > TIMEOUT > ERROR per (id, mode), make_tables' order, as setup/final_old_vs_new.py),
the moves, every (id, mode) whose verdict changed with each side's cap, and the T24 direction
check: a RACE in X1 that is CLEAN in X1b is listed under "DIRECTION CHECK" (exit code 3).

  .env/bin/python eval/baselines/setup/final_b_old_vs_new.py \
      [--old eval/results/baselines-cuvein.csv] [--new eval/results/final-b/merged/baselines-cuvein.csv] \
      > eval/results/final-b/merged/old_vs_new.md

A key whose X1 verdict comes from X1's 5,400 s pass while X1b skipped that pass (FINAL_SWEEP_B.md
section 1 (a)) is compared as it stands: X1's final verdict against X1b's long-pass verdict; the cap
columns say which rows each side holds."""
import argparse, collections, csv, re, sys

ORDER = ("RACE", "CLEAN", "TIMEOUT", "ERROR")
MODES = ["vector-clock", "scalar-clock"]
PSETS = ["P1", "P3", "P4", "P5", "P6", "P7", "P9", "PI"]


def load(p, man):
    per = collections.defaultdict(list)
    for r in csv.DictReader(open(p, newline="")):
        if r["id"] not in man:
            continue
        for m in ([r["mode"]] if r["mode"] else MODES):
            per[(r["id"], m)].append(r)
    out = {}
    for k, reps in per.items():
        vs = [r["verdict"] for r in reps]
        v = next((x for x in ORDER if x in vs), vs[0])
        caps = sorted({int(c) for r in reps for c in re.findall(r"cap=(\d+)", r["notes"] or "")})
        rids = set()
        for r in reps:
            if r["verdict"] == "RACE":
                rids |= set((r.get("report_ids") or "").split())
        nrep = max((int(r["reports_dedup"] or 0) for r in reps if r["verdict"] == "RACE"), default=0)
        out[k] = dict(verdict=v, caps=caps, reports=rids, nrep=nrep, n=len(reps))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", default="eval/results/baselines-cuvein.csv")
    ap.add_argument("--new", default="eval/results/final-b/merged/baselines-cuvein.csv")
    ap.add_argument("--manifest", default="eval/baselines/manifest.csv")
    a = ap.parse_args()
    man = {r["id"]: r for r in csv.DictReader(open(a.manifest, newline=""))}
    old, new = load(a.old, man), load(a.new, man)
    cap = lambda d: "/".join(str(c) for c in d["caps"]) if d and d["caps"] else "—"
    print(f"Old: `{a.old}` (X1). New: `{a.new}` (X1b).\n")
    print("| suite | mode | X1 RACE / CLEAN / TIMEOUT / ERROR | X1b RACE / CLEAN / TIMEOUT / ERROR | (id, mode) whose verdict changed |")
    print("|---|---|---|---|---|")
    for p in PSETS:
        ids = [i for i in man if man[i]["pset"] == p]
        for m in MODES:
            co = collections.Counter(old[(i, m)]["verdict"] if (i, m) in old else "—" for i in ids)
            cn = collections.Counter(new[(i, m)]["verdict"] if (i, m) in new else "—" for i in ids)
            ch = sum(1 for i in ids if (old.get((i, m)) or {}).get("verdict") != (new.get((i, m)) or {}).get("verdict"))
            f = lambda c: " / ".join(str(c[v]) for v in ORDER) + (f" (+{c['—']} no row)" if c["—"] else "")
            print(f"| {p} | {m} | {f(co)} | {f(cn)} | {ch} |")
    keys = sorted(set(old) | set(new), key=lambda k: (PSETS.index(man[k[0]]["pset"]), k[1] != "vector-clock", k[0]))
    changed = [k for k in keys if (old.get(k) or {}).get("verdict") != (new.get(k) or {}).get("verdict")]
    moves = collections.Counter((man[k[0]]["pset"], k[1], (old.get(k) or {}).get("verdict", "—"),
                                 (new.get(k) or {}).get("verdict", "—")) for k in changed)
    print("\n| suite | mode | X1 → X1b | (id, mode) |\n|---|---|---|---|")
    for k in sorted(moves):
        print(f"| {k[0]} | {k[1]} | {k[2]} → {k[3]} | {moves[k]} |")
    print("\nEvery (id, mode) whose verdict changed (reports = distinct deduplicated reports of a RACE row, max over reps):\n")
    print("| id | mode | X1 verdict | X1 cap (s) | X1b verdict | X1b cap (s) | direction |")
    print("|---|---|---|---|---|---|---|")
    bad = []
    for k in changed:
        o, n = old.get(k), new.get(k)
        ov, nv = (o or {}).get("verdict", "—"), (n or {}).get("verdict", "—")
        d = f"{ov} → {nv}"
        if ov == "RACE" and nv == "CLEAN":
            d = "**RACE → CLEAN (direction check)**"
            bad.append(k)
        ovs = f"{ov} ({o['nrep']})" if o and ov == "RACE" else ov
        nvs = f"{nv} ({n['nrep']})" if n and nv == "RACE" else nv
        print(f"| {k[0]} | {k[1]} | {ovs} | {cap(o)} | {nvs} | {cap(n)} | {d} |")
    # same verdict, different caps (the long passes' policy differences), for the record
    same_cap = [k for k in keys if k not in changed and old.get(k) and new.get(k) and old[k]["caps"] != new[k]["caps"]]
    print("\nSame verdict, different cap (s):\n")
    print("| id | mode | verdict | X1 cap | X1b cap |\n|---|---|---|---|---|")
    for k in same_cap:
        print(f"| {k[0]} | {k[1]} | {new[k]['verdict']} | {cap(old[k])} | {cap(new[k])} |")
    rs = collections.Counter(man[k[0]]["pset"] + "|" + k[1] for k in keys
                             if old.get(k) and new.get(k) and old[k]["verdict"] == new[k]["verdict"] == "RACE"
                             and old[k]["reports"] != new[k]["reports"])
    print(f"\nRACE in both with a different report set, per suite|mode: {dict(sorted(rs.items()))}")
    print(f"\nDIRECTION CHECK (RACE in X1, CLEAN in X1b): {len(bad)}" + "".join(f"\n- {k[0]} {k[1]}" for k in bad))
    print(f"\n(id, mode) keys: X1 {len(old)}, X1b {len(new)}; changed {len(changed)}")
    sys.exit(3 if bad else 0)


if __name__ == "__main__":
    main()

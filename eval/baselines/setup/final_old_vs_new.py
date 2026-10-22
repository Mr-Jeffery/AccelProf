#!/usr/bin/env python3
"""X1: collapsed cuVein verdicts per suite and mode, the superseded 2026-09-22 file against the merged
X1 file (RACE > CLEAN > TIMEOUT > ERROR per (id, mode), make_tables' order), and the moves.
  final_old_vs_new.py > eval/results/final/old_vs_new.md"""
import csv, collections
ORDER = ("RACE", "CLEAN", "TIMEOUT", "ERROR"); MODES = ["vector-clock", "scalar-clock"]
man = {r['id']: r for r in csv.DictReader(open('eval/baselines/manifest.csv'))}
def load(p):
    per = collections.defaultdict(list)
    for r in csv.DictReader(open(p)):
        if r['id'] not in man: continue
        for m in ([r['mode']] if r['mode'] else MODES): per[(r['id'], m)].append(r['verdict'])
    return {k: next((v for v in ORDER if v in vs), vs[0]) for k, vs in per.items()}
old = load('eval/results/superseded_baselines-cuvein-2026-09-22.csv'); new = load('eval/results/baselines-cuvein.csv')
print("| suite | mode | old (2026-09-22) RACE / CLEAN / TIMEOUT / ERROR | new (X1) RACE / CLEAN / TIMEOUT / ERROR | (id, mode) whose verdict changed |")
print("|---|---|---|---|---|")
for p in ["P1", "P3", "P4", "P5", "P6", "P7", "P9", "PI"]:
    ids = [i for i in man if man[i]['pset'] == p]
    for m in MODES:
        co = collections.Counter(old.get((i, m), '—') for i in ids); cn = collections.Counter(new.get((i, m), '—') for i in ids)
        ch = sum(1 for i in ids if old.get((i, m)) != new.get((i, m)))
        f = lambda c: " / ".join(str(c[v]) for v in ORDER) + (f" (+{c['—']} no row)" if c['—'] else "")
        print(f"| {p} | {m} | {f(co)} | {f(cn)} | {ch} |")
moves = collections.Counter((man[i]['pset'], m, old.get((i, m), '—'), new.get((i, m))) for (i, m) in new if old.get((i, m)) != new.get((i, m)))
print("\n| suite | mode | old → new | (id, mode) |\n|---|---|---|---|")
for k in sorted(moves): print(f"| {k[0]} | {k[1]} | {k[2]} → {k[3]} | {moves[k]} |")

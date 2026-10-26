#!/usr/bin/env python3
"""X3 (c): coverage of X1b's merged results. Reads only (stdlib, CPU).

Writes under eval/results/final-tables/: coverage_verdicts.md, coverage_residuals.csv,
coverage_partial_rows.csv, coverage_nodehours.md.  Run from the worktree root:
    python3 -I eval/results/final-tables/coverage.py

Partial-row rule (X1_FOLLOW.md Part 4): a run killed by OOM or by the time limit keeps every verdict it
produced; its note reads  partial: <OOM|TIMEOUT> after <N> of <M> kernels, <wall> s, cap=<s>
  N = the row's nkernels, M = nkernels of a complete (RACE/CLEAN, not partial) row of the same program
  in any mode of the merged file, "?" when there is none.
Applied here to the rows of the merged file (X1b did not apply it to its shard CSVs, FINAL_SWEEP_B.md 1 (j)).
"""
import csv, os, re, collections, statistics as st

ROOT = os.getcwd()
R = os.path.join(ROOT, "eval", "results")
FB = os.path.join(R, "final-b")
OUT = os.path.join(R, "final-tables")
rows = []
n_file_rows = sum(1 for _ in open(os.path.join(FB, "merged", "baselines-cuvein.csv"))) - 1
for _r in csv.DictReader(open(os.path.join(FB, "merged", "baselines-cuvein.csv"), newline="")):
    if _r["mode"] == "":  # the 16 never-run needs-sm90 programs have one row with a blank mode: it stands for both
        for _m in ("vector-clock", "scalar-clock"):
            rows.append(dict(_r, mode=_m))
    else:
        rows.append(_r)
n_blank_expanded = sum(1 for r in rows if r["verdict"] == "ERROR" and "missing-exe" in r.get("notes", "")) // 2
diag = {(r["id"], r["mode"]): r for r in csv.DictReader(open(os.path.join(FB, "merged", "baselines-diagnose.csv"), newline=""))}


def note(r, key):
    m = re.search(r"(?:^|;)" + key + r"=([^;]*)", r.get("notes", ""))
    return m.group(1) if m else None


RANK = {"RACE": 0, "CLEAN": 1, "TIMEOUT": 2, "ERROR": 3}
by = collections.defaultdict(list)
for r in rows:
    by[(r["id"], r["mode"])].append(r)
coll = {k: min((r["verdict"] for r in v), key=lambda x: RANK.get(x, 9)) for k, v in by.items()}
pset = {r["id"]: r["pset"] for r in rows}

# 1. verdicts per suite and mode
cnt = collections.Counter((pset[i], m, v) for (i, m), v in coll.items())
suites = sorted({s for s, _, _ in cnt})
with open(os.path.join(OUT, "coverage_verdicts.md"), "w") as f:
    f.write("| suite | mode | ids | RACE | CLEAN | TIMEOUT | ERROR |\n|---|---|---|---|---|---|---|\n")
    tot = collections.Counter()
    for s in suites:
        for m in ("vector-clock", "scalar-clock"):
            c = [cnt[(s, m, v)] for v in ("RACE", "CLEAN", "TIMEOUT", "ERROR")]
            f.write(f"| {s} | {m} | {sum(c)} | " + " | ".join(map(str, c)) + " |\n")
            for v, x in zip(("RACE", "CLEAN", "TIMEOUT", "ERROR"), c):
                tot[(m, v)] += x
    for m in ("vector-clock", "scalar-clock"):
        c = [tot[(m, v)] for v in ("RACE", "CLEAN", "TIMEOUT", "ERROR")]
        f.write(f"| all | {m} | {sum(c)} | " + " | ".join(map(str, c)) + " |\n")
    ids = {i for i, _ in coll}
    f.write(f"\nids: {len(ids)}; (id, mode) keys: {len(coll)}; CSV rows in file: {n_file_rows} (blank-mode rows expanded to both modes for the key counts)\n")

# 2. residual keys (collapsed verdict not RACE/CLEAN)
res = []
for (i, m), v in sorted(coll.items()):
    if v in ("TIMEOUT", "ERROR"):
        d = diag.get((i, m), {})
        rs = by[(i, m)]
        res.append({"id": i, "mode": m, "verdict": v, "cause_class": d.get("cause", "missing"),
                    "peak_mb": d.get("peak_mb", ""), "wall_s": d.get("wall_s", ""),
                    "caps": ",".join(sorted({note(r, "cap") or "?" for r in rs})),
                    "nreps": len(rs), "evidence": d.get("evidence", "")})
with open(os.path.join(OUT, "coverage_residuals.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, list(res[0]))
    w.writeheader()
    w.writerows(res)

# 3. partial rows under the rule
complete = {}
for r in rows:
    if r["verdict"] in ("RACE", "CLEAN") and "partial" not in r.get("notes", "") and note(r, "nkernels"):
        complete.setdefault(r["id"], int(note(r, "nkernels")))
part = []
for r in rows:
    n = r.get("notes", "")
    kind = None
    if r["verdict"] == "TIMEOUT" or r["rc"] == "124":
        kind = "TIMEOUT"
    elif "partial(" in n or "incomplete-trace" in n:
        kind = "OOM" if (r["rc"] in ("1", "137") or "Killed" in n or "rc=1" in n) else "TIMEOUT"
    if not kind:
        continue
    nk = note(r, "nkernels")
    if nk is None:
        m_ = re.search(r"nkernels=(\d+)", n)
        nk = m_.group(1) if m_ else "missing"
    part.append({"id": r["id"], "mode": r["mode"], "rep": r["rep"], "verdict": r["verdict"],
                 "rule_note": f"partial: {kind} after {nk} of {complete.get(r['id'], '?')} kernels, {r['wall_s']} s, cap={note(r, 'cap')}",
                 "peak_mb": r["peak_mb"], "node": note(r, "node") or "", "raw_notes": n})
with open(os.path.join(OUT, "coverage_partial_rows.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, list(part[0]))
    w.writeheader()
    w.writerows(part)

# 4. node-hours from sacct.txt (JobID|name|node|start|end|elapsed_s|state), x1b-* records
nh = collections.defaultdict(float)
nn = collections.defaultdict(int)
nodes = collections.defaultdict(set)
for line in open(os.path.join(FB, "sacct.txt")):
    p = line.rstrip("\n").split("|")
    if len(p) < 7 or "." in p[0]:
        continue
    try:
        e = float(p[5])
    except ValueError:
        continue
    nh[p[1]] += e / 3600.0
    nn[p[1]] += 1
    nodes[p[1]].add(p[2])
with open(os.path.join(OUT, "coverage_nodehours.md"), "w") as f:
    f.write("| job name | records | node-hours | nodes |\n|---|---|---|---|\n")
    for k in sorted(nh):
        f.write(f"| {k} | {nn[k]} | {nh[k]:.1f} | {len(nodes[k] - {'None assigned', ''})} |\n")
    f.write(f"| all | {sum(nn.values())} | {sum(nh.values()):.1f} | |\n")
for fn in ("coverage_verdicts.md", "coverage_nodehours.md"):
    print("##", fn)
    print(open(os.path.join(OUT, fn)).read())
print("## residual keys:", len(res))
for r in res:
    print(r["id"], r["mode"], r["verdict"], r["cause_class"], r["caps"], r["nreps"], r["peak_mb"])
print("## partial rows:", len(part))
c = collections.Counter((p["id"], p["mode"], p["rule_note"].split(" after ")[0]) for p in part)
for p in part:
    if "needs" in p["raw_notes"]:
        continue
    print(p["id"][:50], p["mode"], p["rep"], p["verdict"], p["rule_note"], p["peak_mb"], p["node"])

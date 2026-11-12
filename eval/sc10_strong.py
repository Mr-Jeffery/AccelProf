#!/usr/bin/env python3
"""X14: data-race pairs and unordered-strong-conflict pairs on SuperCollider's ten HeCBench programs,
from the X11 confirm files (eval/x_logs/x11/**/confirm/*.json; X11 = eval/results/sc_native/summary.csv).

Counting rule (eval/baselines/run_cuvein.py split_raw): a confirm file's `raw` list = the RACE reports
(verdict != SC, conflict_class DR) -> "data-race pairs" = len(raw); `raw_sc` = reports with verdict SC
(conflict_class SC) -> "unordered-strong-conflict pairs" = len(raw_sc).  One pair = one entry (a_pc, b_pc, space,
race_type, deduplicated per run).  Runs without a confirm file: partial.json report_ids (class not recorded),
or, for the four programs X11 kept the old rows for, the old cap-84600 CSV row.

usage: sc10_strong.py [--root REPO_ROOT] [--old-ref origin/eval/cap-84600] > table.md
"""
import argparse, csv, glob, io, json, os, subprocess

PROGS = ["atomicCAS", "dxtc2", "knn", "tridiagonal", "expdist", "overlap", "fpc", "gpp", "crs", "mr"]
LABEL = dict(atomicCAS="racy", dxtc2="racy", knn="racy", tridiagonal="racy", expdist="racy",
             overlap="race-free", fpc="race-free", gpp="race-free", crs="race-free", mr="race-free")
CFGS = ["S2*", "scalar", "vector"]
X11 = "eval/x_logs/x11"


def rel(root, x):
    return os.path.relpath(x, root).replace(os.sep, "/")


def confirm_files(root, cfg, p):
    if cfg == "S2*":
        g = [f"{X11}/stageA-chain-r{r}-{p}/confirm/X11-{p}__cuvein__collector-only.json" for r in (1, 2, 3)]
        return [x for x in g if os.path.exists(os.path.join(root, x))]
    m = {"scalar": "scalar-clock", "vector": "vector-clock"}[cfg]
    g = sorted(glob.glob(os.path.join(root, f"{X11}/stageB/x11b-{m}-{p}-r*/confirm/X11-{p}__cuvein__{m}.json")))
    g += sorted(glob.glob(os.path.join(root, f"{X11}/stageB/x11smoke-{m}-{p}-r*/confirm/X11-{p}__cuvein__{m}.json")))
    return [rel(root, x) for x in g]


def partial(root, cfg, p):
    m = {"scalar": "scalar-clock", "vector": "vector-clock"}.get(cfg)
    if not m:
        return None
    for f in sorted(glob.glob(os.path.join(root, f"{X11}/stageB/x11b-{m}-{p}-r*/partial.json"))):
        pd = json.load(open(f))["partial_dirs"][0]
        return rel(root, f), pd["reports"], pd.get("reason", ""), pd["kernel_jsons"]
    return None


def old_rows(old_ref, cfg, p, root):
    m = {"scalar": "scalar-clock", "vector": "vector-clock"}[cfg]
    path = "eval/results/cap-84600/baselines-cuvein.csv"
    txt = subprocess.run(["git", "-C", root, "show", f"{old_ref}:{path}"], capture_output=True, text=True,
                         check=True).stdout
    return path, [r for r in csv.DictReader(io.StringIO(txt)) if r["id"] == f"P9-{p}-cuda" and r["mode"] == m]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--old-ref", default="origin/eval/cap-84600")
    a = ap.parse_args()
    cell, src = {}, {}
    for p in PROGS:
        for cfg in CFGS:
            files = confirm_files(a.root, cfg, p)
            if files:
                dr, sc = [], []
                for f in files:
                    d = json.load(open(os.path.join(a.root, f)))
                    assert all(r.get("conflict_class") == "DR" and r.get("verdict") != "SC" for r in d["raw"])
                    assert all(r.get("verdict") == "SC" for r in d["raw_sc"])
                    dr.append(len(d["raw"])); sc.append(len(d["raw_sc"]))
                cell[p, cfg], src[p, cfg] = ("confirm", dr, sc, ""), files
                continue
            pt = partial(a.root, cfg, p)
            if pt:
                f, n, reason, nk = pt
                cell[p, cfg] = ("partial", [n], None, f"capped; {nk} kernels analysed; {reason or 'prefix'}")
                src[p, cfg] = [f]
                continue
            if cfg != "S2*":
                path, rows = old_rows(a.old_ref, cfg, p, a.root)
                if rows:
                    vs = {r["verdict"] for r in rows}
                    assert vs in ({"CLEAN"}, {"TIMEOUT"}) and all(r["reports_dedup"] == "0" for r in rows), rows
                    cell[p, cfg] = ("oldcsv" if vs == {"CLEAN"} else "oldto", [0] * len(rows), None,
                                    "old row " + "/".join(sorted(vs)) + f", wall_s {rows[0]['wall_s']}")
                    src[p, cfg] = [f"{a.old_ref}:{path} (P9-{p}-cuda, {len(rows)} rows)"]
                    continue
            cell[p, cfg], src[p, cfg] = ("none", [], None, ""), []

    def fmt(v):
        return str(v[0]) if len(set(v)) == 1 else "/".join(map(str, v))

    print("| program (label) | " + " | ".join(f"{c} races | {c} strong" for c in CFGS) + " |")
    print("|---|" + "---|" * (2 * len(CFGS)))
    for p in PROGS:
        cols = []
        for cfg in CFGS:
            kind, dr, sc, note = cell[p, cfg]
            if kind == "confirm":
                cols += [fmt(dr), fmt(sc)]
            elif kind == "partial":
                cols += [f"{dr[0]}†", "n/a†"]
            elif kind == "oldto":
                cols += ["n/a†", "n/a†"]
            elif kind == "oldcsv":
                cols += ["0§", "n/a§"]
            else:
                cols += ["n/a", "n/a"]
        print(f"| {p} ({LABEL[p]}) | " + " | ".join(cols) + " |")
    print()
    for cfg in CFGS:
        sc_only, race, rs = [], [], []
        for p in PROGS:
            kind, dr, sc, _ = cell[p, cfg]
            d, s = (max(dr) if dr else 0), (max(sc) if sc else 0)
            if d > 0: race.append(p)
            if d > 0 or s > 0: rs.append(p)
            if s > 0 and d == 0: sc_only.append(p)
        f = lambda L, lab: [p for p in L if LABEL[p] == lab]
        print(f"LINE {cfg}: strong-only programs {sc_only or 'none'}; races alone: racy {len(f(race,'racy'))}/5, "
              f"race-free {len(f(race,'race-free'))}/5 {f(race,'race-free')}; races or strong: "
              f"racy {len(f(rs,'racy'))}/5, race-free {len(f(rs,'race-free'))}/5 {f(rs,'race-free')}")
    print()
    for p in PROGS:
        for cfg in CFGS:
            kind, dr, sc, note = cell[p, cfg]
            print(f"SRC {p} {cfg} [{kind}] dr={dr} sc={sc} {note}: " + "; ".join(src[p, cfg]))


main()

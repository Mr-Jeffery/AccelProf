#!/usr/bin/env python3
"""X1: the tables of eval/FINAL_SWEEP.md from the merged CSV (markdown on stdout).

  .env/bin/python eval/baselines/setup/final_report_tables.py \
      --merged eval/results/baselines-cuvein.csv --first eval/results/final \
      --long eval/results/final-long,eval/results/final-long-sc --diagnose eval/results/baselines-diagnose.csv \
      [--sacct <file of `sacct -X -n -P -o JobID,JobName,NodeList,Start,End,ElapsedRaw,State`>]

Verdicts per (id, mode) are collapsed as make_tables.load_runs does (any RACE > any CLEAN >
TIMEOUT > ERROR); a row without a mode (missing-exe: the 16 sm_90 cuHadron targets) counts for
both modes. Coverage: every manifest id of the eight psets must have a row for both modes.
"""
import argparse
import collections
import csv
import glob
import re
import statistics

PSETS = ["P1", "P3", "P4", "P5", "P6", "P7", "P9", "PI"]
MODES = ["vector-clock", "scalar-clock"]
ORDER = ("RACE", "CLEAN", "TIMEOUT", "ERROR")


def collapse(rows):
    per = collections.defaultdict(list)
    for r in rows:
        for m in ([r["mode"]] if r["mode"] else MODES):
            per[(r["id"], m)].append(r)
    out = {}
    for k, reps in per.items():
        vs = [r["verdict"] for r in reps]
        out[k] = dict(verdict=next((v for v in ORDER if v in vs), vs[0]), reps=reps)
    return out


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _cap(notes):
    m = re.search(r"cap=(\d+)", notes or "")
    return int(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--merged", required=True)
    ap.add_argument("--manifest", default="eval/baselines/manifest.csv")
    ap.add_argument("--first", required=True)
    ap.add_argument("--long", default="")
    ap.add_argument("--diagnose", default="")
    ap.add_argument("--sacct", default="")
    a = ap.parse_args()
    man = [r for r in csv.DictReader(open(a.manifest, newline="")) if r["pset"] in PSETS]
    rows = list(csv.DictReader(open(a.merged, newline="")))
    col = collapse(rows)
    first = collapse([r for f in sorted(glob.glob(f"{a.first}/baselines-cuvein-shard*.csv"))
                      for r in csv.DictReader(open(f, newline=""))])
    longr = collapse([r for d in (a.long.split(",") if a.long else []) if d
                      for f in sorted(glob.glob(f"{d}/baselines-cuvein-shard*.csv"))
                      for r in csv.DictReader(open(f, newline=""))])

    # coverage
    missing = [(m["id"], mode) for m in man for mode in MODES if (m["id"], mode) not in col]
    extra = sorted({r["id"] for r in rows} - {m["id"] for m in man})
    print(f"Coverage: {len(man)} manifest ids x 2 modes; missing (id, mode): {len(missing)}; "
          f"ids in the CSV not in the manifest: {len(extra)}; CSV rows {len(rows)}.\n")
    for k in missing[:20]:
        print(f"- missing {k}")

    # per-suite table
    caps = collections.defaultdict(set)
    for r in rows:
        c = _cap(r["notes"])
        if c:
            caps[(r["pset"], r["mode"])].add(c)
    print("| suite | programs | rows | mode | CLEAN | RACE | TIMEOUT | ERROR | cap (s) |")
    print("|---|---|---|---|---|---|---|---|---|")
    tot = collections.Counter()
    for p in PSETS:
        ids = [m["id"] for m in man if m["pset"] == p]
        nrows = sum(1 for r in rows if r["pset"] == p)
        for j, mode in enumerate(MODES):
            c = collections.Counter(col[(i, mode)]["verdict"] for i in ids if (i, mode) in col)
            for v in ORDER:
                tot[(mode, v)] += c[v]
            cp = "/".join(str(x) for x in sorted(caps[(p, mode)])) or "—"
            print(f"| {p if j == 0 else ''} | {len(ids) if j == 0 else ''} | {nrows if j == 0 else ''} "
                  f"| {mode} | {c['CLEAN']} | {c['RACE']} | {c['TIMEOUT']} | {c['ERROR']} | {cp} |")
    for j, mode in enumerate(MODES):
        print(f"| {'all' if j == 0 else ''} | {len(man) if j == 0 else ''} | {len(rows) if j == 0 else ''} "
              f"| {mode} | {tot[(mode, 'CLEAN')]} | {tot[(mode, 'RACE')]} | {tot[(mode, 'TIMEOUT')]} "
              f"| {tot[(mode, 'ERROR')]} | |")

    # reason classes of the TIMEOUT/ERROR (id, mode) keys
    if a.diagnose:
        diag = {(r["id"], r["mode"]): r for r in csv.DictReader(open(a.diagnose, newline=""))}
        ps = {m["id"]: m["pset"] for m in man}
        cls = collections.Counter()
        unc = []
        for (i, mode), v in col.items():
            if v["verdict"] in ("TIMEOUT", "ERROR"):
                d = diag.get((i, mode))
                reason = d["cause"] if d else ("missing-exe" if "missing-exe" in v["reps"][0]["notes"]
                                               else "unclassified")
                if not d and reason == "unclassified":
                    unc.append((i, mode))
                cls[(ps.get(i, "?"), mode, v["verdict"], reason)] += 1
        print("\n| suite | mode | verdict | reason class | (id, mode) |")
        print("|---|---|---|---|---|")
        for k in sorted(cls):
            print(f"| {k[0]} | {k[1]} | {k[2]} | {k[3]} | {cls[k]} |")
        for k in unc[:20]:
            print(f"- unclassified {k}")

    # long pass
    if longr:
        print("\n| id | mode | first pass (1,200 s): verdict, rep walls (s) | long pass (5,400 s): verdict | rep walls (s) | median wall (s) | peak MB | node |")
        print("|---|---|---|---|---|---|---|---|")
        fin = collections.Counter()
        for k in sorted(longr, key=lambda k: (k[1] != "vector-clock", k[0])):
            i, mode = k
            fv = first.get(k)
            lv = longr[k]
            fw = ", ".join(r["wall_s"] for r in fv["reps"]) if fv else "—"
            lw = [_f(r["wall_s"]) for r in lv["reps"]]
            lws = ", ".join(r["wall_s"] for r in lv["reps"])
            med = statistics.median([x for x in lw if x is not None]) if any(x is not None for x in lw) else None
            pk = max((_f(r["peak_mb"]) or 0) for r in lv["reps"])
            node = re.search(r"node=(c\d+)", ";".join(r["notes"] for r in lv["reps"]))
            fin[(mode, lv["verdict"])] += 1
            print(f"| {i} | {mode} | {fv['verdict'] if fv else '—'}: {fw} | {lv['verdict']} | {lws} | "
                  f"{med if med is not None else '—'} | {pk:,.0f} | {node.group(1) if node else '—'} |")
        for mode in MODES:
            n = sum(c for (m, v), c in fin.items() if m == mode)
            if n:
                print(f"\nLong pass, {mode}: {n} ids; " +
                      ", ".join(f"{v} {fin[(mode, v)]}" for v in ORDER if fin[(mode, v)]))

    # node-hours
    if a.sacct:
        tot_s = collections.Counter()
        nodes = collections.defaultdict(set)
        t0, t1 = {}, {}
        for ln in open(a.sacct):
            f = ln.rstrip("\n").split("|")
            if len(f) < 7 or not f[5].isdigit():
                continue
            jid, name, node, start, end, el, st = f[:7]
            tot_s[name] += int(el)
            nodes[name].add(node)
            if start and start != "Unknown":
                t0[name] = min(t0.get(name, start), start)
            if end and end not in ("Unknown", "None"):
                t1[name] = max(t1.get(name, end), end)
        print("\n| job name | node-hours | nodes | first start | last end |")
        print("|---|---|---|---|---|")
        for n in sorted(tot_s):
            print(f"| {n} | {tot_s[n] / 3600:.1f} | {len(nodes[n])} | {t0.get(n, '')} | {t1.get(n, '')} |")
        print(f"| all | {sum(tot_s.values()) / 3600:.1f} | {len(set().union(*nodes.values()))} | "
              f"{min(t0.values()) if t0 else ''} | {max(t1.values()) if t1 else ''} |")


if __name__ == "__main__":
    main()

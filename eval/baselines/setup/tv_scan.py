#!/usr/bin/env python3
"""M4: tv_violation census over the X1b stores (BeeGFS: run on a compute node).

Scan (one shard):   tv_scan.py scan --shard I --nshards N --out DIR
Aggregate (CPU):    tv_scan.py agg --in DIR --out eval/results/tv-counts

scan walks <store>/<id>/<mode>/kernel_*.json and writes DIR/shard_I.csv, one row per kernel JSON:
store, id, mode, file, bytes, complete (file ends in '}'), tv (the tv_violation string, '' if the
key is absent or empty), top (for a firing: the file's top-level short string fields as JSON).
It does not parse the large files: it searches the bytes for the key (mmap), and json-loads only a
file that has one.
"""
import argparse
import collections
import csv
import glob
import gzip
import json
import mmap
import os
import re
import sys

ROOT = "/mnt/beegfs/fzheng4/cuvein_traces"
# store name -> pass label (FINAL_SWEEP_B.md section 1: first pass and PI pass share final-2026-11)
STORES = [("final-2026-11", "first+PI"), ("final-2026-11-long", "5400s-vc"),
          ("final-2026-11-long-sc", "5400s-sc"), ("final-2026-11-24h-vc", "84600s-vc"),
          ("final-2026-11-24h-sc", "84600s-sc"), ("final-2026-11-dryrun", "dryrun")]
MODES = ("vector-clock", "scalar-clock")
TV_RE = re.compile(rb'"tv_violation"\s*:\s*"((?:[^"\\]|\\.)*)"')
FIELDS = ["store", "id", "mode", "file", "bytes", "complete", "tv", "top"]


def scan_file(path):
    size = os.path.getsize(path)
    if size == 0:
        return size, 0, "", ""
    with open(path, "rb") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            tail = bytes(mm[max(0, size - 64):]).strip()
            complete = int(tail.endswith(b"}"))
            pos = mm.find(b'"tv_violation"')
            tv = ""
            if pos >= 0:
                m = TV_RE.match(mm[pos:pos + 65536])
                if m:
                    tv = json.loads(b'"' + m.group(1) + b'"')
                else:
                    tv = "<unparsed tv_violation>"
    top = ""
    if tv:
        try:
            t = json.load(open(path))
            top = json.dumps({k: v for k, v in t.items()
                              if isinstance(v, (str, int, float)) and len(str(v)) < 300},
                             sort_keys=True)
        except Exception as e:
            top = "unreadable: %s" % e
    return size, complete, tv, top


def scan(a):
    items = []
    for s, _ in STORES:
        for d in sorted(glob.glob(f"{ROOT}/{s}/*/meta.json")):
            items.append((s, os.path.basename(os.path.dirname(d))))
    mine = [x for i, x in enumerate(items) if i % a.nshards == a.shard]
    os.makedirs(a.out, exist_ok=True)
    with open(f"{a.out}/shard_{a.shard}.csv", "w", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(FIELDS)
        for s, i in mine:
            for mode in MODES:
                for kj in sorted(glob.glob(f"{ROOT}/{s}/{i}/{mode}/kernel_*.json")):
                    try:
                        size, complete, tv, top = scan_file(kj)
                    except OSError as e:
                        size, complete, tv, top = -1, 0, "", f"oserror: {e}"
                    w.writerow([s, i, mode, os.path.basename(kj), size, complete, tv, top])
            fo.flush()
    print(f"shard {a.shard}: {len(mine)} (store, id) dirs of {len(items)}", flush=True)


def check_name(tv):
    m = re.match(r"(TV-[A-Za-z-]+)", tv)
    return m.group(1) if m else ("<none>" if not tv else "<other>")


# dedupe preference: the pass that owns a rerun (FINAL_SWEEP_B.md 1(i)) first
PREF = {"final-2026-11-24h-vc": 0, "final-2026-11-24h-sc": 0, "final-2026-11-long": 1,
        "final-2026-11-long-sc": 1, "final-2026-11": 2}
CHECKS = ["TV-seq-monotonic", "TV-barrier-overfill", "TV-barrier-completion-order",
          "TV-expected-nonzero-multiwarp", "TV-record-after-exit", "TV-barrier-pending-at-end",
          "TV-syncwarp-completion-order", "TV-syncwarp-pending-at-end"]


def agg(a):
    rows = []
    for f in sorted(glob.glob(f"{a.inp}/shard_*.csv")):
        rows += list(csv.DictReader(open(f, newline="")))
    os.makedirs(a.out, exist_ok=True)
    bystore = collections.Counter()
    for r in rows:
        bystore[(r["store"], r["mode"])] += 1
    # per (store, id, mode)
    sim = collections.defaultdict(lambda: [0, 0, 0, 0])
    for r in rows:
        k = (r["store"], r["id"], r["mode"])
        sim[k][0] += 1
        sim[k][1] += bool(r["tv"])
        sim[k][2] += int(r["complete"]) == 0
        sim[k][3] += int(r["bytes"])
    with open(f"{a.out}/tv_by_store_id_mode.csv", "w", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(["store", "pass", "suite", "id", "mode", "kernel_jsons", "tv_nonempty",
                    "incomplete_files", "bytes"])
        lab = dict(STORES)
        for (s, i, m), v in sorted(sim.items()):
            w.writerow([s, lab[s], i.split("-")[0], i, m] + v)
    # dedupe on (id, mode, kernel file); keep the preferred store's copy
    best = {}
    dup = collections.Counter()
    differ = []
    for r in rows:
        if r["store"] == "final-2026-11-dryrun":
            continue
        k = (r["id"], r["mode"], r["file"])
        if k in best:
            dup[(r["mode"], r["store"])] += 1
            o = best[k]
            if bool(o["tv"]) != bool(r["tv"]) or o["tv"] != r["tv"]:
                differ.append((k, o["store"], o["tv"], r["store"], r["tv"]))
            if PREF[r["store"]] < PREF[o["store"]]:
                best[k] = r
        else:
            best[k] = r
    # counts per suite, mode, check
    cnt = collections.defaultdict(lambda: collections.Counter())
    for (i, m, f), r in best.items():
        c = cnt[(i.split("-")[0], m)]
        c["kernels"] += 1
        if not r["tv"]:
            c["empty"] += 1
        else:
            c[check_name(r["tv"])] += 1
        if int(r["complete"]) == 0:
            c["incomplete_files"] += 1
    with open(f"{a.out}/tv_counts_by_suite_mode.csv", "w", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(["suite", "mode", "kernels_recorded", "empty_tv_violation", "nonempty"]
                   + CHECKS + ["other", "incomplete_files"])
        tot = collections.defaultdict(collections.Counter)
        for (su, m), c in sorted(cnt.items()):
            nonempty = c["kernels"] - c["empty"]
            other = nonempty - sum(c[x] for x in CHECKS)
            w.writerow([su, m, c["kernels"], c["empty"], nonempty] + [c[x] for x in CHECKS]
                       + [other, c["incomplete_files"]])
            for k, v in c.items():
                tot[("ALL", m)][k] += v
        for (su, m), c in sorted(tot.items()):
            nonempty = c["kernels"] - c["empty"]
            other = nonempty - sum(c[x] for x in CHECKS)
            w.writerow([su, m, c["kernels"], c["empty"], nonempty] + [c[x] for x in CHECKS]
                       + [other, c["incomplete_files"]])
    with open(f"{a.out}/tv_firings.csv", "w", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(["suite", "id", "mode", "file", "store", "check", "tv_violation", "top"])
        for (i, m, f), r in sorted(best.items()):
            if r["tv"]:
                w.writerow([i.split("-")[0], i, m, f, r["store"], check_name(r["tv"]),
                            r["tv"], r["top"]])
    with open(f"{a.out}/tv_store_counts.csv", "w", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(["store", "pass", "mode", "kernel_jsons", "duplicates_dropped"])
        lab = dict(STORES)
        for (s, m), n in sorted(bystore.items()):
            w.writerow([s, lab[s], m, n, dup[(m, s)]])
        w.writerow(["DEDUP_DIFFER", "", "", len(differ), ""])
    with gzip.open(f"{a.out}/tv_per_kernel.csv.gz", "wt", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(["store", "id", "mode", "file", "bytes", "complete", "tv"])
        for r in rows:
            w.writerow([r["store"], r["id"], r["mode"], r["file"], r["bytes"], r["complete"], r["tv"]])
    print(f"{len(rows)} rows, {len(best)} unique kernels, {sum(dup.values())} duplicates dropped, "
          f"{len(differ)} duplicate pairs differing in tv")
    for d in differ[:20]:
        print("  differ", d)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("scan")
    s.add_argument("--shard", type=int, required=True)
    s.add_argument("--nshards", type=int, required=True)
    s.add_argument("--out", required=True)
    g = sp.add_parser("agg")
    g.add_argument("--in", dest="inp", required=True)
    g.add_argument("--out", required=True)
    a = ap.parse_args()
    {"scan": scan, "agg": agg}[a.cmd](a)

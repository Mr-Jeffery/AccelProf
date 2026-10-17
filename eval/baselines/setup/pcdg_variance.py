#!/usr/bin/env python3
"""X5 (2): how much does a program's PC dependency graph change between two recordings of it?

For every (program, mode) with two or more complete recordings in the T20 parity stores
(`t20-parity` = the first T20 build f9d2996a, `t20-parity2` = the final one 391cf9cc) and the X1
stores (`final-2026-10` and the 5,400 s / 24 h re-recordings), the Jaccard overlap, over every
pair of its recordings, of

  * the edge sets: {(kernel, ancient pc, current pc)} over the `edges` of all of the recording's
    kernel_N.json (cold-miss edges, which have no ancient pc, excluded);
  * the statically unresolved pair sets: the pairs sync_dominance.analyze judged (one per kernel
    and unordered pc pair, over all launches) for which neither R1 (barrier/warpsync dominance of
    the observed distance) nor R3 (a PC-level chain) held in some launch -- the pairs left to the
    dynamic leg, i.e. what the sync pass has to decide.

and, as a labelled extra, whether the two recordings give the same RACE report ids (the single-run
verdict). A kernel is "<dot basename>::<mangled name>", so one program's kernels from two stores
line up by name. Jaccard of two empty sets is 1.0 and is flagged `empty`.

A recording is complete when meta.json says its mode was saved, not partial, with a rep that
finished (`complete`, not timed out, nkernels > 0); a killed or timed-out recording holds a prefix
of the kernels and would differ for that reason alone, so it is listed and left out. X1 kept one
recording of the three reps per mode; the other two exist only as walls in meta.json.

  plan      the recordings of the stores, their completeness, the (program, mode) groups
  collect   analyze one shard of the recordings (SLURM array task), append to a jsonl
  report    Jaccard tables and a pair-level csv
"""
import argparse
import collections
import csv
import glob
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import x5_common as xc                                # noqa: E402
from x5_common import rc                              # noqa: E402

ROOT = "/mnt/beegfs/fzheng4/cuvein_traces"
STORES = ("t20-parity", "t20-parity2", "final-2026-10", "final-2026-10-long",
          "final-2026-10-long-sc", "final-2026-10-24h-vc", "final-2026-10-24h-sc")


def completeness(meta, mode, mdir):
    """-> '' if the recording is complete, else the reason it is not."""
    mm = (meta.get("modes") or {}).get(mode)
    if meta.get("error"):
        return "meta error: " + str(meta["error"])[:60]
    if not mm:
        return "mode not recorded"
    if not mm.get("saved"):
        return "not saved"
    if mm.get("partial"):
        return "partial"
    reps = mm.get("reps") or []
    if not any(r.get("complete", not r.get("timed_out")) and not r.get("timed_out")
               and r.get("nkernels", 0) > 0 for r in reps):
        return "no finished rep"
    if meta.get("status") not in (None, "done"):
        return f"status={meta.get('status')}"
    if not os.path.isdir(mdir) or not any(n.startswith("kernel_") for n in os.listdir(mdir)):
        return "no kernel JSON"
    return ""


def cmd_plan(a):
    root = Path(a.root)
    recs = []
    for store in STORES:
        if not (root / store).is_dir():
            print(f"store {store}: missing")
            continue
        for pid in sorted(os.listdir(root / store)):
            mp = root / store / pid / "meta.json"
            if not mp.exists():
                continue
            meta = json.loads(mp.read_text())
            for mode in xc.MODES:
                mdir = str(root / store / pid / mode)
                why = completeness(meta, mode, mdir)
                rt = meta.get("runtime") or {}
                recs.append({"id": pid, "suite": xc.suite_of(pid), "mode": mode, "store": store,
                             "dir": mdir, "dots": str(root / store / pid / "dots"),
                             "complete": not why, "why": why, "node": meta.get("node"),
                             "libsanalyzer": rt.get("libsanalyzer"), "hb_dump": meta.get("hb_dump"),
                             "kbytes": sum(e.stat().st_size for e in os.scandir(mdir)
                                           if e.name.startswith("kernel_"))
                             if os.path.isdir(mdir) else 0})
    groups = collections.defaultdict(list)
    for r in recs:
        if r["complete"]:
            groups[(r["id"], r["mode"])].append(r)
    keep = {k for k, v in groups.items() if len(v) >= 2}
    sel = [r for r in recs if r["complete"] and (r["id"], r["mode"]) in keep]
    excl = [r for r in recs if not r["complete"] and (r["id"], r["mode"]) in
            {(x["id"], x["mode"]) for x in sel}]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps({"recordings": sel, "excluded": excl,
                                       "stores": list(STORES)}))
    print(f"{len(recs)} (store, program, mode) entries; {len(keep)} (program, mode) groups with "
          f">=2 complete recordings; {len(sel)} recordings selected; {len(excl)} incomplete "
          f"recordings of those groups left out")
    cnt = collections.Counter(k[1] for k in keep)
    print("groups by mode:", dict(cnt))
    print("recordings by store:", dict(collections.Counter(r["store"] for r in sel)))
    print("incomplete, by reason:", dict(collections.Counter(r["why"] for r in excl)))


def analyze_recording(e, a):
    t0 = time.time()

    def work():
        log = xc.PairLog(want_edges=True)
        with xc.Capture(log):
            ids, pcs, raw = rc._analyze_reports(e["dir"], e["dots"])
        race, sc = rc.split_raw(raw)
        und = {}
        for (kid, anc, cur, sp), p in log.pairs.items():
            k = (kid, min(anc, cur), max(anc, cur), sp)
            u = und.setdefault(k, {"cls": set(), "unres": False})
            u["cls"] |= {c or "-" for c in p["cls"]}
            u["unres"] = u["unres"] or p["unresolved"]
        return {"ids": ids, "n_race": len(race), "n_sc": len(sc),
                "edges": sorted(log.edges),
                "judged": len(und),
                "unresolved": sorted([k[0], k[1], k[2], k[3], "+".join(sorted(v["cls"]))]
                                     for k, v in und.items() if v["unres"]),
                "nlaunch": log.nlaunch, "kernels": sorted(log.launches)}

    pay, reason = xc.run_capped(work, a.analysis_timeout, a.mem_gb)
    rec = {k: e[k] for k in ("id", "suite", "mode", "store", "libsanalyzer", "hb_dump", "node",
                             "kbytes")}
    rec.update(reason=reason, elapsed=round(time.time() - t0, 1), host=os.uname().nodename)
    if pay is not None:
        rec.update(pay)
    return rec


def cmd_collect(a):
    plan = json.loads(Path(a.plan).read_text())
    k, n = (int(x) for x in a.shard.split("/"))
    recs = [e for e in plan["recordings"] if not a.only or re.search(a.only, e["id"])]
    mine = xc.lpt_shards(recs, lambda e: e["kbytes"], n)[k]
    out = a.out.format(shard=k)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    done = xc.done_keys(out, lambda r: (r["id"], r["mode"], r["store"]))
    print(f"shard {k}/{n}: {len(mine)} recordings, {len(done)} already done -> {out}", flush=True)
    for i, e in enumerate(mine):
        if (e["id"], e["mode"], e["store"]) in done:
            continue
        rec = analyze_recording(e, a)
        xc.append_jsonl(out, rec)
        print(f"[{i + 1}/{len(mine)}] {e['id']} {e['mode']} {e['store']} "
              f"{rec['reason'] or 'ok'} {rec['elapsed']}s edges={len(rec.get('edges', []))}",
              flush=True)


def jac(a, b):
    if not a and not b:
        return 1.0, True
    return len(a & b) / len(a | b), False


def stats_row(vals):
    if not vals:
        return ["-", "-", "-", "-"]
    return [sum(v == 1.0 for v in vals), f"{min(vals):.4f}", f"{statistics.median(vals):.4f}",
            f"{statistics.mean(vals):.4f}"]


def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def cmd_report(a):
    plan = json.loads(Path(a.plan).read_text())
    recs = []
    for f in sorted(glob.glob(a.inputs)):
        for ln in open(f):
            recs.append(json.loads(ln))
    good = [r for r in recs if not r["reason"]]
    bad = [r for r in recs if r["reason"]]
    groups = collections.defaultdict(list)
    for r in good:
        groups[(r["id"], r["mode"])].append(r)
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    rows = []                                    # one per pair of recordings
    for (pid, mode), rs in sorted(groups.items()):
        rs = sorted(rs, key=lambda r: xc_store_rank(r["store"]))
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                x, y = rs[i], rs[j]
                ex, ey = {tuple(e) for e in x["edges"]}, {tuple(e) for e in y["edges"]}
                ux = {(k[0], k[1], k[2], k[3]): k[4] for k in x["unresolved"]}
                uy = {(k[0], k[1], k[2], k[3]): k[4] for k in y["unresolved"]}
                je, e_empty = jac(ex, ey)
                ju, u_empty = jac(set(ux), set(uy))
                both = set(ux) & set(uy)
                rows.append({
                    "suite": x["suite"], "id": pid, "mode": mode,
                    "store_a": x["store"], "store_b": y["store"],
                    "lib_a": x["libsanalyzer"], "lib_b": y["libsanalyzer"],
                    "edges_a": len(ex), "edges_b": len(ey), "edges_common": len(ex & ey),
                    "jaccard_edges": je, "edges_empty": e_empty,
                    "unres_a": len(ux), "unres_b": len(uy), "unres_common": len(both),
                    "jaccard_unresolved": ju, "unres_empty": u_empty,
                    "class_changed_among_common": sum(ux[k] != uy[k] for k in both),
                    "judged_a": x["judged"], "judged_b": y["judged"],
                    "race_ids_a": len(x["ids"]), "race_ids_b": len(y["ids"]),
                    "jaccard_race_ids": jac(set(x["ids"]), set(y["ids"]))[0],
                    # the id is "<space>:<pc>-<pc>:<RAW|WAR|WAW>"; the type is the first access
                    # order seen in the recording, so compare the pc pairs without it as well
                    "jaccard_race_pcs": jac({i.rsplit(":", 1)[0] for i in x["ids"]},
                                            {i.rsplit(":", 1)[0] for i in y["ids"]})[0],
                    "verdict_a": "RACE" if x["ids"] else "CLEAN",
                    "verdict_b": "RACE" if y["ids"] else "CLEAN"})
    fields = list(rows[0]) if rows else []
    with open(outdir / "pcdg_variance_pairs.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.6f}" if isinstance(v, float) else v) for k, v in r.items()})

    lines = []
    lines.append(f"{len(good)} recordings analysed without error ({len(bad)} failed); "
                 f"{len(groups)} (program, mode) groups; {len(rows)} pairs of recordings.\n")
    lines.append("Recordings by store: " + ", ".join(
        f"{s} {n}" for s, n in sorted(collections.Counter(r["store"] for r in good).items())))
    libs = collections.Counter((r["store"], r["libsanalyzer"]) for r in good)
    lines.append("libsanalyzer by store: " + "; ".join(
        f"{s}: {l} ({n})" for (s, l), n in sorted(libs.items(), key=str)) + "\n")
    suites = sorted({r["suite"] for r in rows}, key=lambda s: (s[0] != "P", len(s), s))

    def block(title, sel):
        out = [f"### {title}\n"]
        t = []
        for s in suites + ["all"]:
            for m in xc.MODES:
                rr = [r for r in sel if (s == "all" or r["suite"] == s) and r["mode"] == m]
                if not rr:
                    continue
                ge = {(r["id"]) for r in rr}
                je = [r["jaccard_edges"] for r in rr]
                ju = [r["jaccard_unresolved"] for r in rr]
                jr = [r["jaccard_race_ids"] for r in rr]
                jp = [r["jaccard_race_pcs"] for r in rr]
                flips = sum(r["verdict_a"] != r["verdict_b"] for r in rr)
                t.append([s, m, len(ge), len(rr)] + stats_row(je) + stats_row(ju)
                         + [sum(r["edges_empty"] for r in rr), sum(r["unres_empty"] for r in rr),
                            sum(v == 1.0 for v in jr), sum(v == 1.0 for v in jp), flips])
        out.append(md_table(
            ["suite", "mode", "programs", "recording pairs",
             "edges: pairs with J=1", "edges min", "edges median", "edges mean",
             "unresolved: pairs with J=1", "unres. min", "unres. median", "unres. mean",
             "both edge sets empty", "both unresolved sets empty",
             "RACE-id sets identical", "RACE pc-pair sets identical", "RACE/CLEAN differs"], t))
        return "\n".join(out) + "\n"

    lines.append(block("Table A -- all pairs of recordings", rows))
    pairs_by = collections.Counter((r["store_a"], r["store_b"]) for r in rows)
    for (sa, sb), n in sorted(pairs_by.items()):
        lines.append(block(f"Table B -- {sa} vs {sb} ({n} recording pairs)",
                           [r for r in rows if (r["store_a"], r["store_b"]) == (sa, sb)]))
    low = sorted(rows, key=lambda r: (r["jaccard_edges"], r["jaccard_unresolved"]))[:25]
    lines.append("### Table C -- the 25 recording pairs with the lowest edge Jaccard\n")
    lines.append(md_table(
        ["program", "mode", "a", "b", "edges a", "edges b", "J edges", "unres a", "unres b",
         "J unresolved", "class changed (common)", "verdict a/b"],
        [[r["id"], r["mode"], r["store_a"], r["store_b"], r["edges_a"], r["edges_b"],
          f"{r['jaccard_edges']:.4f}", r["unres_a"], r["unres_b"],
          f"{r['jaccard_unresolved']:.4f}", r["class_changed_among_common"],
          f"{r['verdict_a']}/{r['verdict_b']}"] for r in low]) + "\n")
    lowu = sorted((r for r in rows if not r["unres_empty"]),
                  key=lambda r: (r["jaccard_unresolved"], r["jaccard_edges"]))[:25]
    lines.append("### Table D -- the 25 recording pairs with the lowest unresolved-pair Jaccard "
                 "(both sets non-empty or one non-empty)\n")
    lines.append(md_table(
        ["program", "mode", "a", "b", "unres a", "unres b", "common", "J unresolved",
         "class changed (common)", "J edges"],
        [[r["id"], r["mode"], r["store_a"], r["store_b"], r["unres_a"], r["unres_b"],
          r["unres_common"], f"{r['jaccard_unresolved']:.4f}", r["class_changed_among_common"],
          f"{r['jaccard_edges']:.4f}"] for r in lowu]) + "\n")
    if bad:
        lines.append("### Failed recordings\n")
        lines.append(md_table(["program", "mode", "store", "reason"],
                              [[r["id"], r["mode"], r["store"], r["reason"]] for r in bad]) + "\n")
    excl = collections.Counter((r["store"], r["why"]) for r in plan.get("excluded", []))
    if excl:
        lines.append("### Incomplete recordings of those groups (left out)\n")
        lines.append(md_table(["store", "reason", "recordings"],
                              [[s, w, n] for (s, w), n in sorted(excl.items())]) + "\n")
    (outdir / "pcdg_variance_tables.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def xc_store_rank(store):
    return list(STORES).index(store) if store in STORES else 99


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--root", default=ROOT)
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("collect")
    p.add_argument("--plan", required=True)
    p.add_argument("--shard", required=True, help="k/n")
    p.add_argument("--out", required=True, help="jsonl; {shard} is replaced by k")
    p.add_argument("--analysis-timeout", type=int, default=14400)
    p.add_argument("--mem-gb", type=float, default=0)
    p.add_argument("--only", default="", help="regex on the program id (pilot runs)")
    p.set_defaults(fn=cmd_collect)
    p = sub.add_parser("report")
    p.add_argument("--plan", required=True)
    p.add_argument("--inputs", required=True)
    p.add_argument("--outdir", required=True)
    p.set_defaults(fn=cmd_report)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

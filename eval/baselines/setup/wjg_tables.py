#!/usr/bin/env python3
"""WARPSYNC join gap, phase 3: per (store, program, mode) rows and the report tables (read only).

  wjg_tables.py --dir eval/results/wjg [--x5 <x5b partial.jsonl>]

Inputs in --dir: files.jsonl (wjg_scan.py list), scan_*.jsonl (wjg_scan.py scan),
census*.jsonl (wjg_census.py run --select partial) and validate*.jsonl (--select validate).
For a file with several census attempts (budgets), the attempt whose census and both replays
finished is used, else the one with the largest budget.

Writes rows.csv (every (store, run directory) with at least one kernel JSON; the run directory is
<program>/<mode> in the standard layout, <program>/<mode>-partial-repN for a timed-out run's kept
dump, else the kernel JSON's directory),
report_tables.md (the tables of eval/WARPSYNC_JOIN_GAP.md) and moves.json (every pair that
appears or disappears with the merge, per row and launch).
"""
import argparse
import collections
import csv
import glob
import json
import os

# (row level, child kind, result key): the oracle's two clocks, and the barrier-only pass
LEVELS = (("races_L1", "replay", "races_L1"), ("sync_only_L1", "replay", "sync_only_L1"),
          ("races_L2", "replay", "races_L2"), ("bpass_sync_only_L1", "bpass", "sync_only_L1"))
LV = [lv for lv, _, _ in LEVELS]


def load_jsonl(paths):
    for p in paths:
        with open(p) as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    yield json.loads(ln)


def nominal(f):
    """the kernel JSON's path inside its own store (wjg_scan.stores)"""
    t = f["store"]
    if t.startswith("home:"):
        root = f"/mnt/beegfs/fzheng4/home_archive/eval_baselines/{t[5:]}"
    elif t.startswith("other:"):
        root = f"/mnt/beegfs/fzheng4/{t[6:]}"
    else:
        root = f"/mnt/beegfs/fzheng4/cuvein_traces/{t}"
    return os.path.join(root, f["rel"])


def outcome(r, kind):
    """-> None if both `kind` children (replay = hb_oracle, bpass = barrier_only_pairs) gave a
    result, else the reason."""
    for name in ("as_recorded", "merged"):
        ch = r.get(f"{kind}_{name}_child", {})
        if ch.get("rc") != 0 or f"{kind}_{name}" not in r:
            return f"{name}: {ch.get('rc')} at {r.get('budget_gb')} GB after {ch.get('secs')} s"
        if "error" in r[f"{kind}_{name}"]:
            return f"{name}: {r[f'{kind}_{name}']['error'][:120]}"
    return None


def census_failure(r):
    cc = r.get("census_child", {})
    if cc.get("rc") != 0 or "census" not in r:
        return f"census: {cc.get('rc')} at {r.get('budget_gb')} GB after {cc.get('secs')} s"
    c = r["census"]
    if c.get("error"):
        return f"census: {c['error']}"
    if c.get("completed") and not c.get("dot"):
        return f"no dot matches the kernel ({c.get('ndots')} dots)"
    return None


def best_attempt(recs):
    """One record per file from its attempts (budgets, classes, a --no-oracle pass): the last
    attempt whose census finished, with each kind of result (bpass, replay) taken from an attempt
    where both of its children finished, else from the attempt with the largest budget."""
    good = [r for r in recs if census_failure(r) is None]
    if not good:
        return max(recs, key=lambda r: r.get("budget_gb", 0))
    out = dict(good[-1])
    for kind in ("bpass", "replay"):
        keys = [f"{kind}_{n}{s}" for n in ("as_recorded", "merged") for s in ("", "_child")]
        done = [r for r in good if outcome(r, kind) is None]
        tried = [r for r in good if f"{kind}_as_recorded_child" in r]
        src = done[-1] if done else max(tried, key=lambda r: r.get("budget_gb", 0)) if tried else None
        for k in keys:
            out.pop(k, None)
            if src is not None and k in src:
                out[k] = src[k]
    sc = [r["streamcheck"] for r in good if "streamcheck" in r]
    if sc:
        out["streamcheck"] = sc[-1]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--x5", default="/home/fzheng4/wt-x5-byte-pairs/eval/results/x5b/partial.jsonl")
    a = ap.parse_args()
    D = a.dir
    files = list(load_jsonl([f"{D}/files.jsonl"]))
    scan = {s["real"]: s for s in load_jsonl(sorted(glob.glob(f"{D}/scan_*.jsonl")))}
    att = collections.defaultdict(list)
    for r in load_jsonl(sorted(glob.glob(f"{D}/census*.jsonl"))):
        att[r["real"]].append(r)
    cen = {k: best_attempt(v) for k, v in att.items()}
    val = {}
    for r in load_jsonl(sorted(glob.glob(f"{D}/validate*.jsonl"))):
        if r.get("census_child", {}).get("rc") == 0:
            val[r["real"]] = r

    # ---- validation: scan counts vs parsed records ----
    vchk = collections.Counter()
    for real, r in list(cen.items()) + list(val.items()):
        s, c = scan.get(real), r.get("census")
        if not s or not c:
            continue
        vchk["files"] += 1
        for k_s, k_c in (("recs", "records"), ("sw_full", "sw_full"), ("sw_partial", "sw_partial")):
            vchk[f"{k_s} equal"] += s[k_s] == c.get(k_c)
        vchk["seq sorted in file"] += c.get("seq_sorted_in_file", False)
        vchk["streamed census"] += bool(c.get("stream"))

    # ---- the streamed census against the verbatim one; the SASS at partial-record pcs ----
    schk, sbad, ops = collections.Counter(), [], collections.Counter()
    for real, r in cen.items():
        s = r.get("streamcheck")
        if s is not None:
            schk["files"] += 1
            schk["equal"] += bool(s.get("equal"))
            if not s.get("equal"):
                sbad.append(real)
        for pc, lst in ((r.get("census") or {}).get("partial_pc_opcodes") or {}).items():
            if not lst:
                ops[("pc not in the dot", "")] += 1
            for cl, op in lst:
                where = "out-of-line helper " + cl if cl.startswith("$__internal") else "kernel body"
                ops[(where, op)] += 1

    # ---- rows ----
    rows = collections.OrderedDict()
    for f in files:
        parts = f["rel"].split("/")
        key = (f["store"], "/".join(parts[:-1]), f.get("id") or parts[0],
               parts[-2] if len(parts) >= 2 else "")
        rows.setdefault(key, []).append(f)
    out_rows, moves = [], []
    for key, fl in rows.items():
        store, rundir, pid, mode = key
        R = collections.Counter()
        reasons, before, after = [], collections.defaultdict(set), collections.defaultdict(set)
        launch_moves = []
        linked = 0
        for f in fl:
            R["kernel_jsons"] += 1
            real = f.get("real")
            if not real:
                reasons.append(f"listing: {f.get('err')}")
                continue
            s = scan.get(real)
            if s is None:
                reasons.append("not scanned")
                continue
            if s.get("err"):
                reasons.append(f"scan: {s['err'][:80]}")
                continue
            if s["recs"] == 0:
                continue
            R["with_records"] += 1
            R["records"] += s["recs"]
            R["sw_full"] += s["sw_full"]
            R["sw_partial"] += s["sw_partial"]
            if real != nominal(f):
                linked += 1                    # a symlink into another store's files
            if s["sw_partial"] == 0:
                continue
            r = cen.get(real)
            if r is None:
                reasons.append("partial syncwarps, census not run")
                continue
            why = census_failure(r)
            c = r.get("census") or {}
            if c:
                R["inst_completed"] += c.get("completed", 0)
                R["inst_open"] += c["x5_census"].get("partial instances never completed", 0)
                R["late_x5"] += c.get("x5_pending_mem", 0)
                ex = c.get("extras", {})
                R["late_once"] += ex.get("memory records of not-yet-arrived lanes (once, sync-mask lanes)", 0)
                R["late_lanes"] += ex.get("lane accesses of not-yet-arrived lanes", 0)
                R["cross_pc"] += ex.get("syncwarp records at another pc inside an open instance", 0)
                R["cross_pc_waiting"] += ex.get("... with lanes the open instance still waits for", 0)
                R["late_shared"] += ex.get("... by space shared", 0)
                R["late_global"] += ex.get("... by space global", 0)
                R["sm_partial_instances"] += ex.get("sync_mask partial", 0)
                for k, v in c["x5_census"].items():
                    if k.startswith("partial instance of "):
                        R[k.replace("partial instance of ", "inst_") .replace(" records", "r")] += v
            if why:
                reasons.append(why)
                continue
            if not c.get("merged"):
                continue
            kn = c["kname"]
            lm = {"kernel_json": f["rel"], "kname": kn}
            ro, bo = outcome(r, "replay"), outcome(r, "bpass")
            R["merged_launches"] += 1
            R["replayed"] += ro is None
            R["bpassed"] += bo is None
            if ro:
                reasons.append(f"vector-clock oracle replay: {ro}")
            if bo:
                reasons.append(f"barrier-only pass: {bo}")
            for lv, kind, key in LEVELS:
                if (ro if kind == "replay" else bo) is not None:
                    continue
                b, m = r[f"{kind}_as_recorded"], r[f"{kind}_merged"]
                bs, ms = set(b[key]), set(m[key])
                before[lv] |= {(kn, p) for p in bs}
                after[lv] |= {(kn, p) for p in ms}
                if bs != ms:
                    lm[lv] = {"appear": sorted(ms - bs), "disappear": sorted(bs - ms)}
            if ro is None:
                b, m = r["replay_as_recorded"], r["replay_merged"]
                R["L3_changed_launches"] += b["races_L3"] != m["races_L3"] or \
                    b["sync_only_L3"] != m["sync_only_L3"]
            if ro is None and bo is None:              # two implementations of the barrier-only clock
                same = all(r[f"replay_{n}"]["sync_only_L3"] == r[f"bpass_{n}"]["sync_only_L3"]
                           for n in ("as_recorded", "merged"))
                R["bpass_equals_oracle"] += same
                R["bpass_differs_from_oracle"] += not same
            if any(lv in lm for lv, _, _ in LEVELS):
                launch_moves.append(lm)
        row = {"store": store, "rundir": rundir, "id": pid, "mode": mode, **R,
               "linked_files": linked}
        for lv in LV:
            row[f"{lv}_before"] = len(before[lv])
            row[f"{lv}_after"] = len(after[lv])
            row[f"{lv}_appear"] = len(after[lv] - before[lv])
            row[f"{lv}_disappear"] = len(before[lv] - after[lv])
        row["missing"] = "; ".join(sorted(set(reasons)))
        out_rows.append(row)
        if launch_moves:
            moves.append({"store": store, "rundir": rundir, "id": pid, "mode": mode,
                          "launches": launch_moves,
                          "appear": {lv: sorted(map(list, after[lv] - before[lv])) for lv in LV},
                          "disappear": {lv: sorted(map(list, before[lv] - after[lv])) for lv in LV}})

    cols = sorted({k for r in out_rows for k in r}, key=lambda k: (k not in ("store", "rundir", "id", "mode"), k))
    with open(f"{D}/rows.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in out_rows:
            w.writerow({k: r.get(k, 0) for k in cols})
    with open(f"{D}/moves.json", "w") as f:
        json.dump(moves, f, indent=1)

    # ---- X5 cross-check: the 60 recordings of x5b_partial.py ----
    x5 = []
    if os.path.exists(a.x5):
        byrow = {(r["store"], r["rundir"]): r for r in out_rows}
        for r in load_jsonl([a.x5]):
            mine = byrow.get((r["store"], f"{r['id']}/{r['mode']}"))
            c = r["census"]
            x5.append({"store": r["store"], "id": r["id"], "mode": r["mode"],
                       "x5_completed": c.get("partial instances completed", 0),
                       "x5_never": c.get("partial instances never completed", 0),
                       "x5_pending": r["pending_lane_mem_records"],
                       "x5_after": sum(r["only_after_merge"].values()),
                       "x5_before": sum(r["only_before_merge"].values()),
                       "x5_shared_only": r["shared_only"],
                       "mine": None if mine is None else
                       {k: mine.get(k, 0) for k in ("inst_completed", "inst_open", "late_x5",
                                                     "races_L1_appear", "races_L1_disappear",
                                                     "sync_only_L1_appear", "sync_only_L1_disappear",
                                                     "missing")}})
    with open(f"{D}/x5_check.json", "w") as f:
        json.dump({"validation": dict(vchk), "x5": x5}, f, indent=1)

    # ---- markdown ----
    L = []
    with_rec = [r for r in out_rows if r.get("with_records")]
    by_store = collections.OrderedDict()
    for r in with_rec:
        by_store.setdefault(r["store"], []).append(r)
    L.append("### A. Per store (rows = (program, mode) with at least one kernel JSON holding records)\n")
    L.append("| store | rows | kernel JSONs with records | records | syncwarp records full / partial | "
             "rows with a diverged instance | (1) diverged instances completed / open at end | "
             "(2) memory records of not-yet-arrived lanes | rows replayed | rows where a pair moves "
             "(races / sync-only) | rows missing |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    tot = collections.Counter()
    for st, rs in by_store.items():
        c = collections.Counter()
        for r in rs:
            c["rows"] += 1
            for k in ("with_records", "records", "sw_full", "sw_partial", "inst_completed", "inst_open",
                      "late_once", "late_x5"):
                c[k] += r.get(k, 0)
            c["div"] += (r.get("inst_completed", 0) + r.get("inst_open", 0)) > 0
            c["replayed"] += r.get("replayed", 0) > 0
            c["mv_r"] += (r["races_L1_appear"] + r["races_L1_disappear"]) > 0
            c["mv_s"] += (r["sync_only_L1_appear"] + r["sync_only_L1_disappear"] +
                          r["bpass_sync_only_L1_appear"] + r["bpass_sync_only_L1_disappear"]) > 0
            c["missing"] += bool(r["missing"])
        tot.update(c)
        L.append(f"| {st} | {c['rows']} | {c['with_records']:,} | {c['records']:,} | "
                 f"{c['sw_full']:,} / {c['sw_partial']:,} | {c['div']} | {c['inst_completed']:,} / "
                 f"{c['inst_open']:,} | {c['late_once']:,} | {c['replayed']} | {c['mv_r']} / {c['mv_s']} | "
                 f"{c['missing']} |")
    L.append(f"| **total** | {tot['rows']} | {tot['with_records']:,} | {tot['records']:,} | "
             f"{tot['sw_full']:,} / {tot['sw_partial']:,} | {tot['div']} | {tot['inst_completed']:,} / "
             f"{tot['inst_open']:,} | {tot['late_once']:,} | {tot['replayed']} | {tot['mv_r']} / {tot['mv_s']} | "
             f"{tot['missing']} |")
    L.append("")
    L.append("### A2. Per suite (rows with records, all stores)\n")
    L.append("| suite | rows | rows with a diverged instance | (1) instances completed / open | (2) late memory "
             "records | rows fully replayed | rows where a pair moves (races / sync-only) | rows missing |")
    L.append("|---|---|---|---|---|---|---|---|")
    su = collections.OrderedDict()
    for r in sorted(with_rec, key=lambda r: r["id"]):
        s = r["id"].split("-")[0] if r["id"].startswith("P") and "-" in r["id"] else "other"
        c = su.setdefault(s, collections.Counter())
        c["rows"] += 1
        c["div"] += (r.get("inst_completed", 0) + r.get("inst_open", 0)) > 0
        for k in ("inst_completed", "inst_open", "late_once"):
            c[k] += r.get(k, 0)
        c["full"] += r.get("merged_launches", 0) > 0 and r.get("replayed", 0) == r.get("merged_launches", 0)
        c["mv_r"] += (r["races_L1_appear"] + r["races_L1_disappear"]) > 0
        c["mv_s"] += (r["sync_only_L1_appear"] + r["sync_only_L1_disappear"] +
                      r["bpass_sync_only_L1_appear"] + r["bpass_sync_only_L1_disappear"]) > 0
        c["missing"] += bool(r["missing"])
    for s, c in su.items():
        L.append(f"| {s} | {c['rows']} | {c['div']} | {c['inst_completed']:,} / {c['inst_open']:,} | "
                 f"{c['late_once']:,} | {c['full']} | {c['mv_r']} / {c['mv_s']} | {c['missing']} |")
    L.append("")
    L.append("### A3. SASS at the pcs with partial syncwarp records ((dump, pc) pairs)\n")
    L.append("| where | opcode | (dump, pc) |")
    L.append("|---|---|---|")
    for (w, op), n in ops.most_common():
        L.append(f"| {w} | {op} | {n:,} |")
    L.append("")
    L.append(f"Streamed census vs the verbatim one (dumps under 2,000 MB with `--check-stream`): {dict(schk)}; "
             f"unequal: {sbad[:10]}\n")
    L.append("### B. Every row with a diverged syncwarp instance\n")
    L.append("| store | program | mode | launches with records | (1) instances completed (2 / 3+ records) / open | "
             "(2) late memory records (shared / global) | lane accesses | races L1 recorded -> merged "
             "(+/-) | sync-only L1 recorded -> merged (+/-) | L2 +/- | launches with any count change | "
             "barrier-only pass: sync-only recorded -> merged (+/-); launches = oracle / differ | status |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in with_rec:
        if not (r.get("inst_completed", 0) + r.get("inst_open", 0) or r["missing"]):
            continue
        three = sum(v for k, v in r.items() if k.startswith("inst_") and k.endswith("r") and k != "inst_2r")
        L.append(f"| {r['store']} | {r['id']} | {r['mode']} | "
                 f"{r.get('with_records', 0)} | {r.get('inst_completed', 0):,} ({r.get('inst_2r', 0):,} / "
                 f"{three:,}) / {r.get('inst_open', 0):,} | {r.get('late_once', 0):,} "
                 f"({r.get('late_shared', 0):,} / {r.get('late_global', 0):,}) | {r.get('late_lanes', 0):,} | "
                 f"{r['races_L1_before']} -> {r['races_L1_after']} (+{r['races_L1_appear']}/-{r['races_L1_disappear']}) | "
                 f"{r['sync_only_L1_before']} -> {r['sync_only_L1_after']} "
                 f"(+{r['sync_only_L1_appear']}/-{r['sync_only_L1_disappear']}) | "
                 f"+{r['races_L2_appear']}/-{r['races_L2_disappear']} | {r.get('L3_changed_launches', 0)} | "
                 f"{r['bpass_sync_only_L1_before']} -> {r['bpass_sync_only_L1_after']} "
                 f"(+{r['bpass_sync_only_L1_appear']}/-{r['bpass_sync_only_L1_disappear']}); "
                 f"{r.get('bpass_equals_oracle', 0)} / {r.get('bpass_differs_from_oracle', 0)} | "
                 f"{r['missing'] or 'complete'} |")
    L.append("")
    L.append(f"Validation (scan vs parsed records): {dict(vchk)}\n")
    with open(f"{D}/report_tables.md", "w") as f:
        f.write("\n".join(L) + "\n")
    i = L.index("### A2. Per suite (rows with records, all stores)\n")
    print("\n".join(L[i:i + 2 + len(su) + 2]))
    print(f"streamcheck {dict(schk)}; validation {dict(vchk)}")
    print("moves:", len(moves), "x5 rows:", len(x5))
    for m in moves[:20]:
        print(m["store"], m["id"][:80], m["mode"],
              {k: v[:4] for k, v in m["appear"].items() if v}, {k: v[:4] for k, v in m["disappear"].items() if v})


if __name__ == "__main__":
    main()

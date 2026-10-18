#!/usr/bin/env python3
"""X5 byte pairs: tables from x5b_merge.py's merged JSONL (read only; prints markdown).

  x5b_summary.py <byte_pairs.jsonl>

A row's mechanism is decided by the recorded facts alone:
  syncwarp-as-NOP   a NOP lies on every CFG path u -> v and no BAR/WARPSYNC/DEPBAR does; every
                    such NOP carries syncwarp records in the events store; the oracle lists the
                    pair in no launch as recorded; and every conflicting instance found in the
                    records (same block, same byte, lanes a != b) is same-warp with a syncwarp
                    holding both lanes between its two accesses (instance_check), at least one
                    instance existing
  async+barrier     u is a cp.async (LDGSTS), a BAR lies on every path u -> v, the oracle lists
                    the pair in no launch as recorded, and removing the BAR's records makes the
                    barrier-only clock list it
  unexplained       anything else (or no events store)
"""
import collections
import json
import sys


def short(pid, n=58):
    return pid if len(pid) <= n else pid[:n] + "…"


def removed(ev, var):
    return ev.get("oracle_with_sync_records_removed", {}).get(var, {})


def mechanism(r):
    st, ev = r["static"], r.get("events")
    if not ev:
        return "unexplained (no events store)"
    c, ic = ev["counts"], ev.get("instances", {})
    clean = c.get("oracle_races:False", 0) == c["launches"] \
        and c.get("oracle_sync_only:False", 0) == c["launches"]
    sw = ev["sync_records_at_cut_pcs"]
    if st["cut_nops"] and not st["cut_syncs"]:
        if clean and all(sw.get(f"{p} syncwarp", 0) > 0 for p in st["cut_nops"]) \
                and ic.get("same_warp_syncwarp_between", 0) > 0 \
                and ic.get("same_warp_NO_syncwarp_between", 0) == 0 \
                and ic.get("cross_warp", 0) == 0:
            return "syncwarp-as-NOP"
    if st["op_u"].startswith("LDGSTS"):
        bars = [s.split()[0] for s in st["cut_syncs"] if s.split()[1].startswith("BAR")]
        if clean and bars and all(removed(ev, p).get("sync_only:True", 0) > 0 for p in bars):
            return "async+barrier"
    return "unexplained"


def main():
    rows = [json.loads(ln) for ln in open(sys.argv[1])]
    print(f"rows: {len(rows)}\n")
    mech = collections.Counter((r["suite"], r["mode"], mechanism(r)) for r in rows)
    print("| suite | mode | mechanism | rows |\n|---|---|---|---|")
    for (s, m, k), n in sorted(mech.items()):
        print(f"| {s} | {m} | {k} | {n} |")

    print("\n### per pair and mode\n")
    head = ["suite", "program", "mode", "u -> v", "opcodes", "on every path u -> v",
            "X5 bin -> with NOP as WARPSYNC", "R1 -> with NOP as WARPSYNC",
            "X1 launches / with edge u->v", "X1 hb_races / sync_only / sync_pass lists it",
            "events store", "sync records at those pcs",
            "same-byte launches / words shared by other bytes only",
            "instances: syncwarp between / NOT / cross-warp / launches with one",
            "oracle as recorded: races / sync_only lists it",
            "oracle, those records removed: races / sync_only lists it",
            "barrier-only pairs at u or v, removed (launches)", "mechanism"]
    print("| " + " | ".join(head) + " |\n|" + "---|" * len(head))
    for r in sorted(rows, key=lambda r: (r["suite"], r["id"], r["u"], r["v"], r["mode"])):
        st, x1, ev = r["static"], r["x1"], r.get("events")
        xc = x1["counts"]
        lst = " / ".join(
            "absent" if xc.get(f"{n}:absent") else f"{xc.get(f'{n}:True', 0)}"
            for n in ("hb_races", "hb_races_sync_only", "hb_sync_pass"))
        cut = ", ".join(st["cut_nops"] + st["cut_syncs"]) or "—"
        rebin = st.get("rebin_nop_as_warpsync", "—")
        r1 = f"{st['r1_strength']} -> {st.get('r1_strength_nop_as_warpsync', '—')}"
        if ev:
            c, ic = ev["counts"], ev.get("instances", {})
            n = c["launches"]
            sw = "; ".join(f"{k} {v}" for k, v in ev["sync_records_at_cut_pcs"].items()) or "—"
            sb = f"{c.get('same_byte_launches', 0)}/{n} / {c.get('words_shared_only_by_different_bytes', 0)}"
            ins = (f"{ic.get('same_warp_syncwarp_between', 0)} / "
                   f"{ic.get('same_warp_NO_syncwarp_between', 0)} / {ic.get('cross_warp', 0)} / "
                   f"{ic.get('launches_with_an_instance', 0)}")
            rec = f"{c.get('oracle_races:True', 0)} / {c.get('oracle_sync_only:True', 0)} of {n}"
            rm = "; ".join(f"{var}: {d.get('races:True', 0)} / {d.get('sync_only:True', 0)}"
                           for var, d in ev["oracle_with_sync_records_removed"].items())
            tp = "; ".join(f"{k.replace('removed ', '')}: " +
                           ", ".join(f"{p} ({m})" for p, m in sorted(d.items()))
                           for k, d in ev.get("sync_only_pairs_at_u_or_v_launches", {}).items()
                           if k != "recorded")
            store = f"{r['events_store']}"
        else:
            sw = sb = ins = rec = rm = tp = "—"
            store = "none"
        cells = [r["suite"], short(r["id"]), r["mode"], f"{r['u']} -> {r['v']}",
                 f"{st['op_u']} / {st['op_v']}", cut, f"{st['x5_bin']} -> {rebin}", r1,
                 f"{xc.get('launches', 0)} / {xc.get('edge_launches', 0)}", lst, store, sw, sb,
                 ins, rec, rm, tp or "—", mechanism(r)]
        print("| " + " | ".join(str(x) for x in cells) + " |")

    print("\n### barrier-only pairs at u or v in the replay as recorded (launches), by row group\n")
    grp = collections.defaultdict(collections.Counter)
    for r in rows:
        ev = r.get("events") or {}
        for p, m in ev.get("sync_only_pairs_at_u_or_v_launches", {}).get("recorded", {}).items():
            grp[(r["suite"], short(r["id"], 40), r["mode"], f"{r['u']}->{r['v']}")][p] += m
    for k in sorted(grp):
        print(f"- {k}: {dict(grp[k])}")

    print("\n### X1 shared-memory race pairs listed by hb_races (vector-clock rows), by program\n")
    seen = {}
    for r in rows:
        if r["mode"] == "vector-clock":
            seen.setdefault(r["id"], set()).update(map(tuple, r["x1"]["shared_race_pairs"]))
    for pid in sorted(seen):
        print(f"- {pid}: {sorted(seen[pid])}")

    print("\n### X1 hb_stats clock-base shape: launch-rows by (suite, mode, vc max_base, pending barriers)\n")
    shapes = collections.Counter()
    for r in rows:
        for k, n in r["x1"]["hb_stats_vc_bases_maxbase_vs_bases_pending"]:
            shapes[(r["suite"], r["mode"], k[1], k[3])] += n
    print("| suite | mode | vc max_base | pending barriers | launch-rows |\n|---|---|---|---|---|")
    for (s, m, mb, pb), n in sorted(shapes.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        print(f"| {s} | {m} | {mb} | {pb} | {n} |")

    print("\n### totals and static facts\n")
    tot = collections.Counter()
    for r in rows:
        for k, n in ((r.get("events") or {}).get("instances") or {}).items():
            tot[(r["suite"], k)] += n
    print("instance-check totals by (suite, field):", dict(sorted(tot.items())))
    kb = collections.Counter(tuple(r["static"]["kernel_bar_warpsync"]) for r in rows)
    print("\nBAR/WARPSYNC instructions of the kernel (as printed), rows:", dict(kb))
    rb = collections.Counter((r["static"]["x5_bin"], r["static"].get("rebin_nop_as_warpsync"))
                             for r in rows)
    print("\nX5 bin -> bin with the cutting NOPs read as WARPSYNC, rows:", dict(rb))
    r1 = collections.Counter((r["observed"], r["static"]["r1_strength"],
                              r["static"].get("r1_strength_nop_as_warpsync")) for r in rows)
    print("\n(observed, R1 strength, R1 strength with NOP as WARPSYNC), rows:", dict(r1))
    sizes = collections.Counter(tuple(r["events"]["access_sizes"]) for r in rows if r.get("events"))
    print("\naccess sizes of the u/v records in the events store, rows:", dict(sizes))
    md = collections.Counter(r["events_store"] for r in rows)
    print("\nevents store, rows:", dict(md))
    masks = collections.Counter(json.dumps(r["events"]["sync_masks_at_cut_pcs"], sort_keys=True)
                                for r in rows if r.get("events"))
    print("\nsync masks at the cutting pcs, rows:", dict(masks))
    rep = collections.Counter(bool((r.get("events") or {}).get("shared_only")) for r in rows)
    print("\nreplay without global records (shared_only), rows:", dict(rep))
    full = sum(1 for r in rows if r.get("events_full"))
    print(f"\nrows that also have a full replay (events_full): {full}")


if __name__ == "__main__":
    main()

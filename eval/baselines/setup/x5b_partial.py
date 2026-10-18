#!/usr/bin/env python3
"""X5 byte pairs: syncwarp records of a diverged warp (read only on the stores).

  x5b_partial.py --pairs <merged byte_pairs.jsonl> --out <jsonl> [--shard i/n]

The model (hb_proof.tex Definition "Instances") takes a syncwarp record as a complete instance
by itself: all its masked lanes depart at its position. A warp that is diverged when it reaches
WARPSYNC executes it in several groups, one record each (active_mask a strict subset of
sync_mask); the hardware releases the warp only when every masked lane has arrived. Per
(events store, program, mode, kernel) of the rows, every launch:

  census     syncwarp records by pc: full (active == sync mask) / partial; partial instances
             (consecutive records of one warp at one pc whose active masks reach the sync mask),
             completed or not; memory records of the warp's not-yet-arrived masked lanes inside
             an open partial instance (accesses the model places after a departure that the
             hardware had not yet made)
  pairs      for each row's (u, v): the instance check of x5b_byte_pairs.py, split by whether a
             covering syncwarp record has BOTH lanes in its active mask (sound whatever the other
             lanes do) or only in its sync mask
  replay     hb_oracle.analyze on the records as recorded and on the records with every completed
             partial instance merged into one record at its completion (active mask = the union,
             the earlier records dropped) -- the exact instance under the model's own rule. Race
             pc pairs (races, races_sync_only) present only after the merge are pairs the
             per-record join hides. Programs with 1296-node inputs replay without their global
             records (x5b_byte_pairs.py --shared-only; memory), the rest in full.
"""
import argparse
import bisect
import collections
import glob
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import x5_common as xc                       # noqa: E402,F401
from x5_common import sd                     # noqa: E402
import hb_oracle as ho                       # noqa: E402
import x5b_byte_pairs as bp                  # noqa: E402

ROOT = "/mnt/beegfs/fzheng4/cuvein_traces"
MEM = ("read", "write", "atomic")


def partial_instances(ev):
    """-> (census Counter, merged event list, open-instance memory-record count)."""
    c = collections.Counter()
    opened = {}                                    # (block, warp, pc) -> [first_seq, union, records]
    drop = set()                                   # seqs of partial records merged away
    widen = {}                                     # seq of a completing record -> union mask
    pending_mem = 0
    for e in ev:
        ty = e.get("type")
        if ty == "syncwarp":
            k = (e["block"], e["warp"], e["pc"])
            sm, am = e["sync_mask"], e["active_mask"]
            if k not in opened:
                if am & sm == sm:
                    c[f"full {e['pc']:#x}"] += 1
                    continue
                opened[k] = [e["seq"], am, [e["seq"]]]
                c[f"partial {e['pc']:#x}"] += 1
                continue
            st = opened[k]
            st[1] |= am
            st[2].append(e["seq"])
            c[f"partial {e['pc']:#x}"] += 1
            if st[1] & sm == sm:
                c["partial instances completed"] += 1
                c[f"partial instance of {len(st[2])} records"] += 1
                drop.update(st[2][:-1])
                widen[st[2][-1]] = st[1]
                del opened[k]
        elif ty in MEM:
            for (b, w, _), st in opened.items():
                if b == e["block"] and w == e["warp"]:
                    lanes = {ln["lane"] for ln in e["lanes"]}
                    if any(not (st[1] >> l) & 1 for l in lanes):
                        pending_mem += 1
    c["partial instances never completed"] += len(opened)
    merged = []
    for e in ev:
        if e["seq"] in drop:
            continue
        if e["seq"] in widen:
            e = dict(e, active_mask=widen[e["seq"]])
        merged.append(e)
    return c, merged, pending_mem


def instance_check2(ev, u, v):
    """x5b_byte_pairs.instance_check, with the covering syncwarp record split by whether its
    ACTIVE mask holds both lanes."""
    sw = collections.defaultdict(list)
    for e in ev:
        if e.get("type") == "syncwarp":
            sw[(e["block"], e["warp"])].append((e["seq"], e["sync_mask"], e["active_mask"]))
    c = collections.Counter()
    last_u = {}
    for e in ev:
        if e.get("type") not in MEM:
            continue
        if e["pc"] == u:
            for ln in e["lanes"]:
                last_u.setdefault((e["block"], ln["addr"]), {})[(e["warp"], ln["lane"])] = e["seq"]
        elif e["pc"] == v:
            for ln in e["lanes"]:
                b = ln["lane"]
                for (w, a), s0 in last_u.get((e["block"], ln["addr"]), {}).items():
                    if (w, a) == (e["warp"], b):
                        continue
                    if w != e["warp"]:
                        c["cross_warp"] += 1
                        continue
                    lst = sw[(e["block"], w)]
                    i = bisect.bisect_right(lst, (s0, 1 << 62, 1 << 62))
                    best = None
                    while i < len(lst) and lst[i][0] < e["seq"]:
                        _, sm, am = lst[i]
                        if (am >> a) & 1 and (am >> b) & 1:
                            best = "both_active"
                            break
                        if (sm >> a) & 1 and (sm >> b) & 1:
                            best = "sync_mask_only"
                        i += 1
                    c[best or "uncovered"] += 1
    return c


def race_sets(dot, t, events, tmpdir):
    t2 = dict(t)
    t2["hb_events"] = events
    fd, path = tempfile.mkstemp(suffix=".json", dir=tmpdir)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(t2, f)
        try:
            rep = ho.analyze(dot, path)
        except sd.AlignmentError as e:
            return {"error": str(e)[:160]}
    finally:
        os.unlink(path)
    return {"races": sorted({f"{r['space']}:{r['a_pc']:#x}-{r['b_pc']:#x}:{r['kind']}:{r['class']}"
                             for r in rep["races"] if r.get("a_pc") is not None}),
            "sync_only": sorted({f"{a:#x}-{b:#x}" for a, b, _ in rep["races_sync_only"]})}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shard", default="0/1")
    a = ap.parse_args()
    groups = collections.OrderedDict()
    for ln in open(a.pairs):
        r = json.loads(ln)
        if not r.get("events_store") or r["suite"] == "P6":
            continue
        k = (r["events_store"], r["id"], r["mode"], r["kernel"])
        groups.setdefault(k, []).append((int(r["u"], 16), int(r["v"], 16)))
    si, sn = map(int, a.shard.split("/"))
    keys = list(groups)[si::sn]
    print(f"{len(groups)} groups; shard {si}/{sn}: {len(keys)}", flush=True)
    tmpdir = os.environ.get("TMPDIR", "/tmp")
    with open(a.out, "w") as out:
        for (store, pid, mode, kernel) in keys:
            dotbase, mangled = kernel.split("::", 1)
            dot = f"{ROOT}/{store}/{pid}/dots/{dotbase}"
            kernels = sd.parse_dot(dot)
            shared_only = "1296n" in pid
            rec = {"store": store, "id": pid, "mode": mode, "kernel": kernel,
                   "shared_only": shared_only, "launches": 0, "census": collections.Counter(),
                   "pending_lane_mem_records": 0,
                   "pairs": {f"{u:#x}->{v:#x}": collections.Counter() for u, v in groups[(store, pid, mode, kernel)]},
                   "only_after_merge": collections.Counter(), "only_before_merge": collections.Counter(),
                   "errors": []}
            for kj, t in bp.launches(f"{ROOT}/{store}/{pid}/{mode}", kernels, mangled):
                ev = sorted(t["hb_events"], key=lambda e: e["seq"])
                if shared_only:
                    ev = [e for e in ev if e.get("space") != "global"]
                rec["launches"] += 1
                cen, merged, pend = partial_instances(ev)
                rec["census"].update(cen)
                rec["pending_lane_mem_records"] += pend
                for u, v in groups[(store, pid, mode, kernel)]:
                    rec["pairs"][f"{u:#x}->{v:#x}"].update(instance_check2(ev, u, v))
                if not any(k.startswith("partial instances completed") for k in cen):
                    continue                           # nothing merged: the replays are equal
                before = race_sets(dot, t, ev, tmpdir)
                after = race_sets(dot, t, merged, tmpdir)
                if "error" in before or "error" in after:
                    rec["errors"].append([os.path.basename(kj), before.get("error"), after.get("error")])
                    continue
                for f in ("races", "sync_only"):
                    for p in set(after[f]) - set(before[f]):
                        rec["only_after_merge"][f"{f} {p}"] += 1
                    for p in set(before[f]) - set(after[f]):
                        rec["only_before_merge"][f"{f} {p}"] += 1
            for k in ("census", "only_after_merge", "only_before_merge"):
                rec[k] = dict(rec[k])
            rec["pairs"] = {k: dict(v) for k, v in rec["pairs"].items()}
            out.write(json.dumps(rec) + "\n")
            out.flush()
            print(pid[:70], mode[:6], rec["launches"], rec["census"], "pend", rec["pending_lane_mem_records"],
                  rec["pairs"], "AFTER-ONLY", rec["only_after_merge"], "BEFORE-ONLY",
                  rec["only_before_merge"], rec["errors"][:2], flush=True)


if __name__ == "__main__":
    main()

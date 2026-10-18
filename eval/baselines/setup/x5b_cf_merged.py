#!/usr/bin/env python3
"""X5 byte pairs: the counterfactual on traces whose diverged-warp syncwarps are merged (read only).

  x5b_cf_merged.py --pairs <merged byte_pairs.jsonl> --out <jsonl> [--shard i/n]

For every row whose counterfactual (the cutting pc's sync records removed) left the pair
unlisted in every launch, replay hb_oracle.analyze, per launch, on
  removed         the records with the cutting pc's sync records removed (as x5b_byte_pairs.py)
  merged+removed  the same, after merging every completed partial syncwarp instance into one
                  record at its completion (x5b_partial.partial_instances)
and report whether the pair is in races / races_sync_only, and the races_sync_only pairs that end
at u or v. Every replay drops the global records (x5b_byte_pairs.py --shared-only), so the vector
clock lacks the (ATOM) joins; the barrier-only clock is exact on these shared pairs.
"""
import argparse
import collections
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import x5_common as xc                       # noqa: E402,F401
from x5_common import sd                     # noqa: E402
import x5b_byte_pairs as bp                  # noqa: E402
import x5b_partial as xp                     # noqa: E402

ROOT = "/mnt/beegfs/fzheng4/cuvein_traces"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shard", default="0/1")
    a = ap.parse_args()
    rows = []
    for ln in open(a.pairs):
        r = json.loads(ln)
        e = r.get("events")
        if not e or r["suite"] == "P6" or not r["static"]["cut_nops"]:
            continue
        var = "+".join(r["static"]["cut_nops"])
        if e["oracle_with_sync_records_removed"].get(var, {}).get("sync_only:True", 0) == 0:
            rows.append(r)
    si, sn = map(int, a.shard.split("/"))
    rows = rows[si::sn]
    print(f"rows {len(rows)} in shard {si}/{sn}", flush=True)
    tmpdir = os.environ.get("TMPDIR", "/tmp")
    with open(a.out, "w") as out:
        for r in rows:
            dotbase, mangled = r["kernel"].split("::", 1)
            dot = f"{ROOT}/{r['events_store']}/{r['id']}/dots/{dotbase}"
            kernels = sd.parse_dot(dot)
            u, v = int(r["u"], 16), int(r["v"], 16)
            key = frozenset((u, v))
            cut = {int(p, 16) for p in r["static"]["cut_nops"]}
            res = {"removed": collections.Counter(), "merged+removed": collections.Counter()}
            touch = {"removed": collections.Counter(), "merged+removed": collections.Counter()}
            n = 0
            for kj, t in bp.launches(f"{ROOT}/{r['events_store']}/{r['id']}/{r['mode']}", kernels, mangled):
                n += 1
                ev = sorted((e for e in t["hb_events"] if e.get("space") != "global"), key=lambda e: e["seq"])
                _, merged, _ = xp.partial_instances(ev)
                for name, evs in (("removed", ev), ("merged+removed", merged)):
                    evs = [e for e in evs if not (e.get("type") in bp.SYNC_TYPES and e.get("pc") in cut)]
                    rr, ss, tp = bp.replay(dot, t, evs, key, tmpdir)
                    res[name][f"races:{rr}"] += 1
                    res[name][f"sync_only:{ss}"] += 1
                    touch[name].update(tp)
            rec = {"id": r["id"], "mode": r["mode"], "u": r["u"], "v": r["v"], "race_type": r["race_type"],
                   "cut": r["static"]["cut_nops"], "launches": n,
                   "result": {k: dict(c) for k, c in res.items()},
                   "sync_only_pairs_at_u_or_v": {k: dict(c) for k, c in touch.items()}}
            out.write(json.dumps(rec) + "\n")
            out.flush()
            print(r["id"][:60], r["mode"][:6], r["u"], r["v"], r["race_type"], rec["result"],
                  rec["sync_only_pairs_at_u_or_v"], flush=True)


if __name__ == "__main__":
    main()

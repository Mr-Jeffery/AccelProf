"""T24: print a kernel JSON's syncwarp records and shared-memory records per warp, the syncwarp
instances they form (records grouped per (block, warp, pc) until the union of their active masks
covers sync_mask), and the kernel's race keys.
    .env/bin/python eval/baselines/setup/t24_events.py <kernel_N.json> [--blocks 1] [--warps 2]
"""
import argparse
import json
from collections import Counter


def instances(events):
    """[(block, warp, pc, [records])] of the syncwarp records, in completion order, and the
    still-open ones; exits take lanes out of the expected set."""
    openi, done, gone = {}, [], {}
    for e in events:
        b, w = e["block"], e["warp"]
        if e["type"] == "exit":
            gone[(b, w)] = gone.get((b, w), 0) | e["active_mask"]
            for k in [k for k in openi if k[:2] == (b, w)]:
                recs = openi[k]
                exp = recs[0]["sync_mask"] & ~gone[(b, w)]
                if exp & ~_union(recs) == 0:
                    done.append((*k, openi.pop(k)))
            continue
        if e["type"] != "syncwarp":
            continue
        k = (b, w, e["pc"])
        recs = openi.setdefault(k, [])
        recs.append(e)
        exp = e["sync_mask"] & ~gone.get((b, w), 0)
        if exp & ~_union(recs) == 0:
            done.append((*k, openi.pop(k)))
    return done, openi


def _union(recs):
    m = 0
    for r in recs:
        m |= r["active_mask"]
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace")
    ap.add_argument("--blocks", type=int, default=1)
    ap.add_argument("--warps", type=int, default=2)
    a = ap.parse_args()
    t = json.load(open(a.trace))
    ev = sorted(t.get("hb_events", []), key=lambda e: e["seq"])
    print(f"kernel {t['kernel'].get('kernel_name')} block_thread_count "
          f"{t['kernel'].get('block_thread_count')} records {len(ev)} hb_exits {t.get('hb_exits')}")
    for e in ev:
        if e["block"] >= a.blocks or e["warp"] >= a.warps:
            continue
        if e["type"] == "syncwarp":
            print(f"  seq {e['seq']:6d} b{e['block']} w{e['warp']} syncwarp pc {e['pc']:#x} "
                  f"sync {e['sync_mask']:#010x} active {e['active_mask']:#010x}")
        elif e["type"] == "exit":
            print(f"  seq {e['seq']:6d} b{e['block']} w{e['warp']} exit pc {e['pc']:#x} "
                  f"active {e['active_mask']:#010x}")
        elif e.get("space") == "shared":
            lanes = [ln["lane"] for ln in e.get("lanes", [])]
            print(f"  seq {e['seq']:6d} b{e['block']} w{e['warp']} {e['type']} shared pc "
                  f"{e['pc']:#x} lanes {lanes[:4]}{'...' if len(lanes) > 4 else ''} ({len(lanes)})")
    done, still = instances(ev)
    print("instances by record count:", dict(Counter(len(r) for *_, r in done)),
          "open at end:", len(still))
    print("instance pcs:", dict(Counter((pc, len(r)) for _, _, pc, r in done)))
    for k in ("hb_races", "hb_races_sync_only", "hb_sync_pass", "tv_violation"):
        v = t.get(k)
        if k == "hb_races" and v is not None:
            v = [(r.get("a_pc"), r.get("b_pc"), r.get("kind"), r.get("space"), r.get("count"))
                 for r in v]
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()

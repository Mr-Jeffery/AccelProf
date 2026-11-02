#!/usr/bin/env python3
"""X3: print hb_stats of chosen kernel JSONs (read only, CPU).

usage: hb_stats_dump.py STORE_ENTRY_DIR [KERNEL ...]   (KERNEL = index or 'last')
Prints the full hb_stats object (compact) and the kernel JSON's byte size.
"""
import json, os, re, sys

def kernels(d):
    ks = []
    for f in os.listdir(d):
        m = re.fullmatch(r"kernel_(\d+)\.json", f)
        if m:
            ks.append(int(m.group(1)))
    return sorted(ks)

def main():
    d = sys.argv[1]
    ks = kernels(d)
    print(f"DIR {d} nkernel_files={len(ks)} first={ks[:1]} last={ks[-1:]}")
    # the highest-indexed file may be incomplete (killed mid-write); walk down to the last that parses
    want = sys.argv[2:] or ["last"]
    for w in want:
        if w == "last":
            for k in reversed(ks):
                p = os.path.join(d, f"kernel_{k}.json")
                try:
                    j = json.load(open(p))
                    break
                except Exception as e:
                    print(f"  kernel_{k}.json unreadable: {type(e).__name__}")
            else:
                print("  no readable kernel"); continue
        else:
            k = int(w); p = os.path.join(d, f"kernel_{k}.json")
            try:
                j = json.load(open(p))
            except Exception as e:
                print(f"  kernel_{k}.json unreadable: {type(e).__name__}"); continue
        print(f"KERNEL {k} bytes={os.path.getsize(p)} mtime={int(os.path.getmtime(p))} keys={sorted(j)[:30]}")
        print("HB_STATS", json.dumps(j.get("hb_stats"), sort_keys=True))

main()

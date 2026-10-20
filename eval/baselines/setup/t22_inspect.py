#!/usr/bin/env python3
"""T22 inspections on BeeGFS (run on a compute node):
  shards <store> <N>     every scalar-clock kernel JSON: does hb_stats carry `sharded` with N shards?
  unreadable <dir>       kernel JSONs that do not parse: size, kernel id, the last bytes
  mem <dir>...           per kernel: buckets bytes, vs bytes / threads / bases, rss and hwm at kernel end
"""
import glob
import json
import os
import sys


def kjs(d):
    return sorted(glob.glob(os.path.join(d, "**", "kernel_*.json"), recursive=True))


def load(p):
    try:
        return json.load(open(p))
    except json.JSONDecodeError:
        return None


def shards(store, n):
    ok = bad = unread = 0
    for p in kjs(store):
        if "/scalar-clock" not in p:
            continue
        t = load(p)
        if t is None:
            unread += 1
            continue
        sh = ((t.get("hb_stats") or {}).get("hb_clock") or {}).get("sharded")
        if sh and sh.get("shards") == n:
            ok += 1
        else:
            bad += 1
            print("not sharded:", p)
    print(f"{store}: {ok} kernel JSONs sharded with N={n}, {bad} not, {unread} unreadable")


def unreadable(d):
    files = kjs(d)
    ids = [int(os.path.basename(p)[7:-5]) for p in files]
    for p in files:
        if load(p) is None:
            raw = open(p, "rb").read()
            k = int(os.path.basename(p)[7:-5])
            closed = raw.endswith(b"}\n")
            print(f"{p}: kernel {k} of max id {max(ids)}, {len(raw)} bytes, "
                  f"ends {raw[-120:]!r}, closed {closed}")


def mem(*dirs):
    for d in dirs:
        for p in kjs(d):
            t = load(p)
            if t is None:
                continue
            s = t.get("hb_stats") or {}
            h = s.get("hb_clock") or {}
            b, v = h.get("buckets") or {}, h.get("vs") or {}
            if t.get("hb_events_count", 0) < 10 ** 6:
                continue
            print(f"{p}: events {t.get('hb_events_count')} buckets {b.get('bytes', 0) / 2**30:.2f} GiB "
                  f"({b.get('entries')} entries) vs {v.get('bytes_est', 0) / 2**30:.2f} GiB "
                  f"(threads {v.get('threads')}, bases {v.get('unique_bases')}) "
                  f"rss {s.get('rss_kb', 0) / 2**20:.2f} GiB hwm {s.get('hwm_kb', 0) / 2**20:.2f} GiB")
            break   # the first big kernel of each run


def slots(*dirs):
    """the private SLOTCOUNT build's hb_stats.hb_clock.slotcount, per kernel: accesses Check ran
    for (lane accesses), slots of the buckets met, visited (after the key-group skip), tested
    (conflict() calls), the largest bucket met (size, the access's pc, address) and at kernel end
    (size, address, its slots' pcs and keys)"""
    for d in dirs:
        for p in sorted(kjs(d), key=lambda x: int(os.path.basename(x)[7:-5])):
            t = load(p)
            if t is None:
                print(f"{p}: unreadable")
                continue
            sc = ((t.get("hb_stats") or {}).get("hb_clock") or {}).get("slotcount")
            if sc is None:
                continue
            a = sc["accesses"] or 1
            pcs = sorted(sc.get("end_max_pcs", {}).items(), key=lambda kv: -kv[1])[:6]
            print(f"{os.path.basename(p)} {t['kernel']['kernel_name'][:40]}: events {t.get('hb_events_count')} "
                  f"accesses {sc['accesses']} in_bucket {sc['in_bucket']} visited {sc['visited']} "
                  f"tested {sc['tested']} tested/access {sc['tested'] / a:.1f} visited/access "
                  f"{sc['visited'] / a:.1f} | max met {sc['max_met']} at pc {hex(sc['max_met_pc'])} "
                  f"addr {hex(sc['max_met_addr'])} space {sc['max_met_space']} block {sc['max_met_block']} "
                  f"| end max {sc.get('end_max')} addr {hex(sc.get('end_max_addr', 0))} space "
                  f"{sc.get('end_max_space')} pcs {[(hex(int(k)), v) for k, v in pcs]} keys {sc.get('end_max_keys')}")


if __name__ == "__main__":
    cmd, *a = sys.argv[1:]
    {"shards": lambda: shards(a[0], int(a[1])), "unreadable": lambda: unreadable(a[0]),
     "mem": lambda: mem(*a), "slots": lambda: slots(*a)}[cmd]()

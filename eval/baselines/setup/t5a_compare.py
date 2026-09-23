#!/usr/bin/env python3
"""T5a: compare the collector dumps of t5a_check.sh up to what moves run to run (device
allocation addresses, renamed by rank as in setup/t8_collector_compare.py; per-edge
`dist` histograms). Prints one line per comparison:
  <prog> <conf>: main vs t5a            (installed library vs the T5a runtime, stats unset)
  <prog> hb-vc: t5a vs t5a+HB_STATS     (the stats run minus its hb_stats field)
  t5a_compare.py /mnt/beegfs/$USER/t5a_check"""
import json
import os
import sys

ADDR_MIN = 1 << 40
RUN_VARIANT = {"dist"}


def _addrs(o, out):
    if isinstance(o, dict):
        for v in o.values():
            _addrs(v, out)
    elif isinstance(o, list):
        for v in o:
            _addrs(v, out)
    elif isinstance(o, int) and not isinstance(o, bool) and o >= ADDR_MIN:
        out.add(o)


def _norm(o, rank):
    if isinstance(o, dict):
        return {k: _norm(v, rank) for k, v in o.items() if k not in RUN_VARIANT}
    if isinstance(o, list):
        return [_norm(v, rank) for v in o]
    if isinstance(o, int) and not isinstance(o, bool) and o >= ADDR_MIN:
        return f"A{rank[o]}"
    return o


def norm(path, drop=()):
    j = json.load(open(path))
    for k in drop:
        j.pop(k, None)
    s = set()
    _addrs(j, s)
    return _norm(j, {a: i for i, a in enumerate(sorted(s))})


def main(root):
    bad = 0
    for prog in sorted(os.listdir(root)):
        pairs = [("default", "main", "t5a", ()), ("hb-vc", "main", "t5a", ()),
                 ("hb-vc", "t5a", "hb-vc-stats/t5a", ("hb_stats",))]
        for conf, a, b, drop in pairs:
            da = f"{root}/{prog}/{conf}/{a}/dump"
            db = f"{root}/{prog}/{b}/dump" if "/" in b else f"{root}/{prog}/{conf}/{b}/dump"
            fa, fb = sorted(os.listdir(da)), sorted(os.listdir(db))
            same = fa == fb and all(norm(f"{da}/{f}") == norm(f"{db}/{f}", drop) for f in fa)
            bad += not same
            what = f"{a} vs {b}" + (" minus hb_stats" if drop else "")
            print(f"{prog} {conf}: {what}: {'IDENTICAL' if same else 'DIFFERENT'} up to "
                  f"device addresses and dist ({len(fa)} files)")
    print("ALL IDENTICAL" if not bad else f"{bad} DIFFERENT")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

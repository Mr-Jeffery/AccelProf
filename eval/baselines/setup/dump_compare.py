#!/usr/bin/env python3
"""Compare two collector dump directories file by file, up to what moves run to run:
device allocation addresses (renamed by rank, as setup/t8_collector_compare.py does) and
the per-edge `dist` histograms. --drop KEY removes a top-level key from the second side's
dumps first (a field a new option adds). Exit 0 iff every kernel_*.json matches.
  dump_compare.py <dir A> <dir B> [--drop hb_stats]"""
import argparse
import glob
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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--drop", action="append", default=[])
    a = ap.parse_args(argv)
    fa = sorted(os.path.basename(p) for p in glob.glob(f"{a.a}/kernel_*.json"))
    fb = sorted(os.path.basename(p) for p in glob.glob(f"{a.b}/kernel_*.json"))
    same = fa == fb and all(norm(f"{a.a}/{f}") == norm(f"{a.b}/{f}", a.drop) for f in fa)
    print(f"{'IDENTICAL' if same else 'DIFFERENT'} up to device addresses and dist "
          f"({len(fa)} vs {len(fb)} kernel dumps){' minus ' + ','.join(a.drop) if a.drop else ''}")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())

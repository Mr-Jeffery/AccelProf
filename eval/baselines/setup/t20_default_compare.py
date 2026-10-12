#!/usr/bin/env python3
"""T20 step 3: the default tool path (no YOSEMITE_HB_TRACE), dumps of t20_check.sh.
  live vs t20   up to device addresses and dist histograms, kernel.kernel_pc(_hex) dropped
                (the installed T19 library prints uninitialised memory there)
  t20 vs t20b   two runs of the T20 library: up to device addresses and dist, kernel_pc kept
                (step 0 makes it 0), and byte for byte
  t20_default_compare.py /mnt/beegfs/$USER/t20-check"""
import filecmp
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from t5a_compare import _addrs, _norm  # noqa: E402


def norm(path, drop_pc):
    j = json.load(open(path))
    if drop_pc and isinstance(j.get("kernel"), dict):
        j["kernel"].pop("kernel_pc", None)
        j["kernel"].pop("kernel_pc_hex", None)
    s = set()
    _addrs(j, s)
    return _norm(j, {a: i for i, a in enumerate(sorted(s))})


def main(root):
    bad = 0
    for prog in sorted(os.listdir(root)):
        d = {r: f"{root}/{prog}/default/{r}/dump" for r in ("live", "t20", "t20b")}
        files = {r: sorted(os.listdir(p)) for r, p in d.items()}
        pcs = set()
        for f in files["t20"]:
            k = json.load(open(f"{d['t20']}/{f}")).get("kernel", {})
            if isinstance(k, dict) and "kernel_pc" in k:
                pcs.add(k["kernel_pc"])
        for a, b, drop in (("live", "t20", True), ("t20", "t20b", False)):
            same = files[a] == files[b] and all(
                norm(f"{d[a]}/{f}", drop) == norm(f"{d[b]}/{f}", drop) for f in files[a])
            bad += not same
            print(f"{prog} default: {a} vs {b}: {'IDENTICAL' if same else 'DIFFERENT'} up to device "
                  f"addresses and dist{' (kernel_pc dropped)' if drop else ' (kernel_pc kept)'} "
                  f"({len(files[a])} files)")
        exact = files["t20"] == files["t20b"] and all(
            filecmp.cmp(f"{d['t20']}/{f}", f"{d['t20b']}/{f}", shallow=False) for f in files["t20"])
        print(f"{prog} default: t20 vs t20b byte for byte: {'IDENTICAL' if exact else 'DIFFERENT'}; "
              f"t20 kernel_pc values {sorted(pcs)}")
    print("ALL IDENTICAL" if not bad else f"{bad} DIFFERENT")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

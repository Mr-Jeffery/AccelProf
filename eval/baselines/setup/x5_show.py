#!/usr/bin/env python3
"""X5: print the SASS around a pair of pcs of one kernel, for checking a bin by hand.

  x5_show.py <dot> <mangled> <pc> [<pc> ...]            one kernel
  x5_show.py --pairs <barrier_ordered_pairs.csv> [--mode vector-clock] [--per-bin K]
                                                        the first K pairs of every (suite, bin)

For each pc: the basic block it is in (instructions with pcs, predication kept) and the block's
successors; then the BAR / WARPSYNC / EXIT / RET instructions of the kernel with the block each
sits in, and every block's successors. Uses sync_dominance.parse_dot / _label_lines; the dot is
read, nothing else.
"""
import argparse
import collections
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import x5_common as xc                       # noqa: E402
from x5_common import sd                     # noqa: E402
import pydot                                 # noqa: E402

ROOT = "/mnt/beegfs/fzheng4/cuvein_traces"


def show(dot, mangled, pcs):
    blocks, edges, entry = sd.parse_dot(dot)[mangled]
    (graph,) = pydot.graph_from_dot_file(dot)
    text = {}
    for sub in graph.get_subgraphs():
        if sub.get_name().strip('"') == "cluster_" + mangled:
            for node in sub.get_nodes():
                label = node.get_attributes().get("label")
                if label is None:
                    continue
                text[node.get_name().strip('"')] = [
                    ln.strip() for ln in sd._label_lines(label.strip('"'))
                    if sd._INSTR.match(ln)]
    succ = {}
    for s, d in edges:
        succ.setdefault(s, []).append(d)
    where = {pc: b for b, ins in blocks.items() for pc, _ in ins}
    print(f"kernel {mangled}  blocks {len(blocks)}  entry {entry}")
    for pc in pcs:
        b = where.get(pc)
        print(f"\n== pc {pc:#x} is in block {b}; successors {succ.get(b, [])}")
        for ln in text.get(b, []):
            print("   ", ln)
    print("\n== BAR / WARPSYNC / EXIT / RET of the kernel")
    order = sorted(blocks.items(), key=lambda kv: kv[1][0][0] if kv[1] else 0)
    for b, ins in order:
        for pc, op in ins:
            if op.split(".")[0] in ("BAR", "WARPSYNC", "EXIT", "RET"):
                line = next((ln for ln in text.get(b, []) if ln.startswith(f"{pc:04x}:")), op)
                print(f"    {line}   [{b}]")
    print("\n== block successors")
    for b, ins in order:
        if ins:
            print(f"    {b} ({ins[0][0]:#x}-{ins[-1][0]:#x}) -> {succ.get(b, [])}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("args", nargs="*")
    ap.add_argument("--pairs")
    ap.add_argument("--mode", default="vector-clock")
    ap.add_argument("--per-bin", type=int, default=1)
    a = ap.parse_args()
    if not a.pairs:
        show(a.args[0], a.args[1], [int(p, 16) for p in a.args[2:]])
        return
    seen = collections.Counter()
    for r in csv.DictReader(open(a.pairs)):
        key = (r["suite"], r["bin"])
        if r["mode"] != a.mode or seen[key] >= a.per_bin:
            continue
        seen[key] += 1
        dotname, mangled = r["kernel"].split("::", 1)
        print("\n" + "=" * 100)
        print(f"{r['suite']} / {r['bin']}: {r['id']}  {r['mode']}  pair {r['anc_pc']} -> "
              f"{r['cur_pc']}  {r['space']} {r['race_type']}  classes {r['classes']}")
        print(f"detail {r['detail']}")
        show(f"{ROOT}/{r['store']}/{r['id']}/dots/{dotname}", mangled,
             [int(r["anc_pc"], 16), int(r["cur_pc"], 16)])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""T6 (design/T6_REVIEW.md, "Evidence on the two settled choices"): static scans of the kept
sm_89 SASS CFGs (the nvdisasm -bbcfg dots of the ScoR artifacts and of every home
eval/baselines/traces_keep*/<id>/dots/), deduplicated by content.

  1. what surrounds each BAR.* instruction (is there a MEMBAR next to BAR.SYNC?)
  2. the fence-like opcodes and their most common two-before/one-after contexts
  3. the engine-timeout programs (setup/engine_timeout_ids.txt) by whether their SASS has
     atomics and/or barriers

Regex over the dot labels only (no pydot: 900+ dots parse too slowly for the login node).
    .env/bin/python eval/baselines/setup/t6_sass_scan.py        (from the checkout root)
"""
import collections
import glob
import hashlib
import os
import re

INS = re.compile(r"([0-9a-f]{4,}):(?:\\ )+(?:@!?U?P[T\d]+(?:\\ )+)?([A-Z][A-Z0-9_.]*)")
LABEL = re.compile(r'label="\{(.*?)\}"\]', flags=re.S)
FENCE = ("MEMBAR", "ERRBAR", "CCTL", "BAR", "WARPSYNC", "DEPBAR", "SYNCS", "ARRIVES")


def blocks(path):
    """Instruction mnemonics per basic block of one dot file."""
    txt = open(path, errors="replace").read()
    return [[m.group(2) for m in INS.finditer(lab)] for lab in LABEL.findall(txt)], txt


def main():
    dots = sorted(glob.glob("ScoR/microbenchmarks/artifacts/*/*_extracted_cubins/*.dot") +
                  glob.glob("eval/baselines/traces_keep*/*/dots/*.dot"))
    seen, bar, fam, ctx = set(), collections.Counter(), collections.Counter(), collections.Counter()
    for p in dots:
        bbs, txt = blocks(p)
        h = hashlib.md5(txt.encode()).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        for ops in bbs:
            for i, op in enumerate(ops):
                if op.startswith(FENCE):
                    fam[op] += 1
                if op.startswith("BAR."):
                    prev = ops[i - 1] if i else ""
                    nxt = ops[i + 1] if i + 1 < len(ops) else ""
                    bar[(".".join(op.split(".")[:2]), prev.startswith("MEMBAR"),
                         nxt.startswith("MEMBAR"))] += 1
                if op in ("CCTL.IVALL", "ERRBAR") or op.startswith("MEMBAR"):
                    ctx[(op, tuple(ops[max(0, i - 2):i]), tuple(ops[i + 1:i + 2]))] += 1
    print(f"distinct dot files: {len(seen)} (of {len(dots)})")
    print("1. BAR instructions: (opcode, MEMBAR before, MEMBAR after) -> count")
    for k, n in bar.most_common():
        print(f"   {n:5d} {k}")
    print("2. fence-like opcodes")
    for k, n in fam.most_common():
        print(f"   {n:5d} {k}")
    print("   top contexts (op, two before, one after)")
    for k, n in ctx.most_common(12):
        print(f"   {n:5d} {k}")
    print("3. engine-timeout programs by SASS content")
    ids = [ln.strip() for ln in open("eval/baselines/setup/engine_timeout_ids.txt")
           if ln.strip() and not ln.startswith("#")]
    cats = collections.defaultdict(list)
    for i in ids:
        dd = next((g for s in sorted(glob.glob("eval/baselines/traces_keep*/"))
                   if (g := glob.glob(os.path.join(s, i, "dots", "*.dot")))), [])
        if not dd:
            cats["no kept dots"].append(i)
            continue
        ops = collections.Counter(op.split(".")[0] for d in dd for bb in blocks(d)[0] for op in bb)
        atom = any(ops[k] for k in ("ATOM", "ATOMG", "ATOMS", "RED"))
        cats[("atomics" if atom else "no atomics") + (" + barriers" if ops["BAR"] else "")].append(i)
    for k, v in sorted(cats.items(), key=lambda kv: -len(kv[1])):
        print(f"   {len(v):3d} {k}: {', '.join(x.split('-')[0] + '-' + x.split('-')[1] for x in v[:8])}"
              f"{' ...' if len(v) > 8 else ''}")


if __name__ == "__main__":
    main()

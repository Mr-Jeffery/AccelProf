#!/usr/bin/env python3
"""T10: inventory of the SASS strength tokens in nvdisasm -bbcfg dots.

For every memory opcode (loads, stores, atomics, reductions) found in the given dots,
count how often each opcode shape occurs and in how many dots, and classify it with
sync_dominance's strength rule under a policy (default: the current default). Used to
check the token grammar the strength column relies on (.STRONG.<scope> on LD/ST/ATOM/RED)
against the real corpus before and after the change.

    python eval/baselines/t10_token_scan.py [--policy P] <dot|dir> [...]
"""
import argparse
import collections
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python"))
import sync_dominance as sd  # noqa: E402

_MEM = {"LD", "LDG", "LDS", "LDL", "LDSM", "ST", "STG", "STS", "STL",
        "ATOM", "ATOMG", "ATOMS", "RED", "REDG", "REDS", "LDGSTS"}


def dots_of(paths):
    for p in paths:
        p = Path(p)
        if p.is_dir():
            yield from sorted(p.rglob("*.dot"))
        elif p.suffix == ".dot":
            yield p


def opcodes_of(dot):
    """Every (pc, opcode) of the dot's instruction labels; regex over the labels, not
    pydot (hundreds of dots through pydot are slow and memory-hungry)."""
    txt = dot.read_text(errors="replace")
    out = []
    for label in txt.split('label="')[1:]:
        label = label.split('"]', 1)[0]
        for line in sd._label_lines(label):
            m = sd._INSTR.match(line)
            if m:
                out.append((int(m.group(1), 16), m.group(2)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--policy", default=None)
    ap.add_argument("--all", action="store_true", help="also list weak shapes")
    a = ap.parse_args(argv)
    count, files = collections.Counter(), collections.Counter()
    ndots = 0
    for dot in dots_of(a.paths):
        ndots += 1
        seen = set()
        for _, op in opcodes_of(dot):
            if op.split(".")[0] in _MEM:
                count[op] += 1
                seen.add(op)
        for op in seen:
            files[op] += 1
    print(f"# {ndots} dots, policy {sd.strong_ldst_policy(a.policy)}")
    print(f"# {'n':>7} {'dots':>5}  {'rmw':>4} {'strength':>9}  opcode")
    for op in sorted(count, key=lambda o: (o.split(".")[0], -count[o], o)):
        rmw = sd.atomic_scope(op)
        s = sd.coherent_scope(op, a.policy)
        if not a.all and s is None and "STRONG" not in op.split(".") and rmw is None:
            continue
        st = "weak" if s is None else sd.SCOPES[s]
        print(f"  {count[op]:7d} {files[op]:5d}  {'rmw' if rmw is not None else '-':>4} "
              f"{st:>9}  {op}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

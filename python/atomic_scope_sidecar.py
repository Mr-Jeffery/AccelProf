#!/usr/bin/env python3
"""Emit a `pc scope` sidecar for the analyzer's dynamic-HB engine.

The C++ engine (pc_dependency_analysis.cpp) needs each atomic PC's coherence scope,
which is a static SASS property only visible in the CFG. getall.sh generates the
CFG .dot before accelprof runs, so we distill it here into a tiny text file the
tool reads via YOSEMITE_ATOMIC_SCOPE_FILE. One line per atomic PC:  `<pc> <scope>`
with scope matching sync_dominance.SCOPES (NONE=0, BLOCK=2, GRID=3).

ponytail: pc offsets are merged across all dots/kernels of the binary. Corpus
binaries are single-kernel so offsets don't collide; key by (kernel, pc) if a
multi-kernel binary ever shares an offset with a different scope.

Usage:  python atomic_scope_sidecar.py <dot> [<dot> ...] -o atomic_scope.txt
"""
import argparse
import sys
from pathlib import Path

import sync_dominance as sd


def collect(dot_paths):
    scopes = {}  # pc -> scope
    for dp in dot_paths:
        # A binary emits one .dot per cubin/arch; empty stubs have no kernel
        # clusters. Skip those (mirrors the oracle trying each dot), don't abort.
        try:
            kernels = sd.parse_dot(dp)
        except sd.AlignmentError:
            continue
        for kern in kernels.values():
            eng = sd.HBGraph(*kern)
            for pc, op in eng.pc_opcode.items():
                s = sd.atomic_scope(op)
                if s is not None:
                    scopes[pc] = s
    return scopes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("dots", nargs="+", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    args = ap.parse_args(argv)
    scopes = collect(args.dots)
    lines = [f"{pc} {s}" for pc, s in sorted(scopes.items())]
    args.output.write_text("\n".join(lines) + ("\n" if lines else ""))
    print(f"[atomic_scope_sidecar] {len(scopes)} atomic pc(s) -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

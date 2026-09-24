#!/usr/bin/env python3
"""Emit the coherent-access sidecar for the analyzer's dynamic-HB engine.

The C++ engine (pc_dependency_analysis.cpp) needs each atomic PC's coherence scope,
which is a static SASS property only visible in the CFG. getall.sh generates the
CFG .dot before accelprof runs, so we distill it here into a tiny text file the
tool reads via YOSEMITE_ATOMIC_SCOPE_FILE. One line per coherent-access PC:

    <pc> <scope> <kind> <kernel>

scope matches sync_dominance.SCOPES (NONE=0, BLOCK=2, GRID=3); kind is `rmw` (an
atomic RMW: release/acquire point) or `ldst` (a .STRONG load/store — cuda::atomic
load()/store() — coherent pairwise only, per the --strong-ldst policy); kernel is the
demangled kernel name with all whitespace removed (what the engine derives from the
launch's kernel_name). pc offsets are function-relative, so the table is per kernel:
a multi-kernel binary routinely has a plain store in one kernel at the offset of an
atomic in another. Every kernel of the binary is declared with a `# kernel <kernel>`
line, so one without any coherent pc gets an EMPTY table instead of the merged one.
`# async <pc> <kernel>` lines list the kernel's cp.async (LDGSTS) pcs (T1a: accesses of the
issuing thread's async agent); engines older than T1a skip them as comments.

Usage:  python atomic_scope_sidecar.py <dot> [<dot> ...] -o atomic_scope.txt
"""
import argparse
import re
import sys
from pathlib import Path

import sync_dominance as sd


def kernel_key(mangled):
    """Engine-side kernel key: demangled name sans whitespace (mangled if no c++filt)."""
    return re.sub(r"\s+", "", sd._demangle(mangled) or mangled)


def collect(dot_paths, policy=None, asyncs=None):
    """-> ({(kernel_key, pc): (scope, kind)}, [kernel_key, ...]); asyncs (a dict, if given)
    receives {kernel_key: {cp.async (LDGSTS) pcs}} (T1a), the union over the dots like the
    coherent-pc table (a multi-arch binary has one cubin per arch)."""
    policy = sd.strong_ldst_policy(policy)
    scopes, names = {}, []
    for dp in dot_paths:
        # A binary emits one .dot per cubin/arch; empty stubs have no kernel
        # clusters. Skip those (mirrors the oracle trying each dot), don't abort.
        try:
            kernels = sd.parse_dot(dp)
        except sd.AlignmentError:
            continue
        for mangled, kern in kernels.items():
            key = kernel_key(mangled)
            names.append(key)
            g = sd.HBGraph(*kern)
            if asyncs is not None and sd.async_pcs(g):
                asyncs.setdefault(key, set()).update(sd.async_pcs(g))
            for pc, op in g.pc_opcode.items():
                s = sd.coherent_scope(op, policy)
                if s is not None:
                    kind = "rmw" if sd.atomic_scope(op) is not None else "ldst"
                    scopes[(key, pc)] = (s, kind)
    return scopes, sorted(set(names))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("dots", nargs="+", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--strong-ldst", choices=sd.STRONG_LDST_POLICIES,
                    help="which .STRONG loads/stores are coherent accesses "
                         "(default: $CUVEIN_STRONG_LDST or 'generic')")
    args = ap.parse_args(argv)
    asyncs = {}
    scopes, names = collect(args.dots, args.strong_ldst, asyncs)
    lines = [f"# kernel {key}" for key in names]
    lines += [f"{pc} {s} {kind} {key}" for (key, pc), (s, kind) in sorted(scopes.items())]
    # T1a: cp.async (LDGSTS) pcs as comment lines -- an engine older than T1a skips them
    # (it would otherwise read an unknown kind as an atomic RMW)
    lines += [f"# async {pc} {key}" for key, pcs in sorted(asyncs.items()) for pc in sorted(pcs)]
    args.output.write_text("\n".join(lines) + ("\n" if lines else ""))
    print(f"[atomic_scope_sidecar] {len(scopes)} coherent pc(s), "
          f"{sum(len(v) for v in asyncs.values())} cp.async pc(s) -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

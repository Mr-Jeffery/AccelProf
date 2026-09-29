#!/usr/bin/env python3
"""Emit the coherent-access sidecar for the analyzer's dynamic-HB engine.

The C++ engine (pc_dependency_analysis.cpp) needs each atomic PC's coherence scope,
which is a static SASS property only visible in the CFG. getall.sh generates the
CFG .dot before accelprof runs, so we distill it here into a tiny text file the
tool reads via YOSEMITE_ATOMIC_SCOPE_FILE. One line per coherent-access PC:

    <pc> <scope> <kind> <kernel>

scope matches sync_dominance.SCOPES (NONE=0, BLOCK=2, GRID=3); kind is `rmw` (an
atomic RMW: release/acquire point) or `ldst` (a strong load/store — cuda::atomic
load()/store(), volatile — per the --strong-ldst policy); kernel is the
demangled kernel name with all whitespace removed (what the engine derives from the
launch's kernel_name). pc offsets are function-relative, so the table is per kernel:
a multi-kernel binary routinely has a plain store in one kernel at the offset of an
atomic in another. Every kernel of the binary is declared with a `# kernel <kernel>`
line, so one without any coherent pc gets an EMPTY table instead of the merged one.
`# async <pc> <kernel>` lines list the kernel's cp.async (LDGSTS) pcs (T1a: accesses of the
issuing thread's async agent); engines older than T1a skip them as comments.

The strength column (T10, D9; under the default policy `token` only):

    # strength <pc> <strong|weak> <scope|-> <kernel>

one line for EVERY memory pc of the kernel -- strength and scope read off the SASS token
(sync_dominance.coherent_scope: .STRONG.<scope> on a load, store, atomic or reduction;
no token or an unknown scope is weak). An engine since T10 takes a non-RMW record's key
and moral strength from these lines; an older engine skips them as comments and reads the
`ldst` lines, which under `token` list the same strong pcs with the same scopes, so both
engines compute the same races from one sidecar. Under a pre-T10 policy (generic, all,
none) no strength line is written and the file is the pre-T10 sidecar.

The gate table (T12, hb_proof.tex Definition "Gate", design/instance_gate.md section 4):

    # gate-kernel <kernel>
    # gate <rmw pc> rel <kernel> <pc> <pc> ...
    # gate <rmw pc> acq <kernel> <pc> <pc> ...

for every RMW pc of scope block/grid: the record pcs p with fenced(p, r, scope(r), release)
(`rel`) and q with fenced(r, q, scope(r), acquire) (`acq`), from sync_dominance.gate_table --
the same table hb_oracle.py evaluates. The FENCED pcs are listed, so a pc the table does not
know is unfenced (the gate errs toward reporting). A kernel in several cubins gets the
intersection. An engine older than T12 skips the lines; an engine since T12 uses the instance
gate for a kernel with a `# gate-kernel` line (unless YOSEMITE_HB_GATE=trusting) and the
trusting gate otherwise. --gate trusting writes no gate lines.

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


def collect(dot_paths, policy=None, asyncs=None, mem=None, gates=None):
    """-> ({(kernel_key, pc): (scope, kind)}, [kernel_key, ...]); asyncs (a dict, if given)
    receives {kernel_key: {cp.async (LDGSTS) pcs}} (T1a), the union over the dots like the
    coherent-pc table (a multi-arch binary has one cubin per arch); mem (a dict, if given)
    receives {kernel_key: {memory pcs}}, the domain of the strength column (T10); gates (a
    dict, if given) receives {kernel_key: {rmw pc: (rel-fenced, acq-fenced)}} (T12),
    intersected over the dots that hold the kernel."""
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
            if gates is not None:
                tab = {r: (rel, acq) for r, (sc, rel, acq) in g.gate_table().items()
                       if sc > sd.NONE}
                old = gates.get(key)
                gates[key] = tab if old is None else \
                    {r: (old[r][0] & v[0], old[r][1] & v[1]) if r in old else (frozenset(),) * 2
                     for r, v in tab.items()}
            if asyncs is not None and sd.async_pcs(g):
                asyncs.setdefault(key, set()).update(sd.async_pcs(g))
            for pc, op in g.pc_opcode.items():
                if mem is not None and sd.classify(op) == "mem":
                    mem.setdefault(key, set()).add(pc)
                s = sd.coherent_scope(op, policy)
                if s is not None:
                    kind = "rmw" if sd.atomic_scope(op) is not None else "ldst"
                    scopes[(key, pc)] = (s, kind)
    return scopes, sorted(set(names))


def strength_lines(scopes, mem):
    """T10: `# strength <pc> <strong|weak> <scope|-> <kernel>` for every memory pc, from the
    same merged table as the coherent-pc lines (so an engine reading either agrees)."""
    out = []
    for key in sorted(mem):
        for pc in sorted(mem[key]):
            s = scopes.get((key, pc))
            out.append(f"# strength {pc} strong {s[0]} {key}" if s is not None
                       else f"# strength {pc} weak - {key}")
    return out


def gate_lines(gates):
    """T12: the gate table as sidecar comment lines."""
    out = [f"# gate-kernel {key}" for key in sorted(gates)]
    for key in sorted(gates):
        for r, (rel, acq) in sorted(gates[key].items()):
            for side, pcs in (("rel", rel), ("acq", acq)):
                out.append(" ".join([f"# gate {r} {side} {key}", *map(str, sorted(pcs))]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("dots", nargs="+", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--strong-ldst", choices=sd.STRONG_LDST_POLICIES,
                    help="which .STRONG loads/stores are strong: 'token' (every one with a "
                         "known scope, T10; writes the strength column) or a pre-T10 "
                         "ablation (default: $CUVEIN_STRONG_LDST or 'token')")
    ap.add_argument("--gate", choices=("instance", "trusting"),
                    help="write the instance gate's table (T12) or none "
                         "(default: $CUVEIN_GATE or 'instance')")
    args = ap.parse_args(argv)
    policy = sd.strong_ldst_policy(args.strong_ldst)
    asyncs, mem = {}, {}
    gates = {} if sd.gate_mode(args.gate) == "instance" else None
    scopes, names = collect(args.dots, policy, asyncs, mem, gates)
    lines = [f"# kernel {key}" for key in names]
    lines += [f"{pc} {s} {kind} {key}" for (key, pc), (s, kind) in sorted(scopes.items())]
    # T1a: cp.async (LDGSTS) pcs as comment lines -- an engine older than T1a skips them
    # (it would otherwise read an unknown kind as an atomic RMW)
    lines += [f"# async {pc} {key}" for key, pcs in sorted(asyncs.items()) for pc in sorted(pcs)]
    # T10: the strength column, comment lines as well (an engine older than T10 skips them)
    strength = strength_lines(scopes, mem) if policy == "token" else []
    lines += strength
    glines = gate_lines(gates) if gates is not None else []   # T12
    lines += glines
    args.output.write_text("\n".join(lines) + ("\n" if lines else ""))
    print(f"[atomic_scope_sidecar] {len(scopes)} coherent pc(s), "
          f"{sum(len(v) for v in asyncs.values())} cp.async pc(s), "
          f"{len(strength)} strength line(s) ({policy}), "
          f"{len(glines)} gate line(s) -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

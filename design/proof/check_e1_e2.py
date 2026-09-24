#!/usr/bin/env python3
"""Exercise findings E1 and E2 of design/algorithms.md section 5 on the real oracle.

Runs python/hb_oracle.py (unmodified, and with the atomic branch reordered to the
proof's publish-then-tick) over hand-made `hb_events` dumps that use the oracle's real
record format, DOT parser and opcode classification. No GPU, no real trace: the dumps
are synthetic, so this is evidence about the algorithm, not about the corpus.

    cd <checkout> && .env/bin/python design/proof/check_e1_e2.py

Output on cuVein 3331d35 (2026-09-24, networkx 3.6.1 / pydot 4.0.1):

  E1 -- rtraw, grid-scope CAS/EXCH on f, plain x  (policy generic)
    checked-in oracle: block 0 first (the miss)  races=0 []                           sync_only=[[24, 40, 1]]
    publish-then-tick: block 0 first (the miss)  races=1 [('RAW', '0x28', 0, '0x18', 1024, '0x1000')]
    checked-in oracle: u.read before t.write     races=1 [('WAR', '0x18', 1024, '0x28', 0, '0x1000')]
    publish-then-tick: u.read before t.write     races=1 [('WAR', '0x18', 1024, '0x28', 0, '0x1000')]
    checked-in oracle: block 1 first (ordered)   races=0 []
    publish-then-tick: block 1 first (ordered)   races=0 []
  E2 -- A: ST.STRONG.SYS x; B: ST.STRONG.SYS x; bar(B,C); C: LDG x
    checked-in oracle, policy generic            races=0 []                           sync_only=[]
    checked-in oracle, policy none               races=1 [('WAW', '0x10', 0, '0x18', 1024, '0x1000')]

E1: the checked-in order misses (t.write x, u.read x) exactly when the write precedes
the read in seq; the reordered oracle reports it; the genuinely ordered schedule stays
silent in both.  E2: with the default policy nothing at x is reported (not even by the
second clock); policy none reports the (w0, w1) pair, the location-level witness.

T6 item (c) turns these into pytest tests on real kernels (a strict xfail each until
T9 / D6 land); this script is the seed, not the test.
"""
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = HERE.parent.parent / "python"
sys.path.insert(0, str(PY))
import hb_oracle  # noqa: E402  (the checked-in oracle)

FULL = 0xffffffff
F, X = 0x2000, 0x1000


def dot(name, instrs):
    body = "\\l".join(f"{pc:04x}: {op} ;" for pc, op in instrs) + "\\l"
    return (f'digraph "x" {{\n subgraph "cluster_{name}" {{\n'
            f'  "{name}" [shape=Mrecord, label="{{{body}}}"];\n }}\n}}\n')


def mem(seq, typ, block, warp, pc, addr, space="global"):
    return {"seq": seq, "type": typ, "block": block, "warp": warp, "pc": pc,
            "space": space, "size": 4, "active_mask": 1,
            "lanes": [{"lane": 0, "addr": addr}]}


def bar(seq, block, warp, bar_index=0, thread_count=0):
    return {"seq": seq, "type": "barrier", "block": block, "warp": warp,
            "bar_index": bar_index, "thread_count": thread_count, "active_mask": FULL}


def dump(name, events, block_tc):
    return {"kernel": {"kernel_name": name, "block_thread_count": block_tc},
            "hb_events": events}


def run(oracle, dot_text, trace, policy, workdir):
    d, t = workdir / "check.dot", workdir / "check.json"
    d.write_text(dot_text)
    t.write_text(json.dumps(trace))
    rep = oracle.analyze(str(d), str(t), strong_ldst=policy)
    races = [(r["kind"], hex(r["a_pc"]) if r["a_pc"] is not None else None, r["a_tid"],
              hex(r["b_pc"]), r["b_tid"], hex(r["addr"])) for r in rep["races"]]
    return races, rep["races_sync_only"]


def patched_oracle(workdir):
    """hb_oracle with Algorithm 1's order: publish the pre-tick clock, record the RMW at
    the pre-tick epoch, then tick.  Fails loudly if the atomic branch moved."""
    src = (PY / "hb_oracle.py").read_text()
    old = ("                vc[t][t] = own(t) + 1\n"
           "                released[loc] = (VC(vc[t]), my_block, my_scope)\n"
           "                last_write[loc] = (t, vc[t][t], owns(t), pc, my_coh, my_block)\n")
    new = ("                released[loc] = (VC(vc[t]), my_block, my_scope)\n"
           "                last_write[loc] = (t, vc[t][t], owns(t), pc, my_coh, my_block)\n"
           "                vc[t][t] = own(t) + 1\n")
    assert src.count(old) == 1, "hb_oracle.py atomic branch not found verbatim; re-derive"
    (workdir / "hb_oracle_ptt.py").write_text(src.replace(old, new))
    sys.path.insert(0, str(workdir))
    return importlib.import_module("hb_oracle_ptt")


def rtraw(order, name):
    ev, s = [], 0
    for typ, block, pc, addr in order:
        s += 1
        ev.append(mem(s, typ, block, 0, pc, addr))
    return dump(name, ev, 32)


def main():
    import tempfile
    workdir = Path(tempfile.mkdtemp(prefix="check_e1_e2_"))
    ptt = patched_oracle(workdir)

    # E1: t = block 0, u = block 1; lock = CAS, unlock = EXCH, both .STRONG.GPU
    K1 = "rtraw_kernel"
    D1 = dot(K1, [(0x10, "ATOMG.E.CAS.STRONG.GPU"), (0x18, "LDG.E"),
                  (0x20, "ATOMG.E.EXCH.STRONG.GPU"), (0x28, "STG.E"), (0x30, "EXIT")])
    t_cs = [("atomic", 0, 0x10, F), ("read", 0, 0x18, X), ("atomic", 0, 0x20, F)]
    u_cs = [("atomic", 1, 0x10, F), ("read", 1, 0x18, X), ("atomic", 1, 0x20, F)]
    t_w = [("write", 0, 0x28, X)]
    cases = [("block 0 first (the miss)", t_cs + t_w + u_cs),
             ("u.read before t.write", t_cs + u_cs[:2] + t_w + u_cs[2:]),
             ("block 1 first (ordered)", u_cs + t_cs + t_w)]
    print("E1 -- rtraw, grid-scope CAS/EXCH on f, plain x  (policy generic)")
    for label, order in cases:
        tr = rtraw(order, K1)
        for oname, o in (("checked-in oracle", hb_oracle), ("publish-then-tick", ptt)):
            races, so = run(o, D1, tr, "generic", workdir)
            print(f"  {oname}: {label:28s} races={len(races)} {races} sync_only={so}")

    # E2: A = block 0; B, C = block 1 (warps 0 and 1 of a 64-thread block)
    K2 = "e2_kernel"
    D2 = dot(K2, [(0x10, "ST.E.STRONG.SYS"), (0x18, "ST.E.STRONG.SYS"),
                  (0x20, "BAR.SYNC.DEFER_BLOCKING"), (0x28, "LDG.E"), (0x30, "EXIT")])
    E2 = dump(K2, [mem(1, "write", 0, 0, 0x10, X), mem(2, "write", 1, 0, 0x18, X),
                   bar(3, 1, 0), bar(4, 1, 1), mem(5, "read", 1, 1, 0x28, X)], 64)
    print("E2 -- A: ST.STRONG.SYS x; B: ST.STRONG.SYS x; bar(B,C); C: LDG x")
    for pol in ("generic", "none"):
        races, so = run(hb_oracle, D2, E2, pol, workdir)
        print(f"  checked-in oracle, policy {pol:8s}          races={len(races)} {races} sync_only={so}")


if __name__ == "__main__":
    main()

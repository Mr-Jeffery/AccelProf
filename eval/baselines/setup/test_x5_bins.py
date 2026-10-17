#!/usr/bin/env python3
"""Hand-built CFGs for barrier_ordered_bins.CfgBinner: one per bin, each checked against the
rule the bin states (run: <env>/bin/python eval/baselines/setup/test_x5_bins.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import barrier_ordered_bins as bob               # noqa: E402
from x5_common import sd                         # noqa: E402

LD, ST, BAR, WS, EXIT = "LDG.E", "STG.E", "BAR.SYNC.DEFER_BLOCKING", "WARPSYNC", "EXIT"


def binner(blocks, edges, entry="B0", ops=None):
    eng = sd.HBGraph({b: [i if isinstance(i, sd._Ins) else sd._Ins(i) for i in ins]
                      for b, ins in blocks.items()}, edges, entry)
    return bob.CfgBinner(eng, ops or {})


def check(name, got, want):
    ok = got[0] == want
    print(("ok   " if ok else "FAIL ") + f"{name}: {got[0]} (want {want}) {got[1]}")
    return ok


def main():
    res = []
    # 1. loop-carried: store, barrier, load in one self-loop
    b = binner({"B0": [(0x0, LD)], "B1": [(0x10, ST), (0x20, BAR), (0x30, LD)], "B2": [(0x40, EXIT)]},
               [("B0", "B1"), ("B1", "B1"), ("B1", "B2")])
    res.append(check("loop with a barrier", b.bin(0x10, 0x30), "loop-carried"))
    # 1b. the same loop without a barrier is not loop-carried (and no barrier lies between)
    b = binner({"B0": [(0x0, LD)], "B1": [(0x10, ST), (0x30, LD)], "B2": [(0x40, EXIT)]},
               [("B0", "B1"), ("B1", "B1"), ("B1", "B2")])
    res.append(check("loop without a barrier", b.bin(0x10, 0x30), "other"))
    # 2. partial participation: a WARPSYNC between the accesses
    b = binner({"B0": [(0x0, ST), (0x10, WS), (0x20, LD), (0x30, EXIT)]}, [])
    res.append(check("warpsync between", b.bin(0x0, 0x20), "partial participation"))
    # 2b. a BAR with a nonzero count operand; BAR.RED's predicate operand is not a count
    ops = {0x10: (BAR, ["0x1", "0x40"])}
    b = binner({"B0": [(0x0, ST), (0x10, BAR), (0x20, LD), (0x30, EXIT)]}, [], ops=ops)
    res.append(check("bar with a count", b.bin(0x0, 0x20), "partial participation"))
    ops = {0x10: ("BAR.RED.POPC.DEFER_BLOCKING", ["0x0", "P0"])}
    b = binner({"B0": [(0x0, ST), (0x10, "BAR.RED.POPC.DEFER_BLOCKING"), (0x20, LD), (0x30, EXIT)]},
               [], ops=ops)
    res.append(check("bar.red with a predicate", b.bin(0x0, 0x20), "other"))
    # 3. early exit: the branch after the store can exit; the barrier is on the other path only
    b = binner({"B0": [(0x0, ST)], "B1": [(0x10, EXIT)], "B2": [(0x20, BAR), (0x30, LD), (0x40, EXIT)]},
               [("B0", "B1"), ("B0", "B2")])
    res.append(check("exit path skipping the barrier", b.bin(0x0, 0x30), "early exit"))
    # 4. branch arm: the barrier sits in one arm of a diamond, both arms reach the join
    b = binner({"B0": [(0x0, ST)], "B1": [(0x10, BAR), (0x20, LD)], "B2": [(0x30, "NOP")],
                "B3": [(0x40, EXIT)]},
               [("B0", "B1"), ("B0", "B2"), ("B1", "B3"), ("B2", "B3")])
    res.append(check("barrier in one arm", b.bin(0x0, 0x20), "branch arm"))
    # 5. other: the barrier dominates the later access and post-dominates the earlier one
    b = binner({"B0": [(0x0, ST), (0x10, BAR), (0x20, LD), (0x30, EXIT)]}, [])
    res.append(check("straight line", b.bin(0x0, 0x20), "other"))
    # nvdisasm ends a basic block at a predicated EXIT (the `exit0` port), so a guard is a block's
    # last instruction with a fall-through edge. One before both accesses is not an early exit ...
    g = sd._Ins((0x0, EXIT))
    g.pred = True
    b = binner({"B0": [g], "B1": [(0x10, ST), (0x20, BAR), (0x30, LD), (0x40, EXIT)]},
               [("B0", "B1")])
    res.append(check("guard exit before u", b.bin(0x10, 0x30), "other"))
    # ... one between the store and the barrier is (the thread that exits never arrives)
    g = sd._Ins((0x10, EXIT))
    g.pred = True
    b = binner({"B0": [(0x0, ST), g], "B1": [(0x20, BAR), (0x30, LD), (0x40, EXIT)]},
               [("B0", "B1")])
    res.append(check("guard exit between u and the barrier", b.bin(0x0, 0x30), "early exit"))
    # precedence: a loop with a barrier and a WARPSYNC is loop-carried, not partial
    b = binner({"B0": [(0x0, LD)], "B1": [(0x10, ST), (0x20, BAR), (0x24, WS), (0x30, LD)],
                "B2": [(0x40, EXIT)]}, [("B0", "B1"), ("B1", "B1"), ("B1", "B2")])
    res.append(check("loop beats warpsync", b.bin(0x10, 0x30), "loop-carried"))
    print(f"{sum(res)}/{len(res)} passed")
    return 0 if all(res) else 1


if __name__ == "__main__":
    sys.exit(main())

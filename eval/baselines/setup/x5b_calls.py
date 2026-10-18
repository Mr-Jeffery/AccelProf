#!/usr/bin/env python3
"""X5 byte pairs: the CALL sites and called subroutines of a dot, with context (read only).

  x5b_calls.py <dot> [<dot> ...]

For every cluster: each CALL instruction with the 3 instructions before and after it, the NOP
instructions, and the full body of every cluster whose name contains 'warpsync'.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import x5_common as xc                       # noqa: E402,F401
from x5_common import sd                     # noqa: E402
import pydot                                 # noqa: E402

for dot in sys.argv[1:]:
    print(f"########## {dot}")
    (graph,) = pydot.graph_from_dot_file(dot)
    for sub in graph.get_subgraphs():
        name = sub.get_name().strip('"')
        lines = []
        for node in sub.get_nodes():
            label = node.get_attributes().get("label")
            if label is None:
                continue
            lines += [ln.strip() for ln in sd._label_lines(label.strip('"')) if sd._INSTR.match(ln)]
        lines.sort(key=lambda ln: int(ln.split(":")[0], 16))
        print(f"== {name}: {len(lines)} instructions")
        if "warpsync" in name:
            for ln in lines:
                print("    ", ln)
            continue
        for i, ln in enumerate(lines):
            op = sd._INSTR.match(ln).group(3)
            if op.startswith("CALL"):
                print("   -- call site")
                for x in lines[max(0, i - 3): i + 4]:
                    print("    ", x)
            elif op.startswith("NOP"):
                print("   nop:", ln)

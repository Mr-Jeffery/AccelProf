#!/usr/bin/env python3
"""C6b step 4: assemble eval/CO_CHAIN_B.md from the narrative parts (c6b-step4/doc_*.md) and the generated fragments in
eval/results/co-chain-b/step4/ (tables/c6b_tables.md, detect/c6b_detect.md, cost/cost.md, retime_summary.md, step3_fragment.md).
Headings of an included fragment are demoted one level where noted."""
import os
import re

S4 = "/home/fzheng4/wt-c6b/eval/baselines/setup"   # narrative parts: c6b_doc_head.md, c6b_doc_tail.md, c6b_doc_retime.md
W = "/home/fzheng4/wt-c6b"
D = f"{W}/eval/results/co-chain-b/step4"


def rd(p):
    return open(p).read() if os.path.exists(p) else f"(missing: {p})\n"


def demote(t):
    return re.sub(r"(?m)^(#{2,5}) ", lambda m: m.group(1) + "# ", t)


detect = rd(f"{D}/detect/c6b_detect.md")
head, moved = detect.split("## What moved against C6", 1)
fp_part = head.split("## False reports: the split by how the verdict step found them", 1)
fp_checks = fp_part[0]
fp_body = "## False reports: the split by how the verdict step found them" + fp_part[1] if len(fp_part) > 1 else head
moved_body = moved.split("\n", 1)[1]
mv = re.split(r"(?m)^### (?=Pair-level moves against C6|Derived and rescued counts|lock_rtraw and matrix)", moved_body)
assert len(mv) == 4, len(mv)
rep = {
    "@@tables@@": demote(rd(f"{D}/tables/c6b_tables.md")),
    "@@fp_checks@@": fp_checks.strip(),
    "@@fp@@": demote(fp_body.split("\n", 1)[1]),
    "@@moved1@@": demote(mv[0]),
    "@@moved2@@": demote("### " + mv[1] + "### " + mv[2]),
    "@@moved3@@": demote("### " + mv[3]),
    "@@step3@@": rd(f"{D}/step3_fragment.md"),
    "@@cost@@": demote(rd(f"{D}/cost/cost.md")),
    "@@retime@@": demote(rd(f"{D}/retime_summary.md")),
    "@@retime_text@@": rd(f"{S4}/c6b_doc_retime.md"),
}
out = rd(f"{S4}/c6b_doc_head.md") + "\n" + rd(f"{S4}/c6b_doc_tail.md")
for k, v in rep.items():
    out = out.replace(k, v)
open(f"{W}/eval/CO_CHAIN_B.md", "w").write(out)
print("written", len(out), "chars", out.count("\n"), "lines; unresolved markers:", re.findall(r"@@[^@]+@@", out))

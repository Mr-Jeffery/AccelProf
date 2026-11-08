#!/usr/bin/env python3
"""C6 step 3: assemble eval/CO_CHAIN.md from the narrative parts (c6-step3/doc_*.md) and the generated fragments in
eval/results/co-chain/step3/.  Headings of an included fragment are demoted one level."""
import os, re
S3 = "/home/fzheng4/c6-step3"
W = "/home/fzheng4/wt-c6"
D = f"{W}/eval/results/co-chain/step3"


def rd(p):
    return open(p).read() if os.path.exists(p) else f"(missing: {p})\n"


def demote(t):
    return re.sub(r"(?m)^(#{2,5}) ", lambda m: m.group(1) + "# ", t)


def sections(t, prefixes):
    """the '## ' sections of t whose heading starts with one of prefixes, in file order"""
    parts = re.split(r"(?m)^(?=## )", t)
    return "".join(p for p in parts if any(p.startswith("## " + x) for x in prefixes))


detect = rd(f"{D}/detect/c6_detect.md")
rep = {
    "@@tables/c6_tables.md@@": demote(rd(f"{D}/tables/c6_tables.md")),
    "@@detect/c6_detect.md@@": demote(sections(detect, ["Detections", "Why scalar-clock", "The production races"])),
    "@@detect/classes_by_program.md@@": demote(rd(f"{D}/detect/classes_by_program.md")),
    "@@detect_fp@@": rd(f"{S3}/doc_fp.md") + "\n" + demote(sections(detect, ["Reports of CO+chain", "Sample of 20"])),
    "@@cost/cost.md@@": demote(rd(f"{D}/cost/cost.md")),
    "@@rw@@": rd(f"{S3}/doc_rw.md") + "\n" + demote(rd(f"{D}/{os.environ.get('RWSUB', 'rw')}/c6_rw_report.md")),
    "@@rw_missing@@": rd(f"{S3}/doc_rwmissing.md"),
}
out = rd(f"{S3}/doc_head.md") + "\n" + rd(f"{S3}/doc_tail.md")
for k, v in rep.items():
    out = out.replace(k, v)
open(f"{W}/eval/CO_CHAIN.md", "w").write(out)
print("written", len(out), "chars", out.count("\n"), "lines; unresolved markers:", re.findall(r"@@[^@]+@@", out))

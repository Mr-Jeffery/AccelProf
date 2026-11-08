#!/usr/bin/env python3
"""C3 check: BASELINES_B.md (make_tables.py --collector-only) with every collector-only column, row, note segment and
sentence clause removed, against BASELINES_A.md (no flag; equals X1b's BASELINES.md but for the revision-pin line and the
disagreements listing, see p_co_tables.sh).  Prints the remaining differences."""
import re, difflib
D = "eval/results/collector-only-tables/mt"
A = open(f"{D}/BASELINES_A.md").read().split("\n")
B = open(f"{D}/BASELINES_B.md").read().split("\n")
def cells(l): return [c.strip() for c in l.strip().strip("|").split(" | ")]
def iscol(c): return "cuVein-CO" in c or c == "cuVein (collector-only)"
def isdash(l): return l.startswith("|") and set(l.replace("|", "").strip()) <= set("-") and l.strip() != "|"
def strip_text(s):
    s = re.sub(r"<br>\*\*cuVein-CO\*\*.*?(?=<br>\*\*|$)", "", s)
    s = re.sub(r"<br>\*\*CO\*\* \(\d+\) — [^|]*?(?=<br>\*\*|$)", "", s)
    s = re.sub(r"cuVein-CO RACE [^;]*; ", "", s)
    return s
out = []; drop = set(); intab = False
for l in B:
    if l.startswith("|"):
        if not intab:
            hc = cells(l); drop = {i for i, c in enumerate(hc) if iscol(c)}; intab = True
            out.append("| " + " | ".join(c for i, c in enumerate(hc) if i not in drop) + " |" if drop else l); continue
        if isdash(l):
            out.append("|" + "---|" * (len(cells(l)) - len(drop))); continue
        cs = cells(l)
        if any(c in ("cuVein-CO", "collector-only") for c in cs[:3]): continue
        cs = [strip_text(c) for i, c in enumerate(cs) if i not in drop]
        out.append("| " + " | ".join(cs) + " |")
    else:
        intab = False; drop = set()
        out.append(strip_text(l))
A2 = ["|" + "---|" * len(cells(l)) if isdash(l) else l for l in A]
def fn7(x):
    return re.sub(r"(Footnotes: .*?)\(7\).*", r"\1", x) if x.startswith("Footnotes:") else x
out = [fn7(x) for x in out]; A2 = [fn7(x) for x in A2]
d = [x for x in difflib.unified_diff(A2, out, lineterm="", n=0) if not x.startswith(("---", "+++"))]
print("A lines", len(A), "B lines", len(B), "stripped B", len(out), "diff lines", len(d), "hunks", sum(1 for x in d if x.startswith("@@")))
for x in d[:40]: print(x[:300])


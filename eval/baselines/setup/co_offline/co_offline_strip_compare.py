#!/usr/bin/env python3
"""C4 check: BASELINES_B.md (make_tables.py --collector-only --co-offline) with every CO-R column, row, note segment and sentence
clause removed, against BASELINES_A.md (--collector-only, C3's run).  Both come from the same CSVs but for the CO-R rows
(sandbox trees of p_co_offline_tables.sh).  Prints the remaining differences; the other columns must be byte-identical:
the check is 0 diff lines.  Same method as C3's co_strip_compare.py, with the column test narrowed to CO-R."""
import difflib
import re
import sys
D = "/home/fzheng4/wt-c4/eval/results/co-offline/mt"
A = open(f"{D}/BASELINES_A.md").read().split("\n")
B = open(f"{D}/BASELINES_B.md").read().split("\n")


def cells(l):
    return [c.strip() for c in l.strip().strip("|").split(" | ")]


def iscol(c):
    return c.startswith("cuVein-CO-R") or c == "cuVein (collector-only, re-scored)"


def isdash(l):
    return l.startswith("|") and set(l.replace("|", "").strip()) <= set("-") and l.strip() != "|"


def strip_text(s):
    s = re.sub(r"<br>\*\*cuVein-CO-R\*\*.*?(?=<br>\*\*|$)", "", s)
    s = re.sub(r"<br>\*\*CO-R\*\* \(\d+\) — [^|]*?(?=<br>\*\*|$)", "", s)
    s = re.sub(r"cuVein-CO-R RACE [^;]*; ", "", s)
    s = re.sub(r"; \w+ collector-only-rescored: CLEAN \d+(?= \()", "", s)
    s = re.sub(r"\w+ collector-only-rescored: [^;]*?; ", "", s)           # footnote 7: per-mode verdict counts
    s = re.sub(r"cuVein \(collector-only, re-scored\): [^;]*; ", "", s)      # footnote 8
    return s


out = []
drop = set()
intab = False
for l in B:
    if l.startswith("|"):
        if not intab:
            hc = cells(l)
            drop = {i for i, c in enumerate(hc) if iscol(c)}
            intab = True
            out.append("| " + " | ".join(c for i, c in enumerate(hc) if i not in drop) + " |" if drop else l)
            continue
        if isdash(l):
            out.append("|" + "---|" * (l.count("|") - 1 - len(drop)))
            continue
        cs = cells(l)
        if any(c in ("cuVein-CO-R", "collector-only-rescored") for c in cs[:3]):
            continue
        cs = [strip_text(c) for i, c in enumerate(cs) if i not in drop]
        out.append("| " + " | ".join(cs) + " |")
    else:
        intab = False
        drop = set()
        out.append(strip_text(l))
A2 = ["|" + "---|" * (l.count("|") - 1) if isdash(l) else l for l in A]
d = [x for x in difflib.unified_diff(A2, out, lineterm="", n=0) if not x.startswith(("---", "+++"))]
print("A lines", len(A), "B lines", len(B), "stripped B", len(out), "diff lines", len(d), "hunks", sum(1 for x in d if x.startswith("@@")))
for x in d[:int(__import__("os").environ.get("NSHOW","60"))]:
    print(x[:300])
import itertools
ms = [x for x in d if not x.startswith("@@")]
for a_, b_ in zip(ms[0::2], ms[1::2]):
    if a_.startswith("-") and b_.startswith("+"):
        j = next((k for k, (u, v) in enumerate(zip(a_[1:], b_[1:])) if u != v), min(len(a_), len(b_)) - 1)
        print("first difference at char", j, "| A:", repr(a_[1 + max(0, j - 60):1 + j + 160]), "| B:", repr(b_[1 + max(0, j - 60):1 + j + 160]))
sys.exit(0 if not d else 1)

#!/usr/bin/env python3
"""T21b: render eval/REALWORLD.md section "2. Recall (T21b)" from eval/results/realworld/recall.csv (+ notes file
eval/realworld/harness/recall_notes.md, hand-written, copied verbatim after the tables). The section is appended at the end of
REALWORLD.md (an existing 'Recall (T21b)' section is replaced)."""
import csv, os, re, collections, json
WT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
rows = list(csv.DictReader(open(f"{WT}/eval/results/realworld/recall.csv")))
notes = open(f"{WT}/eval/realworld/harness/recall_notes.md").read(); pending = open(f"{WT}/eval/realworld/harness/recall_pending.md").read()
main = [r for r in rows if r["flavor"] == "main"]
out = ["## 2. Recall (T21b)", "", notes.rstrip(), ""]
# counts
out += ["### 2.1 Detected, by mode and expected_class (main flavor, buggy builds, rows scored so far)", "",
        "A target of class DR+SC has two components (DR pair, SC pair), counted separately. Outcome words as in the T21b brief; "
        "`DETECTED-AS-DR` = reported in the other class (D20 option (i)).", "",
        "| mode | expected_class | component | DETECTED | DETECTED-AS-other | MISSED | n |", "|---|---|---|---|---|---|---|"]
c = collections.defaultdict(collections.Counter)
for r in main:
    if r["variant"] != "buggy":
        continue
    o = r["outcome"]
    if o in ("VOID", "NOT-SCORED"):
        continue
    k = "DETECTED" if o.startswith("DETECTED") and not o.startswith("DETECTED-AS") else ("DETECTED-AS" if o.startswith("DETECTED-AS") else "MISSED")
    c[(r["mode"], r["expected_class"], r["component"])][k] += 1
for (m, e, comp), v in sorted(c.items()):
    n = sum(v.values())
    out.append(f"| {m} | {e} | {comp} | {v['DETECTED']} | {v['DETECTED-AS']} | {v['MISSED']} | {n} |")
out += ["", "### 2.2 Per target (main flavor; vc = vector-clock mode, sc = scalar-clock mode; fixed: outcome per mode)", "",
        "| target | wave | class | buggy vc | buggy sc | op. point (vc) | a2 | .STRONG | fixed vc | fixed sc | racecheck (buggy) |", "|---|---|---|---|---|---|---|---|---|---|---|"]
by = collections.defaultdict(dict)
for r in main:
    by[r["target"]][(r["variant"], r["mode"], r["component"])] = r
for t in sorted(by, key=lambda t: (list(by[t].values())[0]["wave"], t)):
    d = by[t]; any_ = list(d.values())[0]
    def cell(var, mode):
        rs = [r for (v, m, comp), r in d.items() if v == var and m == mode]
        return " / ".join(f"{(r['component']+': ') if r['component'] else ''}{r['outcome']}" for r in rs) or "-"
    vc = [r for (v, m, comp), r in d.items() if v == "buggy" and m == "vector-clock"]
    op = ", ".join(sorted({r["operating_point"] for r in vc if r["operating_point"]})) or ""
    a2 = ",".join(sorted({r["a2"] for r in vc if r["a2"]}))
    st = ",".join(sorted({r["strong_token"] for r in vc if r["strong_token"]}))
    rc = next((r["racecheck"] for r in vc), "")
    out.append(f"| {t} | {any_['wave']} | {any_['expected_class']} | {cell('buggy','vector-clock')} | {cell('buggy','scalar-clock')} | {op} | {a2} | {st} | {cell('fixed','vector-clock')} | {cell('fixed','scalar-clock')} | {rc} |")
other = [r for r in rows if r["flavor"] != "main" and not r["flavor"].startswith("longcap")]
if other:
    out += ["", "### 2.3 Other flavors (vector-clock only)", "", "| flavor | target | variant | component | run | outcome | operating point |", "|---|---|---|---|---|---|---|"]
    for r in other:
        out.append(f"| {r['flavor']} | {r['target']} | {r['variant']} | {r['component']} | {r['run_verdict']} | {r['outcome']} | {r['operating_point']} |")
sec = "\n".join(out) + "\n"
p = f"{WT}/eval/REALWORLD.md"
s = open(p).read()
i = s.find("## 2. Recall (T21b)")
if i >= 0:
    s = s[:i]
if not s.endswith("\n"):
    s += "\n"
open(p, "w").write(s + "\n" + sec)
print("REALWORLD.md section written,", len(sec), "bytes")

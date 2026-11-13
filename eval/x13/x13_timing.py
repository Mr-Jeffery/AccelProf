#!/usr/bin/env python
"""X13: wall of the reduced runs at N=1 and N=16 with the counter off (timing_n1 / timing_n16), next to the
counter-on N=16 wall of the sweep (runs/) -> markdown table.   x13_timing.py D OUT.md
"""
import glob, json, os, sys

D, out = sys.argv[1], sys.argv[2]


def load(root):
    r = {}
    for f in glob.glob(f"{root}/*__*__*/run.json"):
        j = json.load(open(f))
        r[os.path.basename(os.path.dirname(f))] = j
    return r


n1, n16, on = load(f"{D}/timing_n1"), load(f"{D}/timing_n16"), load(f"{D}/runs")
keys = sorted(set(n1) | set(n16) | set(on))
f = lambda x: "missing" if x is None else (f"{x:,.1f}" if isinstance(x, (int, float)) else str(x))
L = ["| program | size | mode | native (s) | N=1 wall (s) | N=16 wall (s), counter off | speed-up N=1 / N=16 | N=16 wall (s), counter on | counter-on / counter-off | N=16 peak RSS (MB, off) | notes |", "|---|---|---|---|---|---|---|---|---|---|---|"]
for k in keys:
    prog, size, mode = k.split("__")
    a, b, c = n1.get(k), n16.get(k), on.get(k)
    notes = []
    for tag, j in (("N=1", a), ("N=16", b), ("counter on", c)):
        if j and (j.get("rc") not in (0, None) or j.get("timed_out")):
            notes.append(f"{tag}: rc={j.get('rc')} timed_out={j.get('timed_out')} (peak {j.get('peak_mb')} MB)")
    wa = a["wall"] if a and a.get("rc") == 0 and not a.get("timed_out") else None
    wb = b["wall"] if b and b.get("rc") == 0 and not b.get("timed_out") else None
    wc = c["wall"] if c and c.get("rc") == 0 and not c.get("timed_out") else None
    nat = (b or a or c or {}).get("native_wall")
    sp = f"{wa / wb:.2f}x" if wa and wb else "missing"
    co = f"{wc / wb:.2f}x" if wc and wb else "missing"
    L.append(f"| {prog} | {size} | {mode} | {f(nat)} | {f(wa)} | {f(wb)} | {sp} | {f(wc)} | {co} | {f(b['peak_mb']) if b else 'missing'} | {'; '.join(notes)} |")
open(out, "w").write("\n".join(L) + "\n")
print("\n".join(L))

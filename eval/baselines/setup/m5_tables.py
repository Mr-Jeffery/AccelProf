#!/usr/bin/env python3
"""M5: markdown tables (one per suite) from eval/results/closure-atomic-hop/summary/{c1,prod}.json -> summary/tables_{c1,prod}.md"""
import json
D = "/home/fzheng4/wt-m5/eval/results/closure-atomic-hop/summary"
NAMES = {"P1": "P1 Indigo3", "P3": "P3 ECL", "P4": "P4 ScoR applications", "P5": "P5 ScoR litmus + canary", "P6": "P6 cuHadron (analysed 34 of 50)",
         "P7": "P7 HeCBench (other 14)", "P9": "P9 HeCBench (SC's 10)", "PI": "PI Indigo 1.3 inputs (1,862 racy / 1,260 race-free labelled, 1,008 unlabelled)",
         "T21b": "T21b recall set (realworld-2026-10-co)", "T21c": "T21c candidate set (realworld-2026-10-t21c-co)"}
for which, cols in (("c1", (("before", "before (existing S2)"), ("sw0", "control (switch 0)"), ("sw1", "after (switch 1)"))),
                    ("prod", (("sw0", "before (switch 0)"), ("sw1", "after (switch 1)")))):
    r = json.load(open(f"{D}/{which}.json"))
    out = []
    for s, st in r["suites"].items():
        b, a = st[cols[0][0]], st["sw1"]
        new = sorted(set(a["free_reported"]) - set(b["free_reported"]))
        out.append(f"**{NAMES.get(s, s)}**\n")
        out.append("| | " + " | ".join(c[1] for c in cols) + " |")
        out.append("|---|" + "---|" * len(cols))
        def row(label, f):
            out.append(f"| {label} | " + " | ".join(str(f(st[c[0]])) for c in cols) + " |")
        row("programs", lambda x: x["programs"])
        row("programs reported", lambda x: x["reported"])
        row("labelled races detected", lambda x: f"{x['racy_detected']} of {x['labelled_racy']}")
        row("labelled race-free reported", lambda x: f"{len(x['free_reported'])} of {x['labelled_free']}")
        row("report pairs", lambda x: x["report_pairs"])
        row("derived / rescued chain pairs", lambda x: f"{x['derived']} / {x['rescued']}")
        row("kernels at 10^6-pair cap", lambda x: x["cap"])
        row("verdict-step wall time, s", lambda x: x["analysis_s"])
        out.append(f"\nNew race-free reported (after, not before): {', '.join('`'+n+'`' for n in new) if new else 'none'}.\n")
    open(f"{D}/tables_{which}.md", "w").write("\n".join(out))
    print("\n".join(out))

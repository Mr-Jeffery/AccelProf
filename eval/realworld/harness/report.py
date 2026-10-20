#!/usr/bin/env python3
"""Render eval/REALWORLD.md section 1 ("Corpus") from the per-target records.
    report.py [--out eval/REALWORLD.md]
Inputs : eval/realworld/targets.jsonl (waves 1-2 are the commitment, D22), eval/realworld/targets/<id>/status.json (hand/agent
         written: route, status, reason, driver, input, ...), eval/realworld/native/<id>-<variant>.{json,reach},
         eval/realworld/racecheck/<id>-<variant>.txt, eval/realworld/targets/<id>/{fixdiff.check,lineinfo.check}
Head   : eval/realworld/harness/REALWORLD_head.md (static text: layout, rules, storage, nodes) is copied first.
"""
import argparse, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
RW = os.path.dirname(HERE)
EVAL = os.path.dirname(RW)


def jl(p):
    return json.load(open(p)) if os.path.exists(p) else None


def txt(p):
    return open(p).read() if os.path.exists(p) else ""


def native(i):
    out = []
    for v in ("buggy", "fixed"):
        j = jl(os.path.join(RW, "native", "%s-%s.json" % (i, v)))
        if not j:
            out.append("%s: -" % v)
            continue
        out.append("%s: rc %s, outputs %s, %s s" % (v, "/".join(map(str, j["rcs"])), "differ" if j["outputs_differ"] else "identical",
                                                    "/".join("%.2f" % r["wall_s"] for r in j["runs"])))
    return "; ".join(out)


def reach(i):
    out = []
    for v in ("buggy", "fixed"):
        p = os.path.join(RW, "native", "%s-%s.reach" % (i, v))
        out.append("%s: %s" % (v, "yes" if os.path.exists(p) and os.path.getsize(p) else ("NO" if os.path.exists(p) else "-")))
    return "; ".join(out)


def racecheck(i, st):
    if st.get("racecheck"):
        return st["racecheck"]
    out = []
    for v in ("buggy", "fixed"):
        t = txt(os.path.join(RW, "racecheck", "%s-%s.txt" % (i, v)))
        if not t:
            out.append("%s: -" % v)
        elif t.startswith("racecheck n/a"):
            out.append("%s: n/a" % v)
        else:
            m = re.findall(r"RACECHECK SUMMARY: (\d+) hazards? displayed \((\d+) errors?, (\d+) warnings?\)", t)
            out.append("%s: %s" % (v, ("%s hazards (%s errors, %s warnings)" % m[-1]) if m else "no summary line"))
    return "; ".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(EVAL, "REALWORLD.md"))
    a = ap.parse_args()
    T = [json.loads(l) for l in open(os.path.join(RW, "targets.jsonl"))]
    core = [t for t in T if t["tier"] == "core"]
    L = [txt(os.path.join(HERE, "REALWORLD_head.md")).rstrip("\n"), "", "## 1. Corpus", ""]
    L.append("Per-target status, written by `eval/realworld/harness/report.py` from `eval/realworld/targets/<id>/status.json`, "
             "`native/`, `racecheck/` and the checks in each target directory. Waves 1 and 2 (28 targets) are the commitment (D22); wave 3 is not started unless Jeffery says so.")
    L.append("")
    L.append("| wave | id | route | status | driver / input | kernel reached (nsys) | native (3 runs) | racecheck | checks |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    counts = {}
    for w in (1, 2, 3):
        for t in [t for t in core if t["wave"] == w]:
            i = t["id"]
            st = jl(os.path.join(RW, "targets", i, "status.json")) or {}
            status = st.get("status", "pending" if w < 3 else "not started (D22)")
            counts.setdefault(w, {}).setdefault(status.split(":")[0], 0)
            counts[w][status.split(":")[0]] += 1
            if status.startswith("not built") and st.get("reason"):
                status = "not built: " + st["reason"]
            chk = []
            for f in ("fixdiff.check", "lineinfo.check"):
                s = txt(os.path.join(RW, "targets", i, f))
                if s:
                    r = [l for l in s.splitlines() if l.startswith("RESULT")]
                    chk.append("%s %s" % (f.split(".")[0], r[-1].split()[1] if r else "?"))
            L.append("| %d | `%s` | %s | %s | %s | %s | %s | %s | %s |" % (
                w, i, st.get("route", "-"), status.replace("|", "/"), (st.get("driver", "-") + (" / " + st["input"] if st.get("input") else "")).replace("|", "/"),
                reach(i), native(i), racecheck(i, st).replace("|", "/"), ", ".join(chk) or "-"))
    L.append("")
    L.append("Counts by wave (status keyword): " + "; ".join("wave %d: %s" % (w, ", ".join("%s %d" % kv for kv in sorted(c.items()))) for w, c in sorted(counts.items())))
    L.append("")
    L.append("### 1.1 Per-target notes and exact commands")
    for t in core:
        i = t["id"]
        st = jl(os.path.join(RW, "targets", i, "status.json"))
        if not st or t["wave"] == 3:
            continue
        L.append("")
        L.append("**`%s`** (wave %d, %s, class %s)" % (i, t["wave"], st.get("route", "-"), t.get("expected_class", "?")))
        for k in ("route_note", "reason", "toolkit", "notes"):
            if st.get(k):
                L.append("- %s: %s" % (k, st[k]))
        for c in st.get("commands", []):
            L.append("  - `%s`" % c)
    open(a.out, "w").write("\n".join(L) + "\n")
    print("wrote", a.out)


main()

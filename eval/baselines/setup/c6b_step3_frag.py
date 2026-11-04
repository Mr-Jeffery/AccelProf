#!/usr/bin/env python3
"""C6b step 4: the tables of step 3 (results/co-chain-b/step3) for CO_CHAIN_B.md section 4: the per-suite tables as step 3 wrote them
(step3_summary.md), the per-program cause table (programs with missing pairs, by cause class), the programs with a granted certificate and
the programs with a lane drop, the violation counts, and the probe table of assert_no_hb.txt.  Writes $OUTD/step3_fragment.md."""
import collections
import csv
import os
import re

R = "/home/fzheng4/wt-c6b/eval/results/co-chain-b"
D = f"{R}/step3"
OUT = os.environ.get("OUTD", f"{R}/step4")
md = []


def P(*a):
    md.append(" ".join(str(x) for x in a))


def rd(p):
    return list(csv.DictReader(open(p, newline=""), delimiter="\t"))


summ = open(f"{D}/step3_summary.md").read()
secs = re.split(r"(?m)^(?=## )", summ)
P("### 4.1 Per-suite tables (step 3's own, unchanged)\n")
P("Source: `results/co-chain-b/step3/step3_summary.md`. Violation = scalar-clock Race and collector-only not Race, on the same programs (scalar-clock "
  "recordings with every `hb_*` key deleted, run through the unmodified `parallel.py analyze` in collector-only mode). Reverse = collector-only Race and scalar-clock not Race.\n")
for s in secs:
    if s.startswith("## Setting"):
        head = s.split("\n")[0]
        body = s.split("\n", 1)[1]
        body = body.split("Cause per violation program")[0] + "\n" + ("Pairs" + body.split("Pairs", 1)[1] if "Pairs" in body else "")
        P("#### " + head[3:] + "\n")
        P(body.strip() + "\n")
P("\n### 4.2 Program-level violations\n")
P("| setting | programs scalar-clock Race | collector-only Race | both Race | violations (scalar-clock Race, collector-only not Race) | reverse (collector-only Race, scalar-clock not) | of which scalar-clock Clean |")
P("|---|---|---|---|---|---|---|")
for st, nm in (("s1", "S1 (strict)"), ("s2", "S2 (off)"), ("cfg", "cfg (C6's R3, with the widest bound and async)")):
    v = rd(f"{D}/violations_program_{st}.tsv")
    t = [l for l in open(f"{D}/step3_summary.md").read().split("## Setting " + st)[1].split("\n") if l.startswith("| ALL")][0].split("|")[1:-1]
    t = [x.strip() for x in t]
    P(f"| {nm} | {t[2]} | {t[3]} | {t[4]} | **{len(v)}** | {t[10]} | {t[11]} |")
P("\n### 4.3 Per-program causes of the missing pairs (programs where scalar-clock Race and a pair of scalar-clock is not in collector-only's reports)\n")
P("Per program the cause class is: certificate granted if any missing pair is of that class, else candidate missing if any, else other; lane drop only if every missing pair is a lane drop "
  "(step 3's rule). Candidate missing = the collector-only recording has no candidate pair for the scalar-clock pair (the pair's pcs are not joined by an edge or chain of reads, or are joined only "
  "thread-locally, or only through a non-read hop; sub-causes are in `pairs_*_by_program.tsv`). Certificate granted = the pair is a candidate and the verdict step orders it by a certificate "
  "(R2 coherence, morally strong RMW pair). Lane drop = the pair's pc has a dropped-word deficit (first-lane allocation lookup / words past an allocation end; static check (b) of C6).\n")
for st, nm in (("s1", "S1"), ("s2", "S2")):
    rows = rd(f"{D}/pairs_{st}_by_program.tsv")
    cnt = collections.defaultdict(collections.Counter)
    for r in rows:
        if int(r["missing"]) == 0:
            continue
        cause = ("certificate granted" if int(r["certificate_granted"]) else "candidate missing" if int(r["candidate_missing"]) else
                 "other" if int(r["other"]) else "lane drop only")
        cnt[r["suite"]][cause] += 1
        cnt[r["suite"]]["pairs"] += int(r["missing"])
    P(f"\n**{nm}**: programs with at least one missing pair, by suite and program cause class\n")
    P("| suite | programs | missing pairs | certificate granted | candidate missing | lane drop only | other |")
    P("|---|---|---|---|---|---|---|")
    tot = collections.Counter()
    for su in sorted(cnt):
        c = cnt[su]
        tot.update(c)
        P(f"| {su} | {sum(c[k] for k in ('certificate granted', 'candidate missing', 'lane drop only', 'other'))} | {c['pairs']} | {c['certificate granted']} | {c['candidate missing']} | {c['lane drop only']} | {c['other']} |")
    P(f"| **all** | {sum(tot[k] for k in ('certificate granted', 'candidate missing', 'lane drop only', 'other'))} | {tot['pairs']} | {tot['certificate granted']} | {tot['candidate missing']} | {tot['lane drop only']} | {tot['other']} |")
a, b = rd(f"{D}/pairs_s1_by_program.tsv"), rd(f"{D}/pairs_s2_by_program.tsv")
keys = ("sc_pairs", "found_in_co", "missing", "certificate_granted", "candidate_missing", "lane_drop", "other")
diff = [x["id"] for x, y in zip(a, b) if any(x[k] != y[k] for k in keys)]
P(f"\nPrograms whose pair counts differ between S1 and S2: {len(diff)}" + (": " + ", ".join(f"`{i}`" for i in diff) if diff else "") + ".")
P("\n### 4.4 The programs with a granted certificate and the programs with a lane drop (S1; S2 identical where the line above says 0 differ)\n")
P("| program | suite | scalar-clock pairs | found in collector-only | missing | certificate granted | lane drop | sub-causes (step 3) |")
P("|---|---|---|---|---|---|---|---|")
for r in a:
    if int(r["certificate_granted"]) or int(r["lane_drop"]):
        P(f"| `{r['id']}` | {r['suite']} | {r['sc_pairs']} | {r['found_in_co']} | {r['missing']} | {r['certificate_granted']} | {r['lane_drop']} | {r['subcauses']} |")
P(f"\nPrograms with a lane drop: {sum(1 for r in a if int(r['lane_drop']))}, all Indigo 1.3 (`boundsBug` variants: an access past the allocation end): "
  f"{all(r['suite'] == 'PI' and 'boundsBug' in r['id'] for r in a if int(r['lane_drop']))}; each of them is Race in collector-only (0 violations), so the lane drop removes pairs, not programs.")
P("\n### 4.5 The deviation: probes of absent `hb_*` keys\n")
txt = open(f"{D}/assert_no_hb.txt").read()
sec2 = txt.split("## 2.")[1].split("## 3.")[0]
P("From `assert_no_hb.txt` section 2 (the guarded loader over the three runs), verbatim:\n")
P("```")
P("## 2." + sec2.rstrip())
P("```")
open(f"{OUT}/step3_fragment.md", "w").write("\n".join(md) + "\n")
print("\n".join(md)[:6000])

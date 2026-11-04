#!/usr/bin/env python3
"""C6b step 4, false reports and what moved against C6.
Inputs: the confirm JSONs of C6 (eval/results/co-chain/{c1-main,c1-long,c1-24h}/confirm) and of S1 / S2 (eval/results/co-chain-b/s{1,2}/...; later
dirs override earlier ones, as `parallel.py merge --override c1-long,c1-24h`), whose raw records carry chain_src / chain_path / async /
atomic_chain_off; the CSVs of c6b_stage.sh (inputs/) for C1's and scalar-clock's pair sets (report_ids, union of the reps) and for the notes
(chain_derived, chain_rescued, classes); verdicts: races alone (make_tables.race_alone_verdict) from the sandbox.
Unit of a report: a deduped pc pair (space, min pc, max pc) among the RACE-class raw records (`raw`) of a program that is Race in that setting;
the strong-conflict class (`raw_sc`) is tabulated separately.
Class of a record, by precedence:  atomic_chain_off  >  async  >  derived (chain_src == chain)  >  rescued (chain_src == chain_rescue)  >  other.
Class of a pair = the least special class among its records (other < rescued < derived < async < atomic_chain_off), i.e. a pair that some ordinary
record also reports is `other`.  Writes $OUTD/detect/."""
import collections
import csv
import glob
import json
import os
import re
import sys

W = "/home/fzheng4/wt-c6b"
R = f"{W}/eval/results"
S4 = "/home/fzheng4/c6b-step4"
OUT = os.environ.get("OUTD", f"{R}/co-chain-b/step4") + "/detect"
os.makedirs(OUT, exist_ok=True)
sys.argv = [sys.argv[0], "--collector-only"]
SB = os.environ.get("COSB", f"{S4}/sand")
sys.path.insert(0, f"{SB}/eval/baselines")
import make_tables as mt  # noqa: E402

runs, meta = mt.load_runs()
man = mt.load_manifest()
VC, SC, CO = mt.VC, mt.SC, mt.CO
CC, S1, S2 = "collector-only-chain", "collector-only-s1", "collector-only-s2"
NAME = {SC: "scalar-clock", CO: "C1", CC: "C6", S1: "S1", S2: "S2"}
md = []


def P(*a):
    md.append(" ".join(str(x) for x in a))


def wcsv(name, header, rows):
    with open(f"{OUT}/{name}", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


LABEL_OVERRIDE = {"P9-knn-cuda": "CLEAN", "P9-atomicCAS-cuda": "CLEAN"}


def label(i):
    return LABEL_OVERRIDE.get(i, man.get(i, {}).get("label", ""))


LAB = {"RACE": "racy", "CLEAN": "race-free", "": "unlabelled"}
SUITE = {"P1": "Indigo3 (P1)", "PI": "Indigo 1.3 (PI)", "P3": "ECL (P3)", "P4": "ScoR apps (P4)", "P5": "ScoR litmus (P5)",
         "P6": "cuHadron (P6)", "P7": "HeCBench other 14 (P7)", "P9": "HeCBench SC 10 (P9)"}
SUITES = ("P1", "PI", "P3", "P4", "P5", "P6", "P7", "P9")
CLASSES = ("derived", "rescued", "async", "atomic_chain_off", "other")
RANK = {"other": 0, "rescued": 1, "derived": 2, "async": 3, "atomic_chain_off": 4}


def rv(i, mode):
    r = runs.get((i, "cuvein", mode))
    if r is None:
        return None
    if r["verdict"] in ("RACE", "CLEAN"):
        v = mt.race_alone_verdict(r)
        return r["verdict"] if v is None else v
    return r["verdict"]


TOK = re.compile(r"^(\w+):0x([0-9a-f]+)-0x([0-9a-f]+):(\w+)$")


def pk(sp, a, b):
    return (sp, min(a, b), max(a, b))


def csv_pairs(path, mode):
    per = collections.defaultdict(list)
    for r in csv.DictReader(open(path, newline="")):
        if r["mode"] == mode:
            per[r["id"]].append(r)
    out, trunc = {}, 0
    for i, reps in per.items():
        s, tr = set(), False
        for r in reps:
            ts = [TOK.match(t) for t in (r["report_ids"] or "").split()]
            ts = [m for m in ts if m]
            s |= {pk(m.group(1), int(m.group(2), 16), int(m.group(3), 16)) for m in ts}
            n = int(r["reports_dedup"]) if (r.get("reports_dedup") or "").isdigit() else 0
            if len(ts) < n:
                tr = True
        out[i] = s
        trunc += tr
    return out, trunc


INP = f"{S4}/inputs"
PAIRS = {}
TRUNC = {}
PAIRS[SC], TRUNC[SC] = csv_pairs(f"{INP}/baselines-cuvein.csv", "scalar-clock")
PAIRS[CO], TRUNC[CO] = csv_pairs(f"{INP}/baselines-cuvein-co.csv", "collector-only")
CSVP = {}
CSVP[CC], TRUNC[CC] = csv_pairs(f"{INP}/baselines-cuvein-cc.csv", "collector-only-chain")
CSVP[S1], TRUNC[S1] = csv_pairs(f"{INP}/baselines-cuvein-s1.csv", "collector-only-s1")
CSVP[S2], TRUNC[S2] = csv_pairs(f"{INP}/baselines-cuvein-s2.csv", "collector-only-s2")

DIRS = {CC: f"{R}/co-chain", S1: f"{R}/co-chain-b/s1", S2: f"{R}/co-chain-b/s2"}


def rec_class(rec):
    if rec.get("atomic_chain_off"):
        return "atomic_chain_off"
    if rec.get("async"):
        return "async"
    src = rec.get("chain_src") or "edge"
    if src == "chain":
        return "derived"
    if src == "chain_rescue":
        return "rescued"
    return "other"


CONF = {m: {} for m in (CC, S1, S2)}
for m, d in DIRS.items():
    for sub in ("c1-main", "c1-long", "c1-24h"):
        for f in glob.glob(f"{d}/{sub}/confirm/*__cuvein__collector-only.json"):
            CONF[m][os.path.basename(f).split("__")[0]] = f
_cache = {}


def conf(m, pid):
    """-> ({pair: (class, set of classes, record)}, {pair: ...} for raw_sc, raw records list) or None"""
    k = (m, pid)
    if k in _cache:
        return _cache[k]
    f = CONF[m].get(pid)
    if not f:
        _cache[k] = None
        return None
    j = json.load(open(f))
    out = []
    for key in ("raw", "raw_sc"):
        d = {}
        for rec in j.get(key) or []:
            kk = pk(rec.get("space"), rec["a_pc"], rec["b_pc"])
            c = rec_class(rec)
            if kk not in d or RANK[c] < RANK[d[kk][0]]:
                d[kk] = (c, rec)
        out.append(d)
    out.append(j)
    res = tuple(out)
    if len(_cache) > 3000:
        _cache.clear()
    _cache[k] = res
    return res


ids = sorted(i for i in meta if meta[i][0] in SUITE)
P(f"Programs with a confirm JSON: " + ", ".join(f"{NAME[m]} {len(CONF[m])}" for m in (CC, S1, S2)))
P("Programs whose CSV report_ids hold fewer pairs than reports_dedup (pair sets cut by the CSV): " + ", ".join(f"{NAME[m]} {TRUNC[m]}" for m in TRUNC))
# consistency: race-class raw pair set of the confirm JSON against the CSV's report_ids (union of the reps)
for m in (CC, S1, S2):
    bad = nover = 0
    for i in ids:
        if rv(i, m) != "RACE":
            continue
        c = conf(m, i)
        if c is None:
            continue
        nover += 1
        if set(c[0]) != CSVP[m].get(i, set()):
            bad += 1
    P(f"Check {NAME[m]}: programs Race with a confirm JSON {nover}; race-class raw pair set differs from the CSV report_ids in {bad}.")


def ref_pairs(ref, i):
    if ref in (SC, CO):
        return PAIRS[ref].get(i, set())
    c = conf(ref, i)
    return set(c[0]) if c else set()


# ============================================================ 1. false-report split
def split_tables(m):
    nm = NAME[m]
    cnt = {}          # (suite, label, ref) -> Counter(class)
    tags = collections.defaultdict(collections.Counter)   # (suite, label) -> record-level tag counts
    nprog = collections.Counter()
    sc_cnt = collections.defaultdict(collections.Counter)
    missing = collections.Counter()
    for i in ids:
        if rv(i, m) != "RACE":
            continue
        c = conf(m, i)
        if c is None:
            missing[meta[i][0]] += 1
            continue
        S, lab = meta[i][0], LAB.get(label(i), "unlabelled")
        nprog[(S, lab)] += 1
        for k, (cl, rec) in c[0].items():
            cnt.setdefault((S, lab, "all"), collections.Counter())[cl] += 1
            for ref in (CO, CC, SC):
                if ref == m:
                    continue
                if k not in ref_pairs(ref, i):
                    cnt.setdefault((S, lab, ref), collections.Counter())[cl] += 1
            tags[(S, lab)]["pairs"] += 1
            tags[(S, lab)]["chain_src=chain"] += rec.get("chain_src") == "chain"
            tags[(S, lab)]["chain_src=chain_rescue"] += rec.get("chain_src") == "chain_rescue"
            tags[(S, lab)]["async"] += bool(rec.get("async"))
            tags[(S, lab)]["atomic_chain_off"] += bool(rec.get("atomic_chain_off"))
        for k, (cl, rec) in c[1].items():
            sc_cnt[(S, lab)][cl] += 1
    P(f"\n### {nm}: reports (RACE-class pc pairs) of the programs that are Race, split by class, per suite and label\n")
    P("Programs counted: those Race in " + nm + " (races alone). Columns: pairs in all / of them not in C1 / not in C6 / not in scalar-clock, each split into "
      "derived / rescued / async / atomic-chain-off / other (definitions above the tables).\n")
    refs = [("all", "all")] + [(r, "not in " + NAME[r]) for r in (CO, CC, SC) if r != m]
    hdr = "| suite | label | programs | " + " | ".join(f"{t}: total" + "".join(f" | {c}" for c in CLASSES) for _, t in refs) + " |"
    P(hdr)
    P("|---|---|---|" + ("---|" * (1 + len(CLASSES))) * len(refs))
    rows = []
    for S in SUITES:
        for lab in ("racy", "race-free", "unlabelled"):
            if not nprog[(S, lab)]:
                continue
            cells = []
            for r, _ in refs:
                cc_ = cnt.get((S, lab, r), collections.Counter())
                cells.append(str(sum(cc_.values())))
                cells += [str(cc_[c]) for c in CLASSES]
            P(f"| {SUITE[S]} | {lab} | {nprog[(S, lab)]} | " + " | ".join(cells) + " |")
            rows.append((SUITE[S], lab, nprog[(S, lab)], *cells))
    tot = {}
    for r, t in refs:
        for lab in ("racy", "race-free", "unlabelled", "ALL"):
            cc_ = collections.Counter()
            for (S, l, rr), v in cnt.items():
                if rr == r and (lab == "ALL" or l == lab):
                    cc_.update(v)
            tot[(r, lab)] = cc_
    for lab in ("racy", "race-free", "unlabelled", "ALL"):
        npr = sum(v for (S, l), v in nprog.items() if lab == "ALL" or l == lab)
        cells = []
        for r, _ in refs:
            cc_ = tot[(r, lab)]
            cells.append(str(sum(cc_.values())))
            cells += [str(cc_[c]) for c in CLASSES]
        P(f"| **all** | **{lab}** | {npr} | " + " | ".join(cells) + " |")
        rows.append(("all", lab, npr, *cells))
    wcsv(f"false_report_split_{nm.lower()}.csv", ["suite", "label", "programs"] + [f"{r}:{c}" for r, _ in refs for c in ("total",) + CLASSES], rows)
    if missing:
        P(f"\nPrograms Race in {nm} without a confirm JSON: {dict(missing)}")
    rf = {r: tot[(r, "race-free")] for r, _ in refs}
    P(f"\nRace-free-labelled programs, {nm}: " + "; ".join(
        f"{('all reports' if r == 'all' else 'not in ' + NAME[r])}: {sum(rf[r].values())} ("
        + ", ".join(f"{c} {rf[r][c]}" for c in CLASSES) + ")" for r, _ in refs))
    t = collections.Counter()
    for (S, lab), v in tags.items():
        t.update(v)
    P(f"\nRecord-level tag counts for {nm} (not exclusive; pairs with the tag on their chosen record): pairs {t['pairs']}, chain_src=chain {t['chain_src=chain']}, "
      f"chain_src=chain_rescue {t['chain_src=chain_rescue']}, async {t['async']}, atomic_chain_off {t['atomic_chain_off']}.")
    sc_tot = collections.Counter()
    for v in sc_cnt.values():
        sc_tot.update(v)
    P(f"Strong-conflict-class pairs (raw_sc) of the Race programs, {nm}: {sum(sc_tot.values())} (" + ", ".join(f"{c} {sc_tot[c]}" for c in CLASSES) + ")")
    return cnt, nprog


P("\n## False reports: the split by how the verdict step found them\n")
P("Definitions (record = one entry of the confirm JSON's `raw`; pair = deduped (space, pc, pc)):\n"
  "- **derived**: `chain_src` = `chain`: no recorded edge joins the pair, only a chain of reads (the closure's own pair).\n"
  "- **rescued**: `chain_src` = `chain_rescue`: an edge whose own distance is thread-local (or narrower than the chain's) judged at the chain's widest bound.\n"
  "- **async**: `async` = true: the cp.async cross-agent rule (`--co-async`): an edge with a same-thread instance whose earlier access is a `LDGSTS` copy and whose later access is not, unless an unguarded `DEPBAR.LE SB0, 0x0` lies on every CFG path between them; judged at no narrower than warp, with no R1/R3 credit.\n"
  "- **atomic-chain-off**: `atomic_chain_off` = true: the region-dominance certificate (R3, the PC-level atomic hand-off chain) that `--co-r3 cfg` grants was withheld (S1 strict: R3 must also find a chain with scalar-clock's CFG-decidable declines; S2 off: no R3 certificate), so the pair is reported where cfg orders it.\n"
  "- **other**: none of the four: an ordinary edge or event record.\n"
  "Precedence for a record: atomic-chain-off, async, derived, rescued, other. A pair has the least special class among its records (a pair that an ordinary record also reports is `other`). "
  "C6's confirm JSONs predate the async / atomic_chain_off tags (they count as false), so for C6 only derived / rescued / other occur.\n")
SPL = {}
for m in (CC, S1, S2):
    SPL[m] = split_tables(m)

# ============================================================ 2. what moved against C6
P("\n## What moved against C6\n")
# 2a. verdict changes
P("### Verdict changes against C6 (races alone), with the tags of the records that cause them\n")
P("| setting | suite | program | label | C6 | S | reports C6 -> S | pairs of S not in C6 (class) | pairs of C6 not in S |")
P("|---|---|---|---|---|---|---|---|---|")
chg_rows = []
chg_count = collections.defaultdict(collections.Counter)
for m in (S1, S2):
    for i in ids:
        a, b = rv(i, CC), rv(i, m)
        if a is None or b is None or a == b:
            continue
        S = meta[i][0]
        chg_count[m][S] += 1
        ca, cb = conf(CC, i), conf(m, i)
        pa = set(ca[0]) if ca else set()
        pb = {k: v[0] for k, v in cb[0].items()} if cb else {}
        gained = {k: c for k, c in pb.items() if k not in pa}
        lost = pa - set(pb)
        P(f"| {NAME[m]} | {S} | `{i}` | {LAB.get(label(i), 'unlabelled')} | {a} | {b} | {runs[(i, 'cuvein', CC)]['reports']} -> {runs[(i, 'cuvein', m)]['reports']} | "
          + ", ".join(f"{k[0]}:{hex(k[1])}-{hex(k[2])} ({c})" for k, c in sorted(gained.items())) + " | "
          + ", ".join(f"{k[0]}:{hex(k[1])}-{hex(k[2])}" for k in sorted(lost)) + " |")
        chg_rows.append((NAME[m], S, i, LAB.get(label(i), "unlabelled"), a, b))
wcsv("verdict_changes_vs_c6.csv", ["setting", "suite", "id", "label", "c6", "s"], chg_rows)
P("\nPrograms whose verdict changed against C6, per suite: " + "; ".join(
    f"{NAME[m]}: " + (", ".join(f"{s} {chg_count[m][s]}" for s in SUITES if chg_count[m][s]) or "none") + f" (total {sum(chg_count[m].values())})" for m in (S1, S2)))

# 2b. pair-level moves
P("\n### Pair-level moves against C6 (RACE-class pc pairs, programs Race in either)\n")
P("Per suite: pairs only in S (gained), by the class of the gained pair in S; pairs only in C6 (lost), by C6's class (derived / rescued / other); programs with any move; "
  "programs whose verdict is the same in both but whose pair set moved.\n")
for m in (S1, S2):
    nm = NAME[m]
    P(f"\n**{nm} against C6**\n")
    P("| suite | programs compared | programs with a pair move | of them, same verdict | pairs in both | gained | gained: derived | rescued | async | atomic-chain-off | other | lost | lost: derived | rescued | other |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    rows = []
    T = collections.Counter()
    for S in SUITES:
        c = collections.Counter()
        for i in ids:
            if meta[i][0] != S:
                continue
            a, b = rv(i, CC), rv(i, m)
            if a not in ("RACE", "CLEAN") or b not in ("RACE", "CLEAN"):
                continue
            ca, cb = conf(CC, i), conf(m, i)
            if ca is None or cb is None:
                continue
            c["n"] += 1
            pa, pb = ca[0], cb[0]
            g = [k for k in pb if k not in pa]
            l = [k for k in pa if k not in pb]
            c["both"] += len(set(pa) & set(pb))
            if g or l:
                c["moved"] += 1
                c["moved_same"] += (a == b)
            c["gained"] += len(g)
            c["lost"] += len(l)
            for k in g:
                c["g_" + pb[k][0]] += 1
            for k in l:
                c["l_" + pa[k][0]] += 1
        T.update(c)
        row = [SUITE[S], c["n"], c["moved"], c["moved_same"], c["both"], c["gained"]] + [c["g_" + x] for x in CLASSES[:4] + ("other",)] + [c["lost"], c["l_derived"], c["l_rescued"], c["l_other"]]
        P("| " + " | ".join(str(x) for x in row) + " |")
        rows.append(row)
    row = ["**all**", T["n"], T["moved"], T["moved_same"], T["both"], T["gained"]] + [T["g_" + x] for x in CLASSES[:4] + ("other",)] + [T["lost"], T["l_derived"], T["l_rescued"], T["l_other"]]
    P("| " + " | ".join(str(x) for x in row) + " |")
    wcsv(f"pair_moves_{nm.lower()}_vs_c6.csv", ["suite", "n", "moved", "moved_same", "both", "gained", "g_derived", "g_rescued", "g_async", "g_off", "g_other", "lost", "l_derived", "l_rescued", "l_other"], rows + [row])

# 2c. derived / rescued counts: the narrowest (C6) against the widest (C6b) closure bound
P("\n### Derived and rescued counts, narrowest bound (C6) against widest bound (S1, S2)\n")
P("Programs with chain_derived > 0 / chain_rescued > 0 and the sums of the per-program counts (notes `chain_derived`, `chain_rescued`, one row per program: rep 1), "
  "per suite. A derived pair is a pair no edge joins; a rescued one is an edge judged at its chain's bound (C6: edges whose own distance was thread-local; "
  "C6b: every edge whose chain bound is wider than its own distance).\n")


def notes_of(m):
    out = {}
    for (i, t, mm), r in runs.items():
        if t == "cuvein" and mm == m:
            n = r["notes"]
            d = re.search(r"(?:^|;)chain_derived=(\d+)", n)
            s = re.search(r"(?:^|;)chain_rescued=(\d+)", n)
            if d and s:
                out[i] = (int(d.group(1)), int(s.group(1)))
    return out


NT = {m: notes_of(m) for m in (CC, S1, S2)}
P("| suite | programs | C6 derived>0 | S1 | S2 | C6 rescued>0 | S1 | S2 | C6 sum derived | S1 | S2 | C6 sum rescued | S1 | S2 |")
P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
rows = []
for S in SUITES + ("all",):
    sel = [i for i in NT[CC] if (S == "all" or meta[i][0] == S) and i in NT[S1] and i in NT[S2]]
    row = [SUITE.get(S, "**all**"), len(sel)]
    row += [sum(1 for i in sel if NT[m][i][0] > 0) for m in (CC, S1, S2)]
    row += [sum(1 for i in sel if NT[m][i][1] > 0) for m in (CC, S1, S2)]
    row += [sum(NT[m][i][0] for i in sel) for m in (CC, S1, S2)]
    row += [sum(NT[m][i][1] for i in sel) for m in (CC, S1, S2)]
    P("| " + " | ".join(str(x) for x in row) + " |")
    rows.append(row)
wcsv("derived_rescued_by_suite.csv", ["suite", "programs", "c6_der_prog", "s1_der_prog", "s2_der_prog", "c6_res_prog", "s1_res_prog", "s2_res_prog",
                                      "c6_der_sum", "s1_der_sum", "s2_der_sum", "c6_res_sum", "s1_res_sum", "s2_res_sum"], rows)
# per program shifts between derived / rescued
mv = collections.Counter()
for m in (S1, S2):
    for i in NT[CC]:
        if i in NT[m]:
            d0, r0 = NT[CC][i]
            d1, r1 = NT[m][i]
            mv[(NAME[m], "derived up" if d1 > d0 else "derived down" if d1 < d0 else "derived same")] += 1
            mv[(NAME[m], "rescued up" if r1 > r0 else "rescued down" if r1 < r0 else "rescued same")] += 1
P("\nPrograms by change of the per-program count against C6: " + "; ".join(f"{k[0]} {k[1]} {v}" for k, v in sorted(mv.items())))

# ============================================================ 3. lock_rtraw and matrix-multiplication-norace
P("\n### lock_rtraw and matrix-multiplication-norace in every setting\n")
TARGET = [i for i in ids if i == "P5-race_interblock_none-lock_rtraw" or (meta[i][0] == "P4" and "matrix-multiplication-norace" in i)]
P("Cells: races-alone verdict; reports (Race-class pairs); `classes=` of the notes; the RACE-class and strong-class pairs of the confirm JSON with their tags "
  "(src = chain_src; A = async, O = atomic_chain_off).\n")
P("| program | label | mode | verdict | reports | classes | RACE-class pairs (src, tags) | strong-class pairs (src, tags) |")
P("|---|---|---|---|---|---|---|---|")
for i in TARGET:
    for m in (SC, CO, CC, S1, S2):
        r = runs.get((i, "cuvein", m))
        if r is None:
            continue
        cl = re.search(r"(?:^|;)classes=([^;]*)", r["notes"])
        cc_ = conf(m, i) if m in CONF else None
        f = lambda d: ", ".join(f"{k[0]}:{hex(k[1])}-{hex(k[2])} ({rec.get('race_type', '')}, {rec.get('chain_src') or 'edge'}{', A' if rec.get('async') else ''}{', O' if rec.get('atomic_chain_off') else ''})"
                                for k, (c_, rec) in sorted(d.items()))
        P(f"| `{i}` | {LAB.get(label(i), 'unlabelled')} | {NAME[m]} | {rv(i, m)} | {r['reports']} | {cl.group(1) if cl else ''} | "
          + (f(cc_[0]) if cc_ else (", ".join(f"{k[0]}:{hex(k[1])}-{hex(k[2])}" for k in sorted(PAIRS[m].get(i, set()))) if m in PAIRS else "")) + " | "
          + (f(cc_[1]) if cc_ else "") + " |")
open(f"{OUT}/c6b_detect.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))

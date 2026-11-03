#!/usr/bin/env python3
"""C6 step 3: detections of the chain-closure mode against scalar-clock, per suite and both ways, with a reason per miss from the
collector-only kernel JSONs; the false-report split (derived / rescued / other) against C1 and scalar-clock; the 20-pair sample of
derived-only pairs on race-free programs; the named production races and PCL.
Verdicts: races alone (make_tables.race_alone_verdict) from the sandbox of c6_stage.sh; pair sets: the `report_ids` of the reps (union)
of each mode's CSV in c6-step3/inputs (scalar-clock and C1's CO from cap-84600, chain from co-chain/merged), all classes together.
Kernel JSONs: the paths in the chain-kernels-*.jsonl of step 2.  Writes $OUTD/detect/."""
import collections
import csv
import glob
import heapq
import json
import math
import os
import random
import re
import statistics
import subprocess
import sys
import multiprocessing as mp
from multiprocessing import Pool
mp.set_start_method("fork")

W = "/home/fzheng4/wt-c6"
CH = f"{W}/eval/results/co-chain"
S3 = "/home/fzheng4/c6-step3"
OUT = os.environ.get("OUTD", f"{CH}/step3") + "/detect"
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, f"{W}/python")
import sync_dominance as sd  # noqa: E402

sys.argv = [sys.argv[0], "--collector-only", "--co-chain"]
SB = os.environ.get("COSB", f"{S3}/sand-b")
sys.path.insert(0, f"{SB}/eval/baselines")
import make_tables as mt  # noqa: E402

NONE, WARP, GRID = sd.NONE, sd.WARP, sd.GRID
LVL = {NONE: "thread", WARP: "warp", getattr(sd, "BLOCK", 2): "block", GRID: "grid"}
POOL_CAP = 4608          # shared-shadow objects per worker for `accelprof -n 1` (c6-step0.md section 5, pc_dependency_analysis.cpp:2752-2762)
runs, meta = mt.load_runs()
man = mt.load_manifest()
VC, SC, CO, CC = mt.VC, mt.SC, mt.CO, mt.CCHN
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


def rv(i, mode):
    r = runs.get((i, "cuvein", mode))
    if r is None:
        return None
    if r["verdict"] in ("RACE", "CLEAN"):
        v = mt.race_alone_verdict(r)
        return r["verdict"] if v is None else v
    return r["verdict"]


TOK = re.compile(r"^(\w+):0x([0-9a-f]+)-0x([0-9a-f]+):(\w+)$")


def pairs_of(ids_str):
    out = []
    for t in (ids_str or "").split():
        m = TOK.match(t)
        if m:
            out.append((m.group(1), int(m.group(2), 16), int(m.group(3), 16)))
    return out


def pk(sp, a, b):
    return (sp, min(a, b), max(a, b))


def load_pairs(path, mode):
    per = collections.defaultdict(list)
    for r in csv.DictReader(open(path, newline="")):
        if r["mode"] == mode:
            per[r["id"]].append(r)
    out = {}
    for i, reps in per.items():
        s, trunc = set(), False
        for r in reps:
            ts = pairs_of(r["report_ids"])
            s |= {pk(*t) for t in ts}
            n = int(r["reports_dedup"]) if (r.get("reports_dedup") or "").isdigit() else 0
            if len(ts) < n:
                trunc = True
        out[i] = (s, trunc)
    return out


PAIRS = {SC: load_pairs(f"{S3}/inputs/baselines-cuvein.csv", "scalar-clock"),
         CO: load_pairs(f"{S3}/inputs/baselines-cuvein-co.csv", "collector-only"),
         CC: load_pairs(f"{S3}/inputs/baselines-cuvein-cc.csv", "collector-only-chain")}

# ---- kernel lists of step 2
KERN = collections.defaultdict(list)
for d in ("c1-main", "c1-long", "c1-24h", "c2-recall", "c2-cand"):
    for f in sorted(glob.glob(f"{CH}/{d}/chain-kernels-*.jsonl")):
        for ln in open(f):
            try:
                j = json.loads(ln)
            except ValueError:
                continue
            if j["kernel_json"] not in KERN[j["id"]]:
                KERN[j["id"]].append(j["kernel_json"])
CONF = {}
for d in ("c1-main", "c1-long", "c1-24h", "c2-recall", "c2-cand"):
    for f in glob.glob(f"{CH}/{d}/confirm/*__cuvein__collector-only.json"):
        CONF[os.path.basename(f).split("__")[0]] = f

# ---- static deficits (job 325602)
DEF = {}
try:
    so = json.load(open("/home/fzheng4/c6-static/c6_static_out.json"))
    for rec in so["B"]:
        d = {}
        for k, v in rec["pcs"].items():
            name, pc = k.rsplit("\x1f", 1)
            d[(name, int(pc))] = (v["exp"], v["obs"])
        DEF[rec["id"]] = d
except Exception as e:      # noqa: BLE001
    print("static deficits unavailable:", e)


# ---- kernel JSON helpers
_KC = {}


def load_kj(path):
    if path in _KC:
        return _KC[path]
    j = json.load(open(path))
    k = j["kernel"]
    nodes = {n["pc"]: n for n in j.get("nodes", [])}
    hops, inw, edgew = {}, collections.Counter(), {}
    for e in j.get("edges", []):
        dist = e.get("dist", {})
        cur, anc = e["current_pc"], e.get("ancient_pc")
        w = sum(v for kk, v in dist.items() if kk != "intra_instance_launch")
        inw[cur] += w
        if e.get("cold_miss") or anc is None:
            continue
        d, _ = sd._observed(dist)
        if d == NONE and dist.get("intra_instance_launch", 0):
            d = WARP
        row = hops.setdefault(anc, {})
        row[cur] = max(row.get(cur, NONE), d)
        edgew[(anc, cur)] = dist
    info = dict(name=k["kernel_name"], grid=k.get("grid_cta_count"), nodes=nodes, hops=hops, inw=inw, edgew=edgew)
    if len(_KC) > 400:
        _KC.clear()
    _KC[path] = info
    return info


def is_read(info, pc):
    n = info["nodes"].get(pc)
    return bool(n) and (n.get("flags") or "").split()[:1] == ["READ"]


def minimax(info, a, c, read_only=True):
    """-> (bound, path) of the narrowest walk a -> h1..hk -> c (k >= 1, inner nodes reads if read_only) or None."""
    hops = info["hops"]
    best, pred, heap = {}, {}, []
    for h, d in hops.get(a, {}).items():
        if (not read_only or is_read(info, h)) and d < best.get(h, GRID + 1):
            best[h], pred[h] = d, None
            heapq.heappush(heap, (d, h))
    while heap:
        d, h = heapq.heappop(heap)
        if d > best[h]:
            continue
        for x, dc in hops.get(h, {}).items():
            nd = max(d, dc)
            if (not read_only or is_read(info, x)) and nd < best.get(x, GRID + 1):
                best[x], pred[x] = nd, h
                heapq.heappush(heap, (nd, x))
    res = None
    for h, bh in best.items():
        dc = hops.get(h, {}).get(c)
        if dc is not None:
            nd = max(bh, dc)
            if res is None or nd < res[0]:
                res = (nd, h)
    if res is None:
        return None
    path, h = [], res[1]
    while h is not None:
        path.append(h)
        h = pred[h]
    return res[0], [a] + path[::-1] + [c]


_DC = {}


def disposition(kj, a, c):
    """The verdict step's own record for the pc pair in this kernel (sd.analyze with the chain closure on)."""
    if kj not in _DC:
        rep = None
        dots = sorted(glob.glob(os.path.dirname(os.path.dirname(kj)) + "/dots/*.dot"))
        for dot in dots:
            try:
                rep = sd.analyze(dot, kj, chain_closure=True)
                break
            except sd.AlignmentError:
                continue
            except Exception:      # noqa: BLE001
                rep = None
                break
        vm, sm = {}, {}
        if rep:
            for v in rep["verdicts"]:
                key = frozenset((v["current_pc"], v["ancient_pc"]))
                src = "chain" if v.get("chain") else ("chain_rescue" if v.get("chain_rescue") else "edge")
                vm.setdefault(key, []).append((v["verdict"], v.get("hb_class") or v.get("matrix_class") or "", src))
            for s in rep.get("skipped_edges", []):
                sm.setdefault(frozenset((s.get("current_pc"), s.get("ancient_pc"))), []).append(s.get("reason"))
        if len(_DC) > 40:
            _DC.clear()
        _DC[kj] = (rep is not None, vm, sm)
    ok, vm, sm = _DC[kj]
    if not ok:
        return "analysis unavailable"
    key = frozenset((a, c))
    if key in vm:
        vs = sorted(set(vm[key]), key=lambda x: (x[0] != "RACE", x))
        return "judged " + "/".join(f"{v[0]}({v[1]},{v[2]})" for v in vs[:2])
    if key in sm:
        return "skipped " + "/".join(sorted(set(str(x) for x in sm[key])))
    return "no record"


CATS = ["pcs not both recorded", "edge/chain cross-thread, judged not reported", "edge/chain only thread-local", "only via a non-read hop (intervening write/atomic)",
        "not reachable: dropped-word deficit at a or c", "not reachable: deficit at another pc of the kernel",
        "not reachable: shared-pool exhaustion not excluded (grid > 4608 CTAs)", "not reachable: no gap evidence"]


def classify(pid, sp, a, c, want_name=None):
    kjs = KERN.get(pid, [])
    seen_a = seen_c = both = 0
    cat, detail = None, ""
    rank = {k: n for n, k in enumerate(CATS)}
    def upd(cn, dt=""):
        nonlocal cat, detail
        if cat is None or rank[cn] < rank[cat]:
            cat, detail = cn, dt
    dmap = DEF.get(pid, {})
    for kj in kjs:
        try:
            info = load_kj(kj)
        except Exception:      # noqa: BLE001
            continue
        if want_name and info["name"] != want_name:
            continue
        na, nc = a in info["nodes"], c in info["nodes"]
        seen_a += na
        seen_c += nc
        if not (na and nc):
            continue
        both += 1
        h = info["hops"]
        direct = [x for x in (h.get(a, {}).get(c), h.get(c, {}).get(a)) if x is not None]
        ch = [x for x in (minimax(info, a, c), minimax(info, c, a)) if x]
        cross = [d for d in direct if d > NONE] + [x[0] for x in ch if x[0] > NONE]
        if cross:
            upd(CATS[1], ("edge; " if (direct and max(direct) > NONE) else "read-chain; ") + disposition(kj, a, c))
            continue
        if direct or ch:
            upd(CATS[2], "edge" if direct else "read-chain")
            continue
        anyp = minimax(info, a, c, False) or minimax(info, c, a, False)
        if anyp:
            upd(CATS[3], "bound " + LVL.get(anyp[0], str(anyp[0])))
            continue
        nm = info["name"]
        dfa = any(dmap.get((nm, p), (0, 0))[0] > dmap.get((nm, p), (0, 0))[1] for p in (a, c))
        dfk = any(v[0] > v[1] for (n2, p), v in dmap.items() if n2 == nm)
        shared = "SHARED" in ((info["nodes"][a].get("flags") or "") + (info["nodes"][c].get("flags") or ""))
        if dfa:
            upd(CATS[4], "")
        elif dfk:
            upd(CATS[5], "")
        elif shared and (info["grid"] is None or info["grid"] > POOL_CAP):
            upd(CATS[6], f"grid {info['grid']}")
        else:
            upd(CATS[7], f"a out-hops {len(h.get(a, {}))}, c in-hops {sum(1 for s in h.values() if c in s)}")
    if both == 0:
        return CATS[0], f"pc a in {seen_a}, pc c in {seen_c} of {len(kjs)} kernels"
    return cat, detail


def classify_program(args):
    pid, prs = args
    return pid, [(p, *classify(pid, *p)) for p in prs]


# ============================================================ part 1: program and pair level, scalar-clock vs chain
ids = sorted(i for i in meta if meta[i][0] in SUITE)
rowsP, miss_progs, ccmiss = [], [], []
st = collections.defaultdict(collections.Counter)
for i in ids:
    s, c = rv(i, SC), rv(i, CC)
    if s not in ("RACE", "CLEAN") or c not in ("RACE", "CLEAN"):
        st[meta[i][0]]["other"] += 1
        continue
    S = meta[i][0]
    lab = LAB.get(label(i), label(i) or "unlabelled")
    st[S]["n"] += 1
    sp, strunc = PAIRS[SC].get(i, (set(), False))
    cp, ctrunc = PAIRS[CC].get(i, (set(), False))
    op, _ = PAIRS[CO].get(i, (set(), False))
    if c == "RACE" and s == "CLEAN":
        st[S][f"chain_only_{lab}"] += 1
    if s == "RACE" and c == "CLEAN":
        st[S][f"sc_only_{lab}"] += 1
        miss_progs.append(i)
    if s == "RACE" and c == "RACE":
        st[S]["both"] += 1
        sc_only = sp - cp
        if sc_only:
            st[S]["both_with_sc_only_pairs"] += 1
            st[S]["sc_only_pairs"] += len(sc_only)
            ccmiss.append(i)
        st[S]["chain_only_pairs_in_both"] += len(cp - sp)
        st[S]["trunc"] += int(strunc or ctrunc)
    if s == "RACE":
        st[S]["sc_pairs_total"] += len(sp)
        st[S]["sc_pairs_in_c1"] += len(sp & op)
        st[S]["sc_pairs_in_chain"] += len(sp & cp)
    if c == "RACE":
        st[S]["chain_pairs_total"] += len(cp)
        st[S]["chain_pairs_in_sc"] += len(cp & sp) if s == "RACE" else 0
P("## Detections of CO+chain against scalar-clock (verdicts: races alone)\n")
P("Programs that have a verdict in both modes. `chain only` = Race in CO+chain, Clean in scalar-clock; `sc only` = Race in scalar-clock, Clean in CO+chain, "
  "split by the paper's label (racy / race-free / unlabelled). `both` = Race in both; of those `with sc-only pairs` = programs where scalar-clock reports a pc pair "
  "the chain mode does not (pair sets compared as unordered pc pairs per space, over the union of the reps; scalar-clock and CO are separate recordings).\n")
P("| suite | programs | chain only (racy / race-free / unl.) | sc only (racy / race-free / unl.) | both Race | both, with sc-only pairs | sc-only pairs | chain-only pairs in those | scalar-clock pairs in programs Race in sc | of them also in C1 | of them also in chain |")
P("|---|---|---|---|---|---|---|---|---|---|---|")
tot = collections.Counter()
for S in ("P1", "PI", "P3", "P4", "P5", "P6", "P7", "P9"):
    c = st[S]
    tot.update(c)
    P(f"| {SUITE[S]} | {c['n']} | {c['chain_only_racy']} / {c['chain_only_race-free']} / {c['chain_only_unlabelled']} | {c['sc_only_racy']} / {c['sc_only_race-free']} / {c['sc_only_unlabelled']} | "
      f"{c['both']} | {c['both_with_sc_only_pairs']} | {c['sc_only_pairs']} | {c['chain_only_pairs_in_both']} | {c['sc_pairs_total']} | {c['sc_pairs_in_c1']} | {c['sc_pairs_in_chain']} |")
c = tot
P(f"| **all** | {c['n']} | {c['chain_only_racy']} / {c['chain_only_race-free']} / {c['chain_only_unlabelled']} | {c['sc_only_racy']} / {c['sc_only_race-free']} / {c['sc_only_unlabelled']} | "
  f"{c['both']} | {c['both_with_sc_only_pairs']} | {c['sc_only_pairs']} | {c['chain_only_pairs_in_both']} | {c['sc_pairs_total']} | {c['sc_pairs_in_c1']} | {c['sc_pairs_in_chain']} |")
P(f"\nPair sets cut by the CSV (fewer report_ids than reports_dedup) in {c['trunc']} of the Race-in-both programs.")
wcsv("detect_by_suite.csv", ["suite", "key", "value"], [(S, k, v) for S in st for k, v in sorted(st[S].items())])

# ============================================================ part 2: reasons
work = []
for i in miss_progs:
    sp = PAIRS[SC][i][0]
    work.append((i, sorted(sp - PAIRS[CC].get(i, (set(), 0))[0])))
rng = random.Random(20261102)
cc_work = list(ccmiss)
CAPP = int(os.environ.get("C6_PAIR_PROGRAMS", "700"))
if len(cc_work) > CAPP:
    cc_work = sorted(rng.sample(cc_work, CAPP))
for i in cc_work:
    work.append((i, sorted(PAIRS[SC][i][0] - PAIRS[CC][i][0])))
res = {}
with Pool(int(os.environ.get("C6_NP", "12"))) as pool:
    for pid, lst in pool.imap_unordered(classify_program, work, chunksize=2):
        res[pid] = lst
prow = []
for pid, lst in res.items():
    for p, cat, dt in lst:
        prow.append((meta[pid][0], pid, label(pid), "program missed" if pid in miss_progs else "pair missed, program Race", p[0], hex(p[1]), hex(p[2]), cat, dt))
wcsv("sc_only_pairs_classified.csv", ["suite", "id", "label", "kind", "space", "pc_a", "pc_b", "category", "detail"], prow)
P("\n## Why scalar-clock's pairs are missing: classification in the collector-only kernel JSONs\n")
P("For each pc pair that scalar-clock reports and the chain mode does not, over all kernel JSONs of the program's CO recording that contain both pcs as nodes. "
  "The classes are tried in this order and the first that applies in any kernel is used:\n")
for n, k in enumerate(CATS):
    P(f"{n + 1}. {k}")
P("\n'Judged not reported' = the verdict step has a recorded transition (edge, or a chain of reads) joining the pair across threads, and its own record for the pair "
  "is not a Race (the verdict is given in the csv: ORDERED by a certificate, benign, read-read, etc.). 'deficit' = static check (b): expected shadow words from the node's lane "
  "and address counts exceed the words on the edges (c6_static_out.json, per kernel name and pc, estimate). 'pool' = a shared-space pair in a kernel with more than 4,608 "
  "CTAs: `pool_miss_count` is not emitted, so exhaustion cannot be confirmed, only not excluded.\n")
for kind in ("program missed", "pair missed, program Race"):
    P(f"\n**{kind}**: pairs per suite and class\n")
    P("| suite | programs | pairs | " + " | ".join(str(n + 1) for n in range(len(CATS))) + " |")
    P("|---|---|---|" + "---|" * len(CATS))
    for S in ("P1", "PI", "P3", "P4", "P5", "P6", "P7", "P9"):
        rr = [r for r in prow if r[0] == S and r[3] == kind]
        if not rr:
            continue
        cc_ = collections.Counter(r[7] for r in rr)
        P(f"| {SUITE[S]} | {len({r[1] for r in rr})} | {len(rr)} | " + " | ".join(str(cc_[k]) for k in CATS) + " |")
    rr = [r for r in prow if r[3] == kind]
    cc_ = collections.Counter(r[7] for r in rr)
    P(f"| **all** | {len({r[1] for r in rr})} | {len(rr)} | " + " | ".join(str(cc_[k]) for k in CATS) + " |")
P(f"\nPrograms Race in both with sc-only pairs: {len(ccmiss)}; classified: {len(cc_work)} (cap {CAPP}, seeded sample).")
# per missed program: the classes of its pairs
P("\n**Programs Race in scalar-clock and Clean in CO+chain, one by one**\n")
P("| suite | id | label | sc pairs | classes of the sc pairs (counts) | oracle (PI) |")
P("|---|---|---|---|---|---|")
orc = {r["id"]: r for r in csv.DictReader(open(f"{SB}/eval/results/baselines-pi-oracle.csv", newline=""))}
mrows = []
for i in miss_progs:
    lst = res.get(i, [])
    cc_ = collections.Counter(c for _, c, _ in lst)
    P(f"| {meta[i][0]} | `{i}` | {LAB.get(label(i), 'unlabelled')} | {len(PAIRS[SC][i][0])} | " + "; ".join(f"{k} x{v}" for k, v in cc_.items())
      + f" | {orc.get(i, {}).get('oracle', '')} |")
    mrows.append((meta[i][0], i, label(i), len(PAIRS[SC][i][0]), "; ".join(f"{k} x{v}" for k, v in cc_.items()), orc.get(i, {}).get("oracle", "")))
wcsv("sc_race_chain_clean_programs.csv", ["suite", "id", "label", "sc_pairs", "classes", "oracle"], mrows)
# deficit census: programs with a deficit pc (static check b) among the Indigo 1.3 misses and in general
npi_def = sum(1 for i in ids if meta[i][0] == "PI" and any(v[0] > v[1] for v in DEF.get(i, {}).values()))
P(f"\nStatic check (b) deficit programs among Indigo 1.3 program-inputs here: {npi_def}; among the programs Race in scalar-clock and Clean in CO+chain: "
  f"{sum(1 for i in miss_progs if any(v[0] > v[1] for v in DEF.get(i, {}).values()))} of {len(miss_progs)}.")

# ============================================================ part 3: false reports
def conf_records(pid):
    f = CONF.get(pid)
    if not f:
        return None
    j = json.load(open(f))
    out = {}
    for rec in (j.get("raw") or []):      # race-class records only (raw_sc = strong conflicts)
        k = pk(rec.get("space"), rec["a_pc"], rec["b_pc"])
        src = rec.get("chain_src") or "edge"
        old = out.get(k)
        if old is None or src == "edge" or (old[0] != "edge" and src == "chain_rescue"):
            out[k] = (src, rec.get("chain_path"), rec.get("race_type"))
    return out


fp = collections.defaultdict(collections.Counter)
pool_a, pool_b = [], []
for i in ids:
    if rv(i, CC) != "RACE":
        continue
    recs = conf_records(i)
    if recs is None:
        fp["missing_confirm"][meta[i][0]] += 1
        continue
    lab = LAB.get(label(i), "unlabelled")
    S = meta[i][0]
    op = PAIRS[CO].get(i, (set(), 0))[0]
    sp = PAIRS[SC].get(i, (set(), 0))[0]
    for k, (src, path, rt) in recs.items():
        for tag, ref in (("c1", op), ("sc", sp)):
            if k not in ref:
                fp[(S, lab, tag)][src] += 1
        if k not in op and src == "chain" and label(i) == "CLEAN":
            changed = rv(i, CO) != "RACE"
            (pool_a if changed else pool_b).append((i, k, path, rt))
        fp[(S, lab, "all")][src] += 1
P("\n## Reports of CO+chain that C1 and scalar-clock do not have, split by how the verdict step found them\n")
P("Unit: a deduped pc pair of a program that is Race in CO+chain (union of the reps in the CSV for C1 and scalar-clock; the raw records of the chain run's confirm JSON for the source). "
  "derived = `chain_src` chain (a pair no edge joins, only a chain of reads), rescued = chain_rescue (an edge whose own distance is thread-local, judged at its chain's bound), "
  "other = an ordinary edge or event record.\n")
P("| suite | label | reports in CO+chain | not in C1: derived | rescued | other | not in scalar-clock: derived | rescued | other |")
P("|---|---|---|---|---|---|---|---|---|")
frows = []
for S in ("P1", "PI", "P3", "P4", "P5", "P6", "P7", "P9"):
    for lab in ("racy", "race-free", "unlabelled"):
        a, b, c_ = fp[(S, lab, "all")], fp[(S, lab, "c1")], fp[(S, lab, "sc")]
        if not a:
            continue
        row = (SUITE[S], lab, sum(a.values()), b["chain"], b["chain_rescue"], b["edge"], c_["chain"], c_["chain_rescue"], c_["edge"])
        frows.append(row)
        P("| " + " | ".join(str(x) for x in row) + " |")
wcsv("false_report_split.csv", ["suite", "label", "reports", "vs_c1_derived", "vs_c1_rescued", "vs_c1_other", "vs_sc_derived", "vs_sc_rescued", "vs_sc_other"], frows)
tl = collections.Counter()
for (S, lab, tag), cnt in fp.items():
    if tag in ("c1", "sc") and lab == "race-free":
        tl[(tag, "derived")] += cnt["chain"]
        tl[(tag, "rescued")] += cnt["chain_rescue"]
        tl[(tag, "other")] += cnt["edge"]
P(f"\nOn race-free-labelled programs (all suites): reports not in C1 {tl[('c1', 'derived')]} derived / {tl[('c1', 'rescued')]} rescued / {tl[('c1', 'other')]} other; "
  f"not in scalar-clock {tl[('sc', 'derived')]} derived / {tl[('sc', 'rescued')]} rescued / {tl[('sc', 'other')]} other.")
P(f"Race-free-labelled programs Race in CO+chain: {sum(1 for i in ids if label(i) == 'CLEAN' and rv(i, CC) == 'RACE')}; in C1: "
  f"{sum(1 for i in ids if label(i) == 'CLEAN' and rv(i, CO) == 'RACE')}; in scalar-clock: {sum(1 for i in ids if label(i) == 'CLEAN' and rv(i, SC) == 'RACE')}.")
P(f"Programs Race in CO+chain without a confirm JSON: {dict(fp['missing_confirm'])}")

# ---- sample of 20 derived-only pairs on race-free programs
P("\n## Sample of 20 derived-only pairs on race-free programs: can the hops of the chain share an address?\n")
P("Pool A = derived pairs (not in C1's reports) of race-free-labelled programs whose verdict changed Clean -> Race (norace programs); pool B = such pairs of race-free-labelled programs that were already Race in C1. "
  f"Pool sizes: A {len(pool_a)}, B {len(pool_b)}. Sample: up to 10 from A, the rest from B, seeded random (20261102), one pair per program first. "
  "The kernel JSON has no addresses, only words per (pc, ancient pc) edge. For an inner node h with in-hop words n(a,h), out-hop words n(h,c) and N(h) the words that entered the shadow at h "
  "(all incoming edge words except the same-instruction repeat lanes), the accesses of h that follow a and the accesses of h that precede c are subsets of the N(h) accesses of h; "
  "if n(a,h) + n(h,c) > N(h) they share at least n(a,h) + n(h,c) - N(h) accesses of h, so a, h, c are consecutive at one address: **proven**. Otherwise the JSON cannot say: **undetermined** "
  "(the sets may or may not coincide). For a chain with two or more inner nodes the test is per inner node.\n")


def pick(pool, n):
    seen, out = set(), []
    pool = sorted(pool, key=lambda x: (x[0], x[1]))
    rr = random.Random(20261102)
    rr.shuffle(pool)
    for x in pool:
        if x[0] not in seen:
            seen.add(x[0])
            out.append(x)
        if len(out) == n:
            return out
    for x in pool:
        if x not in out:
            out.append(x)
        if len(out) == n:
            break
    return out


sample = pick(pool_a, 10)
sample += pick([x for x in pool_b], 20 - len(sample))
srows = []
P("| # | program | label | space | a -> ... -> c | k | hop levels | hop words (non-repeat) | N(h) | proven same address (inner nodes) | direct edge a-c / c-a in the kernel |")
P("|---|---|---|---|---|---|---|---|---|---|---|")
for n, (pid, key, path, rt) in enumerate(sample, 1):
    pcs = [int(x, 16) for x in (path or [])]
    best = None
    for kj in KERN.get(pid, []):
        try:
            info = load_kj(kj)
        except Exception:      # noqa: BLE001
            continue
        if len(pcs) >= 3 and all(pcs[t + 1] in info["hops"].get(pcs[t], {}) for t in range(len(pcs) - 1)):
            best = (kj, info)
            break
    if best is None:
        P(f"| {n} | `{pid}` | {LAB.get(label(pid))} | {key[0]} | {' -> '.join(path or [])} | | | | | kernel with all hops not found | |")
        srows.append((n, pid, key[0], " -> ".join(path or []), "", "", "", "", "no kernel with all hops"))
        continue
    kj, info = best
    lv = [LVL.get(info["hops"][pcs[t]][pcs[t + 1]], "?") for t in range(len(pcs) - 1)]
    hw = []
    for t in range(len(pcs) - 1):
        d = info["edgew"].get((pcs[t], pcs[t + 1]), {})
        hw.append(sum(v for kk, v in d.items() if kk != "intra_instance_launch"))
    proven, nh = [], []
    for t in range(1, len(pcs) - 1):
        h = pcs[t]
        Nh = info["inw"].get(h, 0)
        nh.append(Nh)
        proven.append(hw[t - 1] + hw[t] > Nh)
    direct = (info["hops"].get(pcs[0], {}).get(pcs[-1]) is not None, info["hops"].get(pcs[-1], {}).get(pcs[0]) is not None)
    verdict = ("all inner nodes proven" if all(proven) else (f"{sum(proven)} of {len(proven)} proven" if any(proven) else "undetermined"))
    P(f"| {n} | `{pid}` | {LAB.get(label(pid))} | {key[0]} | {' -> '.join(path)} | {len(pcs) - 2} | {'/'.join(lv)} | {'/'.join(str(x) for x in hw)} | {'/'.join(str(x) for x in nh)} | {verdict} | {direct[0]} / {direct[1]} |")
    srows.append((n, pid, key[0], " -> ".join(path), len(pcs) - 2, "/".join(lv), "/".join(str(x) for x in hw), "/".join(str(x) for x in nh), verdict))
wcsv("fp_sample20.csv", ["n", "id", "space", "path", "k", "levels", "hop_words", "N_h", "verdict"], srows)
if srows:
    cnt = collections.Counter(r[-1] for r in srows)
    P(f"\nOf the {len(srows)} sampled pairs: " + "; ".join(f"{v} {k}" for k, v in cnt.items()))

# ============================================================ part 4: named production races and PCL
P("\n## The production races (CCCL top-k, Ginkgo range-minimum, Kokkos rw_sum, RAFT select_k) and PCL: scalar-clock's matched pairs in the CO recording\n")
NAMED = [("CCCL top-k", "cccl-3-buggy", "origin/study/realworld-recall", "eval/results/realworld/attrib", "eval/realworld/recall_pairs.json", "cccl-3"),
         ("Ginkgo range-minimum", "ginkgo-5-buggy", "origin/study/realworld-recall", "eval/results/realworld/attrib", "eval/realworld/recall_pairs.json", "ginkgo-5"),
         ("Kokkos rw_sum", "kokkos-5-buggy", "origin/study/realworld-recall", "eval/results/realworld/attrib", "eval/realworld/recall_pairs.json", "kokkos-5"),
         ("RAFT select_k", "raft-1-buggy", "origin/study/realworld-recall", "eval/results/realworld/attrib", "eval/realworld/recall_pairs.json", "raft-1"),
         ("PCL (data-race half)", "pcl-new-1-buggy", "origin/study/realworld-candidates", "eval/results/realworld_t21c/attrib", "eval/realworld/recall_pairs.json", "pcl-new-1")]


def gshow(ref, path):
    return subprocess.run(["git", "-C", W, "show", f"{ref}:{path}"], capture_output=True, text=True).stdout


def hits(frames, ranges, tol=2):
    import fnmatch
    for fr in frames or ():
        base = os.path.basename(fr["file"])
        for pat, l0, l1 in ranges:
            if fnmatch.fnmatch(base, pat) and l0 - tol <= fr["line"] <= l1 + tol:
                return True
    return False


nrows = []
P("| case | id | SC reports matching the oracle's pair(s) | in the chain run's reports | by source (edge / rescued / derived) | classes of the others in the CO recording |")
P("|---|---|---|---|---|---|")
for nm, pid, ref, adir, pj, target in NAMED:
    try:
        spec = json.loads(gshow(ref, pj)).get(target, {})
        att = json.loads(gshow(ref, f"{adir}/{pid}.json"))
    except Exception as e:      # noqa: BLE001
        P(f"| {nm} | {pid} | missing ({e}) | | | |")
        continue
    reps = att["modes"].get("scalar-clock", {}).get("reports", [])
    prs = [p for p in spec.get("pairs", []) if p.get("cls", "DR") == "DR"]
    matched = {}
    for r in reps:
        for p in prs:
            ok = (hits(r.get("a_frames"), p["A"], p.get("tol", 2)) and hits(r.get("b_frames"), p["B"], p.get("tol", 2))) or \
                 (hits(r.get("b_frames"), p["A"], p.get("tol", 2)) and hits(r.get("a_frames"), p["B"], p.get("tol", 2)))
            if ok and r.get("verdict") == "RACE":
                matched[(r["space"], r["a_pc"], r["b_pc"], r.get("kernel", ""))] = p["name"]
    recs = conf_records(pid) or {}
    inch = {k: recs[pk(k[0], k[1], k[2])] for k in matched if pk(k[0], k[1], k[2]) in recs}
    srcs = collections.Counter(v[0] for v in inch.values())
    cl = collections.Counter()
    for k in matched:
        if pk(k[0], k[1], k[2]) in recs:
            continue
        nm_ = next((x["name"] for x in att["modes"]["scalar-clock"]["kernels"] if x["name"] == k[3]), None) if k[3] else None
        cat, dt = classify(pid, k[0], k[1], k[2], nm_)
        cl[cat + (f" [{dt}]" if dt and cat in (CATS[1], CATS[3]) else "")] += 1
        nrows.append((nm, pid, k[0], hex(k[1]), hex(k[2]), matched[k], cat, dt))
    P(f"| {nm} | {pid} | {len(matched)} | {len(inch)} | {srcs['edge']} / {srcs['chain_rescue']} / {srcs['chain']} | " + ("; ".join(f"{k} x{v}" for k, v in cl.items()) or "-") + " |")
    for k in inch:
        nrows.append((nm, pid, k[0], hex(k[1]), hex(k[2]), matched[k], "reported by CO+chain via " + inch[k][0], ""))
wcsv("named_cases.csv", ["case", "id", "space", "pc_a", "pc_b", "oracle_pair", "category", "detail"], nrows)
open(f"{OUT}/c6_detect.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))

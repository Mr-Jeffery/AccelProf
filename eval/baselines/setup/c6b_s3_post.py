#!/usr/bin/env python3
"""C6b step 3 post-processing: merge the three runs, compare with X1b's scalar-clock rows, classify the pairs scalar-clock reports
that collector-only (hb-stripped recordings, guarded loader) does not, write the tables.
Inputs : eval/results/final-b/merged/baselines-cuvein.csv (scalar-clock rows), run-{s1,s2,cfg}/baselines-cuvein-shard*_16.csv,
         the stripped store /mnt/beegfs/fzheng4/c6b-step3/store (collector fields only: no hb_* key), run-*/probes/*.jsonl.
Outputs: eval/results/co-chain-b/step3/{merged-*/, violations_program_*.tsv, violations_pairs_*.tsv, pairs_*.tsv, pairs_*_by_program.tsv,
         assert_no_hb.txt, step3_summary.md}.  Run: python c6b_s3_post.py   (16 worker processes)"""
import collections
import csv
import glob
import heapq
import json
import os
import re
import sys
from multiprocessing import Pool

W = "/home/fzheng4/wt-c6b"
STORE = "/mnt/beegfs/fzheng4/c6b-step3/store"
O = f"{W}/eval/results/co-chain-b/step3"
SC_CSV = f"{W}/eval/results/final-b/merged/baselines-cuvein.csv"
SETS = {"s1": "strict", "s2": "off", "cfg": "cfg"}
POOL_CAP = 4608
sys.path.insert(0, f"{W}/python")
import sync_dominance as sd  # noqa: E402

sys.path.insert(0, f"{W}/eval/baselines")
import make_tables as mt  # noqa: E402

NONE, WARP, GRID = sd.NONE, sd.WARP, sd.GRID
LVL = {NONE: "thread", WARP: "warp", getattr(sd, "BLOCK", 2): "block", GRID: "grid"}
SUITE = {"P1": "Indigo3 (P1)", "PI": "Indigo 1.3 (PI)", "P3": "ECL (P3)", "P4": "ScoR apps (P4)", "P5": "ScoR litmus (P5)",
         "P6": "cuHadron (P6)", "P7": "HeCBench other 14 (P7)", "P9": "HeCBench SC 10 (P9)"}
TOK = re.compile(r"^([^:\s]+):0x([0-9a-f]+)-0x([0-9a-f]+):(\w*)$")
man = mt.load_manifest()


def pairs_of(s):
    out = []
    for t in (s or "").split():
        m = TOK.match(t)
        if m:
            a, b = int(m.group(2), 16), int(m.group(3), 16)
            out.append((m.group(1), min(a, b), max(a, b), m.group(4)))
    return out


def read_rows(paths, mode):
    per = collections.defaultdict(list)
    for p in paths:
        for r in csv.DictReader(open(p, newline="")):
            if r["mode"] == mode:
                per[r["id"]].append(r)
    return per


def pair_union(rows):
    s, n = {}, 0
    for r in rows:
        for t in pairs_of(r["report_ids"]):
            s[t[:3]] = t[3]
        if (r.get("reports_dedup") or "").isdigit():
            n = max(n, int(r["reports_dedup"]))
    return s, n


def rv(runs, i, mode):
    r = runs.get((i, "cuvein", mode))
    if r is None:
        return "NONE"
    if r["verdict"] in ("RACE", "CLEAN"):
        v = mt.race_alone_verdict(r)
        return r["verdict"] if v is None else v
    return r["verdict"]


# ------------------------------------------------------------------ kernel graph helpers (collector fields only)
def load_kj(path):
    j = json.load(open(path))
    k = j["kernel"]
    nodes = {n["pc"]: n for n in j.get("nodes", [])}
    hops, obs = {}, collections.Counter()
    for e in j.get("edges", []):
        dist = e.get("dist", {})
        cur, anc = e["current_pc"], e.get("ancient_pc")
        obs[cur] += sum(dist.values())
        if e.get("cold_miss") or anc is None:
            continue
        d, _ = sd._observed(dist)
        if d == NONE and dist.get("intra_instance_launch", 0):
            d = WARP
        row = hops.setdefault(anc, {})
        row[cur] = max(row.get(cur, NONE), d)
    deficit = {}
    for n in j.get("nodes", []):
        sz, fl = n.get("access_size"), n.get("flags") or ""
        al, di = n.get("active_lane_count"), n.get("distinct_address_count")
        if sz is None or al is None or di is None or "LOCAL" in fl:
            continue
        A = sum(int(kk) * v for kk, v in al.items())
        U = sum(int(kk) * v for kk, v in di.items())
        exp = (A - U) + U * ((sz + 3) // 4)
        o = obs.get(n["pc"], 0)
        if o < exp:
            deficit[n["pc"]] = (exp, o)
    return dict(name=k["kernel_name"], grid=k.get("grid_cta_count"), nodes=nodes, hops=hops, deficit=deficit)


def acc_of(info, pc):
    n = info["nodes"].get(pc)
    fl = (n.get("flags") or "").split() if n else []
    return fl[0] if fl else "?"


def is_read(info, pc):
    return acc_of(info, pc) == "READ"


def minimax(info, a, c, read_only=True):
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


def disposition(dots, kj, co_r3):
    """{frozenset(a,c): [records]}, {frozenset: [skip reasons]} of sd.analyze with --chain-closure --co-async --co-r3 <mode>."""
    rep = None
    for dot in dots:
        try:
            rep = sd.analyze(dot, kj, chain_closure=True, co_async=True, co_r3=co_r3)
            break
        except sd.AlignmentError:
            continue
        except Exception:      # noqa: BLE001
            return None
    if rep is None:
        return None
    vm, sm = {}, {}
    for v in rep["verdicts"]:
        vm.setdefault(frozenset((v["current_pc"], v["ancient_pc"])), []).append(v)
    for s in rep.get("skipped_edges", []):
        sm.setdefault(frozenset((s.get("current_pc"), s.get("ancient_pc"))), []).append(s.get("reason"))
    return vm, sm


def cert_name(v):
    """-> (label, full text) of the certificate that ordered the record."""
    if v.get("hb_chain"):
        return "R3 atomic chain", "R3 atomic chain " + "->".join(v["hb_chain"]) + " (cfg certificate stands)"
    syncs = v.get("ordering_syncs") or []
    sj = json.dumps(syncs)[:240]
    kind = "R1 barrier dominance" if "BAR" in sj else "R1 fence/sync dominance"
    return kind, f"{kind}: strength {v.get('strength')} >= observed {v.get('observed_distance')}; syncs {sj}"


def hexp(p):
    return hex(p)


def path_str(info, path):
    return "->".join(f"{hex(p)}[{acc_of(info, p)}]" for p in path)


# rank: lower wins when several kernels hold the pair (as c6_detect.py: a record in the CO graph beats a gap)
CLS = {"cert": "certificate granted", "cand": "candidate missing", "lane": "collector lane drop", "oth": "other"}


def eval_pair(info, dots, dcache, kj, co_r3, sp, a, c):
    """-> None (a or c not a node of this kernel) or (rank, cls, sub, detail)."""
    nodes = info["nodes"]
    if a not in nodes or c not in nodes:
        return None
    h = info["hops"]
    direct = [x for x in (h.get(a, {}).get(c), h.get(c, {}).get(a)) if x is not None]
    ch = [x for x in (minimax(info, a, c), minimax(info, c, a)) if x]
    cross = [d for d in direct if d > NONE] + [x[0] for x in ch if x[0] > NONE]
    dfa = {p: info["deficit"][p] for p in (a, c) if p in info["deficit"]}
    dnote = "" if not dfa else "; also dropped-word deficit at " + ",".join(f"{hex(p)} exp {e} obs {o}" for p, (e, o) in dfa.items())
    if cross:
        if kj not in dcache:
            dcache[kj] = disposition(dots, kj, co_r3)
        d = dcache[kj]
        how = "edge" if (direct and max(direct) > NONE) else "read-chain"
        if d is None:
            return (2, "oth", "analysis unavailable", f"{how} cross-thread; sd.analyze failed on this kernel")
        vm, sm = d
        key = frozenset((a, c))
        recs = vm.get(key, [])
        ordered = [v for v in recs if v["verdict"] == "ORDERED"]
        races = [v for v in recs if v["verdict"] == "RACE"]
        scs = [v for v in recs if v["verdict"] == "SC"]
        if ordered:
            lab, full = cert_name(ordered[0])
            return (0, "cert", lab,
                    f"{how} cross-thread ({LVL.get(max(cross), max(cross))}); ORDERED by {full}" +
                    f"; record: class {ordered[0].get('hb_class')}, atomic_chain_off {ordered[0].get('atomic_chain_off')}, kernel {info['name']}")
        if races:
            return (1, "oth", "judged RACE in CO under another report key",
                    f"{how}; record {races[0].get('space')}/{races[0].get('race_type')}; kernel {info['name']}")
        if not recs and "rmw_pair_morally_strong" in sm.get(key, []):
            return (0, "cert", "R2 coherence (morally strong RMW pair)", f"{how}; skipped rmw_pair_morally_strong; kernel {info['name']}")
        if scs:
            return (2, "oth", "judged SC (strong conflict), not a Race",
                    f"{how}; class {scs[0].get('hb_class')}, conflict_class {scs[0].get('conflict_class')}, strength {scs[0].get('strength')}; kernel {info['name']}")
        return (2, "oth", "cross-thread edge/chain, no verdict record", f"{how}; skipped {sorted(set(map(str, sm.get(key, []))))}; kernel {info['name']}")
    if direct or ch:
        return (3, "cand", "edge/read-chain exists only at thread-local distance",
                f"pcs {hex(a)},{hex(c)} both in CO graph; no cross-thread bound from an edge or a read chain (the last-accessor shadow kept the thread's own access){dnote}")
    anyp = minimax(info, a, c, False) or minimax(info, c, a, False)
    if anyp:
        bound, path = anyp
        nonread = [p for p in path[1:-1] if not is_read(info, p)]
        return (4, "cand", "reachable only through a non-read hop",
                f"pcs {hex(a)},{hex(c)} both in CO graph; nearest chain {path_str(info, path)} bound {LVL.get(bound, bound)}; non-read hop(s) {','.join(hex(p) for p in nonread)}{dnote}")
    if dfa:
        return (5, "lane", "dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end)",
                "unreachable in the CO graph; " + ", ".join(f"pc {hex(p)}: expected {e} words, observed {o} (deficit {e - o})" for p, (e, o) in dfa.items()))
    if a == 0 or c == 0:
        return (6, "lane", "pc 0 previous accessor", f"unreachable; pair pc {hex(a if a == 0 else c)} is offset 0")
    if info["deficit"]:
        return (7, "oth", "dropped-word deficit only at another pc of the kernel",
                f"unreachable; deficits at {','.join(hex(p) for p in sorted(info['deficit'])[:8])}")
    shared = "SHARED" in ((nodes[a].get("flags") or "") + (nodes[c].get("flags") or ""))
    if shared and (info["grid"] is None or info["grid"] > POOL_CAP):
        return (8, "oth", "shared-pool exhaustion not excluded", f"unreachable; shared pair, grid {info['grid']} CTAs > {POOL_CAP}")
    return (9, "oth", "no gap evidence",
            f"unreachable; a out-hops {len(h.get(a, {}))}, c in-hops {sum(1 for s in h.values() if c in s)}, no deficit, no pc 0, not a shared pool > cap")


def classify_program(args):
    pid, co_r3, pairs = args
    kjs = sorted(glob.glob(f"{STORE}/{pid}/collector-only/kernel_*.json"))
    dots = sorted(glob.glob(f"{STORE}/{pid}/dots/*.dot"))
    best = {p: None for p in pairs}
    seen_a = collections.Counter()
    tallies = {p: collections.Counter() for p in pairs}
    for kj in kjs:
        try:
            info = load_kj(kj)
        except Exception:      # noqa: BLE001
            continue
        dcache = {}
        for p in pairs:
            sp, a, c = p
            for x in (a, c):
                if x in info["nodes"]:
                    seen_a[(p, x)] += 1
            r = eval_pair(info, dots, dcache, kj, co_r3, sp, a, c)
            if r is None:
                continue
            tallies[p][r[2]] += 1
            if best[p] is None or r[0] < best[p][0]:
                best[p] = r + (os.path.basename(kj),)
    out = {}
    for p in pairs:
        if best[p] is None:
            sp, a, c = p
            ina = sum(v for (q, x), v in seen_a.items() if q == p and x == a)
            inc = sum(v for (q, x), v in seen_a.items() if q == p and x == c)
            out[p] = ("cand", "pc not in the CO graph of any kernel with the other pc",
                      f"pc {hex(a)} in {ina} and pc {hex(c)} in {inc} of {len(kjs)} kernels; never both in one kernel", "")
        else:
            rk, cls, sub, det, kn = best[p]
            tl = "; ".join(f"{k} x{v}" for k, v in tallies[p].most_common(4))
            out[p] = (cls, sub, det, f"{kn}; kernel tally: {tl}")
    return pid, out


# ------------------------------------------------------------------ main
def main():
    os.makedirs(O, exist_ok=True)
    ids = [i for i, r in man.items() if r["pset"] in SUITE]
    sc_runs, _ = mt.load_runs(paths=[SC_CSV])
    sc_rows = read_rows([SC_CSV], "scalar-clock")
    sc_pairs, sc_trunc = {}, {}
    for i in ids:
        s, n = pair_union(sc_rows.get(i, []))
        sc_pairs[i] = s
        sc_trunc[i] = n > len(s)
    sc_v = {i: rv(sc_runs, i, "scalar-clock") for i in ids}
    res = {"ids": ids, "sc_v": sc_v}
    act = [os.environ["S3_SET"]] if os.environ.get("S3_SET") else list(SETS)
    if os.environ.get("S3_FINAL"):
        import pickle
        for st in SETS:
            res[st] = pickle.load(open(f"{O}/.state-{st}.pkl", "rb"))
        write_summary(res, sc_pairs, sc_v, ids)
        return
    for st, r3 in SETS.items():
        if st not in act:
            continue
        d = f"{O}/merged-{st}"
        os.makedirs(d, exist_ok=True)
        shards = sorted(glob.glob(f"{O}/run-{st}/baselines-cuvein-shard*_16.csv"))
        rows, fields = [], None
        for p in shards:
            rd = csv.DictReader(open(p, newline=""))
            fields = rd.fieldnames
            rows += list(rd)
        ovf = f"{O}/run-{st}/ov/baselines-cuvein-shardovall.csv"      # ids recorded in a long / 24 h pass: their rows replace the base rows
        ovrows = list(csv.DictReader(open(ovf, newline=""))) if os.path.exists(ovf) else []
        ovids = {r["id"] for r in ovrows}
        rows = [r for r in rows if r["id"] not in ovids] + ovrows
        print(st, "override ids", len(ovids), flush=True)
        with open(f"{d}/baselines-cuvein.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        co_runs, _ = mt.load_runs(paths=[f"{d}/baselines-cuvein.csv"])
        co_rows = read_rows([f"{d}/baselines-cuvein.csv"], "collector-only")
        co_v = {i: rv(co_runs, i, "collector-only") for i in ids}
        co_pairs = {i: pair_union(co_rows.get(i, []))[0] for i in ids}
        res[st] = dict(shards=len(shards), rows=len(rows), co_v=co_v, co_pairs=co_pairs, co_rows=co_rows,
                       co_note={i: ";".join(sorted({r["notes"] for r in co_rows.get(i, []) if r["verdict"] in ("ERROR", "TIMEOUT")}))[:200]
                                for i in ids})
        print(st, "shards", len(shards), "rows", len(rows), flush=True)
    # ---- pair classification: sc=Race programs, pairs sc has and CO lacks
    summary = {}
    for st, r3 in SETS.items():
        if st not in act:
            continue
        R = res[st]
        jobs = []
        for i in ids:
            if sc_v[i] != "RACE":
                continue
            miss = sorted(p for p in sc_pairs[i] if p not in R["co_pairs"][i])
            if miss:
                jobs.append((i, r3, miss))
        jobs.sort(key=lambda j: -len(glob.glob(f"{STORE}/{j[0]}/collector-only/kernel_*.json")))
        with Pool(16) as pool:
            cls = dict(pool.imap_unordered(classify_program, jobs, chunksize=1))
        R["cls"] = cls
        print(st, "classified programs", len(cls), flush=True)
        write_set(st, R, sc_pairs, sc_trunc, sc_v, ids, cls)
        import pickle
        keep = {k: v for k, v in res[st].items() if k not in ("co_rows", "co_pairs", "cls")}
        pickle.dump(keep, open(f"{O}/.state-{st}.pkl", "wb"))
        json.dump(keep["co_v"], open(f"{O}/co_verdicts_{st}.json", "w"))
    if len(act) == len(SETS):
        for st in SETS:
            res[st] = pickle.load(open(f"{O}/.state-{st}.pkl", "rb"))
        write_summary(res, sc_pairs, sc_v, ids)


CAUSE_PRI = ["certificate granted", "candidate missing", "other"]


def prog_cause(pair_cls):
    """pair_cls: list of class names of the program's missing sc pairs -> (primary, composition)"""
    c = collections.Counter(pair_cls)
    comp = ", ".join(f"{k} {v}" for k, v in c.most_common())
    for k in CAUSE_PRI:
        if c.get(k):
            return k, comp
    return ("collector lane drop" if c.get("collector lane drop") else "other"), comp


def write_set(st, R, sc_pairs, sc_trunc, sc_v, ids, cls):
    co_v, co_pairs, cl = R["co_v"], R["co_pairs"], R["cls"]
    R.setdefault("vio_cause", {})
    vio, byprog = [], []
    for i in ids:
        if sc_v[i] != "RACE":
            continue
        sp = sc_pairs[i]
        found = [p for p in sp if p in co_pairs[i]]
        miss = sorted(p for p in sp if p not in co_pairs[i])
        pc = collections.Counter(CLS[cl[i][p][0]] for p in miss) if miss else collections.Counter()
        subs = collections.Counter(cl[i][p][1] for p in miss) if miss else collections.Counter()
        byprog.append([i, man[i]["pset"], sc_v[i], co_v[i], len(sp), len(found), len(miss), pc["certificate granted"],
                       pc["candidate missing"], pc["collector lane drop"], pc["other"], int(sc_trunc[i]),
                       "; ".join(f"{k} x{v}" for k, v in subs.most_common())])
        if co_v[i] != "RACE":
            vio.append(i)
    with open(f"{O}/pairs_{st}_by_program.tsv", "w") as f:
        f.write("\t".join(["id", "suite", "sc_verdict", "co_verdict", "sc_pairs", "found_in_co", "missing", "certificate_granted",
                           "candidate_missing", "lane_drop", "other", "sc_report_ids_truncated", "subcauses"]) + "\n")
        for r in byprog:
            f.write("\t".join(map(str, r)) + "\n")
    tot = collections.defaultdict(lambda: collections.Counter())
    for r in byprog:
        for key in (r[1], "ALL"):
            t = tot[key]
            t["programs"] += 1
            t["programs_co_race"] += r[3] == "RACE"
            for n, v in zip(["sc_pairs", "found", "missing", "cert", "cand", "lane", "other"], r[4:11]):
                t[n] += v
    with open(f"{O}/pairs_{st}.tsv", "w") as f:
        f.write("\t".join(["suite", "programs_sc_race", "programs_co_race", "sc_pairs", "found_in_co", "missing", "certificate_granted",
                           "candidate_missing", "collector_lane_drop", "other"]) + "\n")
        for key in sorted(k for k in tot if k != "ALL") + ["ALL"]:
            t = tot[key]
            f.write("\t".join(map(str, [SUITE.get(key, key), t["programs"], t["programs_co_race"], t["sc_pairs"], t["found"], t["missing"],
                                       t["cert"], t["cand"], t["lane"], t["other"]])) + "\n")
    R["pairs_tot"] = {k: dict(v) for k, v in tot.items()}
    prog_rows, pair_rows = [], []
    for i in vio:
        sp = sc_pairs[i]
        miss = sorted(sp)
        pcl = [CLS[cl[i][p][0]] for p in miss if p in cl.get(i, {})]
        if co_v[i] in ("ERROR", "TIMEOUT", "NONE"):
            prim, comp = "other", f"CO verdict {co_v[i]}: {R['co_note'][i]}"
        elif not sp:
            prim, comp = "other", "sc Race with no parseable report_ids" + (" (truncated)" if sc_trunc[i] else "")
        else:
            prim, comp = prog_cause(pcl)
        R.setdefault("vio_cause", {})[i] = (prim, comp)
        first = [f"{sp_[0]}:{hex(sp_[1])}-{hex(sp_[2])}={CLS[cl[i][sp_][0]]} [{cl[i][sp_][1]}]" for sp_ in miss[:3] if sp_ in cl.get(i, {})]
        prog_rows.append([i, man[i]["pset"], sc_v[i], co_v[i], " ".join(f"{s}:{hex(a)}-{hex(b)}:{t}" for (s, a, b), t in sorted(sp.items())),
                          prim, comp, "; ".join(first), int(sc_trunc[i])])
        for p in miss:
            if p in cl.get(i, {}):
                c_, sub, det, ker = cl[i][p]
                pair_rows.append([i, man[i]["pset"], f"{p[0]}:{hex(p[1])}-{hex(p[2])}:{sp[p]}", CLS[c_], sub, det, ker])
    with open(f"{O}/violations_program_{st}.tsv", "w") as f:
        f.write("\t".join(["id", "suite", "sc_verdict", "co_verdict", "sc_report_ids", "cause", "cause_composition (pairs)", "first_pairs",
                           "sc_report_ids_truncated"]) + "\n")
        for r in sorted(prog_rows, key=lambda r: (r[5], r[0])):
            f.write("\t".join(map(str, r)) + "\n")
    with open(f"{O}/violations_pairs_{st}.tsv", "w") as f:
        f.write("\t".join(["id", "suite", "sc_pair", "cause_class", "sub_cause", "evidence", "kernel / tally"]) + "\n")
        for r in sorted(pair_rows):
            f.write("\t".join(map(str, r)) + "\n")
    R["vio"] = vio


def write_summary(res, sc_pairs, sc_v, ids):
    L = []
    P = L.append
    suites = sorted({man[i]["pset"] for i in ids})
    groups = [(SUITE[s], [s]) for s in suites]
    groups.append(("HeCBench (P7+P9)", ["P7", "P9"]))
    groups.append(("ALL", suites))
    P("# C6b step 3: collector-only verdict layer on the hb-stripped scalar-clock recordings of final-b\n")
    P("Counts are programs of the manifest (`eval/baselines/manifest.csv`, psets P1 P3 P4 P5 P6 P7 P9 PI). Verdicts: Race alone "
      "(`make_tables.race_alone_verdict`, union of reps). Violation = scalar-clock Race and collector-only not Race. "
      "Reverse = collector-only Race and scalar-clock not Race.\n")
    cnt = collections.Counter(sc_v.values())
    P(f"scalar-clock verdicts over {len(ids)} programs: " + ", ".join(f"{k} {v}" for k, v in sorted(cnt.items())) + "\n")
    for st, r3 in SETS.items():
        R = res[st]
        co_v = R["co_v"]
        P(f"\n## Setting {st} (`--chain-closure --co-async --co-r3 {r3}`)\n")
        P(f"{R['shards']} shard CSVs, {R['rows']} rows. collector-only verdicts: " +
          ", ".join(f"{k} {v}" for k, v in sorted(collections.Counter(co_v.values()).items())) + "\n")
        P("| suite | programs | sc=Race | co=Race | both Race | violations | candidate missing | certificate granted | collector lane drop | other | reverse (co Race, sc not) | of which sc CLEAN |")
        P("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for gname, ps in groups:
            g = [i for i in ids if man[i]["pset"] in ps]
            scr = [i for i in g if sc_v[i] == "RACE"]
            cor = [i for i in g if co_v[i] == "RACE"]
            both = [i for i in scr if co_v[i] == "RACE"]
            vio = [i for i in scr if co_v[i] != "RACE"]
            vc = collections.Counter(R["vio_cause"][i][0] for i in vio)
            rev = [i for i in cor if sc_v[i] != "RACE"]
            P(f"| {gname} | {len(g)} | {len(scr)} | {len(cor)} | {len(both)} | {len(vio)} | {vc['candidate missing']} | "
              f"{vc['certificate granted']} | {vc['collector lane drop']} | {vc['other']} | {len(rev)} | {sum(sc_v[i] == 'CLEAN' for i in rev)} |")
        P("\nCause per violation program: certificate granted > candidate missing > other if any pair is of that class; lane drop only if "
          "every missing pair is a lane drop (so lane drop is the sole explanation).\n")
        t = R["pairs_tot"]
        P("Pairs (information only): sc pairs found in co / missing, by cause class of the missing ones (all sc=Race programs):\n")
        P("| suite | programs | sc pairs | found in co | missing | certificate granted | candidate missing | lane drop | other |")
        P("|---|---|---|---|---|---|---|---|---|")
        for k in sorted(x for x in t if x != "ALL") + ["ALL"]:
            v = t[k]
            P(f"| {SUITE.get(k, k)} | {v['programs']} | {v['sc_pairs']} | {v['found']} | {v['missing']} | {v['cert']} | {v['cand']} | {v['lane']} | {v['other']} |")
        P("")
    open(f"{O}/step3_summary.md", "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()

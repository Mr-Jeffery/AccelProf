#!/usr/bin/env python3
"""C6b step 2: merge the s1/s2 re-analysis shards as C1 merged theirs (parallel.py merge --override c1-long,c1-24h), compare per
(id, mode, rep) with the C1 reference (A5 collector-only rows) and with C6's merged CSV; check the parity rule.
  c6b_merge_compare.py <wt> {s1|s2}
Per program counts: derived, rescued (notes chain_*), async, atomic_chain_off (number of raw/raw_sc report records of the
program's confirm JSON whose "async" / "atomic_chain_off" is true).
Parity rule: a program whose derived, rescued, async and atomic_chain_off are all 0 must equal C1 on verdict, reports_dedup,
report_ids, report_lines and the classes= note. Also checks every row's anode= against the lscpu records (cpu-*.txt)."""
import csv, collections, glob, json, os, re, statistics, subprocess, sys
W, which = sys.argv[1], sys.argv[2]
R = f"{W}/eval/results/co-chain-b"
PY = "/home/fzheng4/AccelProf/.env/bin/python"
FIELDS = ("verdict", "reports_dedup", "report_ids", "report_lines")
C6 = "/home/fzheng4/wt-c6/eval/results/co-chain/merged/baselines-cuvein.csv"
REF = f"{W}/eval/results/verdict-timing/collector-only-merged/baselines-cuvein.csv"


def tok(notes, name):
    m = re.search(r"(?:^|;)" + name + r"=([^;]*)", notes)
    return m.group(1) if m else None


def cls(n):
    return tok(n, "classes") or ""


def key(r):
    return (r["id"], r["mode"], r["rep"])


def table(rows):
    d = {}
    for r in rows:
        if key(r) in d:
            print("DUPLICATE KEY", key(r), file=sys.stderr)
        d[key(r)] = r
    return d


res, ovs, out = f"{R}/{which}/c1-main", [f"{R}/{which}/c1-long", f"{R}/{which}/c1-24h"], f"{R}/merged-{which}"
jdirs = [res] + ovs
ref_rows = list(csv.DictReader(open(REF, newline="")))
c6_rows = list(csv.DictReader(open(C6, newline="")))
os.makedirs(out, exist_ok=True)
subprocess.run([PY, f"{W}/eval/baselines/parallel.py", "merge", "--tool", "cuvein", "--results-dir", res, "--out-dir", out,
                "--override", ",".join(ovs)], check=True)
new = list(csv.DictReader(open(f"{out}/baselines-cuvein.csv", newline="")))
N, O, C = table(new), table(ref_rows), table(c6_rows)

prog = {}
for r in new:
    p = prog.setdefault(r["id"], dict(pset=r["pset"], analysed=False, derived=0, rescued=0, hops=0, chain_s=0.0,
                                      analysis_s=0.0, maxk=0, chaincap=False, asyn=0, acoff=0))
    n = r["notes"]
    if tok(n, "chain_derived") is not None and not p["analysed"]:
        p.update(analysed=True, derived=int(tok(n, "chain_derived")), rescued=int(tok(n, "chain_rescued")),
                 hops=int(tok(n, "chain_hops")), chain_s=float(tok(n, "chain_s")), maxk=int(tok(n, "chain_maxk")),
                 analysis_s=float(tok(n, "analysis_s") or 0))
    if r["verdict"] == "ERROR" and "chain-cap" in n:
        p["chaincap"] = True
# async / atomic_chain_off from the confirm JSONs (rep-1 detail of each analysed program)
nconf = 0
for jd in jdirs:
    for f in glob.glob(f"{jd}/confirm/*.json"):
        j = json.load(open(f))
        i = j["id"]
        if i not in prog:
            continue
        nconf += 1
        for rec in list(j.get("raw", [])) + list(j.get("raw_sc", [])):
            if rec.get("async") is True:
                prog[i]["asyn"] += 1
            if rec.get("atomic_chain_off") is True:
                prog[i]["acoff"] += 1
# jsonl cross-check
jl = collections.defaultdict(lambda: [0, 0])
capped = []
for jd in jdirs:
    for f in sorted(glob.glob(f"{jd}/chain-kernels-*.jsonl")):
        for ln in open(f):
            if not ln.strip():
                continue
            j = json.loads(ln)
            if j.get("capped") and "error" in j:
                capped.append(j)
                continue
            jl[j["id"]][0] += j.get("derived", 0)
            jl[j["id"]][1] += j.get("rescued", 0)
jmis = [(i, p["derived"], p["rescued"], jl[i]) for i, p in prog.items()
        if p["analysed"] and (jl[i][0] != p["derived"] or jl[i][1] != p["rescued"])]


def diff(N, O):
    ds = []
    for k in sorted(set(N) | set(O)):
        if k not in N:
            ds.append((k, "missing-in-new", "", ""))
            continue
        if k not in O:
            ds.append((k, "missing-in-ref", "", ""))
            continue
        for f in FIELDS:
            if N[k][f] != O[k][f]:
                ds.append((k, f, O[k][f][:120], N[k][f][:120]))
        if cls(N[k]["notes"]) != cls(O[k]["notes"]):
            ds.append((k, "classes", cls(O[k]["notes"]), cls(N[k]["notes"])))
    return ds


diffs = diff(N, O)
with open(f"{out}/parity_diffs.tsv", "w") as fh:
    for d in diffs:
        fh.write("\t".join(map(str, (*d[0], *d[1:]))) + "\n")
changed = {d[0][0] for d in diffs}
zero = {i for i, p in prog.items() if p["derived"] == 0 and p["rescued"] == 0 and p["asyn"] == 0 and p["acoff"] == 0}
unres = {k[0] for k, r in N.items() if r["verdict"] == "ERROR" and "analysis-timeout" in r["notes"]
         and k in O and O[k]["verdict"] != "ERROR"}
noref = {k[0] for k, r in N.items() if k in O and O[k]["verdict"] == "ERROR" and r["verdict"] != "ERROR"}
violations = sorted(d for d in diffs if d[0][0] in zero and d[0][0] not in unres and d[0][0] not in noref)
L = []


def P(s=""):
    L.append(s)
    print(s)


def tags(i):
    p = prog[i]
    return [t for t, v in (("derived", p["derived"]), ("rescued", p["rescued"]), ("async", p["asyn"]),
                           ("atomic_chain_off", p["acoff"])) if v > 0]


def vchanges(REFT):
    vp = collections.defaultdict(set)
    for k in N:
        if k in REFT and N[k]["verdict"] != REFT[k]["verdict"]:
            vp[(prog[k[0]]["pset"], REFT[k]["verdict"], N[k]["verdict"])].add(k[0])
    return vp


v1, v6 = vchanges(O), vchanges(C)
P(f"{which}: ref rows {len(O)}, new rows {len(N)}, ids ref {len({k[0] for k in O})} new {len({k[0] for k in N})}; C6 rows {len(C)}")
P(f"{which}: confirm JSONs read {nconf}")
P(f"{which}: field differences vs C1 {len(diffs)} over {len(changed)} programs")
P(f"{which}: programs analysed {sum(p['analysed'] for p in prog.values())} of {len(prog)}; all four counts 0 (incl. not analysed): {len(zero)}; "
  f"derived>0 {sum(p['derived'] > 0 for p in prog.values())}; rescued>0 {sum(p['rescued'] > 0 for p in prog.values())}; "
  f"async>0 {sum(p['asyn'] > 0 for p in prog.values())}; atomic_chain_off>0 {sum(p['acoff'] > 0 for p in prog.values())}")
P(f"{which}: PARITY VIOLATIONS (all-four-counts-0 program differing from C1): {len({d[0][0] for d in violations})} programs, {len(violations)} fields")
for d in violations[:60]:
    P(f"  {d}")
P(f"{which}: REFERENCE HAS NO VERDICT (ref ERROR, new verdict), excluded: " + str(sorted(noref)))
P(f"{which}: unresolved (new analysis-timeout, reference has verdict), excluded: {sorted(unres)}")
P(f"{which}: notes-vs-jsonl mismatches: {len(jmis)}")
for m in jmis[:20]:
    P(f"  {m}")
errs = [r for r in new if r["verdict"] == "ERROR"]
P(f"{which}: ERROR rows: {len(errs)} ({len({r['id'] for r in errs})} programs); chain-cap ERROR rows: {sum(p['chaincap'] for p in prog.values())}; jsonl cap lines {len(capped)}")
for r in errs[:40]:
    P(f"  ERROR {r['id']} {r['mode']} {r['rep']} {r['notes'][:150]}")
for name, vp in (("C1", v1), ("C6", v6)):
    P(f"{which}: verdict changes vs {name}: programs per (suite, {name} verdict -> new verdict) with tag counts")
    for k, v in sorted(vp.items()):
        tc = collections.Counter(t for i in v for t in tags(i))
        P(f"  {k[0]}\t{k[1]}->{k[2]}\tprograms={len(v)}\t" + " ".join(f"{t}={tc.get(t, 0)}" for t in ("derived", "rescued", "async", "atomic_chain_off"))
          + f"\tno_tag={sum(1 for i in v if not tags(i))}")
    for k, v in sorted(vp.items()):
        for i in sorted(v):
            P(f"    {name} change {k[1]}->{k[2]}\t{i}\t{','.join(tags(i))}")
# anode verification against the lscpu records
cpu = {}
for f in glob.glob(f"{R}/{which}/*/cpu-*.txt"):
    d = dict(ln.rstrip("\n").split("=", 1) for ln in open(f) if "=" in ln)
    cpu.setdefault(d["host"], set()).add(d["model"])
ok_hosts = {h for h, ms in cpu.items() if all("Xeon" in m and "Silver 4110" in m for m in ms)}
P(f"{which}: lscpu records (host -> model): " + str({h: sorted(ms) for h, ms in sorted(cpu.items())}))
rows_per_host = collections.Counter(tok(r["notes"], "anode") for r in new)
P(f"{which}: rows per anode: {dict(rows_per_host)}")
bad = [r for r in new if tok(r["notes"], "anode") not in ok_hosts]
P(f"{which}: rows whose anode is not a verified Xeon Silver 4110 host: {len(bad)}")
for r in bad[:30]:
    P(f"  {key(r)} anode={tok(r['notes'], 'anode')} verdict={r['verdict']}")
# suite stats
hdr = ["suite", "programs", "analysed", "derived>0", "rescued>0", "async>0", "atomic_chain_off>0", "verdict_changed_vs_C1", "verdict_changed_vs_C6",
       "analysis_s_median", "analysis_s_max", "analysis_s_sum", "chain_s_sum", "chain_share_median", "chain_share_sum_ratio"]
rows = []
for ps in sorted({p["pset"] for p in prog.values()}):
    ids = [i for i, p in prog.items() if p["pset"] == ps]
    an = [prog[i] for i in ids if prog[i]["analysed"]]
    asx = [p["analysis_s"] for p in an]
    share = [p["chain_s"] / p["analysis_s"] for p in an if p["analysis_s"] > 0]
    sa, sc = sum(asx), sum(p["chain_s"] for p in an)
    rows.append([ps, len(ids), len(an), sum(prog[i]["derived"] > 0 for i in ids), sum(prog[i]["rescued"] > 0 for i in ids),
                 sum(prog[i]["asyn"] > 0 for i in ids), sum(prog[i]["acoff"] > 0 for i in ids),
                 len({i for (s, a, b), v in v1.items() if s == ps for i in v}), len({i for (s, a, b), v in v6.items() if s == ps for i in v}),
                 f"{statistics.median(asx):.3f}" if asx else "", f"{max(asx):.3f}" if asx else "", f"{sa:.1f}", f"{sc:.1f}",
                 f"{statistics.median(share):.4f}" if share else "", f"{sc / sa:.4f}" if sa else ""])
with open(f"{out}/suite_stats.tsv", "w") as fh:
    fh.write("\t".join(hdr) + "\n")
    for r in rows:
        fh.write("\t".join(map(str, r)) + "\n")
P("\t".join(hdr))
for r in rows:
    P("\t".join(map(str, r)))
tot = sum(p["analysis_s"] for p in prog.values() if p["analysed"])
P(f"{which}: sum of analysis_s over analysed programs: {tot:.1f} s = {tot / 3600:.3f} h")
with open(f"{out}/derived_programs.tsv", "w") as fh:
    fh.write("id\tpset\tderived\trescued\tasync\tatomic_chain_off\thops\tmaxk\tchain_s\tanalysis_s\n")
    for i, p in sorted(prog.items()):
        if p["derived"] or p["rescued"] or p["asyn"] or p["acoff"]:
            fh.write(f"{i}\t{p['pset']}\t{p['derived']}\t{p['rescued']}\t{p['asyn']}\t{p['acoff']}\t{p['hops']}\t{p['maxk']}\t{p['chain_s']:.3f}\t{p['analysis_s']:.3f}\n")
P("differences vs C1 (id, mode, rep, field, ref, new), first 80:")
for d in diffs[:80]:
    P(f"  {d}")
open(f"{out}/parity_report.txt", "w").write("\n".join(L) + "\n")

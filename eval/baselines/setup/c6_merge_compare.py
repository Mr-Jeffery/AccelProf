#!/usr/bin/env python3
"""C6 step 2: merge the chain-closure re-analysis shards as C1 / C2 merged theirs (parallel.py merge, as
x7a_a5_compare.py), compare per (id, mode, rep) with the reference and check the parity rule.
  c6_merge_compare.py <wt> {c1|c2recall|c2cand}
c1:       eval/results/co-chain/c1-main with --override c1-long, c1-24h -> eval/results/co-chain/merged/baselines-cuvein.csv;
          reference eval/results/verdict-timing/collector-only-merged/baselines-cuvein.csv (A5; 14,141 rows)
c2recall: eval/results/co-chain/c2-recall -> merged-c2-recall/; reference = ref-c2/recall (C2's per-id CSVs; where an
          rean-<id> CSV exists it replaces the id's first-pass rows, as C2's scoring did)
c2cand:   likewise, c2-cand / ref-c2/cand.
Compared: verdict, reports_dedup, report_ids, report_lines, the classes= note.
Parity rule: a program whose chain_derived and chain_rescued are both 0 (notes of its analysed rows; the
chain-kernels jsonl is cross-checked) must equal the reference on all five. Rows without chain_* stats (not analysed:
TIMEOUT / empty-mode ERROR carried over, or ERROR) must equal the reference too. Programs with derived or rescued > 0
may differ; they are listed. Writes parity_diffs.tsv, parity_report.txt, suite_stats.tsv in the merged dir."""
import csv, collections, glob, json, os, re, statistics, subprocess, sys
W, which = sys.argv[1], sys.argv[2]
R = f"{W}/eval/results/co-chain"
PY = "/home/fzheng4/AccelProf/.env/bin/python"
FIELDS = ("verdict", "reports_dedup", "report_ids", "report_lines")


def tok(notes, name):
    m = re.search(r"(?:^|;)" + name + r"=([^;]*)", notes)
    return m.group(1) if m else None


def cls(n):
    return tok(n, "classes") or ""


def key(r):
    return (r["id"], r["mode"], r["rep"])


if which == "c1":
    res, ovs, out = f"{R}/c1-main", [f"{R}/c1-long", f"{R}/c1-24h"], f"{R}/merged"
    ref_rows = list(csv.DictReader(open(f"{W}/eval/results/verdict-timing/collector-only-merged/baselines-cuvein.csv", newline="")))
    jdirs = [f"{R}/c1-main", f"{R}/c1-long", f"{R}/c1-24h"]
else:
    sub, tag = ("recall", "c2-recall") if which == "c2recall" else ("cand", "c2-cand")
    res, ovs, out = f"{R}/{tag}", [], f"{R}/merged-{tag}"
    jdirs = [res]
    d = f"{R}/ref-c2/{sub}"
    ref_rows = []
    for f in sorted(glob.glob(f"{d}/baselines-cuvein-shard*-all.csv")):
        b = os.path.basename(f)
        if b.startswith("baselines-cuvein-shardrean-"):
            continue
        idn = b[len("baselines-cuvein-shard"):-len("-all.csv")]
        rean = f"{d}/baselines-cuvein-shardrean-{idn}-all.csv"
        ref_rows += list(csv.DictReader(open(rean if os.path.exists(rean) else f, newline="")))
os.makedirs(out, exist_ok=True)
cmd = [PY, f"{W}/eval/baselines/parallel.py", "merge", "--tool", "cuvein", "--results-dir", res, "--out-dir", out]
if ovs:
    cmd += ["--override", ",".join(ovs)]
subprocess.run(cmd, check=True)
new = list(csv.DictReader(open(f"{out}/baselines-cuvein.csv", newline="")))
if which != "c1":   # restrict to the reference's ids (the candidate manifest also lists 4 ids that were not run)
    ids = {r["id"] for r in ref_rows}
    new = [r for r in new if r["id"] in ids]


def table(rows):
    d = {}
    for r in rows:
        if key(r) in d:
            print("DUPLICATE KEY", key(r), file=sys.stderr)
        d[key(r)] = r
    return d


N, O = table(new), table(ref_rows)
# per-program chain stats from the notes (one analysis per mode shared by its reps: take the first row)
prog = {}
for r in new:
    i = r["id"]
    p = prog.setdefault(i, dict(pset=r["pset"], analysed=False, derived=0, rescued=0, hops=0, chain_s=0.0,
                                analysis_s=0.0, maxk=0, chaincap=False, kjsons=0))
    n = r["notes"]
    if tok(n, "chain_derived") is not None and not p["analysed"]:
        p.update(analysed=True, derived=int(tok(n, "chain_derived")), rescued=int(tok(n, "chain_rescued")),
                 hops=int(tok(n, "chain_hops")), chain_s=float(tok(n, "chain_s")), maxk=int(tok(n, "chain_maxk")),
                 analysis_s=float(tok(n, "analysis_s") or 0), kjsons=int(tok(n, "analysis_kjsons") or 0))
    if r["verdict"] == "ERROR" and "chain-cap" in n:
        p["chaincap"] = True
# cross-check the jsonl (per-kernel lines) against the notes
jl = collections.defaultdict(lambda: [0, 0, 0])
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
            a = jl[j["id"]]
            a[0] += j.get("derived", 0)
            a[1] += j.get("rescued", 0)
            a[2] += 1
jmis = [(i, p["derived"], p["rescued"], jl[i]) for i, p in prog.items()
        if p["analysed"] and (jl[i][0] != p["derived"] or jl[i][1] != p["rescued"])]
diffs = []
for k in sorted(set(N) | set(O)):
    if k not in N:
        diffs.append((k, "missing-in-new", "", ""))
        continue
    if k not in O:
        diffs.append((k, "missing-in-ref", "", ""))
        continue
    for f in FIELDS:
        if N[k][f] != O[k][f]:
            diffs.append((k, f, O[k][f][:120], N[k][f][:120]))
    if cls(N[k]["notes"]) != cls(O[k]["notes"]):
        diffs.append((k, "classes", cls(O[k]["notes"]), cls(N[k]["notes"])))
with open(f"{out}/parity_diffs.tsv", "w") as fh:
    for d in diffs:
        fh.write("\t".join(map(str, (*d[0], *d[1:]))) + "\n")
changed = {d[0][0] for d in diffs}
zero = {i for i, p in prog.items() if p["derived"] == 0 and p["rescued"] == 0}   # incl. rows without chain stats
# programs whose new analysis hit the timeout while the reference has a verdict: unresolved, not a parity failure
unres = {k[0] for k, r in N.items() if r["verdict"] == "ERROR" and "analysis-timeout" in r["notes"]
         and k in O and O[k]["verdict"] != "ERROR"}
# programs whose REFERENCE holds no verdict (ERROR, e.g. the reference analysis hit its timeout) while the new
# analysis produced one: nothing to compare against (A5's P9-atomicCAS case); listed, not counted as violations
noref = {k[0] for k, r in N.items() if k in O and O[k]["verdict"] == "ERROR" and r["verdict"] != "ERROR"}
violations = sorted(d for d in diffs if d[0][0] in zero and d[0][0] not in unres and d[0][0] not in noref)
L = []


def P(s=""):
    L.append(s)
    print(s)


P(f"{which}: ref rows {len(O)}, new rows {len(N)}, ids ref {len({k[0] for k in O})} new {len({k[0] for k in N})}")
P(f"{which}: field differences {len(diffs)} over {len(changed)} programs")
P(f"{which}: programs analysed (chain stats in notes) {sum(p['analysed'] for p in prog.values())} of {len(prog)}; "
  f"derived=0 and rescued=0 (or not analysed): {len(zero)}; derived>0: {sum(p['derived'] > 0 for p in prog.values())}; "
  f"rescued>0: {sum(p['rescued'] > 0 for p in prog.values())}")
P(f"{which}: PARITY VIOLATIONS (zero-derived/zero-rescued program differing from the reference): "
  f"{len({d[0][0] for d in violations})} programs, {len(violations)} fields")
for d in violations[:60]:
    P(f"  {d}")
P(f"{which}: REFERENCE HAS NO VERDICT (ref ERROR, new verdict), excluded from the violation count: "
  + str(sorted((i, 'derived=%d rescued=%d' % (prog[i]['derived'], prog[i]['rescued'])) for i in noref)))
P(f"{which}: unresolved (new analysis-timeout, reference has a verdict; excluded from the parity check): {sorted(unres)}")
P(f"{which}: notes-vs-jsonl mismatches: {len(jmis)}")
for m in jmis[:20]:
    P(f"  {m}")
P(f"{which}: ERROR chain-cap rows: {sum(p['chaincap'] for p in prog.values())}; jsonl cap lines {len(capped)}")
for c in capped:
    P(f"  {c}")
vch = collections.Counter()
for k in N:
    if k in O and N[k]["verdict"] != O[k]["verdict"]:
        vch[(prog[k[0]]["pset"], O[k]["verdict"], N[k]["verdict"])] += 1
P(f"{which}: verdict changes vs reference rows (suite, ref -> new): " + (str(dict(vch)) if vch else "none"))
vprog = collections.defaultdict(set)
for k in N:
    if k in O and N[k]["verdict"] != O[k]["verdict"]:
        vprog[(prog[k[0]]["pset"], O[k]["verdict"], N[k]["verdict"])].add(k[0])
P(f"{which}: verdict changes vs reference, programs with at least one changed row: " +
  (str({k: len(v) for k, v in sorted(vprog.items())}) if vprog else "none"))
for k, v in sorted(vprog.items()):
    for i in sorted(v):
        P(f"  verdict change {k[1]}->{k[2]}\t{i}")
rows = []
for ps in sorted({p["pset"] for p in prog.values()}):
    ids = [i for i, p in prog.items() if p["pset"] == ps]
    an = [prog[i] for i in ids if prog[i]["analysed"]]
    asx = [p["analysis_s"] for p in an]
    share = [p["chain_s"] / p["analysis_s"] for p in an if p["analysis_s"] > 0]
    sa, sc = sum(asx), sum(p["chain_s"] for p in an)
    rows.append([ps, len(ids), len(an), sum(prog[i]["derived"] > 0 for i in ids), sum(prog[i]["rescued"] > 0 for i in ids),
                 len({i for (s, a, b), v in vprog.items() if s == ps for i in v}),
                 f"{statistics.median(asx):.3f}" if asx else "", f"{max(asx):.3f}" if asx else "", f"{sa:.1f}", f"{sc:.1f}",
                 f"{statistics.median(share):.4f}" if share else "", f"{sc / sa:.4f}" if sa else ""])
hdr = ["suite", "programs", "analysed", "derived>0", "rescued>0", "verdict_changed_programs", "analysis_s_median", "analysis_s_max",
       "analysis_s_sum", "chain_s_sum", "chain_share_median", "chain_share_sum_ratio"]
with open(f"{out}/suite_stats.tsv", "w") as fh:
    fh.write("\t".join(hdr) + "\n")
    for r in rows:
        fh.write("\t".join(map(str, r)) + "\n")
P("\t".join(hdr))
for r in rows:
    P("\t".join(map(str, r)))
tot = sum(p["analysis_s"] for p in prog.values() if p["analysed"])
P(f"{which}: sum of analysis_s over analysed programs (one per (program, mode)): {tot:.1f} s = {tot / 3600:.3f} h")
with open(f"{out}/derived_programs.tsv", "w") as fh:     # programs with derived>0 or rescued>0
    fh.write("id\tpset\tderived\trescued\thops\tmaxk\tchain_s\tanalysis_s\n")
    for i, p in sorted(prog.items()):
        if p["derived"] > 0 or p["rescued"] > 0:
            fh.write(f"{i}\t{p['pset']}\t{p['derived']}\t{p['rescued']}\t{p['hops']}\t{p['maxk']}\t{p['chain_s']:.3f}\t{p['analysis_s']:.3f}\n")
P("differences (id, mode, rep, field, ref, new):")
for d in diffs[:80]:
    P(f"  {d}")
open(f"{out}/parity_report.txt", "w").write("\n".join(L) + "\n")

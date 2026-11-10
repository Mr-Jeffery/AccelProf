#!/usr/bin/env python3
"""X13 steps 1 and 2: inventory.csv (kernels per binary: in the cubin, launches per run id) and curace.csv (cuRace's
verdict per kernel, per mode), plus kernel_verdicts_curace.csv (long format for the table) and curace_checks.txt.
Reads eval/results/per-kernel/{ck,ck2,ck11}/*.csv (curace_kernels.py), cubin_kernels.csv, and the Table 4 runs (tinput)."""
import collections, csv, glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tinput, kfold
mt, runs, meta, man, p9 = tinput.load()
APH = tinput.APH
D = f"{APH}/eval/results/per-kernel"
VC, SC, CO = tinput.VC, tinput.SC, tinput.CO
MODES = [("vector-clock", VC), ("scalar-clock", SC), ("collector-only", CO)]
SHORT = {VC: "vector-clock", SC: "scalar-clock", CO: "collector-only"}
nk = lambda s: s.replace(" ", "")

def rows_of(pat, drop=()):
    for f in sorted(glob.glob(pat)):
        for r in csv.DictReader(open(f)):
            if r["id"] in drop:
                continue
            yield r

extra = set(open(f"{D}/missing_sc_extra.txt").read().split())      # last id of two timed-out first-pass files
src = {VC: list(rows_of(f"{D}/ck/vc-*.csv")),
       SC: list(rows_of(f"{D}/ck/sc-*.csv", extra)) + list(rows_of(f"{D}/ck2/sc*.csv")) + list(rows_of(f"{D}/ck3/sc-*.csv")),
       CO: list(rows_of(f"{D}/ck/co-*.csv")) + list(rows_of(f"{D}/ck2/co-*.csv"))}
# ck11b tasks 3 (expdist vector-clock: out of memory), 8, 17, 50, 83, 116 (tridiagonal, 8 h time limit) left no complete output:
# ignored here, the tridiagonal stores are redone in ck11t (32 kernel-JSON shards each).
_bad = {f"{D}/ck11b/t{n}.csv" for n in (3, 8, 17, 50, 83, 116)}
_x = [r for f in sorted(glob.glob(f"{D}/ck11b/t*.csv")) if f not in _bad for r in csv.DictReader(open(f))] + \
     list(rows_of(f"{D}/ck11t/t*.csv"))
x11 = {m: [r for r in _x if r["mode"] == sm] for sm, m in ((a, b) for a, b in (("vector-clock", VC), ("scalar-clock", SC), ("collector-only", CO)))}

def group(rows):
    """(id, store) -> {kernel_norm: dict(n_json, pairs:set, classes:set, kname)}; statuses"""
    g = collections.OrderedDict()
    for r in rows:
        key = (r["id"], r["store"])
        e = g.setdefault(key, dict(k={}, st=collections.Counter()))
        e["st"][r["status"].split(":")[0]] += 1
        if not r["kjson"]:
            continue
        kn = nk(r["kernel_name"]) or "UNNAMED"
        k = e["k"].setdefault(kn, dict(n=0, pairs=set(), classes=set(), kname=r["kernel_name"]))
        k["n"] += 1
        if r["pairs"]:
            k["pairs"] |= set(r["pairs"].split())
            k["classes"] |= set(r["classes"].split())
    return g

G = {m: group(src[m]) for m in src}
G11 = {m: group(x11[m]) for m in x11}
# cubin kernels
cub = collections.defaultdict(dict)       # exe -> {norm: demangled}
for r in csv.DictReader(open(f"{D}/cubin_kernels.csv")):
    if r["status"] == "ok" and r["is_entry"] == "1":
        cub[r["exe"]][nk(r["demangled"])] = r["demangled"]

# binaries
views = {v: set(mt.binary_view_ids(meta, v)) for v in ("P1", "PI", "PI@sc7", "P4", "P6@in", "P9")}
bin_ids = collections.defaultdict(list)
for i, m in man.items():
    if m["pset"] in ("P1", "PI", "P4", "P6", "P9") and m.get("exe"):
        bin_ids[m["exe"]].append(i)
checks = []
conflicts = []
inv_rows, cur_rows, kv_rows = [], [], []
unmatched = collections.Counter()

def run_entry(rid, mode, g_entry, verdict):
    launched = set(g_entry["k"]) if g_entry else set()
    reporting = {k for k, v in g_entry["k"].items() if v["pairs"]} if g_entry else set()
    return dict(id=rid, verdict=verdict, launched=launched, reporting=reporting, g=g_entry)

for exe, ids in sorted(bin_ids.items()):
    prog_p9 = None
    if man[ids[0]]["pset"] == "P9":
        prog_p9 = man[ids[0]]["program"][:-5]
        key_b = f"hecbench:{prog_p9}"
        exe_show = exe
    else:
        key_b = exe
    pset = man[ids[0]]["pset"]
    label = {man[i]["label"].upper() for i in ids}
    assert len(label) == 1, (exe, label)
    label = label.pop()
    vws = [v for v, s in views.items() if s & set(ids)]
    per_mode = {}
    for sm, m in MODES:
        rl = []
        if prog_p9:
            st = p9[(prog_p9, sm)]
            if m == CO:
                ents = [(k, e) for k, e in G11[m].items() if k[0] == f"X11-{prog_p9}"]
                for (rid, store), e in ents:
                    rl.append(run_entry(f"{store}/{rid}", m, e, "RACE" if any(v["pairs"] for v in e["k"].values()) else "CLEAN"))
            elif st["runs"].startswith("0"):
                rl.append(dict(id=f"X11-{prog_p9}-notrun", verdict="TIMEOUT", launched=set(), reporting=set(), g=None))
            elif "new:" in st["source_files"]:
                ents = [(k, e) for k, e in G11[m].items() if k[0] == f"X11-{prog_p9}"]
                for (rid, store), e in ents:
                    part = "partial" in store or e["st"].get("no-kernel-json")
                    anyr = any(v["pairs"] for v in e["k"].values())
                    rl.append(run_entry(f"{store}/{rid}", m, e, "RACE" if anyr else ("TIMEOUT" if "partial" in store else "CLEAN")))
                if not ents:      # recorded but no analysis output (expdist vector-clock: the verdict step ran out of memory, 108 GB)
                    rl.append(dict(id=f"X11-{prog_p9}-no-analysis", verdict={"TO": "TIMEOUT"}.get(st["new_verdict"], st["new_verdict"]), launched=set(), reporting=set(), g=None))
            else:
                for i in ids:
                    for (rid, store), e in G[m].items():
                        if rid == i:
                            rl.append(run_entry(i, m, e, runs.get((i, "cuvein", m), {}).get("verdict", "ERROR")))
        else:
            for i in ids:
                rv = runs.get((i, "cuvein", m))
                if not rv:
                    continue
                es = [(k, e) for k, e in G[m].items() if k[0] == i]
                e = es[-1][1] if es else None
                rl.append(run_entry(i, m, e, rv["verdict"]))
        per_mode[m] = rl
        # id-level consistency
        if not prog_p9:
            for r in rl:
                v = r["verdict"]
                if v in ("RACE",) and not r["reporting"]:
                    checks.append(("RACE-without-kernel-report", exe, SHORT[m], r["id"], ""))
                if v in ("CLEAN",) and r["reporting"]:
                    checks.append(("CLEAN-with-kernel-report", exe, SHORT[m], r["id"], ""))
                if r["g"] is None and v in ("RACE", "CLEAN"):
                    checks.append(("no-store-for-analysed-row", exe, SHORT[m], r["id"], ""))
                if r["g"] is not None:
                    pairs = collections.defaultdict(set)
                    for kk, kv in r["g"]["k"].items():
                        for p in kv["pairs"]:
                            pairs[p].add(kk)
                    for p, ks in pairs.items():
                        if len(ks) > 1:
                            conflicts.append((exe, SHORT[m], r["id"], p, ";".join(sorted(ks))))
                    nrep = runs[(r["id"], "cuvein", m)]["reports"]
                    if v in ("RACE", "CLEAN") and nrep != len(pairs):
                        checks.append(("report-count-differs", exe, SHORT[m], r["id"], f"csv={nrep} kernels={len(pairs)}"))
    # kernel universe
    univ = set()
    for m in per_mode:
        univ |= kfold.universe_of(per_mode[m])
    ccub = cub.get(exe, {})
    for kn in univ:
        if kn not in ccub and ccub:
            unmatched[(exe, kn)] += 1
    disp = lambda kn: ccub.get(kn) or next((v["kname"] for m in per_mode for r in per_mode[m] if r["g"] for k2, v in r["g"]["k"].items() if k2 == kn), kn)
    kernels_all = sorted(set(ccub) | univ)
    for kn in kernels_all:
        for sm, m in MODES:
            for r in per_mode[m]:
                n = r["g"]["k"][kn]["n"] if r["g"] and kn in r["g"]["k"] else 0
                inv_rows.append([key_b, disp(kn), int(kn in ccub), sm, r["id"], n])
    # per-mode kernel verdicts
    for sm, m in MODES:
        rl = per_mode[m]
        kvd = kfold.fold_kernels(rl, univ)
        # fold back
        if prog_p9:
            want = {"TO": "TIMEOUT"}.get(p9[(prog_p9, sm)]["new_verdict"], p9[(prog_p9, sm)]["new_verdict"])
        else:
            want = mt.fold_verdict([r["verdict"] for r in rl]) if rl else None
        back = kfold.fold_back(kvd)
        if want != back:
            checks.append(("fold-back-differs", key_b, sm, "", f"binary={want} from-kernels={back} kernels={dict(kvd)}"))
        for kn, v in kvd.items():
            pr = set(); cl = set(); nl = 0
            for r in rl:
                if r["g"] and kn in r["g"]["k"]:
                    pr |= r["g"]["k"][kn]["pairs"]; cl |= r["g"]["k"][kn]["classes"]; nl += 1
            cur_rows.append([key_b, pset, label, sm, disp(kn), v, len(pr), len(rl), nl, " ".join(sorted(pr))[:300], " ".join(sorted(cl))[:300]])
            kv_rows.append([key_b, ";".join(vws), label, disp(kn), "cuvein", m, v])

def w(path, hdr, rows):
    with open(path, "w", newline="") as f:
        cw = csv.writer(f); cw.writerow(hdr); cw.writerows(rows)
w(f"{D}/inventory.csv", ["binary", "kernel", "in_cubin", "mode", "run_id", "launches"], inv_rows)
w(f"{D}/curace.csv", ["binary", "pset", "binary_label", "mode", "kernel", "verdict", "report_pairs", "runs", "runs_launched", "pairs", "classes"], cur_rows)
w(f"{D}/kernel_verdicts_curace.csv", ["binary", "views", "binary_label", "kernel", "tool", "mode", "verdict"], kv_rows)
w(f"{D}/curace_conflicts.csv", ["binary", "mode", "run", "pair", "kernels"], conflicts)
with open(f"{D}/curace_checks.txt", "w") as f:
    c = collections.Counter(x[0] for x in checks)
    f.write(f"checks: {dict(c)}\nlaunched kernels not in the cubin entry list: {len(unmatched)}\n")
    for u in list(unmatched)[:40]:
        f.write(f"  unmatched {u}\n")
    f.write(f"pair in two kernels: {len(conflicts)}\n")
    for x in checks:
        f.write("\t".join(map(str, x)) + "\n")
print(open(f"{D}/curace_checks.txt").read()[:3000])

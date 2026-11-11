#!/usr/bin/env python3
"""M5: per-suite before/after tables and the line-3 check for a re-scored set.
  m5_report.py c1   : before = C6b's S2 re-analysis of the C1 store (wt-c6b/eval/results/co-chain-b/merged-s2, same recordings, rev 93ae2d66),
                      control = this branch's sw0 run (CUVEIN_CHAIN_ATOMIC_HOP=0, same node as sw1), after = sw1 (default).
  m5_report.py prod : before = sw0, after = sw1 (the production stores have no earlier S2 result).
Writes eval/results/closure-atomic-hop/summary/<set>.json and <set>_changed.tsv.  Unit definitions:
  reported = the program's CSV verdict is RACE in any rep; labelled = manifest label (RACE / CLEAN, the P9 overrides of c6b_tables);
  report pairs = sum over programs of reports_dedup (max over reps); derived / rescued = notes chain_derived / chain_rescued (rep with the stat);
  verdict-step time = sum of notes analysis_s; cap = chain-kernels jsonl lines with capped+error, plus ERROR rows naming chain-cap;
  changed = verdict, reports_dedup, report_ids, report_lines, classes= note or the set of raw/raw_sc records (without chain_src/chain_path) differs;
  new chain pairs = chain_derived + chain_rescued of the after run minus the before run."""
import collections, csv, glob, json, os, re, subprocess, sys
W = "/home/fzheng4/wt-m5"
PY = "/home/fzheng4/AccelProf/.env/bin/python"
R = f"{W}/eval/results/closure-atomic-hop"
OUT = f"{R}/summary"
LABEL_OVERRIDE = {"P9-knn-cuda": "CLEAN", "P9-atomicCAS-cuda": "CLEAN"}


def tok(notes, name):
    m = re.search(r"(?:^|;)" + name + r"=([^;]*)", notes)
    return m.group(1) if m else None


def manifest(path):
    return {r["id"]: r for r in csv.DictReader(open(path, newline=""))}


def merge(shard_dir, out, overrides):
    os.makedirs(out, exist_ok=True)
    cmd = [PY, f"{W}/eval/baselines/parallel.py", "merge", "--tool", "cuvein", "--results-dir", shard_dir, "--out-dir", out]
    if overrides:
        cmd += ["--override", ",".join(overrides)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    return f"{out}/baselines-cuvein.csv"


def load(csv_path, conf_dirs, jsonl_dirs):
    P = {}
    for r in csv.DictReader(open(csv_path, newline="")):
        if r["mode"] != "collector-only":
            continue
        p = P.setdefault(r["id"], dict(pset=r["pset"], verdict=set(), rd=0, ids=set(), lines=set(), classes=set(), derived=None, rescued=None,
                                       analysis_s=0.0, capped=False, hops=0, err=set(), rows=0))
        n = r["notes"]
        p["rows"] += 1
        p["verdict"].add(r["verdict"])
        if r["reports_dedup"].isdigit():
            p["rd"] = max(p["rd"], int(r["reports_dedup"]))
        p["ids"].add(r["report_ids"])
        p["lines"].add(r["report_lines"])
        p["classes"].add(tok(n, "classes") or "")
        if tok(n, "chain_derived") is not None and p["derived"] is None:
            p.update(derived=int(tok(n, "chain_derived")), rescued=int(tok(n, "chain_rescued")), hops=int(tok(n, "chain_hops") or 0),
                     analysis_s=float(tok(n, "analysis_s") or 0))
        if r["verdict"] == "ERROR":
            p["err"].add(n[:90])
            if "chain-cap" in n:
                p["capped"] = True
    for p in P.values():
        p["verdict"] = "RACE" if "RACE" in p["verdict"] else ("ERROR" if "ERROR" in p["verdict"] else "/".join(sorted(p["verdict"])))
        p["ids"], p["lines"], p["classes"] = sorted(p["ids"]), sorted(p["lines"]), sorted(p["classes"])
        p["derived"] = p["derived"] or 0
        p["rescued"] = p["rescued"] or 0
        p["raw"], p["raw_full"] = None, None
    ncap = 0
    for d in jsonl_dirs:
        for f in glob.glob(f"{d}/chain-kernels-*.jsonl"):
            for ln in open(f):
                if ln.strip():
                    j = json.loads(ln)
                    if j.get("capped") and "error" in j:
                        ncap += 1
    for d in conf_dirs:
        for f in glob.glob(f"{d}/*.json"):
            j = json.load(open(f))
            i = j["id"]
            if i not in P:
                continue
            recs = list(j.get("raw", [])) + [dict(x, _sc=1) for x in j.get("raw_sc", [])]
            P[i]["raw"] = frozenset(json.dumps({k: v for k, v in x.items() if k not in ("chain_src", "chain_path")}, sort_keys=True) for x in recs)
            P[i]["raw_full"] = frozenset(json.dumps(x, sort_keys=True) for x in recs)
    return P, ncap


def changed(a, b):
    d = [f for f in ("verdict", "rd", "ids", "lines", "classes") if a[f] != b[f]]
    if (a["raw"] or frozenset()) != (b["raw"] or frozenset()):
        d.append("raw")
    return d


def suite_stats(P, lab, ids, ncap=None):
    S = dict(programs=len(ids), analysed=sum(P[i]["derived"] is not None and P[i]["analysis_s"] > 0 for i in ids))
    rep = [i for i in ids if P[i]["verdict"] == "RACE"]
    S["reported"] = len(rep)
    racy = [i for i in ids if lab(i) == "RACE"]
    free = [i for i in ids if lab(i) == "CLEAN"]
    S["labelled_racy"], S["racy_detected"] = len(racy), sum(P[i]["verdict"] == "RACE" for i in racy)
    S["labelled_free"], S["free_reported"] = len(free), sorted(i for i in free if P[i]["verdict"] == "RACE")
    S["unlabelled_reported"] = sum(1 for i in rep if lab(i) not in ("RACE", "CLEAN"))
    S["report_pairs"] = sum(P[i]["rd"] for i in ids)
    S["derived"], S["rescued"] = sum(P[i]["derived"] for i in ids), sum(P[i]["rescued"] for i in ids)
    S["cap"] = sum(P[i]["capped"] for i in ids)
    S["analysis_s"] = round(sum(P[i]["analysis_s"] for i in ids), 1)
    S["errors"] = sorted(i for i in ids if P[i]["verdict"] == "ERROR")
    return S


def main():
    which = sys.argv[1]
    os.makedirs(OUT, exist_ok=True)
    if which == "c1":
        man = manifest(f"{W}/eval/baselines/manifest.csv")
        B0 = "/home/fzheng4/wt-c6b/eval/results/co-chain-b"
        sets = {}
        sets["before"] = load(f"{B0}/merged-s2/baselines-cuvein.csv", [f"{B0}/s2/{d}/confirm" for d in ("c1-main", "c1-long", "c1-24h")],
                              [f"{B0}/s2/{d}" for d in ("c1-main", "c1-long", "c1-24h")])
        for sw in ("0", "1"):
            d = f"{R}/c1/sw{sw}"
            c = merge(f"{d}/c1-main", f"{R}/c1/merged-sw{sw}", [f"{d}/c1-long", f"{d}/c1-24h"])
            sets["sw" + sw] = load(c, [f"{d}/{x}/confirm" for x in ("c1-main", "c1-long", "c1-24h")], [f"{d}/{x}" for x in ("c1-main", "c1-long", "c1-24h")])
        order = ["P1", "P3", "P4", "P5", "P6", "P7", "P9", "PI"]
        bf, af = "before", "sw1"
    else:
        man = manifest(f"{W}/eval/realworld/manifest_t21b.csv")
        man.update(manifest(f"{W}/eval/realworld/manifest_t21c.csv"))
        sets = {}
        for sw in ("0", "1"):
            d = f"{R}/prod/sw{sw}"
            P = {}
            nc = 0
            for tag in ("c2-recall", "c2-cand"):
                p, n = load(f"{d}/merged-{tag}/baselines-cuvein.csv", [f"{d}/{tag}/confirm"], [f"{d}/{tag}"])
                for i, v in p.items():
                    v["pset"] = "T21b" if tag == "c2-recall" else "T21c"
                P.update(p)
                nc += n
            sets["sw" + sw] = (P, nc)
        sets["before"] = sets["sw0"]
        order = ["T21b", "T21c"]
        bf, af = "before", "sw1"

    def lab(i):
        return LABEL_OVERRIDE.get(i, man.get(i, {}).get("label", ""))

    res = {"suites": {}, "changed": [], "violations": [], "chain_changed": []}
    names = [k for k in ("before", "sw0", "sw1") if k in sets]
    for s in order:
        res["suites"][s] = {}
        for k in names:
            P, nc = sets[k]
            ids = sorted(i for i, p in P.items() if p["pset"] == s)
            st = suite_stats(P, lab, ids)
            res["suites"][s][k] = st
        # cap: jsonl lines of the whole set (suite split by program id prefix is not recorded there): reported once per set
    res["cap_lines"] = {k: sets[k][1] for k in names}
    allids = sorted(set(sets[bf][0]) & set(sets[af][0]))
    for pair in ((bf, af), ("sw0", "sw1"), (bf, "sw0")):
        if pair[0] not in sets or pair[1] not in sets or pair[0] == pair[1]:
            continue
        A, B = sets[pair[0]][0], sets[pair[1]][0]
        ch, vio, newc, pathonly = [], [], 0, []
        for i in sorted(set(A) & set(B)):
            d = changed(A[i], B[i])
            dn = (B[i]["derived"] + B[i]["rescued"]) - (A[i]["derived"] + A[i]["rescued"])
            if dn:
                newc += 1
            if d:
                ch.append((i, A[i]["pset"], lab(i), A[i]["verdict"], B[i]["verdict"], ",".join(d), dn, A[i]["rd"], B[i]["rd"]))
                if dn == 0:
                    vio.append(i)
            elif (A[i]["raw_full"] or frozenset()) != (B[i]["raw_full"] or frozenset()):
                pathonly.append(i)
        key = f"{pair[0]}->{pair[1]}"
        res.setdefault("cmp", {})[key] = dict(programs_compared=len(set(A) & set(B)), changed=len(ch), programs_with_new_chain_pairs=newc,
                                              changed_with_zero_new_chain_pairs=vio, path_only_changes=len(pathonly),
                                              only_in_before=sorted(set(A) - set(B))[:20], only_in_after=sorted(set(B) - set(A))[:20])
        with open(f"{OUT}/{which}_changed_{pair[0]}_{pair[1]}.tsv", "w") as f:
            f.write("id\tsuite\tlabel\tverdict_from\tverdict_to\tfields\tnew_chain_pairs\treport_pairs_from\treport_pairs_to\n")
            for r in ch:
                f.write("\t".join(map(str, r)) + "\n")
        if pair == (bf, af):
            res["changed"] = ch
    json.dump(res, open(f"{OUT}/{which}.json", "w"), indent=1, sort_keys=True)
    for s in order:
        for k in names:
            x = res["suites"][s][k]
            print(s, k, {a: (b if not isinstance(b, list) else len(b)) for a, b in x.items()})
    print(json.dumps(res["cmp"], indent=1))
    print("cap lines", res["cap_lines"])


main()

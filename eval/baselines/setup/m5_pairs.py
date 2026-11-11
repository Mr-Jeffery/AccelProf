#!/usr/bin/env python3
"""M5 line 4 in M4's unit (eval/PAIRS_PER_TIER.md of study/r1-distance, 3084e455): (kernel name, unordered pc pair), launches merged, worst class.
cuRace alone = S2 (analyze(chain_closure=True, co_async=True, co_r3="off")) on the collector-only recordings of final-2026-11-co and
realworld-2026-10-co, with CUVEIN_CHAIN_ATOMIC_HOP = 0 (sw0) and 1 (sw1), by this branch's python (base 4cb6547e, without the R1 widest-distance fix).
The scalar-clock side and the population are M4's pairs.csv (m5_m4_pairs.csv, a copy of eval/results/pairs-per-tier/pairs.csv read from study/r1-distance).
  m5_pairs.py run [--workers 15]     one subprocess per (program, switch)  -> eval/results/closure-atomic-hop/pairs/sw{0,1}/<id>.json
  m5_pairs.py summary                -> pairs/summary.json + printed table"""
import csv, glob, json, os, resource, subprocess, sys, time, concurrent.futures as cf
from collections import Counter, defaultdict
W = "/home/fzheng4/wt-m5"
HERE = f"{W}/eval/baselines/setup"
OUT = f"{W}/eval/results/closure-atomic-hop/pairs"
B = "/mnt/beegfs/fzheng4/cuvein_traces"
STORES = (f"{B}/final-2026-11-co", f"{B}/realworld-2026-10-co")
SEV = {"RACE": 2, "SC": 1, "ORDERED": 0}


def pop():
    P = defaultdict(dict)       # id -> {(kernel, a, b): row}
    suite = {}
    for r in csv.DictReader(open(f"{HERE}/m5_m4_pairs.csv", newline="")):
        P[r["id"]][(r["kernel"], int(r["pc_a"], 16), int(r["pc_b"], 16))] = r
        suite[r["id"]] = r["suite"]
    return P, suite


def worker(pdir, out):
    sys.path.insert(0, f"{W}/python")
    import sync_dominance as sd
    names = os.listdir(f"{pdir}/collector-only")   # raises on a BeeGFS I/O error (glob returns [] silently)
    kjs = sorted(f"{pdir}/collector-only/{n}" for n in names if n.startswith("kernel_") and n.endswith(".json"))
    dots = sorted(f"{pdir}/dots/{n}" for n in os.listdir(f"{pdir}/dots") if n.endswith(".dot"))
    if not kjs or not dots:
        raise SystemExit("no kernel JSON or dot found in " + pdir)
    pairs, unal = {}, []
    for kj in kjs:
        rep = None
        for dot in dots:
            try:
                rep = sd.analyze(dot, kj, chain_closure=True, co_async=True, co_r3="off")
                break
            except sd.AlignmentError:
                continue
        if rep is None:
            unal.append(os.path.basename(kj))
            continue
        name = rep["kernel"]["name"]
        for v in rep["verdicts"]:
            c, a = v["current_pc"], v["ancient_pc"]
            k = (name, min(c, a), max(c, a))
            if k not in pairs or SEV[v["verdict"]] > SEV[pairs[k]]:
                pairs[k] = v["verdict"]
    json.dump({"unaligned": unal, "pairs": [[n, a, b, v] for (n, a, b), v in sorted(pairs.items())]}, open(out + ".tmp", "w"))
    os.replace(out + ".tmp", out)


def run(workers):
    P, suite = pop()
    pdirs = {}
    for st in STORES:
        for m in glob.glob(f"{st}/*/meta.json"):
            try:
                i = json.load(open(m)).get("id")
            except (OSError, ValueError):
                continue
            if i in P:
                pdirs[i] = os.path.dirname(m)
    print(len(P), "ids in M4 population,", len(pdirs), "found", flush=True)
    tasks = [(i, sw) for i in sorted(pdirs, key=lambda x: (suite[x] != "RW", x)) for sw in ("1", "0")]   # RW first (heaviest)
    for sw in ("0", "1"):
        os.makedirs(f"{OUT}/sw{sw}", exist_ok=True)

    def one(t):
        i, sw = t
        out = f"{OUT}/sw{sw}/{i}.json"
        if os.path.exists(out):
            return f"{i} sw{sw} exists"
        env = dict(os.environ, CUVEIN_CHAIN_ATOMIC_HOP=sw, CUVEIN_DOT_PREFILTER="1")
        t0 = time.time()
        p = subprocess.run([sys.executable, __file__, "_worker", pdirs[i], out], env=env, capture_output=True, text=True,
                           preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_AS, (60 * 2**30,) * 2))
        return f"{i} sw{sw} rc={p.returncode} {time.time() - t0:.0f}s {p.stderr[-200:] if p.returncode else ''}"
    with cf.ThreadPoolExecutor(workers) as ex:
        for ln in ex.map(one, tasks):
            print(ln, flush=True)


def summary():
    P, suite = pop()
    res = {}
    for sw in ("0", "1"):
        C = {}
        for i in P:
            f = f"{OUT}/sw{sw}/{i}.json"
            if os.path.exists(f):
                C[i] = {(n, a, b): v for n, a, b, v in json.load(open(f))["pairs"]}
        res[sw] = C
    missing = sorted(i for i in P if i not in res["0"] or i not in res["1"])
    tab = defaultdict(lambda: Counter())
    for sw in ("0", "1"):
        for i, rows in P.items():
            if i not in res[sw]:
                continue
            s = suite[i]
            for k, r in rows.items():
                if r["scalar_kind"] == "race":
                    tab[(sw, s)]["scalar_race"] += 1
                    if res[sw][i].get(k) != "RACE":
                        tab[(sw, s)]["only_scalar"] += 1
                        tab[(sw, s)]["prog:" + i] += 1
            tab[(sw, s)]["co_race"] += sum(v == "RACE" for v in res[sw][i].values())
    # M4's own cuRace-alone column against sw0 (the R1 widest-distance fix is in M4's python only)
    m4 = Counter()
    for i, rows in P.items():
        if i not in res["0"]:
            continue
        for k, r in rows.items():
            m4["m4_only_scalar"] += (r["scalar_kind"] == "race" and r["curace_kind"] != "race")
            m4["sw0_only_scalar"] += (r["scalar_kind"] == "race" and res["0"][i].get(k) != "RACE")
            m4["m4_co_race_in_csv"] += (r["curace_kind"] == "race")
            m4["sw0_vs_m4_curace_differs"] += ((res["0"][i].get(k) == "RACE") != (r["curace_kind"] == "race"))
    out = {"missing": missing, "m4_vs_sw0": dict(m4), "suites": {}}
    for sw in ("0", "1"):
        tot, progs = Counter(), set()
        for (s_w, s), c in tab.items():
            if s_w != sw:
                continue
            out["suites"][f"sw{sw}/{s}"] = {k: v for k, v in c.items() if not k.startswith("prog:")}
            tot.update({k: v for k, v in c.items() if not k.startswith("prog:")})
            progs |= {k[5:] for k in c if k.startswith("prog:")}
        out[f"sw{sw}_total"] = dict(tot, programs_with_only_scalar=len(progs))
    json.dump(out, open(f"{OUT}/summary.json", "w"), indent=1, sort_keys=True)
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    if sys.argv[1] == "_worker":
        worker(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "run":
        run(int(sys.argv[3]) if len(sys.argv) > 3 else 15)
    else:
        summary()

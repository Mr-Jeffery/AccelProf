#!/usr/bin/env python3
"""M3: re-score of the verdict step for fix/r1-at-widest-distance (886b6bf), before / after.

MEASUREMENT ONLY, read-only on the stores. python/sync_dominance.py is imported as it is; both
states are produced by the SAME code on the SAME recording: before = $CUVEIN_R1_OBSERVED_ONLY=1
(R1 and R3 asked at the edge distance), after = the variable unset (widest distance). Per kernel
JSON, analyze() runs twice (before, then after) on the same CFG; every pc pair (kernel name, pc a,
pc b) whose (verdict, class, model_bug) differs is kept. The distance each state asked R1/R3 at
and whether R3 was asked come from HBGraph.ordered() (shadowed in this process to log its
arguments and result; nothing in sync_dominance.py is changed).

  collect  one JSON per (program, clock mode) under --out/detail; each program in a child process
           under a wall-clock and address-space cap, --workers children at a time (one node = 16).
  report   eval/R1_DISTANCE.md and eval/results/r1-distance/changes.csv from the detail files and
           the mode_pairs.py outputs (--mp-before, --mp-after directories).

    .venv python eval/baselines/r1_distance.py collect --workers 16
    .venv python eval/baselines/r1_distance.py report
"""
import argparse
import concurrent.futures as cf
import csv
import glob
import json
import os
import resource
import subprocess
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, f"{APH}/python")
sys.path.insert(0, f"{APH}/eval")
sys.path.insert(0, HERE)
import latent_census as lc  # noqa: E402

VC, SC = lc.VC, lc.SC
STORES = ("final-2026-11", "final-2026-11-long", "final-2026-11-long-sc",
          "final-2026-11-24h-vc", "final-2026-11-24h-sc", "realworld-2026-10")
OUT = f"{APH}/eval/results/r1-distance"
SEV = {"RACE": 2, "SC": 1, "ORDERED": 0}
SCOPES = ["none", "warp", "block", "grid"]


def worker(pdir, mode, out):
    import sync_dominance as sd
    cap = {}

    class _J:                                  # shadows sync_dominance's `json` name
        def __getattr__(self, k):
            return getattr(json, k)

        def loads(self, s):
            cap["trace"] = json.loads(s)
            return cap["trace"]

    class _G(sd.HBGraph):                      # logs the (distance, strength, chain) of ordered()
        def __init__(self, *a):
            super().__init__(*a)
            cap["calls"] = {}

        def ordered(self, cur, anc, d, cur_read, anc_read, static=True):
            r = super().ordered(cur, anc, d, cur_read, anc_read, static)
            if not getattr(self, "r3_cfg_only", False):
                cap["calls"][(cur, anc)] = (d, bool(static), r["strength"], r["chain"] is not None)
            return r

    sd.json, sd.HBGraph = _J(), _G
    meta = json.load(open(f"{pdir}/meta.json"))
    dots = sorted(glob.glob(f"{pdir}/dots/*.dot"))
    t0 = time.time()

    def run(dot, kj, before):
        if before:
            os.environ["CUVEIN_R1_OBSERVED_ONLY"] = "1"
        else:
            os.environ.pop("CUVEIN_R1_OBSERVED_ONLY", None)
        rep = sd.analyze(dot, kj)
        calls = cap["calls"]
        m = {}
        for v in rep["verdicts"]:
            cur, anc = v["current_pc"], v["ancient_pc"]
            key = (min(cur, anc), max(cur, anc))
            c = calls.get((cur, anc))
            rec = {"verdict": v["verdict"], "class": v.get("matrix_class"),
                   "model_bug": v.get("model_bug"), "strength": v["strength"],
                   "observed": v["observed_distance"], "chain": v["hb_chain"] is not None,
                   "event_candidate": bool(v.get("event_candidate")), "space": v["space"],
                   "asked_dist": SCOPES[c[0]] if c else None,
                   "r3_asked": bool(c and c[1] and c[2] < c[0]), "cur": cur, "anc": anc}
            if key not in m or SEV[rec["verdict"]] > SEV[m[key]["verdict"]]:
                m[key] = rec
        return rep["kernel"]["name"], m

    changed = {}                               # (name, a, b, before tuple, after tuple) -> row
    race = {"before": False, "after": False}
    sc = {"before": False, "after": False}
    kernels, unaligned = 0, []
    for kj in sorted(glob.glob(f"{pdir}/{mode}/kernel_*.json")):
        res = None
        for dot in dots:
            try:
                name, mb = run(dot, kj, True)
                _, ma = run(dot, kj, False)
                res = (name, mb, ma)
                break
            except sd.AlignmentError:
                continue
        if res is None:
            unaligned.append(os.path.basename(kj))
            continue
        kernels += 1
        name, mb, ma = res
        race["before"] |= any(r["verdict"] == "RACE" for r in mb.values())
        race["after"] |= any(r["verdict"] == "RACE" for r in ma.values())
        sc["before"] |= any(r["verdict"] == "SC" for r in mb.values())
        sc["after"] |= any(r["verdict"] == "SC" for r in ma.values())
        for key in set(mb) | set(ma):
            b, a = mb.get(key), ma.get(key)
            tb = (b["verdict"], b["class"], b["model_bug"]) if b else None
            ta = (a["verdict"], a["class"], a["model_bug"]) if a else None
            if tb == ta:
                continue
            k = (name,) + key + (tb, ta)
            if k in changed:
                changed[k]["launches"] += 1
            else:
                changed[k] = {"kernel": name, "pc_a": key[0], "pc_b": key[1], "before": b,
                              "after": a, "launches": 1, "kernel_file": os.path.basename(kj)}
    res = {"id": meta.get("id"), "mode": mode, "pset": meta.get("pset"), "pdir": pdir,
           "status": "ok", "wall_s": round(time.time() - t0, 2), "kernels": kernels,
           "unaligned": unaligned, "race_before": race["before"], "race_after": race["after"],
           "sc_before": sc["before"], "sc_after": sc["after"],
           "changed": list(changed.values())}
    tmp = out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(res, f)
    os.replace(tmp, out)


def cmd_collect(a):
    src, why = lc.select_sources(a.stores.split(","))
    keys = sorted(src, key=lambda k: -src[k]["dump_mb"])       # biggest first
    if a.id_file:
        keep = {ln.strip() for ln in open(a.id_file) if ln.strip()}
        keys = [k for k in keys if k[0] in keep]
    k, n = map(int, a.shard.split("/"))
    keys = keys[k::n]
    if a.limit:
        keys = keys[:a.limit]
    if a.sample:                   # an even spread over the dump-size order, for timing
        keys = keys[::max(1, len(keys) // a.sample)][:a.sample]
    os.makedirs(f"{a.out}/detail", exist_ok=True)
    with open(f"{a.out}/sources.json", "w") as f:
        json.dump({"stores": a.stores, "selected": {f"{i}|{m}": v for (i, m), v in src.items()},
                   "not_available": {f"{i}|{m}": w for (i, m), w in why.items()}},
                  f, indent=0, sort_keys=True)
    memb = int(a.mem_gb * 2**30)

    def lim():
        resource.setrlimit(resource.RLIMIT_AS, (memb, memb))

    def one(k):
        _id, mode = k
        out = f"{a.out}/detail/{_id}__{mode}.json"
        if os.path.exists(out) and not a.force:
            return f"{_id} {mode} exists"
        s = src[k]
        t0 = time.time()
        try:
            p = subprocess.run([sys.executable, __file__, "_worker", s["pdir"], mode, out],
                               preexec_fn=lim, timeout=a.timeout, capture_output=True, text=True)
            status = "ok" if p.returncode == 0 and os.path.exists(out) else \
                ("analysis-oom" if "MemoryError" in p.stderr else f"error(rc={p.returncode})")
            err = p.stderr[-800:]
        except subprocess.TimeoutExpired:
            status, err = f"analysis-timeout={a.timeout}s", ""
        if status != "ok":
            with open(out, "w") as f:
                json.dump({"id": _id, "mode": mode, "pset": s.get("pset"), "pdir": s["pdir"],
                           "status": status, "stderr": err}, f)
        return f"{_id} {mode} {status} {time.time() - t0:.1f}s"
    print(f"{len(keys)} (program, mode) recordings, {a.workers} workers", flush=True)
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for line in ex.map(one, keys):
            print(line, flush=True)


# ---------------------------------------------------------------- report


def _t(r):
    return "none" if r is None else f"{r['verdict']}/{r['class']}"


def trans(c):
    s = f"{_t(c['before'])} -> {_t(c['after'])}"
    b, a = c["before"], c["after"]
    if b and a and b.get("model_bug") and not a.get("model_bug"):
        s += " (model_bug removed)"
    return s


def load_detail(out):
    det = []
    for f in sorted(glob.glob(f"{out}/detail/*.json")):
        try:
            det.append(json.load(open(f)))
        except ValueError:
            pass
    return det


def _md(head, rows):
    o = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    o += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(o)


def mp_rows(d):
    """-> the summary rows of one mode_pairs output directory (suites.csv rows `all` and `RW`)
    and the counts of differences.csv by kind."""
    rows = {r["suite"]: r for r in csv.DictReader(open(f"{d}/suites.csv", newline=""))}
    diffs = Counter()
    for r in csv.DictReader(open(f"{d}/differences.csv", newline="")):
        diffs[(r["suite"] == "RW", r["difference"])] += 1
    return rows, diffs


M2 = (("cccl-3-buggy", 0x80, 0xad90), ("raft-1-buggy", 0x2df0, 0x60a0),
      ("raft-1-fixed", 0x2df0, 0x60d0), ("kokkos-5-buggy", 0xbc0, 0xc90),
      ("kokkos-5-fixed", 0xbd0, 0xca0))


def mp_pair(d, _id, a, b):
    """-> [(vc verdict/class, sc verdict/class, sc R1 flag)] of the pair in mode_pairs detail."""
    f = f"{d}/detail/{_id}.json"
    if not os.path.exists(f):
        return "missing: no detail file"
    j = json.load(open(f))
    if j.get("status") != "ok":
        return f"missing: {j.get('status')}"
    out = []
    for n, pa, pb, tuples in j["pairs"]:
        if (pa, pb) == (a, b):
            for t in tuples:
                out.append(f"vector-clock {t[0]}/{t[1]}; scalar-clock {t[5]}/{t[6]} (R1 {t[7]}, "
                           f"R3 {t[8]}) x{t[10]} launches [{t[11]}]")
    return out or "missing: pair absent"


def mp_summary(d):
    if not os.path.exists(f"{d}/suites.csv"):
        return [["missing: " + d + "/suites.csv not written"] + [""] * 15]
    rows, diffs = mp_rows(d)
    out = []
    for name in ("all", "RW"):
        r = rows.get(name)
        if not r:
            continue
        kinds = Counter()
        for (rw, k), n in diffs.items():
            if name == "all" or rw:
                kinds[k.split(":")[0] if k in ("a", "b") else k] += n
        out.append([name, r["population"], int(r["vc_structural"]) + int(r["vc_latent"]),
                    r["vc_latent"], r["vc_sc"], r["r3_race_R1"], r["r3_race_R3"],
                    r["r3_race_barrier-ordered"], r["r3_race_no-cert"], r["r3_sc_R1"],
                    r["r3_sc_R3"], r["r4_Race"], r["r4_Strong_conflict"],
                    kinds["a"], kinds["b"], sum(v for k, v in kinds.items() if k.startswith("finding"))])
    return out


def m2_rows(det, _id, a, b):
    for d in det:
        if d["id"] == _id and d["mode"] == VC and d["status"] == "ok":
            for c in d["changed"]:
                if (c["pc_a"], c["pc_b"]) == (a, b):
                    return f"{trans(c)}; strength {c['before']['strength']}, asked {c['before']['asked_dist']} -> {c['after']['asked_dist']}"
            return "unchanged (not in changed rows)"
    return "missing: no vector-clock re-score row"


NOTES = """
## Commands, revision, what was not re-scored

Revision: branch `study/r1-distance` = `origin/fix/r1-at-widest-distance` 886b6bf5 (`Judge R1 at the pair's widest distance, not the edge distance alone`), plus this report's commit (scripts `eval/baselines/r1_distance.py`, `eval/baselines/mode_pairs.py` copied unchanged from `eval/mode-pairs` be08b7eb, logs `eval/x_logs/m3/`). Worktree `~/wt-m2`, sparse set `eval python design bin` (`design` is needed by `test_barrier_exit.py` / `test_hb_substitutions.py`, `bin` for `accelprof` on PATH in `test_no_dump.py`). Env `/home/fzheng4/AccelProf/.env/bin/python`. All runs on partition `normal`, `-N 1 -c 16`.

Green set (CLAUDE.md A4, job 334165; the first try, 334162, failed at collection for want of `design/`): `python/test_sync_dominance.py test_barrier_soundness.py test_coherent_ldst.py test_atomic_memory_model.py test_barrier_exit.py test_hb_substitutions.py test_cp_async.py test_co_chain.py test_co_rules.py`: **97 passed, 151 skipped, 0 failed**, against the expected 305 passed, 2 skipped. All 151 skips are `no trace produced (GPU / collector unavailable)`: the normal nodes have no GPU (no GPU allowed here), so the recording halves of the tests did not run. `test_no_dump.py`: 1 failed (`test_no_dump.py:310`, `accelprof` ran and returned 0 where the test expects non-zero, on a node without GPU), 30 skipped, against the expected 27/27. `python/test_r1_distance.py`: 7 passed (the branch's own count). The `rm -rf ScoR/microbenchmarks/artifacts/*` step and the ScoR-parametrised gate tests (55/55) were not run (`ScoR/` is not in the checkout). So the green set is NOT confirmed against the expected counts; the failure of `test_no_dump.py:310` was not investigated further.

Commands (repository root `~/wt-m2`):
- re-score, 4 shards of 16 workers (jobs 334166-334169): `python eval/baselines/r1_distance.py collect --workers 16 --shard k/4 --mem-gb 6 --timeout 3600`; the 15 ids that hit the 3,600 s / 6 GB cap re-run (job 334256, `--id-file eval/x_logs/m3/long_ids_r1.txt --force --workers 7 --mem-gb 10 --timeout 36000`; the two P4 `matrix-multiplication-*-large` vector-clock recordings need 70 GB: job 334311 `eval/x_logs/m3/bigmem.sh`); sample timing job 334164 (96 recordings, 87 s on one node: about 2.3 node-hours predicted for 9,519; measured 4 jobs of 1h17m plus the long ids).
- mode_pairs, before (`CUVEIN_R1_OBSERVED_ONLY=1`, job 334208 `eval/x_logs/m3/mp.sh before`) and after (job 334174 `mp.sh after`), `--stores` default (the six stores of M1), `--shard k/16 --mem-gb 6 --timeout 3600`; long reruns with `--id-file ... --force --mem-gb 10 --timeout 36000`: after 334253 (13 ids), before 334302 (15 ids); P4 matrix-multiplication at 70 GB in 334311; `mode_pairs.py tables` for both (job 335307) into `eval/results/r1-distance/mode-pairs-{before,after}/`.
- this report: `python eval/baselines/r1_distance.py report`.

Re-scored: every (program, clock mode) recording that `latent_census.select_sources` selects over `final-2026-11`, `-long`, `-long-sc`, `-24h-vc`, `-24h-sc`, `realworld-2026-10`: 9,519 of 9,519 (9,517 ok). Not re-scored: `amrex-1-buggy` and `amrex-1-fixed`, scalar-clock recording, `analysis-timeout=36000s` (10 h). Not available as recordings (not selected; reason from `sources.json`, 43 of them): the P6 `bulkcpy`/`dsmem` ids (no mode saved), P7/P9 ids whose 24 h recordings are missing or unsaved, `amrex-1` and `ginkgo-1` vector-clock recordings (unsaved / partial); the same reasons as M1. Not part of this re-score: `realworld-2026-10-t21c` (not a store the paper's tables use through M1's stores list), collector-only recordings (the change is in the clock-mode verdict path only; collector-only dumps carry no `hb_races`, so the widest distance equals the edge distance there: not re-scored), the scalar-clock pass over the vector-clock recordings is covered by mode_pairs (pass 2).

Definitions: program verdict = RACE if any pc pair has verdict RACE (strong conflicts, verdict SC, are not counted); a pair changed if (verdict, matrix class, model_bug) changed between the two states; `edge distance` = the distance R1/R3 were asked at before (the pair's edge distance, or the event-stream distance for a rescued pair), `widest distance` = the distance asked after (max of edge, widest `hb_races` instance, widest barrier-pass instance), both read from the arguments of `HBGraph.ordered()` (shadowed in the driver; sync_dominance.py is unchanged); `R3 asked` = the pair is not a same-instruction warp pair and the R1 strength was below the asked distance. Labels come from `latent_census._labels()`; the real-world ids have no manifest label, so the id suffix (buggy / fixed build) is shown. In the mode_pairs rows the R1 flag of a tuple is `strength >= observed_distance` of the verdict record, the field the unchanged `mode_pairs.py` reads; it keeps the edge distance, which is why the five M2 pairs still show `R1 True` next to a RACE verdict after the change.

The before state of mode_pairs reproduces M1's committed numbers (all rows: 5,038 vector-clock Race pairs, 962 strong conflicts, scalar-clock orders 5 by R1 and 94 by R3, 159 strong conflicts by R3, 5 findings), so the code differences between `eval/mode-pairs` and this branch other than the R1 rule do not move these rows.
"""


def cmd_report(a):
    det = load_detail(a.out)
    lab, _ = lc._labels()
    ok = [d for d in det if d["status"] == "ok"]
    bad = [d for d in det if d["status"] != "ok"]
    suite = lambda d: d.get("pset") or d["id"].split("-")[0]
    rows, t1 = [], defaultdict(Counter)
    for d in ok:
        s, m = suite(d), d["mode"]
        c = t1[(s, m)]
        c["programs"] += 1
        c["pairs_changed"] += len(d["changed"])
        if not d["race_before"] and d["race_after"]:
            c["CLEAN->RACE"] += 1
        if d["race_before"] and not d["race_after"]:
            c["RACE->CLEAN"] += 1
        for ch in d["changed"]:
            c["pair " + trans(ch)] += 1
            rows.append({"suite": s, "id": d["id"], "mode": m, "label": lab.get(d["id"]) or ("buggy build, no manifest label" if d["id"].endswith("-buggy") else "fixed build, no manifest label" if d["id"].endswith("-fixed") else "unlabelled"),
                         "kernel": ch["kernel"], "pc_a": hex(ch["pc_a"]), "pc_b": hex(ch["pc_b"]),
                         "transition": trans(ch), "launches": ch["launches"],
                         "program_before": "RACE" if d["race_before"] else "CLEAN",
                         "program_after": "RACE" if d["race_after"] else "CLEAN",
                         "strength_before": (ch["before"] or {}).get("strength"),
                         "strength_after": (ch["after"] or {}).get("strength"),
                         "edge_distance": (ch["before"] or {}).get("asked_dist"),
                         "observed_distance_before": (ch["before"] or {}).get("observed"),
                         "widest_distance": (ch["after"] or {}).get("asked_dist"),
                         "r3_asked_before": (ch["before"] or {}).get("r3_asked"),
                         "r3_asked_after": (ch["after"] or {}).get("r3_asked"),
                         "chain_after": (ch["after"] or {}).get("chain"),
                         "event_candidate": (ch["after"] or {}).get("event_candidate"),
                         "space": (ch["after"] or ch["before"] or {}).get("space"),
                         "kernel_file": ch["kernel_file"]})
    os.makedirs(a.out, exist_ok=True)
    cols = list(rows[0]) if rows else ["suite"]
    with open(f"{a.out}/changes.csv", "w", newline="") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(rows)
    kinds = sorted({k for c in t1.values() for k in c if k.startswith("pair ")})
    h = ["suite", "clock mode", "re-scored", "CLEAN->RACE", "RACE->CLEAN", "pairs changed"] + \
        [k[5:] for k in kinds]
    t1rows = [[s, m, c["programs"], c["CLEAN->RACE"], c["RACE->CLEAN"], c["pairs_changed"]] +
              [c[k] for k in kinds] for (s, m), c in sorted(t1.items())]
    pchg = [d for d in ok if d["race_before"] != d["race_after"]]
    t2 = []
    for d in pchg:
        for ch in d["changed"]:
            if (ch["after"] or {}).get("verdict") == "RACE" or (ch["before"] or {}).get("verdict") == "RACE":
                b, af = ch["before"] or {}, ch["after"] or {}
                t2.append([d["id"], d["mode"], lab.get(d["id"]) or ("buggy build, no manifest label" if d["id"].endswith("-buggy") else "fixed build, no manifest label" if d["id"].endswith("-fixed") else "unlabelled"),
                           f"{'CLEAN->RACE' if af.get('verdict') == 'RACE' else 'RACE->CLEAN'}",
                           f"{ch['kernel'][:40]} {hex(ch['pc_a'])}/{hex(ch['pc_b'])}",
                           f"{b.get('strength')}->{af.get('strength')}", b.get("asked_dist"),
                           af.get("asked_dist"), f"{b.get('r3_asked')}->{af.get('r3_asked')}"])
    md = ["# M3: re-score for fix/r1-at-widest-distance", "",
          f"Generated by `eval/baselines/r1_distance.py report`. {len(ok)} (program, clock mode) "
          f"recordings re-scored, {len(bad)} not (status below). Before = `CUVEIN_R1_OBSERVED_ONLY=1`, "
          "after = unset, same recording, same code.", "",
          "## Table 1: per suite and clock mode", "", _md(h, t1rows), "",
          "Program verdict = RACE if any pc pair of any kernel has verdict RACE. Pair transitions are "
          "`verdict/class` before -> after.", "",
          f"## Table 2: programs whose verdict changed ({len(pchg)} programs, {len(t2)} rows)", "",
          _md(["program", "mode", "label", "change", "pair", "strength", "edge distance",
               "widest distance", "R3 asked"], t2) if t2 else "none", "",
          f"## Changed pairs ({len(rows)} rows; all in `eval/results/r1-distance/changes.csv`)", "",
          _md(["program", "mode", "label", "kernel / pcs", "before -> after", "strength", "edge distance",
               "widest distance", "R3 asked (before -> after)"],
              [[r["id"], r["mode"], r["label"], f"{r['kernel'][:40]} {r['pc_a']}/{r['pc_b']}", r["transition"],
                f"{r['strength_before']}->{r['strength_after']}", r["edge_distance"], r["widest_distance"],
                f"{r['r3_asked_before']}->{r['r3_asked_after']}"] for r in rows[:80]]) if rows else "none", "",
          "## Mode-pairs summary rows (population rows of suites.csv; before = "
          "`CUVEIN_R1_OBSERVED_ONLY=1`, after = unset)", "",
          _md(["state", "rows", "population", "pairs vc Race+Latent (class structural + latent)", "of them Latent",
               "vc Strong conflict", "sc orders by R1 (Race/Latent)", "sc orders by R3", "sc barrier-ordered",
               "sc no cert", "SC pairs: R1", "SC pairs: R3", "sc reports, vc files Latent: Race",
               "sc reports, vc files Latent: Strong conflict", "diff (a)", "diff (b)", "diff finding"],
              [["before"] + r for r in mp_summary(a.mp_before)] +
              [["after"] + r for r in mp_summary(a.mp_after)]), "",
          "## The five M2 pairs after the change", "",
          _md(["pair", "mode_pairs after (both clock modes, same recording)",
               "r1_distance vector-clock row (before -> after)"],
              [[f"{i} {hex(x)}/{hex(y)}", "; ".join(mp_pair(a.mp_after, i, x, y)) if not isinstance(
                  mp_pair(a.mp_after, i, x, y), str) else mp_pair(a.mp_after, i, x, y),
                m2_rows(det, i, x, y)] for i, x, y in M2]), "",
          "## Not re-scored", "",
          _md(["id", "mode", "status"], [[d["id"], d["mode"], d["status"]] for d in bad])
          if bad else "none", ""]
    md.append(NOTES)
    open(a.md, "w").write("\n".join(md))
    print(f"wrote {a.md}, {a.out}/changes.csv ({len(rows)} rows)")


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("collect")
    c.add_argument("--stores", default=",".join(STORES))
    c.add_argument("--out", default=OUT)
    c.add_argument("--workers", type=int, default=16)
    c.add_argument("--id-file")
    c.add_argument("--limit", type=int, default=0)
    c.add_argument("--sample", type=int, default=0)
    c.add_argument("--shard", default="0/1")
    c.add_argument("--force", action="store_true")
    c.add_argument("--timeout", type=int, default=3600)
    c.add_argument("--mem-gb", type=float, default=5)
    r = sp.add_parser("report")
    r.add_argument("--out", default=OUT)
    r.add_argument("--md", default=f"{APH}/eval/R1_DISTANCE.md")
    r.add_argument("--mp-before", default=f"{OUT}/mode-pairs-before")
    r.add_argument("--mp-after", default=f"{OUT}/mode-pairs-after")
    w = sp.add_parser("_worker")
    w.add_argument("pdir")
    w.add_argument("mode")
    w.add_argument("out")
    a = ap.parse_args()
    if a.cmd == "_worker":
        worker(a.pdir, a.mode, a.out)
    else:
        {"collect": cmd_collect, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    main()

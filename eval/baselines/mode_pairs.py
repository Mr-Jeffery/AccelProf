#!/usr/bin/env python3
"""M1 mode pairs: the pc pairs scalar-clock mode reports and certifies, against vector-clock
mode's, on the SAME recorded trace.

MEASUREMENT ONLY. python/sync_dominance.py (the verdict layer) runs unchanged over the kept
no-dump vector-clock recordings of the final store; this script observes it, as
eval/baselines/latent_census.py does (and reuses its store selection):
  * pass 1 analyses each vector-clock kernel JSON as recorded;
  * pass 2 analyses the same JSON with `hb_races` and `hb_races_sync_only` dropped and
    `hb_sync_pass` kept (sync_dominance's `json` name is shadowed, as in latent_census.py), which
    is what a scalar-clock recording carries: analyze() takes its scalar-clock path.
Every pc pair of both passes is kept per kernel launch, then merged per (kernel name, pc pair).

  collect  one JSON per vector-clock recording under --out/detail (a CPU node: BeeGFS is not
           mounted on the login node); each program in a child process under a wall-clock and
           address-space cap.
  tables   eval/MODE_PAIRS.md and eval/results/mode-pairs/*.csv from the detail files.

    .venv python eval/baselines/mode_pairs.py collect --shard 0/1
    .venv python eval/baselines/mode_pairs.py tables
"""
import argparse
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
DEFAULT_STORES = ("final-2026-11", "final-2026-11-long", "final-2026-11-long-sc",
                  "final-2026-11-24h-vc", "final-2026-11-24h-sc", "realworld-2026-10")
DEFAULT_OUT = f"{APH}/eval/results/mode-pairs"
MERGED = f"{APH}/eval/results/final-b/merged/baselines-cuvein.csv"
SEV = {"RACE": 2, "SC": 1, "ORDERED": 0}
# the vector-clock class of a pair, worst first (row 2 files each pair under its worst class)
VC_ORDER = ("structural", "latent", "sc", "latent-sc", "ordered", "barrier-ordered", None)
VERSION = __import__("hashlib").sha1(
    open(__file__, "rb").read().split(b"-" * 16 + b" tables\n")[0]).hexdigest()[:12]


# ---------------------------------------------------------------- the worker


def worker(pdir, out):
    import sync_dominance as sd
    cap = {"strip": False}

    class _J:                                  # shadows sync_dominance's `json` name
        def __getattr__(self, k):
            return getattr(json, k)

        def loads(self, s):
            t = json.loads(s)
            if cap["strip"]:
                t.pop("hb_races", None)
                t.pop("hb_races_sync_only", None)
            cap["trace"] = t
            return t

    class _G(sd.HBGraph):                      # keeps the graph analyze() builds
        def __init__(self, *a):
            super().__init__(*a)
            cap["eng"] = self

    sd.json, sd.HBGraph = _J(), _G
    meta = json.load(open(f"{pdir}/meta.json"))
    dots = sorted(glob.glob(f"{pdir}/dots/*.dot"))
    t0 = time.time()

    def vmap(rep):
        m = {}
        for v in rep["verdicts"]:
            key = (min(v["current_pc"], v["ancient_pc"]), max(v["current_pc"], v["ancient_pc"]))
            obs = sd.SCOPES.index(v["observed_distance"])
            rec = (v["verdict"], v.get("matrix_class"),
                   sd.SCOPES.index(v["strength"]) >= obs, v["hb_chain"] is not None,
                   bool(v.get("event_candidate")))
            if key not in m or SEV[rec[0]] > SEV[m[key][0]]:
                m[key] = rec
        return m

    pairs = {}                                 # (kernel name, pc a, pc b) -> {tuple: [n, kfile]}
    kernels, unaligned = 0, []
    rmw_pc = rmw_x = False
    prog = {VC: False, SC: False}              # any RACE verdict
    for kj in sorted(glob.glob(f"{pdir}/{VC}/kernel_*.json")):
        res = None
        for dot in dots:
            try:
                cap["strip"] = False
                rv = sd.analyze(dot, kj)
                tr, eng = cap["trace"], cap["eng"]
                cap["strip"] = True
                rs = sd.analyze(dot, kj)
                res = (rv, rs)
                break
            except sd.AlignmentError:
                continue
        if res is None:
            unaligned.append(os.path.basename(kj))
            continue
        rv, rs = res
        kernels += 1
        atom = eng.atom
        rmw_pc = rmw_pc or bool(atom)
        if not rmw_x and atom:
            for e in tr.get("edges", []):
                cur, anc = e["current_pc"], e.get("ancient_pc")
                if e.get("cold_miss") or anc is None or not (cur in atom or anc in atom):
                    continue
                if sd._observed(e.get("dist", {}))[0] > sd.NONE:
                    rmw_x = True
                    break
        mv, ms = vmap(rv), vmap(rs)
        name = rv["kernel"]["name"]
        prog[VC] = prog[VC] or any(r[0] == "RACE" for r in mv.values())
        prog[SC] = prog[SC] or any(r[0] == "RACE" for r in ms.values())
        for key in set(mv) | set(ms):
            t = (mv.get(key) or (None,) * 5) + (ms.get(key) or (None,) * 5)
            slot = pairs.setdefault((name,) + key, {})
            if t in slot:
                slot[t][0] += 1
            else:
                slot[t] = [1, os.path.basename(kj)]
    res = {"version": VERSION, "id": meta.get("id"), "pset": meta.get("pset"),
           "program": meta.get("program"), "pdir": pdir, "status": "ok",
           "runtime": meta.get("runtime"), "wall_s": round(time.time() - t0, 2),
           "kernels": kernels, "unaligned": unaligned, "rmw_pc": rmw_pc, "rmw_xthread": rmw_x,
           "vc_race": prog[VC], "sc_race": prog[SC],
           "pairs": [[n, a, b, [list(t) + [c, kf] for t, (c, kf) in sl.items()]]
                     for (n, a, b), sl in sorted(pairs.items())]}
    tmp = out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(res, f)
    os.replace(tmp, out)


# ---------------------------------------------------------------- collect


def _outname(out, _id):
    return f"{out}/detail/{_id}.json"


def cmd_collect(a):
    src, why = lc.select_sources(a.stores.split(","))
    ids = sorted({i for i, m in src if m == VC} | {i for i, m in why if m == VC})
    if a.id_file:
        keep = {ln.strip() for ln in open(a.id_file) if ln.strip()}
        ids = [i for i in ids if i in keep]
    k, n = map(int, a.shard.split("/"))
    ids = ids[k::n]
    os.makedirs(f"{a.out}/detail", exist_ok=True)
    if k == 0:
        with open(f"{a.out}/sources.json", "w") as f:
            json.dump({"stores": a.stores, "version": VERSION,
                       "selected": {i: v for (i, m), v in src.items() if m == VC},
                       "not_available": {i: w for (i, m), w in why.items() if m == VC}},
                      f, indent=0, sort_keys=True)
    print(f"shard {k}/{n}: {len(ids)} programs", flush=True)
    for _id in ids:
        out = _outname(a.out, _id)
        if os.path.exists(out) and not a.force:
            continue
        s = src.get((_id, VC))
        if s is None:
            with open(out, "w") as f:
                json.dump({"id": _id, "status": f"not-analysable:{why[(_id, VC)]}"}, f)
            print(f"{_id} not-analysable {why[(_id, VC)]}", flush=True)
            continue
        t0 = time.time()
        memb = int(a.mem_gb * 2**30)

        def lim():
            resource.setrlimit(resource.RLIMIT_AS, (memb, memb))
        try:
            p = subprocess.run([sys.executable, __file__, "_worker", s["pdir"], out],
                               preexec_fn=lim, timeout=a.timeout, capture_output=True, text=True)
            status = "ok" if p.returncode == 0 and os.path.exists(out) else \
                ("analysis-oom" if "MemoryError" in p.stderr else f"error(rc={p.returncode})")
            err = p.stderr[-800:]
        except subprocess.TimeoutExpired:
            status, err = f"analysis-timeout={a.timeout}s", ""
        if status != "ok":
            with open(out, "w") as f:
                json.dump({"id": _id, "pset": s.get("pset"), "pdir": s["pdir"],
                           "status": status, "stderr": err}, f)
        print(f"{_id} {status} {time.time() - t0:.1f}s", flush=True)


# ---------------------------------------------------------------- tables


def _key_cells(tuples):
    """Cells of one (kernel, pc pair) over the tuples seen in its launches. A tuple is
    (vc verdict, vc class, vc R1, vc R3, vc ec, sc verdict, sc class, sc R1, sc R3, sc ec,
    launches, first kernel file); a side without a verdict did not generate the pair."""
    vcs = [t[1] if t[0] else None for t in tuples]
    worst = min(vcs, key=lambda c: VC_ORDER.index(c))
    c = {"vc_class": worst, "r3": set(), "r4": set(), "diff": set(), "class_change": False}
    for t in tuples:
        v_ver, v_cls, v_r1, v_r3, _, s_ver, s_cls, s_r1, s_r3, _ = t[:10]
        v_rep = v_ver in ("RACE", "SC")
        s_rep = s_ver in ("RACE", "SC")
        # row 3: vc reports (Race / Latent; strong conflicts kept apart), sc certifies ordered
        if v_ver in ("RACE", "SC") and s_ver == "ORDERED":
            if s_cls == "barrier-ordered":
                cert = "barrier-ordered"
            else:
                cert = "R1" if s_r1 else "R3" if s_r3 else "no-cert"
            c["r3"].add((v_cls, cert))
        # row 4: sc reports, vc files the pair as Latent
        if v_cls in ("latent", "latent-sc") and s_ver in ("RACE", "SC"):
            c["r4"].add("Race" if s_ver == "RACE" else "Strong conflict")
        # differences between the two reported sets
        if v_rep and not s_rep:
            if s_ver is None:
                c["diff"].add("b")               # never generated as a candidate on the sc side
            elif s_ver == "ORDERED" and s_cls != "barrier-ordered" and s_r3 and not s_r1:
                c["diff"].add("a")               # an R3 certificate the vector clock vetoes
            else:
                c["diff"].add("finding:vc-reports/sc-%s%s" % (
                    s_ver, "" if s_cls is None else "/" + s_cls) + (
                    "+R1" if s_r1 and s_ver == "ORDERED" else ""))
        elif s_rep and not v_rep:
            c["diff"].add("finding:sc-reports/vc-%s" % (v_ver or "absent"))
        elif v_rep and s_rep and v_ver != s_ver:
            c["class_change"] = True
    return c


def _md(head, rows):
    o = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    o += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(o)


def cmd_tables(a):
    det = {}
    for f in glob.glob(f"{a.out}/detail/*.json"):
        try:
            j = json.load(open(f))
        except ValueError:
            continue
        det[j["id"]] = j
    src = json.load(open(f"{a.out}/sources.json")) if os.path.exists(f"{a.out}/sources.json") else {}
    csvv = defaultdict(set)
    if os.path.exists(a.merged):
        for r in csv.DictReader(open(a.merged, newline="")):
            if r["tool"] == "cuvein" and r["mode"] == VC:
                csvv[r["id"]].add(r["verdict"])
    progs, diffs = [], []
    status = defaultdict(Counter)
    for _id, j in sorted(det.items()):
        pset = j.get("pset") or (src.get("selected", {}).get(_id, {}) or {}).get("pset") or _id.split("-")[0]
        status[pset][j["status"].split("=")[0].split(":")[0].split("(")[0]] += 1
        if j["status"] != "ok":
            progs.append({"suite": pset, "id": _id, "status": j["status"]})
            continue
        row = {"suite": pset, "id": _id, "status": "ok", "kernels": j["kernels"],
               "unaligned": len(j["unaligned"]), "rmw_pc": j["rmw_pc"],
               "rmw_xthread": j["rmw_xthread"],
               "vc_verdict": "RACE" if j["vc_race"] else "CLEAN",
               "sc_verdict": "RACE" if j["sc_race"] else "CLEAN",
               "csv_vc_verdicts": "/".join(sorted(csvv.get(_id, ()))),
               "store": os.path.basename(os.path.dirname(j["pdir"])),
               "runtime": (j.get("runtime") or {}).get("libsanalyzer", "") if isinstance(
                   j.get("runtime"), dict) else ""}
        row["csv_agrees"] = "" if _id not in csvv else row["vc_verdict"] in csvv[_id]
        pairs = Counter()
        att = set()
        for name, pa, pb, tuples in j["pairs"]:
            c = _key_cells(tuples)
            pairs["pairs"] += 1
            pairs["vc_" + str(c["vc_class"])] += 1
            for v_cls, cert in c["r3"]:
                pairs[f"r3_{'race' if v_cls in ('structural', 'latent') else 'sc'}_{cert}"] += 1
            for x in c["r4"]:
                pairs["r4_" + x.replace(" ", "_")] += 1
            if c["class_change"]:
                pairs["class_change"] += 1
            for d in c["diff"]:
                att.add(d.split(":")[0])
                diffs.append({"suite": pset, "id": _id, "kernel": name, "pc_a": hex(pa),
                              "pc_b": hex(pb), "difference": d,
                              "kernel_file": tuples[0][11]})
        row.update(pairs)
        row["differs"] = bool(att)
        row["attribution"] = "+".join(sorted(att))
        row["verdict_differs"] = row["vc_verdict"] != row["sc_verdict"]
        progs.append(row)
    os.makedirs(a.out, exist_ok=True)
    cols = ["suite", "id", "status", "store", "kernels", "unaligned", "rmw_pc", "rmw_xthread",
            "vc_verdict", "sc_verdict", "verdict_differs", "csv_vc_verdicts", "csv_agrees",
            "pairs", "vc_structural", "vc_latent", "vc_sc", "vc_latent-sc", "vc_ordered",
            "vc_barrier-ordered", "r3_race_R1", "r3_race_R3", "r3_race_barrier-ordered",
            "r3_race_no-cert", "r3_sc_R1", "r3_sc_R3", "r3_sc_barrier-ordered", "r3_sc_no-cert",
            "r4_Race", "r4_Strong_conflict", "class_change", "differs", "attribution"]
    with open(f"{a.out}/programs.csv", "w", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore", restval="")
        w.writeheader()
        for r in progs:
            w.writerow(r)
    dcols = ["suite", "id", "kernel", "pc_a", "pc_b", "difference", "kernel_file"]
    with open(f"{a.out}/differences.csv", "w", newline="") as f:
        w = csv.DictWriter(f, dcols)
        w.writeheader()
        w.writerows(diffs)

    ok = [r for r in progs if r["status"] == "ok"]

    def inpop(r):
        return r["suite"] == "RW" or r["rmw_xthread"]
    suites = sorted({r["suite"] for r in progs})
    sumcols = ["pairs", "vc_structural", "vc_latent", "vc_sc", "vc_latent-sc", "vc_ordered",
               "vc_barrier-ordered", "r3_race_R1", "r3_race_R3", "r3_race_barrier-ordered",
               "r3_race_no-cert", "r3_sc_R1", "r3_sc_R3", "r3_sc_barrier-ordered",
               "r3_sc_no-cert", "r4_Race", "r4_Strong_conflict", "class_change"]
    srows = []
    for s in suites:
        rs = [r for r in progs if r["suite"] == s]
        okr = [r for r in rs if r["status"] == "ok"]
        pop = [r for r in okr if inpop(r)]
        o = {"suite": s, "programs_with_vc_recording": len(rs), "analysed_ok": len(okr),
             "with_rmw_pc": sum(bool(r["rmw_pc"]) for r in okr),
             "population": len(pop),
             "programs_differ": sum(bool(r["differs"]) for r in pop),
             "verdict_differs": sum(bool(r["verdict_differs"]) for r in pop)}
        for c in sumcols:
            o[c] = sum(int(r.get(c) or 0) for r in pop)
        srows.append(o)
    tot = {"suite": "all"}
    for k in srows[0] if srows else ():
        if k != "suite":
            tot[k] = sum(o[k] for o in srows)
    if srows:
        srows.append(tot)
    with open(f"{a.out}/suites.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(srows[0]) if srows else ["suite"])
        w.writeheader()
        w.writerows(srows)

    md = ["# M1: scalar-clock mode's pc pairs against vector-clock mode's (same recorded trace)", "",
          f"Generated by `eval/baselines/mode_pairs.py tables` (collect version `{VERSION}`) from "
          f"`eval/results/mode-pairs/detail/` (not committed; `collect` regenerates it from the "
          f"stores). Numbers only; definitions at the end.", ""]
    md += ["## Table 1-4, one row per suite (population only)", ""]
    h1 = ["suite", "vc recordings", "analysed", "population", "programs differ", "verdict differs"]
    md += [_md(h1, [[o["suite"], o["programs_with_vc_recording"], o["analysed_ok"],
                     o["population"], o["programs_differ"], o["verdict_differs"]] for o in srows]), ""]
    md += ["### 2. vector-clock pc pairs by class (each pair under its worst class)", ""]
    h2 = ["suite", "pairs", "Race", "Latent", "Strong conflict", "Latent-SC", "ordered",
          "barrier-ordered"]
    md += [_md(h2, [[o["suite"], o["pairs"], o["vc_structural"], o["vc_latent"], o["vc_sc"],
                     o["vc_latent-sc"], o["vc_ordered"], o["vc_barrier-ordered"]] for o in srows]), ""]
    md += ["### 3. pairs vector-clock mode reports and scalar-clock mode certifies as ordered", ""]
    h3 = ["suite", "Race/Latent: R1", "Race/Latent: R3", "Race/Latent: barrier-ordered",
          "Race/Latent: no cert", "Strong conflict: R1", "Strong conflict: R3",
          "Strong conflict: barrier-ordered", "Strong conflict: no cert"]
    md += [_md(h3, [[o["suite"], o["r3_race_R1"], o["r3_race_R3"], o["r3_race_barrier-ordered"],
                     o["r3_race_no-cert"], o["r3_sc_R1"], o["r3_sc_R3"],
                     o["r3_sc_barrier-ordered"], o["r3_sc_no-cert"]] for o in srows]), ""]
    md += ["### 4. pairs scalar-clock mode reports and vector-clock mode files as Latent", ""]
    md += [_md(["suite", "scalar-clock Race", "scalar-clock Strong conflict",
                "reported in both, Race in one and Strong conflict in the other"],
               [[o["suite"], o["r4_Race"], o["r4_Strong_conflict"], o["class_change"]]
                for o in srows]), ""]
    pd = [r for r in ok if inpop(r) and r["verdict_differs"]]
    md += ["## Programs whose verdict differs (vc RACE/CLEAN vs sc RACE/CLEAN)", ""]
    md += [_md(["suite", "id", "vc", "sc", "attribution"],
               [[r["suite"], r["id"], r["vc_verdict"], r["sc_verdict"], r["attribution"]]
                for r in pd]) if pd else "none", ""]
    dp = [r for r in ok if inpop(r) and r["differs"]]
    md += ["## Programs on which the reported pair sets differ", "",
           _md(["attribution", "programs"],
               [[k, v] for k, v in sorted(Counter(r["attribution"] for r in dp).items())]), ""]
    md += [_md(["suite", "id", "attribution", "pairs (a)", "pairs (b)", "pairs (finding)"],
               [[r["suite"], r["id"], r["attribution"],
                 sum(1 for d in diffs if d["id"] == r["id"] and d["difference"] == "a"),
                 sum(1 for d in diffs if d["id"] == r["id"] and d["difference"] == "b"),
                 sum(1 for d in diffs if d["id"] == r["id"] and d["difference"].startswith("finding"))]
                for r in dp[:300]]), ""]
    fd = [d for d in diffs if d["difference"].startswith("finding")]
    md += ["## Findings (a difference that fits neither (a) nor (b)); all rows in differences.csv", "",
           _md(["difference", "pairs"],
               [[k, v] for k, v in sorted(Counter(d["difference"] for d in fd).items())])
           if fd else "none", ""]
    bad = [r for r in ok if r["csv_agrees"] is False]
    md += ["## Cross-check against the merged CSV (the recording's vector-clock verdict is among the "
           "CSV's rep verdicts)", "",
           f"programs checked: {sum(r['csv_agrees'] != '' for r in ok)}; disagreeing: {len(bad)}", ""]
    if bad:
        md += [_md(["id", "recomputed", "csv"], [[r["id"], r["vc_verdict"], r["csv_vc_verdicts"]]
                                                 for r in bad[:100]]), ""]
    md += ["## Status of the vector-clock recordings", ""]
    allst = sorted({k for c in status.values() for k in c})
    md += [_md(["suite"] + allst, [[s] + [status[s].get(k, 0) for k in allst] for s in sorted(status)]), ""]
    na = [r for r in progs if r["status"] != "ok"]
    md += ["### Recordings not analysed (no vector-clock recording to read)", "",
           _md(["suite", "id", "reason"], [[r["suite"], r["id"], r["status"]] for r in na])
           if na else "none", ""]
    md += ["The reason is the last store that lists the id. In the merged CSV the P7 and P9 ids have "
           "only vector-clock TIMEOUT rows (no complete rep), the P6 ids have no vector-clock row, "
           "and amrex-1 / ginkgo-1 are the final-m4 / partial real-world recordings.", ""]
    md += ["## Definitions", "",
           "- Source: the vector-clock no-dump recording of each program in the final stores "
           f"({a.stores}); later stores win, as in latent_census.py. A recording counts only if "
           "its mode is saved, not partial and has a complete rep.",
           "- Pass 1 = `sync_dominance.analyze` on the kernel JSON as recorded; pass 2 = the same "
           "JSON with `hb_races` and `hb_races_sync_only` removed, `hb_sync_pass` kept (a scalar-clock "
           "recording's content; analyze() takes its scalar-clock path).",
           "- A pair is a (kernel name, unordered pc pair) with a verdict in at least one pass; "
           "launches of one kernel are merged. Row 2 files each pair under its worst vector-clock "
           "class over its launches (structural = Race, latent = Latent). Rows 3 and 4 and the "
           "differences count a pair if some launch has the stated pair of verdicts.",
           "- Reported = verdict RACE or SC (strong conflict). Race/Latent = verdict RACE with class "
           "structural / latent; Strong conflict = verdict SC.",
           "- Row 3: vector-clock reports the pair; scalar-clock verdict ORDERED with certificate "
           "R1 (strength >= observed distance), else R3 (`hb_chain`), or barrier-ordered "
           "(the barrier-only clock; not a certificate), else no cert.",
           "- Row 4: vector-clock class latent / latent-sc and a scalar-clock verdict RACE / SC.",
           "- Attribution of a reported-set difference: (a) vector-clock reports, scalar-clock "
           "certifies by R3 only; (b) vector-clock reports and the pair is not a candidate on the "
           "scalar-clock side; anything else is a finding.",
           "- Population: programs with at least one trace edge, at inter-thread distance, with a "
           "read-modify-write pc (an atomic RMW opcode, `HBGraph.atom`) at an endpoint; the RW rows "
           "are all real-world recordings. `rmw_pc` in programs.csv is the looser opcode-only flag.",
           ""]
    with open(a.md, "w") as f:
        f.write("\n".join(md))
    print(f"wrote {a.md}: {len(ok)} analysed, {len(progs) - len(ok)} not, {len(diffs)} differences")


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("collect")
    c.add_argument("--stores", default=",".join(DEFAULT_STORES))
    c.add_argument("--out", default=DEFAULT_OUT)
    c.add_argument("--shard", default="0/1")
    c.add_argument("--id-file")
    c.add_argument("--force", action="store_true")
    c.add_argument("--timeout", type=int, default=3600)
    c.add_argument("--mem-gb", type=float, default=60)
    t = sp.add_parser("tables")
    t.add_argument("--out", default=DEFAULT_OUT)
    t.add_argument("--stores", default=",".join(DEFAULT_STORES))
    t.add_argument("--merged", default=MERGED)
    t.add_argument("--md", default=f"{APH}/eval/MODE_PAIRS.md")
    w = sp.add_parser("_worker")
    w.add_argument("pdir")
    w.add_argument("out")
    a = ap.parse_args()
    {"collect": cmd_collect, "tables": cmd_tables}.get(a.cmd, lambda a: worker(a.pdir, a.out))(a)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""M4: reported pc pairs per configuration, one counting unit.

Counting unit (as eval/baselines/mode_pairs.py): a pair is (kernel name, unordered pc pair); the
launches of one kernel are merged; a pair is counted under its worst class over its launches (data
race = verdict RACE, strong conflict = verdict SC; RACE wins over SC). Programs: P3 (ECL) and the
canary programs are left out; only programs with a result in all three configurations count.

Configurations
  vector clock, scalar clock : the per-pair output of mode_pairs.py (detail files of
      eval/results/r1-distance/mode-pairs-after, the "after" state of M3: fix/r1-at-widest-distance).
      The scalar-clock pass is mode_pairs' pass 2: the vector-clock recording without hb_races
      (what a scalar-clock recording carries).
  cuRace alone : the collector-only recordings of store final-2026-11-co, setting S2 of
      eval/co-chain-b: sync_dominance.analyze(chain_closure=True, co_async=True, co_r3="off") on
      every kernel JSON (the keywords run_cuvein._analyze_reports passes for `--chain-closure
      --co-async --co-r3 off`), written to a new path.

  collect  one JSON per collector-only program under --out/co (child processes, wall and memory cap)
  names    the kernel names of every vector-clock recording of the population (head of each kernel
           JSON), for the "launched kernels" of Table 3        -> --out/names.json
  bclass   part B: the pairs the vector clock reports and the scalar clock orders through R3, each
           classified F2-acq / F2-rel / F1 / other from the recording's hb_rmw_points and
           HBGraph.fenced()                                    -> --out/b/<id>.json
  report   eval/PAIRS_PER_TIER.md and eval/results/pairs-per-tier/pairs.csv

    .venv python eval/baselines/pairs_per_tier.py collect --workers 16
    .venv python eval/baselines/pairs_per_tier.py report
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

CO = "collector-only"
CO_STORE = f"{lc.BEEGFS}/final-2026-11-co"
RW_STORE = f"{lc.BEEGFS}/realworld-2026-10-co"   # the collector-only recordings of the same targets
OUT = f"{APH}/eval/results/pairs-per-tier"
MP_AFTER = f"{APH}/eval/results/r1-distance/mode-pairs-after"
MD = f"{APH}/eval/PAIRS_PER_TIER.md"
SEV = {"RACE": 2, "SC": 1, "ORDERED": 0}
EXCLUDE_SUITES = ("P3",)
M2 = (("cccl-3-buggy", 0x80, 0xad90), ("raft-1-buggy", 0x2df0, 0x60a0),
      ("raft-1-fixed", 0x2df0, 0x60d0), ("kokkos-5-buggy", 0xbc0, 0xc90),
      ("kokkos-5-fixed", 0xbd0, 0xca0))


def excluded(_id, suite):
    return suite in EXCLUDE_SUITES or "canary" in _id.lower()


def co_ok(meta, pdir):
    md = meta.get("modes", {}).get(CO)
    if not md:
        return False, "no collector-only mode in meta"
    if meta.get("status") == "collecting":
        return False, "collection-interrupted"
    if not md.get("saved"):
        return False, "unsaved"
    if md.get("partial"):
        return False, "partial"
    if not glob.glob(f"{pdir}/{CO}/kernel_*.json"):
        return False, "no-kernel-json"
    return True, ""


# ---------------------------------------------------------------- the worker


def worker(pdir, out):
    import sync_dominance as sd
    meta = json.load(open(f"{pdir}/meta.json"))
    dots = sorted(glob.glob(f"{pdir}/dots/*.dot"))
    t0 = time.time()
    pairs = {}                      # (kernel, a, b) -> record of the worst verdict over launches
    unaligned, kernels, knames = [], 0, set()
    for kj in sorted(glob.glob(f"{pdir}/{CO}/kernel_*.json")):
        rep = None
        for dot in dots:
            try:
                rep = sd.analyze(dot, kj, chain_closure=True, co_async=True, co_r3="off")
                break
            except sd.AlignmentError:
                continue
        if rep is None:
            unaligned.append(os.path.basename(kj))
            continue
        kernels += 1
        name = rep["kernel"]["name"]
        knames.add(name)
        skip = {}
        for s in rep["skipped_edges"]:
            if s.get("ancient_pc") is not None:
                skip.setdefault((name, min(s["current_pc"], s["ancient_pc"]),
                                 max(s["current_pc"], s["ancient_pc"])), set()).add(s["reason"])
        for k, rs in skip.items():
            pairs.setdefault(k, {"skipped": set()})["skipped"] |= rs
        for v in rep["verdicts"]:
            cur, anc = v["current_pc"], v["ancient_pc"]
            k = (name, min(cur, anc), max(cur, anc))
            src = "chain" if v.get("chain") else "chain_rescue" if v.get("chain_rescue") else "edge"
            r1 = sd.SCOPES.index(v["strength"]) >= sd.SCOPES.index(v["observed_distance"])
            rec = {"verdict": v["verdict"], "class": v.get("matrix_class"),
                   "conflict_class": v.get("conflict_class"), "source": src,
                   "r1": r1, "r3": v["hb_chain"] is not None, "strength": v["strength"],
                   "observed": v["observed_distance"], "space": v["space"],
                   "event_candidate": bool(v.get("event_candidate")),
                   "kernel_file": os.path.basename(kj), "skipped": set()}
            old = pairs.get(k)
            if old is None or "verdict" not in old or SEV[rec["verdict"]] > SEV[old["verdict"]]:
                if old:
                    rec["skipped"] = old["skipped"]
                pairs[k] = rec
            elif rec["verdict"] == "ORDERED" and old["verdict"] == "ORDERED":
                old["r1"] = old["r1"] or rec["r1"]
                old["r3"] = old["r3"] or rec["r3"]
    rows = []
    for (n, a, b), r in sorted(pairs.items()):
        r = dict(r, skipped=sorted(r["skipped"]))
        rows.append([n, a, b, r])
    res = {"id": meta.get("id"), "pset": meta.get("pset"), "pdir": pdir, "status": "ok",
           "wall_s": round(time.time() - t0, 2), "kernels": kernels, "unaligned": unaligned,
           "pairs": rows}
    tmp = out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(res, f)
    os.replace(tmp, out)


def cmd_collect(a):
    import glob as g
    roots = [CO_STORE] + ([RW_STORE] if a.with_rw else [])
    todo, notes = [], {}
    for root in roots:
        for pdir in sorted(g.glob(f"{root}/*/")):
            pdir = pdir.rstrip("/")
            try:
                meta = json.load(open(f"{pdir}/meta.json"))
            except (OSError, ValueError):
                continue
            _id = meta.get("id") or os.path.basename(pdir)
            ok, why = co_ok(meta, pdir)
            if ok:
                todo.append((_id, pdir, meta.get("pset")))
            else:
                notes[_id] = why
    os.makedirs(f"{a.out}/co", exist_ok=True)
    with open(f"{a.out}/co_sources.json", "w") as f:
        json.dump({"stores": roots, "n": len(todo), "not_available": notes}, f, indent=0)
    if a.limit:
        todo = todo[::max(1, len(todo) // a.limit)][:a.limit]
    memb = int(a.mem_gb * 2**30)

    def lim():
        resource.setrlimit(resource.RLIMIT_AS, (memb, memb))

    def one(t):
        _id, pdir, pset = t
        out = f"{a.out}/co/{_id}.json"
        if os.path.exists(out) and not a.force:
            if not a.retry or json.load(open(out)).get("status") == "ok":
                return f"{_id} exists"
        t0 = time.time()
        try:
            p = subprocess.run([sys.executable, __file__, "_worker", pdir, out],
                               preexec_fn=lim, timeout=a.timeout, capture_output=True, text=True)
            status = "ok" if p.returncode == 0 and os.path.exists(out) else \
                ("analysis-oom" if "MemoryError" in p.stderr else f"error(rc={p.returncode})")
            err = p.stderr[-800:]
        except subprocess.TimeoutExpired:
            status, err = f"analysis-timeout={a.timeout}s", ""
        if status != "ok":
            with open(out, "w") as f:
                json.dump({"id": _id, "pset": pset, "pdir": pdir, "status": status, "stderr": err}, f)
        return f"{_id} {status} {time.time() - t0:.1f}s"
    print(f"{len(todo)} collector-only programs, {a.workers} workers", flush=True)
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for line in ex.map(one, todo):
            print(line, flush=True)


# ---------------------------------------------------------------- names (part A)

import re  # noqa: E402

_KN = re.compile(rb'"kernel_name"\s*:\s*("(?:[^"\\]|\\.)*")')


def kernel_name_of(path):
    with open(path, "rb") as f:
        head = f.read(1 << 16)
    m = _KN.search(head)
    if m:
        return json.loads(m.group(1))
    return json.load(open(path))["kernel"]["kernel_name"]


def cmd_names(a):
    sel = json.load(open(f"{a.mp_after}/sources.json"))["selected"]
    out = {}
    ids = [k.split("|")[0] for k in sel if k.endswith("|" + lc.VC)] if any("|" in k for k in sel) else list(sel)
    pdirs = {(k.split("|")[0] if "|" in k else k): v["pdir"] for k, v in sel.items()
             if ("|" not in k) or k.endswith("|" + lc.VC)}

    def one(i):
        names = set()
        for kj in glob.glob(f"{pdirs[i]}/{lc.VC}/kernel_*.json"):
            try:
                names.add(kernel_name_of(kj))
            except Exception as e:   # noqa: BLE001
                names.add(f"<unreadable {os.path.basename(kj)}: {type(e).__name__}>")
        return i, sorted(names)
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for i, n in ex.map(one, sorted(pdirs)):
            out[i] = n
    os.makedirs(a.out, exist_ok=True)
    json.dump(out, open(f"{a.out}/names.json", "w"))
    print(f"names of {len(out)} vector-clock recordings")


# ---------------------------------------------------------------- bclass (part B)

SCOPES = ["none", "warp", "block", "grid"]


def b_population(mp):
    """{id: {(kernel, a, b): kind}} of the pairs the vector clock reports (kind race / sc, worst over
    launches) and the scalar clock orders through R3 (verdict ORDERED, hb_chain set, not R1, not
    barrier-ordered) in some launch -- M1's attribution (a)."""
    pop = {}
    for i, pr in mp.items():
        for k, m in pr.items():
            hit = any(v[0] in ("RACE", "SC") and s[0] == "ORDERED" and s[1] != "barrier-ordered"
                      and s[3] and not s[2] for v in m["vc"] for s in m["sc"])
            if hit:
                pop.setdefault(i, {})[k] = kind_of([v[0] for v in m["vc"]])
    return pop


def b_files(d, i):
    """first kernel file of every mode_pairs tuple of program i that meets the population rule."""
    j = json.load(open(f"{d}/detail/{i}.json"))
    out = set()
    for n, a, b, tuples in j["pairs"]:
        for t in tuples:
            if t[0] in ("RACE", "SC") and t[5] == "ORDERED" and t[6] != "barrier-ordered" and t[8] and not t[7]:
                out.add(t[11])
    return sorted(out)


def bworker(pdir, _id, out, wanted_json, with_sass, files_json=None):
    import sync_dominance as sd
    wanted = {(n, a, b) for n, a, b in json.load(open(wanted_json))}
    cap = {}

    class _J:                                  # shadows sync_dominance's `json` name
        def __getattr__(self, k):
            return getattr(json, k)

        def loads(self, s):
            t = json.loads(s)
            cap["hb_races"] = t.get("hb_races")
            t.pop("hb_races", None)            # the scalar-clock pass: a recording without them
            t.pop("hb_races_sync_only", None)
            cap["trace"] = t
            return t

    class _G(sd.HBGraph):
        def __init__(self, *a):
            super().__init__(*a)
            cap["eng"] = self
            cap["calls"] = {}

        def ordered(self, cur, anc, d, cur_read, anc_read, static=True):
            r = super().ordered(cur, anc, d, cur_read, anc_read, static)
            if not getattr(self, "r3_cfg_only", False):
                cap["calls"][(cur, anc)] = (d, bool(static), r["strength"])
            return r

    sd.json, sd.HBGraph = _J(), _G
    meta = json.load(open(f"{pdir}/meta.json"))
    dots = sorted(glob.glob(f"{pdir}/dots/*.dot"))
    only = set(json.load(open(files_json))) if files_json else None
    res = {"id": _id, "pset": meta.get("pset"), "status": "ok", "pairs": {}, "unaligned": [],
           "launches_analysed": "all kernel JSONs" if only is None else sorted(only)}
    for kj in sorted(glob.glob(f"{pdir}/{lc.VC}/kernel_*.json")):
        if only is not None and os.path.basename(kj) not in only:
            continue
        rep = None
        for dot in dots:
            try:
                rep = sd.analyze(dot, kj)
                break
            except sd.AlignmentError:
                continue
        if rep is None:
            res["unaligned"].append(os.path.basename(kj))
            continue
        name, eng, tr = rep["kernel"]["name"], cap["eng"], cap["trace"]
        for v in rep["verdicts"]:
            cur, anc = v["current_pc"], v["ancient_pc"]
            key = (name, min(cur, anc), max(cur, anc))
            if key not in wanted or v["verdict"] != "ORDERED" or v["hb_chain"] is None:
                continue
            d, _, strength = cap["calls"].get((cur, anc), (None, None, None))
            if d is None or sd.SCOPES.index(v["strength"]) >= d:
                continue                                   # ordered by R1 in this launch
            # the direction the rule used: chain(anc, cur) first, else chain(cur, anc)
            if eng.chain(anc, cur) is not None:
                x, y = anc, cur
            elif eng.chain(cur, anc) is not None:
                x, y = cur, anc
            else:
                x = y = None
            rec = {"launch": os.path.basename(kj), "distance": SCOPES[d], "chain": v["hb_chain"],
                   "dir": None if x is None else [hex(x), hex(y)],
                   "release_points_present": eng.release_points is not None,
                   "acquire_points_present": eng.acquire_points is not None,
                   "has_hb_rmw_points": "hb_rmw_points" in tr}
            if x is not None:
                rec["x_is_rmw"], rec["y_is_rmw"] = x in eng.atom, y in eng.atom
                rp = None if eng.release_points is None or x in eng.atom else eng.release_points.get(x)
                ap = None if eng.acquire_points is None or y in eng.atom else eng.acquire_points.get(y)
                rec["release_points"] = None if rp is None else [hex(p) for p in sorted(rp)]
                rec["acquire_points"] = None if ap is None else [hex(p) for p in sorted(ap)]
                rec["release_fenced"] = None if not rp else [bool(eng.fenced(x, p, d, "rel")) for p in sorted(rp)]
                rec["acquire_fenced"] = None if not ap else [bool(eng.fenced(p, y, d, "acq")) for p in sorted(ap)]
            if cap["hb_races"] is not None:
                rr = [r for r in cap["hb_races"] if frozenset((r["a_pc"], r["b_pc"])) == frozenset(key[1:])]
                rec["hb_races"] = [{"a": [r["a_tid"] >> 10, (r["a_tid"] >> 5) & 31, r["a_tid"] & 31],
                                    "b": [r["b_tid"] >> 10, (r["b_tid"] >> 5) & 31, r["b_tid"] & 31],
                                    "distance": SCOPES[sd.thread_distance(r["a_tid"], r["b_tid"])],
                                    "class": r.get("class"), "count": r.get("count")} for r in rr[:50]]
            if with_sass and "sass" not in res:
                pcs = sorted(eng.pc_opcode)
                want = {key[1], key[2]} | {int(p, 16) for p in v["hb_chain"]}
                keep = set()
                for p in want:
                    i0 = pcs.index(p) if p in pcs else None
                    if i0 is not None:
                        keep.update(pcs[max(0, i0 - 6):i0 + 7])
                res["sass"] = [[hex(p), eng.pc_opcode[p]] for p in sorted(keep)]
                res["dot"] = dot
            res["pairs"].setdefault("|".join([name, hex(key[1]), hex(key[2])]), []).append(rec)
    json.dump(res, open(out, "w"))


def classify_b(recs):
    """pair-level class from its launch records -> (set of classes, sorted reasons).
    Each side is judged on its own: rmw (the endpoint is itself an RMW: no recorded point), nopoint,
    ok (fenced at every recorded point), bad (some recorded point unfenced). F2-rel / F2-acq when that
    side is bad; F1 when both sides are ok; otherwise other. Over launches: any F2 wins, else F1 only
    if every launch is F1, else other."""
    per, why = [], set()
    for r in recs:
        if r["dir"] is None:
            per.append({"other"}); why.add("chain direction not reproduced"); continue
        if not r["has_hb_rmw_points"]:
            per.append({"other"}); why.add("missing field hb_rmw_points in the recording"); continue
        rel, acq = r.get("release_fenced"), r.get("acquire_fenced")
        rs = "rmw" if r["x_is_rmw"] else ("nopoint" if not rel else ("ok" if all(rel) else "bad"))
        as_ = "rmw" if r["y_is_rmw"] else ("nopoint" if not acq else ("ok" if all(acq) else "bad"))
        c = set()
        if rs == "bad":
            c.add("F2-rel")
        if as_ == "bad":
            c.add("F2-acq")
        if not c:
            if rs == "ok" and as_ == "ok":
                c.add("F1")
            else:
                c.add("other")
                why.add(f"release side {rs}, acquire side {as_}")
        per.append(c)
    f2 = set().union(*[c for c in per if c & {"F2-rel", "F2-acq"}]) if any(
        c & {"F2-rel", "F2-acq"} for c in per) else set()
    if f2:
        return f2 & {"F2-rel", "F2-acq"}, sorted(why)
    return ({"F1"} if all(c == {"F1"} for c in per) else {"other"}), sorted(why)


def cmd_bclass(a):
    mp, _ = load_mp(a.mp_after)
    pop = b_population(mp)
    sel = json.load(open(f"{a.mp_after}/sources.json"))["selected"]
    pdirs = {(k.split("|")[0] if "|" in k else k): v["pdir"] for k, v in sel.items()
             if ("|" not in k) or k.endswith("|" + lc.VC)}
    os.makedirs(f"{a.out}/b", exist_ok=True)
    json.dump({i: [[n, x, y, kd] for (n, x, y), kd in p.items()] for i, p in pop.items()},
              open(f"{a.out}/b_population.json", "w"))
    memb = int(a.mem_gb * 2**30)

    def lim():
        resource.setrlimit(resource.RLIMIT_AS, (memb, memb))

    def one(i):
        out = f"{a.out}/b/{i}.json"
        wj = f"{a.out}/b/{i}.wanted.json"
        json.dump([[n, x, y] for (n, x, y) in pop[i]], open(wj, "w"))
        if os.path.exists(out) and not a.force and json.load(open(out)).get("status") == "ok":
            return f"{i} exists"
        nk = len(glob.glob(f"{pdirs[i]}/{lc.VC}/kernel_*.json"))
        fj = ""
        if nk > a.max_launches:               # programs with very many launches: the recorded first launch of each tuple
            fj = f"{a.out}/b/{i}.files.json"
            json.dump(b_files(a.mp_after, i), open(fj, "w"))
        try:
            p = subprocess.run([sys.executable, __file__, "_bworker", pdirs[i], i, out, wj,
                                "1" if "hrd-indirect" in i else "0"] + ([fj] if fj else []), preexec_fn=lim,
                               timeout=a.timeout, capture_output=True, text=True)
            st = "ok" if p.returncode == 0 and os.path.exists(out) else \
                ("analysis-oom" if "MemoryError" in p.stderr else f"error(rc={p.returncode}): {p.stderr[-300:]}")
        except subprocess.TimeoutExpired:
            st = f"analysis-timeout={a.timeout}s"
        if st != "ok":
            json.dump({"id": i, "status": st}, open(out, "w"))
        return f"{i} {st}"
    print(f"{len(pop)} programs with population pairs, {sum(len(p) for p in pop.values())} pairs", flush=True)
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for line in ex.map(one, sorted(pop)):
            print(line, flush=True)


# ---------------------------------------------------------------- report


def kind_of(verdicts):
    """worst class of a pair over its launches: 'race', 'sc' or None."""
    if "RACE" in verdicts:
        return "race"
    if "SC" in verdicts:
        return "sc"
    return None


def _md(head, rows):
    o = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    o += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(o)


def load_mp(d):
    """-> {id: {(kernel, a, b): {"vc": [tuples], "sc": [tuples]}}} and {id: status}."""
    out, st = {}, {}
    for f in glob.glob(f"{d}/detail/*.json"):
        try:
            j = json.load(open(f))
        except ValueError:
            continue
        st[j["id"]] = j
        if j.get("status") != "ok":
            continue
        pr = {}
        for n, a, b, tuples in j["pairs"]:
            pr[(n, a, b)] = {"vc": [t[0:5] for t in tuples if t[0]],
                             "sc": [t[5:10] for t in tuples if t[5]]}
        out[j["id"]] = pr
    return out, st


def cause_sc_only(sc_tuples, co):
    """why cuRace alone does not report a pair the scalar clock reports -> (cause, detail)."""
    if co is None or "verdict" not in co:
        if co is not None and co.get("skipped"):
            return "c", "edge skipped: " + "/".join(co["skipped"])
        return "a", "no verdict record (no recorded edge, no chain joins the pair)"
    if co["verdict"] == "ORDERED" and co["r1"]:
        return "b", f"ORDERED by R1 (strength {co['strength']} >= observed {co['observed']})"
    if co["verdict"] == "ORDERED":
        return "c", f"ORDERED by {'R3 chain' if co['r3'] else 'no certificate'} ({co['class']})"
    return "c", f"cuRace alone {co['verdict']}/{co['class']} (kind differs)"


def cause_co_only(sc_tuples, co):
    """why only cuRace alone reports a pair -> (cause, detail)."""
    if not sc_tuples:
        if co["source"] in ("chain", "chain_rescue"):
            return "derived", f"closure ({co['source']}), pair not a scalar-clock candidate"
        return "other", "recorded edge, pair not a scalar-clock candidate"
    if all(t[0] == "ORDERED" and t[1] == "barrier-ordered" for t in sc_tuples):
        return "barrier", "scalar clock: ORDERED, barrier-ordered in every instance"
    return "other", "scalar clock: " + "/".join(sorted({f"{t[0]}/{t[1]}" for t in sc_tuples}))


def cmd_report(a):
    mp, mpst = load_mp(a.mp_after)
    co_det = {}
    for f in glob.glob(f"{a.out}/co/*.json"):
        try:
            j = json.load(open(f))
        except ValueError:
            continue
        co_det[j["id"]] = j
    src = json.load(open(f"{a.out}/co_sources.json")) if os.path.exists(f"{a.out}/co_sources.json") else {}
    pset = {}
    for i, j in co_det.items():
        pset[i] = (mpst.get(i) or {}).get("pset") or j.get("pset") or i.split("-")[0]
    pop, left = {}, defaultdict(Counter)
    for i, j in sorted(co_det.items()):
        s = pset[i]
        if excluded(i, s):
            left[s]["excluded (P3 / canary)"] += 1
        elif j["status"] != "ok":
            left[s]["no collector-only result: " + j["status"].split("=")[0]] += 1
        elif i not in mp:
            st = (mpst.get(i) or {}).get("status", "no mode_pairs file")
            left[s]["no vector-/scalar-clock result: " + st.split("=")[0].split(":")[0]] += 1
        else:
            pop[i] = s
    names = json.load(open(f"{a.out}/names.json")) if os.path.exists(f"{a.out}/names.json") else None
    bpop = json.load(open(f"{a.out}/b_population.json")) if os.path.exists(f"{a.out}/b_population.json") else None
    bres = {}
    for f in glob.glob(f"{a.out}/b/*.json"):
        if f.endswith((".wanted.json", ".files.json")):
            continue
        try:
            j = json.load(open(f))
        except ValueError:
            continue
        if j.get("status") != "ok":
            bres[(j["id"], None)] = j["status"]
            continue
        bres[(j["id"], "sass")] = (j.get("sass"), j.get("dot"))
        for key, recs in j["pairs"].items():
            n, x, y = key.rsplit("|", 2)
            bres[(j["id"], n, int(x, 16), int(y, 16))] = (classify_b(recs), recs)
    rows, T1, T2 = [], defaultdict(Counter), defaultdict(Counter)
    ex = defaultdict(list)
    kern = {}                        # id -> {cfg: {"race": set, "any": set}}, universe, kernel -> pairs
    for i, s in sorted(pop.items()):
        T1[s]["programs"] += 1
        cop = {(n, a_, b): r for n, a_, b, r in co_det[i]["pairs"]}
        keys = set(cop) | set(mp[i])
        kk_ = {c: {"race": set(), "any": set()} for c in ("co", "sc", "vc")}
        kpairs = defaultdict(list)
        uni = set(co_det[i].get("kernel_names", [])) | set((names or {}).get(i, []))
        for k in sorted(keys):
            c = cop.get(k)
            m = mp[i].get(k, {"vc": [], "sc": []})
            ck = kind_of([c["verdict"]]) if c and "verdict" in c else None
            sk = kind_of([t[0] for t in m["sc"]])
            vk = kind_of([t[0] for t in m["vc"]])
            for nm, kk in (("co", ck), ("sc", sk), ("vc", vk)):
                if kk:
                    kk_[nm]["any"].add(k[0])
                if kk == "race":
                    kk_[nm]["race"].add(k[0])
            uni.add(k[0])
            kpairs[k[0]].append((k[1], k[2], ck, sk, vk))
            for kind, col in (("race", "r"), ("sc", "s")):
                for nm, kk in (("co", ck), ("sc", sk), ("vc", vk)):
                    if kk == kind:
                        T1[s][f"{nm}_{kind}"] += 1
                both, onlyco, onlysc = ck == kind and sk == kind, ck == kind and sk != kind, \
                    sk == kind and ck != kind
                if both:
                    T2[s][f"both_{kind}"] += 1
                if onlyco:
                    T2[s][f"co_only_{kind}"] += 1
                    cz, det = cause_co_only(m["sc"], c)
                    T2[s][f"co_only_{kind}_{cz}"] += 1
                    ex[(kind, "co_only", cz)].append((i, k, det))
                if onlysc:
                    T2[s][f"sc_only_{kind}"] += 1
                    cz, det = cause_sc_only(m["sc"], c)
                    T2[s][f"sc_only_{kind}_{cz}"] += 1
                    ex[(kind, "sc_only", cz)].append((i, k, det))
            if ck or sk or vk:
                bc = bres.get((i,) + k)
                if bpop is not None and any(x[0] == k[0] and x[1] == k[1] and x[2] == k[2]
                                            for x in bpop.get(i, [])):
                    bcls = ("+".join(sorted(bc[0][0])) if bc else
                            ("missing: " + str(bres[(i, None)]) if (i, None) in bres else
                             "other (no launch record reproduces R3-not-R1)"))
                else:
                    bcls = ""
                rows.append({"suite": s, "id": i, "kernel": k[0], "pc_a": hex(k[1]), "pc_b": hex(k[2]),
                             "curace_alone": (f"{c['verdict']}/{c['class']}/{c['source']}" if c and "verdict" in c
                                              else ("none" if not c else "skipped:" + "/".join(c["skipped"]))),
                             "scalar_clock": "/".join(sorted({f"{t[0]}/{t[1]}" for t in m["sc"]})) or "none",
                             "vector_clock": "/".join(sorted({f"{t[0]}/{t[1]}" for t in m["vc"]})) or "none",
                             "curace_kind": ck or "", "scalar_kind": sk or "", "vector_kind": vk or "",
                             "r3_class": bcls})
        kern[i] = {"cfg": kk_, "uni": uni, "pairs": kpairs}
    os.makedirs(a.out, exist_ok=True)
    with open(f"{a.out}/pairs.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]) if rows else ["suite"])
        w.writeheader()
        w.writerows(rows)
    suites = sorted(T1)
    tot = Counter()
    for s in suites:
        tot.update(T1[s])
    tot2 = Counter()
    for s in suites:
        tot2.update(T2[s])

    def t1row(s, c):
        return [s, c["programs"]] + [c[f"{n}_{k}"] for k in ("race", "sc") for n in ("co", "sc", "vc")]
    md = ["# M4: reported pairs per configuration, one counting unit", "",
          "Commands (repository root `~/wt-m2`, branch `study/r1-distance`, `.env/bin/python` of AccelProf, partition `normal`): "
          "`pairs_per_tier.py collect --workers 16 [--with-rw --retry]` (jobs 334254, 334293, 334508; "
          "`CUVEIN_DOT_PREFILTER=1` for the last, which re-ran the real-world ids and the failed ones), `pairs_per_tier.py names` "
          "(job 334254), `pairs_per_tier.py bclass` (jobs 335307, 335317, 335319, 335436), `pairs_per_tier.py report` (job 335436). "
          "The sources are the after state of `eval/R1_DISTANCE.md` (`eval/results/r1-distance/mode-pairs-after/`, fix/r1-at-widest-distance 886b6bf5). "
          "The page limit of the first brief is exceeded: Tables 1-2 and the cause splits are first, parts A and B follow.", "",
          "Unit: (kernel name, unordered pc pair), launches merged, a pair under its worst class (data race = verdict RACE, strong "
          "conflict = verdict SC, RACE over SC). **cuRace alone** = collector-only recordings, setting S2 (`analyze(chain_closure=True, "
          "co_async=True, co_r3=\"off\")`, the keywords `run_cuvein._analyze_reports` passes for `--chain-closure --co-async --co-r3 off`), "
          "re-scored here into `eval/results/pairs-per-tier/co/`: store `final-2026-11-co` for the benchmark suites and "
          "`realworld-2026-10-co` for the real-world targets (C2's `-n 1` collector-only recordings, the same recording generation as the "
          "`realworld-2026-10` clock-mode store M3 re-scored; the `-n 16` re-recordings `realworld-2026-11-co-sh` were not used: X12 found "
          "them equal to C2's). `merged-s2` of eval/co-chain-b has no per-pair output and no real-world ids, so it was not used. "
          "**Scalar clock / vector clock** = the per-pair output of `mode_pairs.py` in M3's after state (the scalar-clock pass is the "
          "vector-clock recording without `hb_races`). M3 changed 9 pair rows (5 real-world pairs of the vector-clock pass lost `model_bug`, 4 real-world "
          "pairs of the scalar-clock recordings went ORDERED to RACE; `eval/results/r1-distance/changes.csv`); the five pairs of M2 are among them. "
          "Population: programs with a result in all three configurations; P3 (ECL) and the canary program left out (counts in `Left out`). "
          "Real-world T21c (`realworld-2026-10-t21c`): M3's after state has no clock-mode result for it (M1's store list has only `realworld-2026-10`), "
          "so T21c is not in the population, and its collector-only store `realworld-2026-10-t21c-co` was not scored.", "",
          "## Table 1: pairs per suite", "",
          _md(["suite", "programs", "data races: cuRace alone", "scalar clock", "vector clock",
               "strong conflicts: cuRace alone", "scalar clock", "vector clock"],
              [t1row(s, T1[s]) for s in suites] + [t1row("all", tot)]), "",
          "## Table 2: cuRace alone against the scalar clock", ""]
    for kind, nm in (("race", "data races"), ("sc", "strong conflicts")):
        md += [f"### {nm}", "",
               _md(["suite", "in both", "only cuRace alone", "only scalar clock",
                    "scalar-only (a)", "(b)", "(c)", "co-only: barrier-ordered", "derived", "other"],
                   [[s, T2[s][f"both_{kind}"], T2[s][f"co_only_{kind}"], T2[s][f"sc_only_{kind}"],
                     T2[s][f"sc_only_{kind}_a"], T2[s][f"sc_only_{kind}_b"], T2[s][f"sc_only_{kind}_c"],
                     T2[s][f"co_only_{kind}_barrier"], T2[s][f"co_only_{kind}_derived"],
                     T2[s][f"co_only_{kind}_other"]] for s in suites] +
                   [["all", tot2[f"both_{kind}"], tot2[f"co_only_{kind}"], tot2[f"sc_only_{kind}"],
                     tot2[f"sc_only_{kind}_a"], tot2[f"sc_only_{kind}_b"], tot2[f"sc_only_{kind}_c"],
                     tot2[f"co_only_{kind}_barrier"], tot2[f"co_only_{kind}_derived"],
                     tot2[f"co_only_{kind}_other"]]]), ""]
    md += ["### Only with the scalar clock: causes (a) no recorded edge and no chain joins the pair "
           "(no verdict record in cuRace alone); (b) cuRace alone certifies it by R1; (c) other. "
           "Only in cuRace alone: barrier clock ordered it in every recorded instance; derived by the "
           "closure (chain or rescue) and not a scalar-clock candidate; other.", ""]
    for (kind, side, cz), lst in sorted(ex.items()):
        cnt = Counter(d for _, _, d in lst)
        md += [f"- {kind} / {side} / {cz}: {len(lst)} pairs; data: " +
               "; ".join(f"{d} x{n}" for d, n in cnt.most_common(4)),
               "  examples: " + " | ".join(f"{i} {k[0][:50]} {hex(k[1])}/{hex(k[2])}" for i, k, _ in lst[:10])]

    # ------------------------------------------------------------ part A
    try:
        import make_tables as mt
        man = mt.load_manifest()
        exe_of = {i: (man.get(i) or {}).get("exe") or i for i in pop}
    except Exception as e:   # noqa: BLE001
        man, exe_of = None, None
        exe_note = f"missing: make_tables.load_manifest failed ({type(e).__name__})"

    def t3(units, key):
        """units: {(suite, unit): {"uni": bool, "co": bool, "sc": bool, "vc": bool}} -> rows."""
        out = {}
        for (s, u), d in units.items():
            for sname in (s, "all"):
                c = out.setdefault(sname, Counter())
                c["kernels"] += 1
                for x in ("co", "sc", "vc"):
                    c[x] += d[x]
                c["co-sc"] += d["co"] and not d["sc"]
                c["sc-co"] += d["sc"] and not d["co"]
                c["sc-vc"] += d["sc"] and not d["vc"]
                c["vc-sc"] += d["vc"] and not d["sc"]
        return out

    def units_of(key, fold):
        u = {}
        for i, s in pop.items():
            for n in kern[i]["uni"]:
                uk = (s, (exe_of[i], n) if fold else (i, n))
                d = u.setdefault(uk, {"co": False, "sc": False, "vc": False})
                for c in ("co", "sc", "vc"):
                    d[c] = d[c] or n in kern[i]["cfg"][c][key]
        return u

    def t3md(key, fold):
        o = t3(units_of(key, fold), key)
        order = sorted(k for k in o if k != "all") + ["all"]
        return _md(["suite", "kernels", "cuRace alone", "scalar clock", "vector clock",
                    "cuRace not scalar", "scalar not cuRace", "scalar not vector", "vector not scalar"],
                   [[s, o[s]["kernels"], o[s]["co"], o[s]["sc"], o[s]["vc"], o[s]["co-sc"],
                     o[s]["sc-co"], o[s]["sc-vc"], o[s]["vc-sc"]] for s in order])

    md += ["## Part A: per kernel", "",
           "Unit: (program id, kernel name), launches folded; a kernel counts if some analysed launch of it "
           "exists in the collector-only recording or in the vector-clock recording (kernel names read from "
           "the head of each kernel JSON; " + ("`names.json` present" if names is not None else
                                                "missing: names.json, only kernels with a pair counted") +
           "). Reported = at least one of its pairs is a data race in that configuration.", "",
           "### Table 3: data races", "", t3md("race", False), "",
           "### Table 3 with strong conflicts counted as reports", "", t3md("any", False), ""]
    if exe_of is not None:
        md += ["### Table 3 on X13's unit (kernel of one binary, folded over the runs of the binary: "
               "units (executable of the manifest row, kernel name)); data races, then with strong conflicts", "",
               t3md("race", True), "", t3md("any", True), ""]
    else:
        md += [f"X13-unit variant not computed: {exe_note}", ""]

    def pairs_text(i, n, filt):
        out = []
        for x, y, ck, sk, vk in kern[i]["pairs"][n]:
            if filt(ck, sk, vk):
                out.append(f"{hex(x)}/{hex(y)} (cuRace {ck or '-'}, scalar {sk or '-'}, vector {vk or '-'})")
        return "; ".join(out[:6]) + (f" (+{len(out) - 6})" if len(out) > 6 else "")

    def klist(c1, c2, limit):
        L = []
        for i in sorted(pop):
            for n in sorted(kern[i]["uni"]):
                d = kern[i]["cfg"]
                if (n in d[c1]["race"]) != (n in d[c2]["race"]):
                    L.append((i, n))
        return L[:limit], len(L)
    ls, tot_sv = klist("sc", "vc", 10**9)
    md += [f"### Kernels (data-race reports) where the scalar clock and the vector clock differ: {tot_sv}", ""]
    md += [f"- {i} / {n[:70]}: " + pairs_text(i, n, lambda c, s_, v: (s_ == "race") != (v == "race"))
           for i, n in ls] or ["none"]
    lc2, tot_cs = klist("co", "sc", 20)
    md += ["", f"### Kernels where cuRace alone and the scalar clock differ: {tot_cs} (first 20 listed)", ""]
    md += [f"- {i} / {n[:70]}: " + pairs_text(i, n, lambda c, s_, v: (c == "race") != (s_ == "race"))
           for i, n in lc2] or ["none"]
    md += ["", "### Kernel unit against X13", "",
           "X13 (`eval/baselines/per_kernel/kfold.py` and `eval/PER_KERNEL_TABLES.md` on "
           "origin/eval/per-kernel-tables 99e1c32d, read with `git show`, not in this checkout): a "
           "kernel is one `__global__` function (one template instantiation) of one *binary*; its "
           "verdict folds every launch of every run (manifest id) of that binary; a kernel no run "
           "launched is not counted. Table 3 above is per (program id, kernel); the folded variant "
           "(units (exe, kernel name)) is the same unit as X13 up to the kernel-name string (X13's key "
           "is its own inventory name; this one is the recording's `kernel_name`), and the "
           "`launched` rule differs: X13 counts kernels launched in a *finished* run in any tool/mode, "
           "this one counts kernels with a kernel JSON in the collector-only or vector-clock "
           "recording of the population. Not checked: that the two name strings agree kernel by kernel.", ""]

    # ------------------------------------------------------------ part B
    md += ["## Part B: pairs the vector clock reports and the scalar clock orders through R3", ""]
    if bpop is None:
        md += ["missing: b_population.json (bclass step not run)", ""]
    else:
        def bkey(i, p):
            return (i,) + tuple(p[:3])
        T4 = defaultdict(Counter)
        perprog = defaultdict(Counter)
        for i, plist in bpop.items():
            if i not in pop:
                continue
            s = pop[i]
            for n, x, y, kind in plist:
                for tgt, key in ((T4[(s, kind)], None), (T4[("all", kind)], None), (perprog[(i, kind)], None)):
                    tgt["pairs"] += 1
                bc = bres.get((i, n, x, y))
                cls = bc[0][0] if bc else {"other"}
                for tgt in (T4[(s, kind)], T4[("all", kind)], perprog[(i, kind)]):
                    for c in cls:
                        tgt[c] += 1
                    if "F2-acq" in cls and "F2-rel" in cls:
                        tgt["overlap"] += 1
        def t4rows(kind):
            ss = sorted({s for (s, k) in T4 if k == kind and s != "all"}) + ["all"]
            return [[s] + [T4[(s, kind)][c] for c in ("pairs", "F2-acq", "F2-rel", "overlap", "F1", "other")]
                    for s in ss if (s, kind) in T4]
        for kind, nm in (("race", "data races"), ("sc", "strong conflicts")):
            md += [f"### Table 4: {nm}", "",
                   _md(["suite", "pairs in population", "F2-acq", "F2-rel", "of them both", "F1", "other"],
                       t4rows(kind)), ""]
        md += ["A pair that is both F2-acq and F2-rel is counted under each; `of them both` is the overlap. "
               "F1/other are counted once. The sum of the class columns is therefore at least the population.", ""]
        sel_ids = [i for i in sorted({k[0] for k in perprog})
                   if any(t in i for t in ("cccl-3", "raft-1", "hecbench-hungarian-1", "hrd-indirect"))]
        md += ["### Per program", "",
               _md(["program", "kind", "pairs", "F2-acq", "F2-rel", "both", "F1", "other"],
                   [[i, k, perprog[(i, k)]["pairs"], perprog[(i, k)]["F2-acq"], perprog[(i, k)]["F2-rel"],
                     perprog[(i, k)]["overlap"], perprog[(i, k)]["F1"], perprog[(i, k)]["other"]]
                    for i in sel_ids for k in ("race", "sc") if (i, k) in perprog]) if sel_ids else
               "none of cccl-3, raft-1, hecbench-hungarian-1, hrd-indirect has a population pair after M3", ""]
        reasons = Counter()
        for k, v in bres.items():
            if len(k) == 4:
                for w in v[0][1]:
                    reasons[w] += 1
        md += ["`other` reasons: " + ("; ".join(f"{w} x{n}" for w, n in reasons.items()) or "none recorded"), ""]
        hid = [i for i in bpop if "hrd-indirect" in i]
        md += ["### norace_interwarp-block_fence-atom_hrd-indirect", ""]
        if not hid:
            md += ["no population pair for this program after M3 (or program not in the population).", ""]
        for i in hid:
            md += [f"program {i}; pairs: " + "; ".join(f"{hex(x)}/{hex(y)} ({k})" for n, x, y, k in bpop[i]), ""]
            for key, v in sorted(bres.items(), key=lambda kv: str(kv[0])):
                if key[0] == i and len(key) == 4:
                    (cl, why), recs = v
                    for r in recs[:2]:
                        md += [f"- pair {hex(key[2])}/{hex(key[3])}: class {sorted(cl)}; direction {r['dir']}; "
                               f"distance {r['distance']}; release points {r.get('release_points')} fenced "
                               f"{r.get('release_fenced')}; acquire points {r.get('acquire_points')} fenced "
                               f"{r.get('acquire_fenced')}; chain {r['chain']}; hb_races records "
                               f"{[(x_['a'], x_['b'], x_['distance'], x_['class']) for x_ in r.get('hb_races', [])[:4]]}"]
            sass = bres.get((i, "sass"))
            if sass and sass[0]:
                md += ["", "SASS around the pair pcs and the chain pcs (from " + str(sass[1]) + "):", "```"]
                md += [f"{p}  {o}" for p, o in sass[0]]
                md += ["```", ""]
            srcp = "/home/fzheng4/AccelProf/ScoR/microbenchmarks/src/" + i.split("-", 1)[1] + ".cu"
            if os.path.exists(srcp):
                md += [f"source `{srcp}`:", "```"] + [ln.rstrip("\n") for ln in open(srcp)][:90] + ["```", ""]
            else:
                md += [f"source: missing ({srcp} not found)", ""]
        md += ["### What the classification used", "",
               "`sync_dominance.analyze()` on the scalar-clock pass (vector-clock recording with `hb_races` and "
               "`hb_races_sync_only` removed, as mode_pairs.py pass 2), M3's after state; the captured "
               "`HBGraph`: `release_points` / `acquire_points` (filled from the recording's `hb_rmw_points` by "
               "`aggregated_rmw_points` via `trace_rmw_points`), `atom`, `chain(anc, cur)` then `chain(cur, anc)` "
               "to find the direction the rule used, `fenced(p, q, s, side)` with `s` = the distance `ordered()` "
               "was asked at (logged by shadowing `HBGraph.ordered`), `pc_opcode`; `fence_scope` (the fence "
               "inventory by opcode: MEMBAR.SC/ALL.<scope>, CCTL.IVALL acquire side, BAR.SYNC/RED) is what "
               "`fenced` consults. Release side: for the recorded next-RMW points of the release endpoint, "
               "`fenced(u, a, d, 'rel')`; acquire side: for the recorded previous-RMW points of the acquire "
               "endpoint, `fenced(a, v, d, 'acq')`. Recording fields read: `hb_rmw_points`, `hb_sync_pass` (via "
               "`use_aggregates`), `hb_races` (thread ids, only for the block/warp of the hrd-indirect pairs). "
               "No new fence predicate was written.", ""]
    md += ["", "## The five M2 pairs (cuRace alone, S2, `realworld-2026-10-co`)", ""]
    rw = {i: j for i, j in co_det.items() if i in dict((x[0], 1) for x in M2)}
    m2 = []
    for i, x, y in M2:
        if i in rw and rw[i]["status"] == "ok":
            r = [p for n, a_, b, p in rw[i]["pairs"] if (a_, b) == (x, y)]
            m2.append([i, hex(x), hex(y)] + ([f"{r[0].get('verdict')}/{r[0].get('class')}/{r[0].get('source')}"]
                                             if r else ["not a candidate"]))
        else:
            m2.append([i, hex(x), hex(y), "missing: no collector-only result of this id"])
    md += [_md(["id", "pc", "pc", "cuRace alone S2"], m2), "",
           "## Left out", ""]
    noco = defaultdict(list)
    for i, pr in mp.items():
        s_ = (mpst.get(i) or {}).get("pset") or i.split("-")[0]
        if i not in co_det and not excluded(i, s_):
            noco[s_].append(i)
    for s_, ids in noco.items():
        left[s_]["no collector-only recording in the stores used (" + ", ".join(sorted(ids)[:12]) +
                 (", ..." if len(ids) > 12 else "") + ")"] += len(ids)
    md += [_md(["suite", "reason", "programs"], [[s, r, n] for s in sorted(left) for r, n in left[s].items()])
           if left else "none", "",
           "Real-world programs without a collector-only result in `realworld-2026-10-co` (X12 section 8.3 lists the known gaps: amrex-1 kept out, "
           "lightgbm-new-1/-2 and llamacpp-open-2 never recorded collector-only, colmap-new-1 buggy ERROR in the standard re-analysis) drop out of "
           "every column; so do the real-world programs whose clock-mode recording M3 could not use (`amrex-1`, `ginkgo-1`: unsaved / partial)."]
    open(a.md, "w").write("\n".join(md))
    print(f"wrote {a.md}, {a.out}/pairs.csv ({len(rows)} rows), population {len(pop)}")


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("collect")
    c.add_argument("--out", default=OUT)
    c.add_argument("--workers", type=int, default=16)
    c.add_argument("--with-rw", action="store_true")
    c.add_argument("--limit", type=int, default=0)
    c.add_argument("--force", action="store_true")
    c.add_argument("--retry", action="store_true", help="re-run the programs whose file is not status ok")
    c.add_argument("--timeout", type=int, default=3600)
    c.add_argument("--mem-gb", type=float, default=6)
    r = sp.add_parser("report")
    r.add_argument("--out", default=OUT)
    r.add_argument("--md", default=MD)
    r.add_argument("--mp-after", default=MP_AFTER)
    n = sp.add_parser("names")
    n.add_argument("--out", default=OUT)
    n.add_argument("--mp-after", default=MP_AFTER)
    n.add_argument("--workers", type=int, default=16)
    b = sp.add_parser("bclass")
    b.add_argument("--out", default=OUT)
    b.add_argument("--mp-after", default=MP_AFTER)
    b.add_argument("--workers", type=int, default=8)
    b.add_argument("--timeout", type=int, default=3600)
    b.add_argument("--mem-gb", type=float, default=20)
    b.add_argument("--max-launches", type=int, default=200)
    b.add_argument("--force", action="store_true")
    w = sp.add_parser("_worker")
    w.add_argument("pdir")
    w.add_argument("out")
    bw = sp.add_parser("_bworker")
    for x in ("pdir", "id", "out", "wanted", "sass"):
        bw.add_argument(x)
    bw.add_argument("files", nargs="?")
    a = ap.parse_args()
    if a.cmd == "_worker":
        worker(a.pdir, a.out)
    elif a.cmd == "_bworker":
        bworker(a.pdir, a.id, a.out, a.wanted, a.sass == "1", a.files)
    else:
        {"collect": cmd_collect, "report": cmd_report, "names": cmd_names,
         "bclass": cmd_bclass}[a.cmd](a)


if __name__ == "__main__":
    main()

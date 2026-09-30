#!/usr/bin/env python3
"""T9-0 latent census: how many labelled races only `latent` catches in the recorded
run, what the tier costs in false positives, and whether the hand-offs are fenced.

MEASUREMENT ONLY. The detector (python/sync_dominance.py, hb_oracle.py, the engine) is
run unchanged over the kept BeeGFS stores; this script only observes it:
  * HBGraph is subclassed to keep a handle on the kernel's graph (for the R3 decline
    reason and the fence adjacency of the hand-off atomics);
  * sync_dominance's `json` name is shadowed so the loaded dump can be kept and, for
    the same-trace variant, the engine's race keys (hb_races, hb_races_sync_only)
    removed -- exactly what a scalar-clock dump lacks (the collector writes neither key
    in that mode), so analyze() takes its scalar-clock path on the SAME recorded trace.

Phases (see eval/LATENT_CENSUS.md for the commands and the reading):

  collect  one JSON per (program, mode[, variant]) under --out: every verdict of every
           kernel (not only RACE: ordered / barrier-ordered too), the per-report
           dedup the harness applies (run_cuvein._analyze_reports), and for every pair
           without a static proof the R3 decline reason and the hand-off fence check.
           Runs on a CPU node (BeeGFS is not mounted on the login node); each program
           in a child process under a wall-clock and address-space cap.
  tables   CSV + Markdown from the collect output, labels from make_tables.load_manifest
           (+ the evcand manifest for ids the current manifest dropped, flagged), and
           the other tools' verdicts from the merged eval/results/baselines-*.csv that
           eval/BASELINES.md is generated from (make_tables.load_runs; nothing re-run).

    .env/bin/python eval/baselines/latent_census.py collect --shard 0/1
    .env/bin/python eval/baselines/latent_census.py tables
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
import hb_modes  # noqa: E402

VC, SC = hb_modes.VECTOR_CLOCK, hb_modes.SCALAR_CLOCK
BEEGFS = f"/mnt/beegfs/{os.environ.get('USER', 'fzheng4')}/cuvein_traces"
# later stores win: full-2026-09-22 re-collected (uncapped) programs evcand had dropped
DEFAULT_STORES = ("evcand", "full-2026-09-22")
DEFAULT_OUT = f"{APH}/eval/results/latent-census"
SAME = "sametrace"   # variant: the vector-clock dump analysed as scalar-clock
# hash of this script's collect code (everything above the tables marker), stamped into
# every detail file: a census regenerated from details written by different collect code is
# reported as such by `tables`; edits to the tables code do not change it
VERSION = __import__("hashlib").sha1(
    open(__file__, "rb").read().split(b"-" * 16 + b" tables\n")[0]).hexdigest()[:12]

# ---------------------------------------------------------------- store selection


def _mode_ok(meta, pdir, mode):
    """-> (ok, why). A mode counts only if its verdict-bearing dump is on disk: saved,
    not a partial (timed-out prefix), not dropped by a pre-T0 cap, collection finished,
    and at least one rep that reached its own exit."""
    md = meta.get("modes", {}).get(mode)
    if not md:
        return False, "missing"
    if meta.get("status") == "collecting":
        return False, "collection-interrupted"
    if not md.get("saved"):
        return False, "unsaved"
    if md.get("partial"):
        return False, "partial"
    td = meta.get("trace_dropped")
    if td and (td is True or mode in str(td)):
        return False, "trace-dropped"
    reps = md.get("reps", [])
    if reps and not any(r.get("complete", not r.get("timed_out")) for r in reps):
        return False, "no-complete-rep"
    if not glob.glob(f"{pdir}/{mode}/kernel_*.json"):
        return False, "no-kernel-json"
    return True, ""


def select_sources(stores):
    """-> ({(id, mode): {store, pdir, dump_mb}}, {(id, mode): why-not}) over the stores,
    later store first."""
    src, why = {}, {}
    for st in stores:
        root = st if os.path.isabs(st) else f"{BEEGFS}/{st}"
        for pdir in sorted(glob.glob(f"{root}/*/")):
            pdir = pdir.rstrip("/")
            try:
                meta = json.load(open(f"{pdir}/meta.json"))
            except (OSError, ValueError):
                continue
            _id = meta.get("id") or os.path.basename(pdir)
            for mode in (VC, SC):
                ok, w = _mode_ok(meta, pdir, mode)
                if ok:
                    mb = max([r.get("dump_mb") or 0 for r in meta["modes"][mode].get("reps", [])]
                             + [0])
                    src[(_id, mode)] = {"store": os.path.basename(root), "pdir": pdir,
                                        "dump_mb": mb, "pset": meta.get("pset")}
                    why.pop((_id, mode), None)
                elif (_id, mode) not in src:
                    why[(_id, mode)] = f"{os.path.basename(root)}:{w}"
    return src, why


# ---------------------------------------------------------------- the worker


def _fence_adjacent(blocks, edges, pc, forward, need):
    """The PTX gate of hb_proof.tex Definition "Gate", evaluated for one RMW pc on the
    kernel CFG: rel(r) (forward=False) iff, with the MEMBARs of scope >= need deleted, no
    memory pc other than r reaches r; acq(r) (forward=True) iff none is reachable from r.
    Walks every CFG path backward/forward from r: a MEMBAR of scope >= need ends the path
    (gated), a memory pc (sync_dominance._MEM_OPS) ends it ungated, r itself (a spin
    loop's retry) and anything else (ALU, branches, BAR, weaker fences, ERRBAR/CCTL) are
    transparent; reaching the kernel entry/exit without a memory pc is gated (vacuous).
    Used here only to CLASSIFY hand-offs; nothing feeds back into the verdicts."""
    import sync_dominance as sd
    where = {}
    for b, ins in blocks.items():
        for i, (p, _) in enumerate(ins):
            where[p] = (b, i)
    nxt = defaultdict(list)
    for s, d in edges:
        (nxt[s] if forward else nxt[d]).append(d if forward else s)
    seen = set()
    stack = [(where[pc][0], where[pc][1], True)]
    while stack:
        b, i, first = stack.pop()
        ins = blocks[b]
        idx = (range(i + 1, len(ins)) if first else range(len(ins))) if forward else \
            (range(i - 1, -1, -1) if first else range(len(ins) - 1, -1, -1))
        stop = False
        for j in idx:
            p, op = ins[j]
            if p == pc:
                stop = True
                break
            c = sd.classify(op)
            if isinstance(c, tuple) and op.split(".")[0] == "MEMBAR" and c[1] >= need:
                stop = True
                break
            if c == "mem":
                return False
        if stop:
            continue
        for n in nxt[b]:
            if n in blocks and n not in seen:
                seen.add(n)
                stack.append((n, 0, False))
    return True


def _r3_diag(eng, graph_args, cur, anc, d, cur_read, anc_read, asy):
    """Why R3 did not certify (anc, cur) at distance d. Mirrors HBGraph.ordered/chain
    step by step (read-only) and names the first gate the pair failed:
      copy             a cp.async copy is one side (T1a: no R3 credit)
      cs-unfenced      a plain store inside a CAS critical section without a fence of
                       scope >= d between the CAS and the store (_cs_fenced)
      no-release-point a plain access with no atomic after it in certified program order
      no-release-fence atomics follow it, but no MEMBAR in postdom(access) & dom(atomic)
      missing-hop      no observed atomic sync hop (trace edge) leaves the release side
                       at a distance the release fence covers
      dominance        hops land, but on no atomic that certifiably precedes the other
                       access (the acquire does not dominate it)
      past-release     the only landing acquires are CAS acquires the other access has
                       left (_past_release: the ScoR rtraw gate)
    Both orientations are tried (the chain is direction-agnostic); the reason is the
    one that got furthest. Also returns the observed hand-offs (atomic sync edges from
    the release side to an acquire before the other access) with their fence check."""
    import sync_dominance as sd
    if cur in asy or anc in asy:
        return {"reason": "copy", "gate": [], "handoffs": []}
    ok = lambda x, rd: x in eng.atom or rd or eng._cs_fenced(x, d)
    gate = [hex(x) for x, rd in ((anc, anc_read), (cur, cur_read)) if not ok(x, rd)]
    rank = ["no-release-point", "no-release-fence", "missing-hop", "dominance",
            "past-release", "chain"]
    hops = defaultdict(list)
    for a1, a2, dd in eng.sync_edges:
        hops[a1].append((a2, dd))

    def direction(x, y):
        if x in eng.atom:
            starts = [(x, sd.GRID)]
        else:
            after = [a for a in eng.atom if eng.po(x, a)]
            if not after:
                return "no-release-point"
            starts = [(a, s) for a in eng.atom if (s := eng.release_scope(x, a)) > sd.NONE]
            if not starts:
                return "no-release-fence"
        best = "missing-hop"
        for a0, fs in starts:
            stack, seen = [(a0, False, None)], set()
            while stack:
                n, synced, acq = stack.pop()
                if synced and n != y:
                    if eng.po(n, y):
                        if not eng._past_release(acq, y):
                            return "chain"
                        best = max(best, "past-release", key=rank.index)
                    else:
                        best = max(best, "dominance", key=rank.index)
                if (n, synced, acq) in seen:
                    continue
                seen.add((n, synced, acq))
                for a2, dd in hops.get(n, ()):
                    if synced or dd <= fs:
                        stack.append((a2, True, a2))
                if synced or x in eng.atom:
                    for b in eng.atom:
                        if b != n and eng.po(n, b):
                            stack.append((b, synced, acq))
        return best

    r = max(direction(anc, cur), direction(cur, anc), key=rank.index)
    if gate:
        r = "cs-unfenced"
    blocks, edges = graph_args[0], graph_args[1]

    def _ho(a1, a2, dd):
        return {"release": hex(a1), "acquire": hex(a2), "hop": sd.SCOPES[dd],
                "release_op": eng.pc_opcode[a1], "acquire_op": eng.pc_opcode[a2],
                "release_fenced": _fence_adjacent(blocks, edges, a1, False,
                                                  max(eng.atom[a1], sd.WARP)),
                "acquire_fenced": _fence_adjacent(blocks, edges, a2, True,
                                                  max(eng.atom[a2], sd.WARP))}
    ho = []
    for x, y in ((anc, cur), (cur, anc)):
        for a1, a2, dd in eng.sync_edges:
            if (a1 == x or eng.po(x, a1)) and (a2 == y or eng.po(a2, y)):
                ho.append(_ho(a1, a2, dd))
    certified = bool(ho)
    if not ho:
        # R3 found no hand-off in certified program order (dominance). Fall back to the
        # observed hops whose release RMW is CFG-reachable from one access and whose
        # acquire RMW reaches the other: the candidates the run's ordering went through,
        # marked uncertified (reachability is not ordering; only used to classify fences).
        import networkx as nx
        reach = lambda u, v: u == v or nx.has_path(eng.G, eng.pc_node[u], eng.pc_node[v])
        for x, y in ((anc, cur), (cur, anc)):
            for a1, a2, dd in eng.sync_edges:
                if reach(x, a1) and reach(a2, y):
                    ho.append(_ho(a1, a2, dd))
    uniq = {tuple(sorted(h.items())): h for h in ho}
    return {"reason": r, "gate": gate, "handoffs": list(uniq.values()),
            "handoffs_certified": certified}


def worker(pdir, mode, variant, out):
    import aggregate as agg
    import sync_dominance as sd
    strip = variant == SAME
    cap = {}

    class _J:                                  # shadows sync_dominance's `json` name
        def __getattr__(self, k):
            return getattr(json, k)

        def loads(self, s):
            t = json.loads(s)
            if strip:
                t.pop("hb_races", None)
                t.pop("hb_races_sync_only", None)
            cap["trace"] = t
            return t

    class _G(sd.HBGraph):                      # keeps the graph analyze() builds
        def __init__(self, *a):
            super().__init__(*a)
            cap["eng"], cap["args"] = self, a

    sd.json, sd.HBGraph = _J(), _G
    meta = json.load(open(f"{pdir}/meta.json"))
    pc_lines = meta.get("pc_lines", {})
    dots = sorted(glob.glob(f"{pdir}/dots/*.dot"))
    t0 = time.time()
    kernels, verdicts, ded = [], [], {}
    for kj in sorted(glob.glob(f"{pdir}/{mode}/kernel_*.json")):   # run_cuvein's order
        rep = None
        for dot in dots:
            try:
                rep = sd.analyze(dot, kj)
                break
            except sd.AlignmentError:
                continue
        if rep is None:
            kernels.append({"file": os.path.basename(kj), "aligned": False})
            continue
        tr, eng, gargs = cap["trace"], cap["eng"], cap["args"]
        asy = sd.dump_async_pcs(eng, tr)
        hbr = tr.get("hb_races")
        raced = {frozenset((r["a_pc"], r["b_pc"])) for r in hbr or () if r.get("a_pc") is not None}
        so = tr.get("hb_races_sync_only")
        sync = {frozenset((a, b)): n for a, b, n in so} if so is not None else None
        kernels.append({"file": os.path.basename(kj), "aligned": True,
                        "name": rep["kernel"]["name"], "hb_races": None if hbr is None else len(hbr),
                        "sync_only": None if so is None else len(so),
                        "events": len(tr.get("hb_events") or ()),
                        "lanes": sum(len(e.get("lanes", ())) for e in tr.get("hb_events") or ()),
                        "event_candidates": rep["diagnostics"]["event_candidates"],
                        "hb_classes": rep["summary"]["hb_classes"]})
        for v in rep["verdicts"]:
            cur, anc = v["current_pc"], v["ancient_pc"]
            k = frozenset((cur, anc))
            rec = {k2: v[k2] for k2 in ("current_pc", "ancient_pc", "space", "race_type",
                                         "observed_distance", "strength", "atomic_coherence",
                                         "hb_chain", "event_candidate", "edge_rescued",
                                         "hb_class", "benign", "verdict", "opcodes")}
            rec["kernel"] = rep["kernel"]["name"]
            rec["kfile"] = os.path.basename(kj)
            # T9 (D12): the verdict-matrix class before judge's relabels and the DR/SC class
            rec["matrix_class"] = v.get("matrix_class")
            rec["conflict_class"] = v.get("conflict_class")
            rec["raced"] = None if hbr is None else k in raced
            rec["sync_raced"] = None if sync is None else k in sync
            rec["sync_count"] = None if sync is None else sync.get(k, 0)
            obs = sd.SCOPES.index(v["observed_distance"])
            static = sd.SCOPES.index(v["strength"]) >= obs or v["hb_chain"] is not None
            rec["static_proof"] = static
            # the class before the benign re-bucketing (benign overwrites structural/latent)
            if v["hb_class"] == "benign" and hbr is not None:
                rec["class_pre_benign"] = sd._hb_class(sd.SCOPES.index(v["strength"]) >= obs,
                                                       v["hb_chain"] is not None, rec["raced"],
                                                       rec["sync_raced"])
            if not static:
                ca = "atomic" if cur in eng.atom else sd.parse_flags(
                    next((n["flags"] for n in tr.get("nodes", []) if n["pc"] == cur), ""))[1]
                aa = "atomic" if anc in eng.atom else sd.parse_flags(
                    next((n["flags"] for n in tr.get("nodes", []) if n["pc"] == anc), ""))[1]
                rec["r3"] = _r3_diag(eng, gargs, cur, anc, max(obs, sd.WARP),
                                     ca == "read", aa == "read", asy)
            rec["lines"] = [pc_lines.get(str(cur), ""), pc_lines.get(str(anc), "")]
            verdicts.append(rec)
            key = agg._dedup_key(v)
            # the harness's per-report dedup: first RACE per key; ORDERED keys without a
            # RACE keep their first verdict
            if v["verdict"] == "RACE" and ded.get(key, {}).get("verdict") != "RACE":
                ded[key] = rec
            else:
                ded.setdefault(key, rec)
    res = {"census_version": VERSION, "id": meta.get("id"), "pset": meta.get("pset"),
           "program": meta.get("program"),
           "mode": mode, "variant": variant or "recorded", "pdir": pdir,
           "status": "ok", "wall_s": round(time.time() - t0, 2), "kernels": kernels,
           "reports": [dict(r, key=list(k)) for k, r in sorted(ded.items(), key=lambda kv: kv[0])],
           "verdicts_total": len(verdicts)}
    tmp = out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(res, f)
    os.replace(tmp, out)


# ---------------------------------------------------------------- collect


def _outname(out, _id, mode, variant):
    return f"{out}/detail/{_id}__{mode}{'__' + variant if variant else ''}.json"


def cmd_collect(a):
    src, why = select_sources(a.stores.split(","))
    ids = sorted({i for i, _ in src} | {i for i, _ in why})
    if a.id_file:
        keep = {ln.strip() for ln in open(a.id_file) if ln.strip()}
        ids = [i for i in ids if i in keep]
    if a.min_mb is not None or a.max_mb is not None:
        big = lambda i: max(src.get((i, m), {}).get("dump_mb", 0) for m in (VC, SC))
        ids = [i for i in ids if (a.min_mb is None or big(i) >= a.min_mb)
               and (a.max_mb is None or big(i) < a.max_mb)]
    k, n = map(int, a.shard.split("/"))
    ids = ids[k::n]
    os.makedirs(f"{a.out}/detail", exist_ok=True)
    if k == 0:
        with open(f"{a.out}/sources.json", "w") as f:
            json.dump({"stores": a.stores, "selected": {f"{i}|{m}": v for (i, m), v in src.items()},
                       "not_available": {f"{i}|{m}": w for (i, m), w in why.items()}},
                      f, indent=0, sort_keys=True)
    print(f"shard {k}/{n}: {len(ids)} programs", flush=True)
    for _id in ids:
        jobs = [(m, None) for m in (VC, SC) if (_id, m) in src]
        if (_id, VC) in src and not a.no_sametrace:
            jobs.append((VC, SAME))
        for mode, variant in jobs:
            out = _outname(a.out, _id, mode, variant)
            if os.path.exists(out) and not a.force:
                continue
            s = src[(_id, mode)]
            t0 = time.time()
            memb = int(a.mem_gb * 2**30)

            def lim():
                resource.setrlimit(resource.RLIMIT_AS, (memb, memb))
            try:
                p = subprocess.run([sys.executable, __file__, "_worker", s["pdir"], mode,
                                    variant or "", out], preexec_fn=lim, timeout=a.timeout,
                                   capture_output=True, text=True)
                status = "ok" if p.returncode == 0 and os.path.exists(out) else \
                    ("analysis-oom" if "MemoryError" in p.stderr else f"error(rc={p.returncode})")
                err = p.stderr[-800:]
            except subprocess.TimeoutExpired:
                status, err = f"analysis-timeout={a.timeout}s", ""
            if status != "ok":
                with open(out, "w") as f:
                    json.dump({"id": _id, "pset": s.get("pset"), "mode": mode,
                               "variant": variant or "recorded", "pdir": s["pdir"],
                               "status": status, "stderr": err, "dump_mb": s["dump_mb"]}, f)
            print(f"{_id} {mode} {variant or 'recorded'} {status} {time.time() - t0:.1f}s",
                  flush=True)


# ---------------------------------------------------------------- tables

RACE_CLASSES = ("structural", "model_bug", "latent", "benign")
ALL_CLASSES = ("structural", "model_bug", "latent", "benign", "barrier-ordered", "ordered",
               "warp-po-ordered", "sc", "latent-sc")   # sc / latent-sc: T9 (D12), verdict SC


def _cls(r):
    """Report class. vector-clock: hb_class. scalar-clock (hb_class None): a RACE is
    `race` (no static proof, not barrier-ordered), an ORDERED `ordered`."""
    c = r.get("hb_class")
    if c == "structural" and r.get("model_bug"):
        return "model_bug"   # the annotation on a DR pair (an SC one stays sc: not a race)
    if c:
        return c
    return "race" if r["verdict"] == "RACE" else "ordered"



def load_detail(out):
    d = {}
    for f in glob.glob(f"{out}/detail/*.json"):
        try:
            j = json.load(open(f))
        except ValueError:
            continue
        d[(j["id"], j["mode"], j.get("variant", "recorded"))] = j
    return d


def _labels():
    import make_tables as mt
    man = mt.load_manifest()
    lab = {i: (r.get("label") or "").upper() for i, r in man.items()}
    src = {i: "manifest.csv" for i in lab}
    for p in (f"{HERE}/setup/manifest.evcand.csv", f"{HERE}/manifest.pre-PI.csv"):
        if os.path.exists(p):
            for r in csv.DictReader(open(p, newline="")):
                if r["id"] not in lab:
                    lab[r["id"]] = (r.get("label") or "").upper()
                    src[r["id"]] = os.path.relpath(p, APH)
    return lab, src


def _baselines(ids):
    """Other tools' verdicts, from the merged CSVs eval/BASELINES.md is built from."""
    import make_tables as mt
    runs, _ = mt.load_runs()
    out = {}
    for i in ids:
        row = {}
        for (rid, tool, mode), r in runs.items():
            if rid != i or tool == "cuvein":
                continue
            row[f"{tool}{'/' + mode if mode else ''}"] = r["verdict"]
        out[i] = row
    return out


def _md_table(head, rows):
    o = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    o += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(o)


def cmd_tables(a):
    det = load_detail(a.out)
    lab, labsrc = _labels()
    census = []
    for (i, mode, var), j in sorted(det.items()):
        row = {"suite": j.get("pset"), "program": i, "mode": mode, "variant": var,
               "label": lab.get(i, ""), "status": j["status"]}
        if j["status"] == "ok":
            reps = j["reports"]
            c = Counter(_cls(r) for r in reps)
            for k in ALL_CLASSES + ("race",):
                row[k] = c.get(k, 0)
            row["race_reports"] = sum(r["verdict"] == "RACE" for r in reps)
            row["event_candidate"] = sum(bool(r.get("event_candidate")) for r in reps)
            row["event_candidate_race"] = sum(bool(r.get("event_candidate")) and
                                              r["verdict"] == "RACE" for r in reps)
            row["verdict"] = "RACE" if row["race_reports"] else "CLEAN"
            row["kernels"] = len(j["kernels"])
        census.append(row)
    cols = ["suite", "program", "mode", "variant", "label", "status", "verdict", "race_reports",
            "structural", "model_bug", "latent", "benign", "race", "barrier-ordered", "ordered",
            "warp-po-ordered", "sc", "latent-sc", "event_candidate", "event_candidate_race",
            "kernels"]
    with open(f"{a.out}/census.csv", "w", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        for r in census:
            w.writerow(r)

    md = []
    rec = {(r["program"], r["mode"], r["variant"]): r for r in census}
    vcrows = [r for r in census if r["mode"] == VC and r["variant"] == "recorded"]
    scrows = [r for r in census if r["mode"] == SC and r["variant"] == "recorded"]
    ok = lambda r: r["status"] == "ok"

    # ---- pairs of interest
    def pairs(i, mode, var="recorded"):
        j = det.get((i, mode, var))
        return j["reports"] if j and j["status"] == "ok" else []

    def is_latent(r):
        return r.get("hb_class") == "latent" or r.get("class_pre_benign") == "latent"

    latent_only, latent_fp, latent_rows = [], [], []
    for r in vcrows:
        if not ok(r):
            continue
        reps = [p for p in pairs(r["program"], VC) if p["verdict"] == "RACE"]
        lat = [p for p in reps if is_latent(p)]
        if not lat:
            continue
        other = [p for p in reps if not is_latent(p)]
        if r["label"] == "RACE" and not other:
            latent_only.append(r["program"])
        if r["label"] == "CLEAN":
            latent_fp.append(r["program"])
        for p in lat:
            latent_rows.append((r, p))

    # ---- headline
    tot_lat = len(latent_rows)
    fp_lat = [x for x in latent_rows if x[0]["label"] == "CLEAN"]
    tp_lat = [x for x in latent_rows if x[0]["label"] == "RACE"]
    unl_lat = [x for x in latent_rows if x[0]["label"] not in ("RACE", "CLEAN")]
    def fence_status(p):
        """Per latent pair: is there an observed hand-off whose release RMW and acquiring
        RMW are both fence-adjacent (Definition "Gate", PTX gate)? Else which side lacks."""
        hs = p.get("r3", {}).get("handoffs", [])
        if not hs:
            return "no observed hand-off"
        if any(h["release_fenced"] and h["acquire_fenced"] for h in hs):
            return "gated hand-off present"
        if any(h["release_fenced"] for h in hs):
            return "acquire side ungated"
        if any(h["acquire_fenced"] for h in hs):
            return "release side ungated"
        return "both sides ungated"
    fen = Counter()
    for r, p in latent_rows:
        side = {"RACE": "racy", "CLEAN": "race-free"}.get(r["label"], "unlabelled")
        cert = "certified" if p.get("r3", {}).get("handoffs_certified", True) else "reach"
        fen[(side, cert, fence_status(p))] += 1
    racy_vc = [r for r in vcrows if ok(r) and r["label"] == "RACE" and r["verdict"] == "RACE"]
    clean_vc = [r for r in vcrows if ok(r) and r["label"] == "CLEAN" and r["verdict"] == "RACE"]
    lo_fp = [i for i in latent_fp if all(is_latent(p) for p in pairs(i, VC) if p["verdict"] == "RACE")]
    md.append("## Headline (generated)\n")
    md.append(f"- Programs with a vector-clock verdict from a complete kept dump: "
              f"{sum(ok(r) for r in vcrows)} (scalar-clock: {sum(ok(r) for r in scrows)}).")
    md.append(f"- Labelled-racy programs reported RACE by vector-clock: {len(racy_vc)}; of these "
              f"caught **only** through `latent` (no structural/model_bug report): "
              f"**{len(latent_only)}** — " + (", ".join(f"`{i}`" for i in latent_only) or "none") + ".")
    md.append(f"- `latent` reports (deduped pc pairs): **{tot_lat}** on "
              f"{len({x[0]['program'] for x in latent_rows})} programs — on labelled-racy "
              f"{len(tp_lat)}, on labelled race-free **{len(fp_lat)}** "
              f"({(100.0 * len(fp_lat) / tot_lat if tot_lat else 0):.1f}% of all latent reports; "
              f"{len({x[0]['program'] for x in fp_lat})} programs), unlabelled {len(unl_lat)}.")
    md.append(f"- Labelled race-free programs reported RACE by vector-clock: {len(clean_vc)}; "
              f"of these RACE **only** through `latent`: {len(lo_fp)}"
              + (" — " + ", ".join(f"`{i}`" for i in lo_fp) if lo_fp else "") + ".")
    md.append("- Hand-off fencing of the latent pairs (Definition \"Gate\" adjacency per observed "
              "hand-off RMW; `certified` = the hand-off lies in R3's dominance program order, "
              "`reach` = only CFG-reachable):")
    for (side, cert, st), v in sorted(fen.items()):
        md.append(f"  - {side}, {cert}: {st} — {v}")
    md.append("")

    # ---- with / without the latent tier (the D8 counterfactual on the recorded runs)
    md.append("## Vector-clock TP/FP with and without `latent` (recorded runs; no detector change)\n")
    md.append("`without latent` = the program's verdict if every `latent` report (and a `benign` "
              "report whose underlying class is latent) were ORDERED -- the \"ordered in this "
              "execution\" reading of D8 applied to the unchanged engine (I1/I2/I4 as they are).\n")
    d8 = []
    for s_ in sorted({r["suite"] for r in vcrows}):
        rs = [r for r in vcrows if r["suite"] == s_ and ok(r)]
        def v_wo(r):
            return any(p["verdict"] == "RACE" and not is_latent(p) for p in pairs(r["program"], VC))
        racy = [r for r in rs if r["label"] == "RACE"]
        clean = [r for r in rs if r["label"] == "CLEAN"]
        d8.append([s_, len(racy), sum(r["verdict"] == "RACE" for r in racy), sum(v_wo(r) for r in racy),
                   len(clean), sum(r["verdict"] == "RACE" for r in clean), sum(v_wo(r) for r in clean)])
    tot = [sum(x[i] for x in d8) for i in range(1, 7)]
    md.append(_md_table(["suite", "labelled racy", "TP", "TP without latent", "labelled race-free",
                         "FP", "FP without latent"], d8 + [["**all**"] + tot]))
    md.append("")

    # ---- per-suite census summary
    md.append("## Census by suite and mode (deduped reports; recorded dumps)\n")
    agg_rows = []
    for mode, rows in ((VC, vcrows), (SC, scrows)):
        by = defaultdict(list)
        for r in rows:
            by[r["suite"]].append(r)
        for s in sorted(by):
            rs = [r for r in by[s] if ok(r)]
            c = Counter()
            for r in rs:
                for k in ALL_CLASSES + ("race", "event_candidate", "event_candidate_race"):
                    c[k] += r.get(k, 0)
            agg_rows.append([s, mode, len(by[s]), len(rs),
                             sum(r["verdict"] == "RACE" for r in rs),
                             c["structural"], c["model_bug"], c["latent"], c["benign"], c["race"],
                             c["barrier-ordered"], c["ordered"], c["event_candidate"],
                             c["event_candidate_race"]])
    md.append(_md_table(["suite", "mode", "programs", "analysed", "RACE programs", "structural",
                         "model_bug", "latent", "benign", "race (sc)", "barrier-ordered",
                         "ordered", "event_candidate", "event_candidate ∧ RACE"], agg_rows))
    md.append("")

    # ---- latent pairs, TP side and FP side
    def pair_row(r, p):
        k = frozenset((p["current_pc"], p["ancient_pc"]))
        scp = next((q for q in pairs(r["program"], SC)
                    if frozenset((q["current_pc"], q["ancient_pc"])) == k), None)
        stp = next((q for q in pairs(r["program"], VC, SAME)
                    if frozenset((q["current_pc"], q["ancient_pc"])) == k), None)
        r3 = p.get("r3", {})
        hs = r3.get("handoffs", [])
        ho = ("" if r3.get("handoffs_certified", True) or not hs else "(reach) ") + \
            "; ".join(f"{h['release']}({h['release_op']})→{h['acquire']}({h['acquire_op']}) "
                      f"{h['hop']} rel{'+' if h['release_fenced'] else '−'} "
                      f"acq{'+' if h['acquire_fenced'] else '−'}" for h in hs) or "—"
        return [f"`{r['program']}`", r["label"] or "—", p["kernel"][:40],
                f"{hex(p['ancient_pc'])}↔{hex(p['current_pc'])}", p["space"], p["race_type"],
                p["observed_distance"], "yes" if p.get("event_candidate") else "no",
                p.get("sync_count", ""), r3.get("reason", "?"), ho,
                (_cls(scp) + ("/" + scp["verdict"]) if scp else "absent"),
                (_cls(stp) + ("/" + stp["verdict"]) if stp else "absent"),
                " ; ".join(sorted(set(x for x in p.get("lines", []) if x))) or "—",
                "benign" if p.get("hb_class") == "benign" else ""]
    head = ["program", "label", "kernel", "pc pair (anc↔cur)", "space", "type", "dist",
            "event cand.", "barrier-pass conflicts", "R3 declined", "observed hand-off(s), fence",
            "scalar-clock (own run)", "scalar-clock (same trace)", "source", "tag"]
    md.append("## Latent-only true positives (compact)\n")
    md.append(_md_table(["program", "pc pair", "type", "dist", "R3 declined", "fence status",
                         "hand-off(s)"],
                        [[f"`{r['program']}`", f"{hex(p['ancient_pc'])}↔{hex(p['current_pc'])}",
                          p["race_type"], p["observed_distance"], p.get("r3", {}).get("reason", "?"),
                          fence_status(p),
                          ("" if p.get("r3", {}).get("handoffs_certified", True) else "(reach) ")
                          + "; ".join(f"{h['release']}→{h['acquire']} rel{'+' if h['release_fenced'] else '−'}"
                                      f" acq{'+' if h['acquire_fenced'] else '−'}"
                                      for h in p.get("r3", {}).get("handoffs", []))]
                         for r, p in tp_lat if r["program"] in latent_only]))
    md.append("")
    md.append("## Latent pairs on labelled-racy programs\n")
    md.append(_md_table(head, [pair_row(r, p) for r, p in tp_lat]) if tp_lat else "none")
    md.append("")
    md.append("## Latent pairs on labelled race-free programs (the tier's cost)\n")
    md.append(_md_table(head, [pair_row(r, p) for r, p in fp_lat]) if fp_lat else "none")
    md.append("")
    by_reason = Counter(p.get("r3", {}).get("reason", "?") for _, p in fp_lat)
    md.append("R3 decline reasons, race-free side: " +
              (", ".join(f"{k} {v}" for k, v in by_reason.most_common()) or "none") + "; racy side: " +
              (", ".join(f"{k} {v}" for k, v in
                         Counter(p.get("r3", {}).get("reason", "?") for _, p in tp_lat).most_common())
               or "none") + ".\n")
    if unl_lat:
        md.append("Unlabelled programs with latent pairs: " +
                  ", ".join(sorted({f"`{x[0]['program']}`" for x in unl_lat})) + ".\n")

    # ---- baselines for the latent-only TPs (and every latent program)
    lat_progs = sorted({x[0]["program"] for x in latent_rows})
    bl = _baselines(lat_progs)
    tools = ["racecheck", "hirace", "iguard", "supercollider"]   # the race detectors
    md.append("## Other tools on the programs with latent reports (merged baselines CSVs)\n")
    md.append(_md_table(["program", "label", "latent-only?"] + tools,
                        [[f"`{i}`", lab.get(i, "") or "—", "yes" if i in latent_only else "no"]
                         + [bl[i].get(t, "—") for t in tools] for i in lat_progs]))
    md.append("")

    # ---- sanity (step 8): scalar-clock Race set vs vector-clock classes
    def keyset(i, mode, var, pred):
        return {tuple(p["key"]) for p in pairs(i, mode, var) if pred(p)}
    san = []
    for r in vcrows:
        i = r["program"]
        if not ok(r):
            continue
        vc_all = keyset(i, VC, "recorded", lambda p: p["verdict"] == "RACE")
        # vetoes: the full clock overrides a static proof (structural with a chain,
        # model_bug) -- reports the scalar-clock leg cannot make by construction
        vc_noveto = keyset(i, VC, "recorded", lambda p: p["verdict"] == "RACE" and not p["static_proof"])
        for var, lbl in ((SAME, "same trace"), ("recorded", "own run")):
            srow = rec.get((i, SC, var) if var == "recorded" else (i, VC, SAME))
            if not srow or not ok(srow):
                san.append([f"`{i}`", lbl, "n/a", "", "", srow["status"] if srow else "no dump"])
                continue
            m = SC if var == "recorded" else VC
            sc_set = keyset(i, m, var, lambda p: p["verdict"] == "RACE")
            j = det[(i, m, var)]
            cut = [k["file"] for k in j["kernels"]
                   if k.get("aligned") and k.get("lanes", 0) > int(os.environ.get(
                       "CUVEIN_BARRIER_PASS_MAX_LANES", "5000000"))]
            eq = sc_set == vc_noveto
            if not eq:
                san.append([f"`{i}`", lbl, "differs",
                            len(sc_set - vc_noveto), len(vc_noveto - sc_set),
                            (f"barrier-pass cutoff on {len(cut)} kernel(s); " if cut else "")
                            + f"vetoes={len(vc_all - vc_noveto)}"])
    n_same = sum(1 for r in vcrows if ok(r) and rec.get((r["program"], VC, SAME), {}).get("status") == "ok")
    n_own = sum(1 for r in vcrows if ok(r) and rec.get((r["program"], SC, "recorded"), {}).get("status") == "ok")
    n_veto = sum(len(keyset(r["program"], VC, "recorded", lambda p: p["verdict"] == "RACE" and p["static_proof"]))
                 for r in vcrows if ok(r))
    same_bad = [s for s in san if s[1] == "same trace" and s[2] != "n/a"]
    own_bad = [s for s in san if s[1] == "own run" and s[2] != "n/a"]
    md.append("## Sanity: scalar-clock Race set = vector-clock Race set minus the vetoes (hb_proof.tex §5 fact (i))\n")
    md.append(f"A veto = a vector-clock RACE on a pair a static certificate (R1/R2 strength or R3 "
              f"chain) orders: `model_bug`, or `structural` with a chain. Vetoed report keys over "
              f"all programs: {n_veto}.\n")
    md.append(f"**Same trace** (the vector-clock dump re-analysed with its engine keys removed, "
              f"i.e. through the scalar-clock path): {n_same} programs checked, "
              f"**{len(same_bad)} mismatches**.\n")
    if same_bad:
        md.append(_md_table(["program", "comparison", "result", "sc-only", "vc-only", "cause / note"],
                            same_bad))
        md.append("")
    md.append(f"**Own run** (the scalar-clock mode's separately recorded dump): {n_own} programs "
              f"checked, {len(own_bad)} differ. Two recordings are two schedules (and, for the "
              f"event-stream candidates, two event streams), so these differences are run-to-run, "
              f"not model differences; the same-trace check above is the model comparison.\n")
    if own_bad:
        md.append(_md_table(["program", "comparison", "result", "sc-only", "vc-only", "cause / note"],
                            own_bad))
        md.append("")
    na = [s for s in san if s[2] == "n/a"]
    if na:
        md.append(f"Not comparable ({len(na)}): " + ", ".join(f"{s[0]} [{s[1]}: {s[5]}]" for s in na) + "\n")
    vers = Counter(j.get("census_version", "?") for j in det.values())
    md.append("Detail files by census_version: " + ", ".join(f"{k} {v}" for k, v in vers.items()) + ".\n")

    # ---- coverage
    fails = [r for r in census if r["status"] != "ok"]
    src = json.load(open(f"{a.out}/sources.json")) if os.path.exists(f"{a.out}/sources.json") else {}
    md.append("## Coverage\n")
    md.append(f"Analysis failures ({len(fails)}): " +
              (", ".join(f"`{r['program']}` {r['mode']}/{r['variant']} {r['status']}" for r in fails)
               or "none") + ".\n")
    have = {(i, m) for (i, m, v) in det if v == "recorded"} | \
        {(i, SC + "@same") for (i, m, v) in det if v == SAME}
    pend = sorted(k for k in src.get("selected", {})
                  for i, m in [k.split("|")]
                  if (i, m) not in have or (m == VC and (i, SC + "@same") not in have))
    md.append(f"Selected but without a finished detail file (not analysed / still running when "
              f"the tables were generated) ({len(pend)}): "
              + (", ".join(f"`{k}`" for k in pend) or "none") + ".\n")
    nav = Counter(v.split(":", 1)[1] for v in src.get("not_available", {}).values())
    md.append("No usable kept dump (per program × mode, by reason): " +
              ", ".join(f"{k} {v}" for k, v in nav.most_common()) + ".\n")
    lbl_other = sorted({i for i in {r["program"] for r in census} if labsrc.get(i, "") != "manifest.csv"})
    if lbl_other:
        md.append(f"Labels not from the current manifest ({len(lbl_other)} programs, e.g. P2 "
                  f"dropped when PI replaced it): taken from " +
                  ", ".join(sorted({labsrc.get(i, 'none') for i in lbl_other})) + ".\n")
    with open(f"{a.out}/census.md", "w") as f:
        f.write("\n".join(md) + "\n")
    # per-program census table as its own markdown
    with open(f"{a.out}/census_programs.md", "w") as f:
        f.write(_md_table(cols, [[r.get(c, "") for c in cols] for r in census]) + "\n")
    with open(f"{a.out}/latent_pairs.json", "w") as f:
        json.dump([{"program": r["program"], "label": r["label"], **p} for r, p in latent_rows],
                  f, indent=1)
    print(f"wrote {a.out}/census.csv, census.md, census_programs.md, latent_pairs.json")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--stores", default=",".join(DEFAULT_STORES),
                   help="BeeGFS store tags (or absolute paths); a later store wins")
    c.add_argument("--out", default=DEFAULT_OUT)
    c.add_argument("--shard", default="0/1")
    c.add_argument("--id-file")
    c.add_argument("--min-mb", type=float, help="only programs whose largest dump >= this")
    c.add_argument("--max-mb", type=float, help="only programs whose largest dump < this")
    c.add_argument("--timeout", type=int, default=3600)
    c.add_argument("--mem-gb", type=float, default=100)
    c.add_argument("--no-sametrace", action="store_true")
    c.add_argument("--force", action="store_true")
    t = sub.add_parser("tables")
    t.add_argument("--out", default=DEFAULT_OUT)
    w = sub.add_parser("_worker")
    w.add_argument("pdir")
    w.add_argument("mode")
    w.add_argument("variant")
    w.add_argument("out")
    a = ap.parse_args()
    if a.cmd == "collect":
        cmd_collect(a)
    elif a.cmd == "tables":
        cmd_tables(a)
    else:
        worker(a.pdir, a.mode, a.variant or None, a.out)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""X5 (1): bin every barrier-ordered pair of the X1 recording from the CFG alone.

A pair is `barrier-ordered` (sync_dominance._hb_class) when no static rule orders it (not R1,
not R3), the run did not race it, and the barrier/syncwarp-only clock orders every observed
conflict of it. This script finds those pairs for every (program, mode) of the X1 recording that
has a confirm file, and bins each one from the kernel's CFG (nvdisasm dot) with `u` = the pair's
ancient pc, `v` = its current pc, first match wins:

  loop-carried          both pcs lie in one natural loop (back edge = edge into a dominator)
                        that contains a qualifying BAR (BAR.SYNC* / BAR.RED*)
  partial participation some qualifying barrier between u and v is a WARPSYNC, or a BAR with a
                        count operand that is not a literal zero (BAR.RED's predicate operand
                        is not a count)
  early exit            for some barrier s between u and v: an EXIT/RET instruction x is
                        reachable from u without passing s and is not reachable from s (the
                        threads taking that path never arrive at s)
  branch arm            some barrier between u and v is not in postdom(u), and none of the
                        above applies
  other                 everything else (counted apart: no qualifying barrier between u and v)

"Between u and v": a qualifying barrier s with a CFG path u -> s and a CFG path s -> v (cycles
included). Regions, dominators and post-dominators are sync_dominance.HBGraph's (the region
graph split at every sync instruction, virtual EXIT as the post-dominator root); the EXIT test
uses HBGraph's instruction-level successor map, where an unguarded EXIT has no successor and a
guarded one falls through.

Why re-analysis: the confirm files (eval/baselines/confirm_final*) hold the RACE and SC reports
only -- rc._analyze_reports drops the ORDERED pairs, so none of them carries a barrier-ordered
pair (`confirm-scan` counts that). The pairs are therefore re-derived by running the harness's
own _analyze_reports over the kept X1 trace of each (program, mode) -- the store the merged
row came from, via final-2026-10-view -- with sync_dominance.analyze observed, and each re-run
is checked against its confirm file (same report ids, same SC count).

  plan          list the (program, mode) keys: the view's store, the confirm file, the work size
  collect       analyze one shard of the plan (SLURM array task), append to a jsonl
  report        merge the shards: tables + a pair-level csv
  confirm-scan  count the barrier-ordered pairs the confirm files contain
  resplit       re-plan the keys that waited behind a long-running key (cluster load balancing)
  explain       re-analyse the keys holding `other`-bin pairs and record why those pairs got
                their class (observed distance, R1 strength, warp-same-instruction, ...)
"""
import argparse
import collections
import csv
import glob
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import x5_common as xc                                # noqa: E402
from x5_common import sd, rc                          # noqa: E402
import networkx as nx                                 # noqa: E402
import pydot                                          # noqa: E402

CONFIRM_OF = {"final-2026-10": "confirm_final",
              "final-2026-10-long": "confirm_final-long",
              "final-2026-10-long-sc": "confirm_final-long-sc",
              "final-2026-10-24h-vc": "confirm_final-24h-vc",
              "final-2026-10-24h-sc": "confirm_final-24h-sc"}
BINS = ("loop-carried", "partial participation", "early exit", "branch arm", "other")
PRED = re.compile(r"!?U?P[T0-9]+")
ZERO = re.compile(r"0x0+|0")


# ---------------------------------------------------------------- CFG binning

def sync_operands(dot_path, mangled):
    """pc -> (opcode, [operands]) of the BAR*/WARPSYNC instructions of one kernel cluster
    (sync_dominance.parse_dot keeps only (pc, opcode); the count operand is in the label)."""
    (graph,) = pydot.graph_from_dot_file(str(dot_path))
    out = {}
    for sub in graph.get_subgraphs():
        if sub.get_name().strip('"') != "cluster_" + mangled:
            continue
        for node in sub.get_nodes():
            label = node.get_attributes().get("label")
            if label is None:
                continue
            for line in sd._label_lines(label.strip('"')):
                m = sd._INSTR.match(line)
                if m and m.group(3).split(".")[0] in ("BAR", "WARPSYNC"):
                    rest = line[m.end():].strip().rstrip(";").strip()
                    out[int(m.group(1), 16)] = (
                        m.group(3), [o.strip() for o in rest.split(",")] if rest else [])
    return out


class CfgBinner:
    def __init__(self, eng, ops):
        """eng: a sync_dominance.HBGraph; ops: {pc: (opcode, [operands])} of its BAR/WARPSYNC."""
        self.eng, self.ops = eng, ops
        self.exits = {pc for pc, op in eng.pc_opcode.items() if sd.classify(op) == "exit"}
        self._reach, self._ir, self._loops = {}, {}, None

    @classmethod
    def from_dot(cls, dot_path, mangled, parsed):
        if dot_path not in parsed:
            parsed[dot_path] = sd.parse_dot(dot_path)
        return cls(sd.HBGraph(*parsed[dot_path][mangled]), sync_operands(dot_path, mangled))

    def reach(self, node):
        r = self._reach.get(node)
        if r is None:
            r = self._reach[node] = nx.descendants(self.eng.G, node) | {node}
        return r

    def ins_reach(self, start, block=None):
        """pcs reachable from `start` in >= 1 steps, never entering pc `block`."""
        key = (start, block)
        got = self._ir.get(key)
        if got is None:
            got, stack = set(), list(self.eng.ins_succ.get(start, ()))
            while stack:
                x = stack.pop()
                if x in got or x == block:
                    continue
                got.add(x)
                stack.extend(self.eng.ins_succ.get(x, ()))
            self._ir[key] = got
        return got

    def loops(self):
        """[(header, body nodes, contains a qualifying BAR)] -- natural loops, one per header."""
        if self._loops is None:
            G, dom, syncs = self.eng.G, self.eng.dom, self.eng.syncs
            heads = {}
            for t, h in G.edges():
                if h in dom.get(t, ()):                     # back edge: h dominates t
                    body = heads.setdefault(h, {h})
                    stack = [t]
                    while stack:
                        x = stack.pop()
                        if x in body:
                            continue
                        body.add(x)
                        stack.extend(G.predecessors(x))
            self._loops = [
                (h, body, any(s in syncs and syncs[s][3] and syncs[s][1].split(".")[0] == "BAR"
                              for s in body))
                for h, body in heads.items()]
        return self._loops

    def bin(self, u, v):
        """-> (bin, detail) for the pair (u earlier, v later)."""
        eng = self.eng
        ru, rv = eng.pc_node[u], eng.pc_node[v]
        for h, body, has_bar in self.loops():
            if has_bar and ru in body and rv in body:
                return "loop-carried", {"loop_header": h, "loop_nodes": len(body)}
        ur = self.reach(ru)
        between = [s for s in eng.qualifying if s in ur and rv in self.reach(s)]
        det = {"between": [hex(eng.syncs[s][0]) + " " + eng.syncs[s][1] for s in between]}
        partial = []
        for s in between:
            pc, op = eng.syncs[s][0], eng.syncs[s][1]
            if op.split(".")[0] == "WARPSYNC":
                partial.append(f"{pc:#x} WARPSYNC")
            else:
                cnt = [o for o in self.ops.get(pc, (op, []))[1][1:] if not PRED.fullmatch(o)]
                if any(not ZERO.fullmatch(o) for o in cnt):
                    partial.append(f"{pc:#x} {op} count={','.join(cnt)}")
        if partial:
            det["partial"] = partial
            # the bin fires on ANY partial barrier between u and v; record whether a full-block
            # BAR (BAR.SYNC / BAR.RED without a count operand) is also between
            det["full_bar_between"] = sum(
                1 for s in between if eng.syncs[s][1].split(".")[0] == "BAR"
                and not any(eng.syncs[s][0] == int(p.split()[0], 16) for p in partial))
            return "partial participation", det
        for s in between:
            pc_s = eng.syncs[s][0]
            avoid, after = self.ins_reach(u, pc_s), self.ins_reach(pc_s)
            wit = sorted(x for x in self.exits if x in avoid and x not in after)
            if wit:
                det["early_exit_pc"] = hex(wit[0])
                det["early_exit_barrier"] = hex(pc_s)
                return "early exit", det
        pd = eng.postdom.get(ru, ())
        notpd = [s for s in between if s not in pd]
        if notpd:
            det["not_postdom"] = [hex(eng.syncs[s][0]) for s in notpd]
            return "branch arm", det
        return "other", det


# ---------------------------------------------------------------- plan / collect

def cmd_plan(a):
    view, croot = Path(a.view), Path(a.confirm_root)
    keys, skipped = [], collections.Counter()
    for pid in sorted(os.listdir(view)):
        for mode in xc.MODES:
            p = view / pid / mode
            if not p.exists():
                skipped[(xc.suite_of(pid), mode, "no recording in the view")] += 1
                continue
            real = Path(os.path.realpath(p))
            store = real.parts[-3]
            conf = croot / CONFIRM_OF[store] / f"{pid}__cuvein__{mode}.json"
            if not conf.exists():
                skipped[(xc.suite_of(pid), mode, "no confirm file")] += 1
                continue
            sizes = [e.stat().st_size for e in os.scandir(real) if e.name.startswith("kernel_")]
            keys.append({"id": pid, "suite": xc.suite_of(pid), "mode": mode, "store": store,
                         "dir": str(real), "dots": str(real.parent / "dots"),
                         "confirm": str(conf), "kbytes": sum(sizes), "nk": len(sizes)})
    out = {"view": str(view), "confirm_root": str(croot), "keys": keys,
           "skipped": [list(k) + [n] for k, n in sorted(skipped.items())]}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out))
    by = collections.Counter((k["suite"], k["mode"]) for k in keys)
    print(f"{len(keys)} keys with a recording and a confirm file; skipped {sum(skipped.values())}")
    for k, n in sorted(by.items()):
        print(" ", k, n)
    for k, n in sorted(skipped.items()):
        print("  skipped", k, n)


def analyze_key(e, a):
    t0 = time.time()

    def work():
        log = xc.PairLog()
        with xc.Capture(log):
            ids, pcs, raw = rc._analyze_reports(e["dir"], e["dots"])
        race, sc = rc.split_raw(raw)
        parsed, binners, pairs = {}, {}, []
        cls = collections.Counter()
        for (kid, anc, cur, space), p in log.pairs.items():
            for c in p["cls"]:
                cls[c or "-"] += 1
            if "barrier-ordered" not in p["cls"]:
                continue
            if kid not in binners:
                binners[kid] = CfgBinner.from_dot(log.kdot[kid], kid.split("::", 1)[1], parsed)
            b, det = binners[kid].bin(anc, cur)
            pairs.append({"kernel": kid, "anc": anc, "cur": cur, "space": space,
                          "classes": sorted(c or "-" for c in p["cls"]),
                          "race_type": sorted(p["race_type"]), "launches": p["n"],
                          "bin": b, "detail": det})
        return {"ids": ids, "n_race": len(race), "n_sc": len(sc), "pairs": pairs,
                "n_pair_keys": len(log.pairs), "nlaunch": log.nlaunch,
                "pair_classes": dict(cls)}

    pay, reason = xc.run_capped(work, a.analysis_timeout, a.mem_gb)
    rec = {k: e[k] for k in ("id", "suite", "mode", "store", "kbytes", "nk")}
    rec.update(reason=reason, elapsed=round(time.time() - t0, 1), node=os.uname().nodename)
    if pay is not None:
        conf = json.loads(Path(e["confirm"]).read_text())
        rec["same_ids"] = sorted(conf["report_ids"]) == sorted(pay["ids"])
        rec["same_sc"] = len(conf["raw_sc"]) == pay["n_sc"]
        rec["conf_ids"] = len(conf["report_ids"])
        rec.update({k: pay[k] for k in ("n_race", "n_sc", "pairs", "n_pair_keys", "nlaunch",
                                        "pair_classes")})
    return rec


def cmd_collect(a):
    plan = json.loads(Path(a.plan).read_text())
    k, n = (int(x) for x in a.shard.split("/"))
    keys = [e for e in plan["keys"] if not a.only or re.search(a.only, e["id"])]
    mine = xc.lpt_shards(keys, lambda e: e["kbytes"], n)[k]
    out = a.out.format(shard=k)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    done = xc.done_keys(out, lambda r: (r["id"], r["mode"]))
    print(f"shard {k}/{n}: {len(mine)} keys, {len(done)} already done -> {out}", flush=True)
    for i, e in enumerate(mine):
        if (e["id"], e["mode"]) in done:
            continue
        rec = analyze_key(e, a)
        xc.append_jsonl(out, rec)
        print(f"[{i + 1}/{len(mine)}] {e['id']} {e['mode']} {rec['reason'] or 'ok'} "
              f"{rec['elapsed']}s pairs={len(rec.get('pairs', []))}", flush=True)


class ExplainLog(xc.PairLog):
    """PairLog plus the verdict-record fields that say why a pair got its class: the observed
    thread distance, R1's strength, whether the pair was seen as warp-same-instruction, came from
    the event stream (no edge) or was rescued from an intra-thread edge, and the opcodes."""

    def __init__(self):
        super().__init__()
        self.extra = {}

    def __call__(self, dot, kj, rep):
        super().__call__(dot, kj, rep)
        kid = f"{os.path.basename(dot)}::{rep['kernel']['mangled']}"
        for v in rep["verdicts"]:
            x = self.extra.setdefault(
                (kid, v["ancient_pc"], v["current_pc"], v["space"].split("/")[0]),
                {"observed": set(), "strength": set(), "warp_same_inst": False,
                 "event_candidate": False, "edge_rescued": False, "opcodes": set()})
            x["observed"].add(v["observed_distance"])
            x["strength"].add(v["strength"])
            x["warp_same_inst"] |= bool(v["warp_same_inst"])
            x["event_candidate"] |= bool(v["event_candidate"])
            x["edge_rescued"] |= bool(v["edge_rescued"])
            x["opcodes"].add("/".join(v["opcodes"]))


def cmd_explain(a):
    """Re-analyse the keys that hold `other`-bin pairs, with ExplainLog, and write the extra
    fields of exactly those pairs (a separate pass: the main run did not record them)."""
    plan = {(e["id"], e["mode"]): e for e in json.loads(Path(a.plan).read_text())["keys"]}
    want = {}
    for f in sorted(glob.glob(a.inputs)):
        for ln in open(f):
            r = json.loads(ln)
            ps = [p for p in r.get("pairs", []) if p["bin"] == "other"]
            if ps:
                want[(r["id"], r["mode"])] = {(p["kernel"], p["anc"], p["cur"], p["space"])
                                              for p in ps}
    print(f"{len(want)} keys hold other-bin pairs")
    Path(a.out).write_text("")
    for k, pairs in sorted(want.items()):
        e = plan[k]

        def work():
            log = ExplainLog()
            with xc.Capture(log):
                rc._analyze_reports(e["dir"], e["dots"])
            out = []
            for key in sorted(pairs):
                x, p = log.extra[key], log.pairs[key]
                out.append({"kernel": key[0], "anc": key[1], "cur": key[2], "space": key[3],
                            "observed": sorted(x["observed"]), "strength": sorted(x["strength"]),
                            "warp_same_inst": x["warp_same_inst"],
                            "event_candidate": x["event_candidate"],
                            "edge_rescued": x["edge_rescued"], "opcodes": sorted(x["opcodes"]),
                            "race_type": sorted(p["race_type"]),
                            "classes": sorted(c or "-" for c in p["cls"])})
            return out
        pay, reason = xc.run_capped(work, a.analysis_timeout, a.mem_gb)
        xc.append_jsonl(a.out, {"id": k[0], "mode": k[1], "suite": e["suite"], "reason": reason,
                                "pairs": pay or []})
        print(k, reason or "ok", len(pay or []), flush=True)


def cmd_cfgfacts(a):
    """For the pairs of the branch-arm / early-exit / partial-participation bins: is u (v) inside a
    natural loop that contains a qualifying BAR? CFG only (no trace analysis). The pair sets of the
    two modes are identical (Table 2), so the vector-clock records are used."""
    plan = {(e["id"], e["mode"]): e for e in json.loads(Path(a.plan).read_text())["keys"]}
    Path(a.out).write_text("")
    seen = set()
    for f in sorted(glob.glob(a.inputs)):
        for ln in open(f):
            r = json.loads(ln)
            if r["mode"] != "vector-clock" or r["id"] in seen:
                continue
            ps = [p for p in r.get("pairs", [])
                  if p["bin"] in ("branch arm", "early exit", "partial participation")]
            if not ps:
                continue
            seen.add(r["id"])
            e, parsed, binners, out = plan[(r["id"], r["mode"])], {}, {}, []
            for p in ps:
                dotname, mangled = p["kernel"].split("::", 1)
                dot = f"{e['dots']}/{dotname}"
                if (dot, mangled) not in binners:
                    binners[(dot, mangled)] = CfgBinner.from_dot(dot, mangled, parsed)
                b = binners[(dot, mangled)]
                ru, rv = b.eng.pc_node[p["anc"]], b.eng.pc_node[p["cur"]]
                out.append({"kernel": p["kernel"], "anc": p["anc"], "cur": p["cur"],
                            "bin": p["bin"],
                            "u_in_barrier_loop": any(h and ru in body for _, body, h in b.loops()),
                            "v_in_barrier_loop": any(h and rv in body for _, body, h in b.loops())})
            xc.append_jsonl(a.out, {"id": r["id"], "suite": r["suite"], "pairs": out})
    print(f"{len(seen)} programs -> {a.out}")


def cmd_resplit(a):
    """Move the keys that wait behind a long-running key to new shards: for each listed shard of
    the base partition, drop what is already in a shard output and the first remaining key (the
    one in flight -- a shard works through its list in order), pool the rest into a new plan.
    The old tasks are left to finish their in-flight key."""
    plan = json.loads(Path(a.plan).read_text())
    parts = xc.lpt_shards(plan["keys"], lambda e: e["kbytes"], a.base_n)
    done = set()
    for f in glob.glob(a.done):
        for ln in open(f):
            r = json.loads(ln)
            done.add((r["id"], r["mode"]))
    pool = []
    for k in a.shards:
        rem = [e for e in parts[k] if (e["id"], e["mode"]) not in done]
        print(f"shard {k}: {len(parts[k])} assigned, {len(rem)} not done; in flight: "
              f"{rem[0]['id'] if rem else '-'}; moved: {max(len(rem) - 1, 0)}")
        pool += rem[1:]
    out = dict(plan, keys=pool, resplit_of=a.shards)
    Path(a.out).write_text(json.dumps(out))
    print(f"{len(pool)} keys -> {a.out}")


# ---------------------------------------------------------------- report

def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def cmd_report(a):
    plan = json.loads(Path(a.plan).read_text())
    recs, dups, disagree = {}, 0, []

    def sig(r):                       # what a duplicate must reproduce
        return (r["reason"], r.get("same_ids"), r.get("same_sc"), r.get("n_race"), r.get("n_sc"),
                r.get("n_pair_keys"), r.get("nlaunch"),
                sorted((p["kernel"], p["anc"], p["cur"], p["space"], p["bin"],
                        tuple(p["classes"]), p["launches"]) for p in r.get("pairs", [])))

    for f in sorted(glob.glob(a.inputs)):
        for ln in open(f):
            r = json.loads(ln)
            k = (r["id"], r["mode"])
            if k in recs:                 # the same key from two shards (a moved key an old task also ran)
                dups += 1
                if sig(recs[k]) != sig(r):
                    disagree.append(k)
                if r["reason"] and not recs[k]["reason"]:
                    continue              # keep the copy that ran
            recs[k] = r
    keys = {(k["id"], k["mode"]): k for k in plan["keys"]}
    missing = sorted(set(keys) - set(recs))
    suites = sorted({k["suite"] for k in keys.values()},
                    key=lambda s: (s[0] != "P", len(s), s))
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # pair-level csv
    with open(outdir / "barrier_ordered_pairs.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["suite", "id", "mode", "store", "kernel", "anc_pc", "cur_pc", "space",
                    "race_type", "classes", "launches", "bin", "detail"])
        for r in sorted(recs.values(), key=lambda r: (r["suite"], r["id"], r["mode"])):
            for p in r.get("pairs", []):
                w.writerow([r["suite"], r["id"], r["mode"], r["store"], p["kernel"],
                            hex(p["anc"]), hex(p["cur"]), p["space"], "/".join(p["race_type"]),
                            "+".join(p["classes"]), p["launches"], p["bin"],
                            json.dumps(p["detail"], separators=(",", ":"))])

    lines = []
    ok = [r for r in recs.values() if not r["reason"]]
    bad = [r for r in recs.values() if r["reason"]]
    lines.append(f"Keys in the plan (a recording and a confirm file): {len(keys)}; analysed "
                 f"without error: {len(ok)}; failed: {len(bad)}; not yet run: {len(missing)}.")
    lines.append(f"Keys present in more than one shard output (deduplicated by (program, mode)): "
                 f"{dups}; duplicates whose pair bins / counts / confirm check differ from the "
                 f"first copy: {len(disagree)}"
                 + (" (" + ", ".join(f"{i} {m}" for i, m in disagree[:20]) + ")" if disagree else "")
                 + ".\n")

    # table 1: per suite x mode
    rows = []
    tot = collections.defaultdict(collections.Counter)
    for s in suites + ["all"]:
        for m in xc.MODES:
            rs = [r for r in ok if (s == "all" or r["suite"] == s) and r["mode"] == m]
            if not rs:
                continue
            c = collections.Counter()
            c["files"] = len(rs)
            for r in rs:
                if r["pairs"]:
                    c["with"] += 1
                for p in r["pairs"]:
                    c["pairs"] += 1
                    c[p["bin"]] += 1
                    if len(p["classes"]) > 1:
                        c["mixed"] += 1
            rows.append([s, m, c["files"], c["with"], c["pairs"]]
                        + [c[b] for b in BINS] + [c["mixed"]])
    lines.append("### Table 1 -- barrier-ordered pairs by suite, mode and CFG bin\n")
    lines.append(md_table(["suite", "mode", "confirm files re-analysed", "files with >=1 pair",
                           "pairs"] + list(BINS) + ["pairs also seen in another class"], rows))
    lines.append("\nA pair is one (kernel, ancient pc, current pc, space class) over all launches "
                 "of the recording; \"also seen in another class\" counts pairs that were "
                 "barrier-ordered in one launch and in another hb_class in a different launch.\n")

    # table 2: pairs in both modes / one mode (union by identity)
    ident = collections.defaultdict(set)
    for r in ok:
        for p in r["pairs"]:
            ident[(r["suite"], r["id"], p["kernel"], p["anc"], p["cur"], p["space"])].add(r["mode"])
    rows = []
    for s in suites + ["all"]:
        c = collections.Counter()
        for k, ms in ident.items():
            if s == "all" or k[0] == s:
                c["both" if len(ms) == 2 else ms.copy().pop()] += 1
        if sum(c.values()):
            rows.append([s, sum(c.values()), c["both"], c["vector-clock"], c["scalar-clock"]])
    lines.append("### Table 2 -- the same pair in the two modes\n")
    lines.append(md_table(["suite", "distinct pairs", "in both modes", "vector-clock only",
                           "scalar-clock only"], rows))

    # table 3: what the bins contain (the any-semantics of the partial and branch-arm bins, made
    # visible), per suite and mode
    rows = []
    for s in suites + ["all"]:
        for m in xc.MODES:
            c = collections.Counter()
            for r in ok:
                if (s != "all" and r["suite"] != s) or r["mode"] != m:
                    continue
                for p in r["pairs"]:
                    d = p["detail"]
                    if p["bin"] == "other":
                        c["other-nobar" if not d.get("between") else "other-bar"] += 1
                    if p["bin"] == "partial participation":
                        t = d["partial"]
                        c["ws"] += any("WARPSYNC" in x for x in t)
                        c["bc"] += any("count=" in x for x in t)
                        c["nofull"] += d.get("full_bar_between", 0) == 0
                    if p["bin"] == "branch arm":
                        c["arm"] += 1
                        c["arm-all"] += len(d["not_postdom"]) == len(d["between"])
                    if p["bin"] == "early exit":
                        c["exit"] += 1
            if any(c.values()):
                rows.append([s, m, c["ws"], c["bc"], c["nofull"], c["exit"], c["arm"],
                             c["arm-all"], c["other-nobar"], c["other-bar"]])
    lines.append("### Table 3 -- what the bins contain\n")
    lines.append(md_table(["suite", "mode", "partial: a WARPSYNC between",
                           "partial: a BAR with a count operand",
                           "partial: no full-block BAR between u and v", "early exit",
                           "branch arm", "branch arm: every barrier between is outside postdom(u)",
                           "other: no qualifying barrier between u and v",
                           "other: a barrier between, none of the tests fired"], rows))

    # table 5: the pairs of the "other" bin, from the explain pass (verdict-record fields)
    ex = Path(a.outdir) / "bo_explain.jsonl"
    if ex.exists():
        c = collections.Counter()
        seen = set()
        for ln in open(ex):
            e = json.loads(ln)
            for p in e["pairs"]:
                c[(e["suite"], e["mode"], p["space"], tuple(p["observed"]), tuple(p["strength"]),
                   p["warp_same_inst"], p["event_candidate"], p["edge_rescued"],
                   tuple(p["race_type"]))] += 1
        lines.append("\n### Table 5 -- the pairs of the `other` bin: fields of their verdict records\n")
        lines.append(md_table(
            ["suite", "mode", "space", "observed distance", "R1 strength", "warp-same-instruction",
             "event candidate", "edge rescued", "race type", "pairs"],
            [list(map(lambda x: "/".join(x) if isinstance(x, tuple) else x, k)) + [n]
             for k, n in sorted(c.items(), key=str)]))
        lines.append("")

    # table 6: CFG facts of the partial / early-exit / branch-arm pairs (vector-clock records)
    cf = Path(a.outdir) / "bo_cfgfacts.jsonl"
    if cf.exists():
        c = collections.Counter()
        for ln in open(cf):
            e = json.loads(ln)
            for p in e["pairs"]:
                c[(e["suite"], p["bin"], p["u_in_barrier_loop"], p["v_in_barrier_loop"])] += 1
        lines.append("\n### Table 6 -- the partial / early-exit / branch-arm pairs: is u (v) inside a "
                     "natural loop that contains a BAR? (pairs; the two modes have the same pairs)\n")
        lines.append(md_table(["suite", "bin", "u in a barrier loop", "v in a barrier loop", "pairs"],
                              [list(k) + [n] for k, n in sorted(c.items(), key=str)]))
        lines.append("")

    # table 4: re-analysis vs the confirm files
    c = collections.Counter()
    bad_ids = []
    for r in ok:
        c["files"] += 1
        c["same_ids"] += bool(r["same_ids"])
        c["same_sc"] += bool(r["same_sc"])
        if not (r["same_ids"] and r["same_sc"]):
            bad_ids.append((r["id"], r["mode"]))
    lines.append("### Table 4 -- the re-analysis against the X1 confirm files\n")
    lines.append(f"{c['files']} files re-analysed; report ids identical to the confirm file's: "
                 f"{c['same_ids']}; SC-report count identical: {c['same_sc']}.")
    if bad_ids:
        lines.append("Differing: " + ", ".join(f"{i} ({m})" for i, m in bad_ids[:40]))
    if bad:
        lines.append("\nFailed keys: " + ", ".join(
            f"{r['id']} {r['mode']} ({r['reason']})" for r in bad[:40]))
    if missing:
        lines.append("\nNot run: " + ", ".join(f"{i} {m}" for i, m in missing[:40]))
    lines.append("")
    lines.append("### Skipped at planning\n")
    lines.append(md_table(["suite", "mode", "reason", "keys"], plan["skipped"]))
    (outdir / "barrier_ordered_tables.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def cmd_scan(a):
    """Barrier-ordered pairs in the confirm files themselves."""
    n = withb = 0
    classes = collections.Counter()
    for d in a.dirs:
        for f in glob.glob(f"{d}/*.json"):
            j = json.loads(Path(f).read_text())
            n += 1
            has = False
            for key in ("raw", "raw_sc"):
                for r in j.get(key, []):
                    for fld in ("hb_class", "matrix_class"):
                        classes[(key, fld, r.get(fld))] += 1
                        has = has or r.get(fld) == "barrier-ordered"
            withb += has
    print(f"{n} confirm files in {len(a.dirs)} directories; {withb} carry a barrier-ordered pair")
    for k, v in sorted(classes.items(), key=lambda kv: -kv[1]):
        print(" ", k, v)


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--view", default="/mnt/beegfs/fzheng4/cuvein_traces/final-2026-10-view")
    p.add_argument("--confirm-root", default="/home/fzheng4/AccelProf/eval/baselines")
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("collect")
    p.add_argument("--plan", required=True)
    p.add_argument("--shard", required=True, help="k/n")
    p.add_argument("--out", required=True, help="jsonl; {shard} is replaced by k")
    p.add_argument("--analysis-timeout", type=int, default=14400)
    p.add_argument("--mem-gb", type=float, default=0)
    p.add_argument("--only", default="", help="regex on the program id (pilot runs)")
    p.set_defaults(fn=cmd_collect)
    p = sub.add_parser("explain")
    p.add_argument("--plan", required=True)
    p.add_argument("--inputs", required=True, help="glob of the shard jsonl files")
    p.add_argument("--out", required=True)
    p.add_argument("--analysis-timeout", type=int, default=14400)
    p.add_argument("--mem-gb", type=float, default=0)
    p.set_defaults(fn=cmd_explain)
    p = sub.add_parser("cfgfacts")
    p.add_argument("--plan", required=True)
    p.add_argument("--inputs", required=True, help="glob of the shard jsonl files")
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_cfgfacts)
    p = sub.add_parser("resplit")
    p.add_argument("--plan", required=True)
    p.add_argument("--base-n", type=int, required=True, help="shard count of the original run")
    p.add_argument("--shards", type=int, nargs="+", required=True)
    p.add_argument("--done", required=True, help="glob of the shard outputs so far")
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_resplit)
    p = sub.add_parser("report")
    p.add_argument("--plan", required=True)
    p.add_argument("--inputs", required=True, help="glob of the shard jsonl files")
    p.add_argument("--outdir", required=True)
    p.set_defaults(fn=cmd_report)
    p = sub.add_parser("confirm-scan")
    p.add_argument("dirs", nargs="+")
    p.set_defaults(fn=cmd_scan)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

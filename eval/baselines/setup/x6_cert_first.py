#!/usr/bin/env python3
"""X6: the certificate-first dry run (offline analysis; no detector change, no GPU).

cuRace runs the clock on every access and the certificates afterwards. The proposed variant runs
the certificates first, on the reuse graph, and tracks only the pcs they leave open. This script
measures, per (program, mode) of the X1b recording, which pcs would be left open and what fraction
of the recorded accesses they carry. Everything it reads is existing: the kernel JSONs of the
final-2026-11 view (cuVein's reuse edges, hb_sync_pass, per-pc statistics), the CFG dots next to
them, the merged X1b CSV and the X1b confirm files. Stores are read-only.

Definitions (as implemented):

 1. Candidate pairs. Per kernel JSON (one launch): the undirected graph whose vertices are the
    memory pcs (the JSON's `nodes`) and whose edges are the reuse edges (`edges` with an ancient
    pc and no cold miss). Two pcs in one connected component may share a location. A candidate
    pair is {u, v} (u == v allowed) in one component with at least one write or atomic (access
    from sync_dominance.parse_flags, `atomic` for an RMW opcode); a pc paired with itself needs
    that pc to write. The pair's distance d is the widest distance class of any edge in its
    component: GRID > BLOCK > WARP (intra_warp, or intra_instance_launch, which the verdict layer
    also reads as WARP) > NONE (only intra_thread edges, or no edge). Over-approximate: a pc is
    paired with every pc of its component, not only those it shares a location with.
    Class: SC if HBGraph.coherence(u, v) >= d (both strong, the strength rule of the sidecar =
    sync_dominance.coherent_scope), else DR. `d12` marks the pairs of two RMW atomics with
    coherence >= d, which the verdict layer does not count as a conflict (D12); they stay
    candidates (the brief's definition), and a second open-pc count leaves them out.
 2. Settled pairs. A candidate pair is settled when HBGraph.dominance(u, v) (the call the verdict
    layer makes: R1, the barrier/warpsync dominance certificate) returns a scope >= d; a pair
    with d == NONE (the component has no cross-thread edge) is settled trivially (every scope
    is >= NONE) and counted apart. u == v is never settled (dominance returns NONE for one
    region). No atomic-chain certificate (R3) and no R2: a pair only the chain could settle is
    open. The cp.async exception the verdict layer applies after dominance (judge(): a copy as
    the earlier access gets no R1 credit) is NOT applied.
 3. Open pcs. A pc is open when it belongs to at least one open candidate pair.

Kernel identity across launches: (dot, mangled kernel name). A (kernel, pc) is open when it is open
in at least one launch; a candidate pair counts once per (kernel, pc pair) and is open if open in at
least one launch; its distance in the count is that of the launch where it was open (else the widest).
Records on a pc: nodes[].active_lane_count (histogram: lane count -> warp-level records of that pc);
sum = warp-level records, sum(lanes * n) = lane accesses; local-space pcs are left out (the HB
record stream carries none, I5) and counted apart.

Checks run per (program, mode):
 (a) every pair of every launch's hb_sync_pass is a candidate pair (same component, at least one
     write) of that launch's graph;
 (b) every RACE / SC report of the X1b confirm file (the verdict layer's output) is an open
     candidate pair of some kernel of the program (existential over kernels: the confirm files
     do not name the kernel);
 (c) informational: hb_sync_pass pairs whose recorded distance exceeds the component's d.

Usage:  x6_cert_first.py [--only REGEX] [--workers N] [--out-dir DIR] ...
"""
import argparse
import collections
import csv
import glob
import json
import multiprocessing
import multiprocessing.connection
import os
import re
import statistics
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = HERE.parents[2]                                # eval/baselines/setup -> checkout root
sys.path.insert(0, str(WT / "python"))
import sync_dominance as sd                         # noqa: E402
import networkx as nx                               # noqa: E402
import pydot                                        # noqa: E402

NONE, WARP, BLOCK, GRID = sd.NONE, sd.WARP, sd.BLOCK, sd.GRID
MODES = ("scalar-clock", "vector-clock")
HECB = ("P7", "P9")
FLOOR_US = 0.075          # X1-follow collector-only cost, measured on heartwall and knn only
CODE = 1 << 32


# ---------------------------------------------------------------------------- CFG binning
# Copied verbatim from eval/baselines/setup/barrier_ordered_bins.py of origin/eval/x5-static-dynamic
# (1a2f1da): the X5 bins of a pc pair. Used only for the narrative programs (--detail).
PRED = re.compile(r"!?U?P[T0-9]+")
ZERO = re.compile(r"0x0+|0")


def sync_operands(dot_path, mangled):
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
        self.eng, self.ops = eng, ops
        self.exits = {pc for pc, op in eng.pc_opcode.items() if sd.classify(op) == "exit"}
        self._reach, self._ir, self._loops = {}, {}, None

    def reach(self, node):
        r = self._reach.get(node)
        if r is None:
            r = self._reach[node] = nx.descendants(self.eng.G, node) | {node}
        return r

    def ins_reach(self, start, block=None):
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
        if self._loops is None:
            G, dom, syncs = self.eng.G, self.eng.dom, self.eng.syncs
            heads = {}
            for t, h in G.edges():
                if h in dom.get(t, ()):
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


# ---------------------------------------------------------------------------- per-key analysis

class KeyAbort(Exception):
    pass


def edge_class(dist):
    """Widest distance class of one reuse edge's `dist` buckets (sync_dominance._observed, plus
    intra_instance_launch -> WARP, as judge() reads a warp-same-instruction conflict)."""
    for sc, key in ((GRID, "intra_grid"), (BLOCK, "intra_block"), (WARP, "intra_warp")):
        if dist.get(key, 0) > 0:
            return sc
    return WARP if dist.get("intra_instance_launch", 0) > 0 else NONE


class Dsu:
    def __init__(self, items):
        self.p = {x: x for x in items}

    def find(self, x):
        p = self.p
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


class Kern:
    """Accumulators of one kernel (dot, mangled) over the launches of a recording."""

    def __init__(self, dot, mangled, eng):
        self.dot, self.mangled, self.eng = dot, mangled, eng
        self.dom_memo = {}
        self.pcs = {}            # pc -> access ('read'/'write'/'atomic')
        self.space = {}          # pc -> space
        self.rec = collections.Counter()      # pc -> warp-level records (non-local)
        self.lanes = collections.Counter()    # pc -> lane accesses (non-local)
        self.cand = set()        # pair codes
        self.trivial = set()     # candidate pairs whose component has d == NONE (settled trivially)
        self.open = {}           # pair code -> mask: 1 some open instance DR, 2 some SC, 4 some non-d12
        self.open_d = {}         # pair code -> d at which it was open
        self.dpc = collections.Counter()      # pc -> widest component d over launches
        self.seen = set()        # component keys already enumerated
        self.syncpass = {}       # (a, b) -> [first json, widest recorded dist, widest d, launches]
        self.nlaunch = 0
        self.violations = {}     # check (a): (a, b) -> reason
        self.sp_entries = 0

    def dom(self, u, v):
        if u == v:
            return NONE
        ru, rv = self.eng.pc_node[u], self.eng.pc_node[v]
        k = (ru, rv) if ru <= rv else (rv, ru)
        got = self.dom_memo.get(k)
        if got is None:
            got = self.dom_memo[k] = self.eng.dominance(u, v)[0]
        return got


def comp_counts(n, w):
    """Candidate pairs of a component with n pcs, w writers/atomics: w self pairs + the
    conflicting unordered pairs of distinct pcs."""
    r = n - w
    return w + n * (n - 1) // 2 - r * (r - 1) // 2


class Recording:
    def __init__(self, depdir, deadline, pair_cap):
        self.depdir, self.deadline, self.pair_cap = depdir, deadline, pair_cap
        self.dots = sorted(glob.glob(f"{Path(depdir).parent}/dots/*.dot"))
        self.parsed = {}         # dot -> kernels dict or None
        self.engs = {}           # (dot, mangled) -> HBGraph
        self.sel = {}            # (dot, kernel_name) -> mangled or None
        self.kerns = {}          # (dot, mangled) -> Kern
        self.fit_memo = {}       # kernel_name -> (dot, mangled) or None
        self.pairs_seen = 0

    def kernels_of(self, dot):
        if dot not in self.parsed:
            try:
                self.parsed[dot] = sd.parse_dot(dot)
            except sd.AlignmentError:
                self.parsed[dot] = None
        return self.parsed[dot]

    def fit(self, trace):
        """The first dot whose kernel fits the trace, as rc._analyze_reports + analyze() choose
        (AlignmentError -> next dot) -> Kern, or None."""
        name = trace["kernel"]["kernel_name"]
        pcs = {n["pc"] for n in trace.get("nodes", [])} | \
            {e[k] for e in trace.get("edges", []) for k in ("current_pc", "ancient_pc")
             if e.get(k) is not None}
        for dot in self.dots:
            ks = self.kernels_of(dot)
            if ks is None:
                continue
            key = (dot, name)
            if key not in self.sel:
                try:
                    self.sel[key] = sd.select_kernel(ks, name)
                except sd.AlignmentError:
                    self.sel[key] = None
            mangled = self.sel[key]
            if mangled is None:
                continue
            kk = (dot, mangled)
            if kk not in self.engs:
                self.engs[kk] = sd.HBGraph(*ks[mangled])
                self.kerns[kk] = Kern(dot, mangled, self.engs[kk])
            eng = self.engs[kk]
            if all(pc in eng.pc_opcode and sd.classify(eng.pc_opcode[pc]) == "mem" for pc in pcs):
                return self.kerns[kk]
        return None

    def tick(self):
        if time.time() > self.deadline:
            raise KeyAbort("analysis-timeout")


def analyze_launch(R, K, trace, jname):
    """Fold one launch (kernel JSON) into the kernel's accumulators."""
    eng = K.eng
    K.nlaunch += 1
    nodes = trace.get("nodes", [])
    atom = {n["pc"] for n in nodes if sd.atomic_scope(eng.pc_opcode[n["pc"]]) is not None}
    coh = {n["pc"]: sc for n in nodes
           if (sc := sd.coherent_scope(eng.pc_opcode[n["pc"]])) is not None}
    acc, local, lane_sum = {}, set(), 0
    for n in nodes:
        pc = n["pc"]
        space, access = sd.parse_flags(n["flags"])
        if pc in atom:
            access = "atomic"
        acc[pc] = access
        K.pcs[pc], K.space[pc] = access, space
        hist = n.get("active_lane_count") or {}
        if space == "local":
            local.add(pc)
            continue
        K.rec[pc] += sum(hist.values())
        ln = sum(int(k) * v for k, v in hist.items())
        K.lanes[pc] += ln
        lane_sum += ln
    stats = {"lane_mismatch": int(lane_sum != int(trace.get("hb_lanes_count") or 0)),
             "hb_events": int(trace.get("hb_events_count") or 0),
             "hb_lanes": int(trace.get("hb_lanes_count") or 0), "lanes_hist": lane_sum}
    # the reuse graph
    dsu = Dsu(acc)
    dcls = {}
    off_node = 0
    ed = []
    for e in trace.get("edges", []):
        cur, anc = e["current_pc"], e.get("ancient_pc")
        if e.get("cold_miss") or anc is None:
            continue
        if cur not in acc or anc not in acc:
            off_node += 1
            continue
        ed.append((cur, anc, edge_class(e.get("dist", {}))))
    for cur, anc, _ in ed:
        dsu.union(cur, anc)
    comps = collections.defaultdict(list)
    for pc in acc:
        comps[dsu.find(pc)].append(pc)
    cd = collections.Counter()
    for cur, anc, c in ed:
        r = dsu.find(cur)
        if c > cd[r]:
            cd[r] = c
    stats["edge_off_node"] = off_node
    comp_of, d_of = {}, {}
    for r, pcs in comps.items():
        d = cd[r]
        for pc in pcs:
            comp_of[pc] = r
            d_of[pc] = d
            if d > K.dpc[pc]:
                K.dpc[pc] = d
    for r, pcs in comps.items():
        R.tick()
        d = cd[r]
        P = sorted(pcs)
        wr = frozenset(pc for pc in P if acc[pc] != "read")
        key = (tuple(P), wr, d)
        if key in K.seen:
            continue
        K.seen.add(key)
        R.pairs_seen += comp_counts(len(P), len(wr))
        if R.pairs_seen > R.pair_cap:
            raise KeyAbort(f"pair-cap({R.pair_cap})")
        for i, u in enumerate(P):
            wu = u in wr
            for v in P[i:]:
                if not (wu or v in wr):
                    continue
                code = u * CODE + v
                K.cand.add(code)
                if d == NONE:
                    K.trivial.add(code)
                    continue
                if u != v and K.dom(u, v) >= d:
                    continue
                strong = u in coh and v in coh and min(coh[u], coh[v]) >= d   # R2: the class
                d12 = u in atom and v in atom and strong
                m = (2 if strong else 1) | (0 if d12 else 4)
                K.open[code] = K.open.get(code, 0) | m
                if code not in K.open_d or d > K.open_d[code]:
                    K.open_d[code] = d
    # check (a), (c): hb_sync_pass
    sp = trace.get("hb_sync_pass") or []
    for a, b, n, dist, f, s in sp:
        K.sp_entries += 1
        lo, hi = (a, b) if a <= b else (b, a)
        ent = K.syncpass.get((lo, hi))
        if ent is None:
            ent = K.syncpass[(lo, hi)] = [jname, dist, d_of.get(lo, -1), 1]
        else:
            ent[1] = max(ent[1], dist)
            ent[3] += 1
        if lo not in acc or hi not in acc:
            reason = "pc not a memory pc of the kernel (not in nodes)"
        elif comp_of[lo] != comp_of[hi]:
            reason = "different components"
        elif acc[lo] == "read" and acc[hi] == "read":
            reason = "both reads"
        elif lo == hi and acc[lo] == "read":
            reason = "both reads"
        else:
            reason = None
            ent[2] = max(ent[2], d_of[lo])
        if reason and (lo, hi) not in K.violations:
            K.violations[(lo, hi)] = (reason, jname)
    return stats


def read_confirm(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception as e:                           # noqa: BLE001 -- reported
        return {"error": f"{type(e).__name__}:{e}"}


def check_b(R, kerns, conf):
    """Check (b): every RACE / SC report of the confirm file is an open candidate pair of some
    kernel of the program."""
    out = {"checked": 0, "host_skipped": 0, "exceptions": []}
    if conf is None or "error" in conf:
        out["error"] = (conf or {}).get("error", "no confirm file")
        return out
    reports = [("RACE", r) for r in conf.get("raw", [])] + \
              [("SC", r) for r in conf.get("raw_sc", [])]
    for kind, r in reports:
        a, b = r.get("a_pc"), r.get("b_pc")
        if r.get("host") or a is None or b is None:
            out["host_skipped"] += 1
            continue
        out["checked"] += 1
        lo, hi = (a, b) if a <= b else (b, a)
        code = lo * CODE + hi
        in_k = [K for K in kerns if lo in K.pcs and hi in K.pcs]
        if any(code in K.open for K in in_k):
            continue
        if not in_k:
            reason = "a pc is not a memory pc of any kernel of the recording"
        elif any(code in K.cand for K in in_k):
            sc = in_k[0].dom(lo, hi) if lo != hi else NONE
            triv = all(code in K.trivial for K in in_k if code in K.cand)
            reason = ("candidate, settled trivially: its component has no cross-thread edge"
                      if triv else
                      f"candidate, settled by dominance (scope {sd.SCOPES[sc]} >= the component's d)")
        elif all(K.pcs[lo] == "read" and K.pcs[hi] == "read" for K in in_k):
            reason = "not a candidate: both pcs read"
        else:
            reason = "not a candidate: no launch puts the two pcs in one component"
        out["exceptions"].append({"kind": kind, "a_pc": a, "b_pc": b, "space": r.get("space"),
                                  "race_type": r.get("race_type"), "reason": reason})
    return out


def analyze_key(job):
    """One (program, mode) recording -> a row dict."""
    pid, mode, depdir = job["id"], job["mode"], job["dir"]
    t0 = time.time()
    row = {"id": pid, "mode": mode, "suite": pid.split("-", 1)[0], "dir": depdir,
           "reason": "", "node": os.uname().nodename}
    R = Recording(depdir, t0 + job["timeout"], job["pair_cap"])
    kjs = sorted(glob.glob(f"{depdir}/kernel_*.json"))
    row["n_json"] = len(kjs)
    try:
        if not kjs:
            raise KeyAbort("no-kernel-json")
        unmatched, mism, edge_off = 0, 0, 0
        ev_total = lanes_total = 0
        for kj in kjs:
            R.tick()
            trace = json.loads(Path(kj).read_text())
            K = R.fit(trace)
            if K is None:
                unmatched += 1
                continue
            st = analyze_launch(R, K, trace, os.path.basename(kj))
            mism += st["lane_mismatch"]
            edge_off += st["edge_off_node"]
            ev_total += st["hb_events"]
            lanes_total += st["hb_lanes"]
        row.update(unmatched_json=unmatched, lane_mismatch_json=mism, edge_off_node=edge_off,
                   hb_events=ev_total, hb_lanes=lanes_total)
        kerns = [K for K in R.kerns.values() if K.nlaunch]
        mem_pcs = cand = trivial = opn = 0
        open_pcs = open_pcs_nod12 = 0
        rec_all = rec_open = ln_all = ln_open = rec_open_nod12 = 0
        open_dr = open_sc = open_d12 = 0
        local_pcs = 0
        for K in kerns:
            op, opn12 = set(), set()
            for code, m in K.open.items():
                u, v = divmod(code, CODE)
                op.add(u)
                op.add(v)
                if m & 4:
                    opn12.add(u)
                    opn12.add(v)
                open_dr += bool(m & 1)
                open_sc += bool(m & 2) and not (m & 1)
                open_d12 += not (m & 4)
            nl = [pc for pc in K.pcs if K.space[pc] != "local"]
            local_pcs += len(K.pcs) - len(nl)
            mem_pcs += len(K.pcs)
            cand += len(K.cand)
            trivial += len(K.trivial)
            opn += len(K.open)
            open_pcs += len(op)
            open_pcs_nod12 += len(opn12)
            for pc in nl:
                rec_all += K.rec[pc]
                ln_all += K.lanes[pc]
                if pc in op:
                    rec_open += K.rec[pc]
                    ln_open += K.lanes[pc]
                if pc in opn12:
                    rec_open_nod12 += K.rec[pc]
        row.update(n_kernels=len(kerns), mem_pcs=mem_pcs, local_pcs=local_pcs, cand_pairs=cand,
                   settled_pairs=cand - opn, trivial_pairs=trivial, open_pairs=opn,
                   open_pairs_dr=open_dr, open_pairs_sc=open_sc, open_pairs_d12_only=open_d12,
                   open_pcs=open_pcs, open_pcs_nod12=open_pcs_nod12,
                   rec_all=rec_all, rec_open=rec_open, lanes_all=ln_all, lanes_open=ln_open,
                   rec_open_nod12=rec_open_nod12)
        # check (a) / (c)
        chk = {"entries": sum(K.sp_entries for K in kerns),
               "distinct": sum(len(K.syncpass) for K in kerns), "violations": [],
               "dist_exceeds": 0, "dist_exceeds_open_at_dist": 0}
        for K in kerns:
            for (lo, hi), (j, dist, dd, nl_) in K.syncpass.items():
                if (lo, hi) in K.violations:
                    reason, jj = K.violations[(lo, hi)]
                    chk["violations"].append({"kernel": K.mangled, "json": jj, "pcs": [lo, hi],
                                              "reason": reason})
                elif dd >= 0 and dist > dd:
                    chk["dist_exceeds"] += 1
                    if lo == hi or K.dom(lo, hi) < dist:
                        chk["dist_exceeds_open_at_dist"] += 1
        row["check_a"] = chk
        row["check_b"] = check_b(R, kerns, read_confirm(job["confirm"]) if job.get("confirm") else None)
        if job.get("detail"):
            row["detail"] = make_detail(kerns, R)
    except KeyAbort as e:
        row["reason"] = str(e)
    except MemoryError:
        row["reason"] = "memory-error"
    except Exception as e:                           # noqa: BLE001 -- reported, never swallowed
        row["reason"] = f"exception:{type(e).__name__}:{str(e)[:200]}:{traceback.format_exc()[-300:]}"
    row["elapsed"] = round(time.time() - t0, 1)
    return row


def make_detail(kerns, R, top=8, partners=6):
    """For the narrative programs: per kernel, the open pcs with the most records, their opcodes
    and the open pairs that keep them open (with the X5 bin of the pair)."""
    out = []
    tot = sum(sum(K.rec[pc] for pc in K.pcs if K.space[pc] != "local") for K in kerns) or 1
    for K in sorted(kerns, key=lambda K: -sum(K.rec.values())):
        if not K.open:
            out.append({"kernel": K.mangled, "dot": os.path.basename(K.dot), "open_pcs": 0,
                        "records": sum(K.rec.values()), "launches": K.nlaunch,
                        "mem_pcs": len(K.pcs)})
            continue
        part = collections.defaultdict(list)
        for code, m in K.open.items():
            u, v = divmod(code, CODE)
            part[u].append((v, m, K.open_d[code]))
            if v != u:
                part[v].append((u, m, K.open_d[code]))
        binner = None
        rows = []
        for pc in sorted(part, key=lambda p: -K.rec[p])[:top]:
            if binner is None:
                binner = CfgBinner(K.eng, sync_operands(K.dot, K.mangled))
            ps = []
            for v, m, d in sorted(part[pc], key=lambda x: (-K.rec[x[0]], x[0]))[:partners]:
                b, det = binner.bin(*sorted((pc, v)))
                ps.append({"partner": v, "opcode": K.eng.pc_opcode[v], "access": K.pcs[v],
                           "d": sd.SCOPES[d], "class": "DR" if m & 1 else "SC",
                           "d12": not (m & 4), "bin": b, "dom": sd.SCOPES[K.dom(pc, v)],
                           "between": det.get("between", [])[:3]})
            rows.append({"pc": pc, "opcode": K.eng.pc_opcode[pc], "access": K.pcs[pc],
                         "space": K.space[pc], "records": K.rec[pc],
                         "n_open_partners": len(part[pc]), "partners": ps})
        n_open_pcs = len(part)
        out.append({"kernel": K.mangled, "dot": os.path.basename(K.dot), "launches": K.nlaunch,
                    "mem_pcs": len(K.pcs), "open_pcs": n_open_pcs,
                    "records": sum(K.rec.values()),
                    "records_open": sum(K.rec[pc] for pc in part if K.space[pc] != "local"),
                    "syncs": sorted({f"{hex(pc)} {op} [{sd.SCOPES[sc]}{'' if q else ',non-qualifying'}]"
                                     for pc, op, sc, q in K.eng.syncs.values()}),
                    "top": rows})
        if len(out) >= 12:
            break
    return {"total_records": tot, "kernels": out}


def _run(job):
    try:
        return analyze_key(job)
    except BaseException as e:                       # noqa: BLE001
        return {"id": job["id"], "mode": job["mode"], "suite": job["id"].split("-", 1)[0],
                "reason": f"fatal:{type(e).__name__}:{e}", "elapsed": 0}


# ---------------------------------------------------------------------------- plan / csv

def plan(view, confirm_dir, only, detail_re):
    jobs = []
    for pid in sorted(os.listdir(view)):
        if only and not re.search(only, pid):
            continue
        for mode in MODES:
            p = Path(view) / pid / mode
            if not p.exists():
                continue
            real = os.path.realpath(p)
            kb = sum(e.stat().st_size for e in os.scandir(real) if e.name.startswith("kernel_"))
            meta = {}
            try:
                m = json.loads(Path(real).parent.joinpath("meta.json").read_text())
                meta = m.get("modes", {}).get(mode, {})
            except Exception:                         # noqa: BLE001
                pass
            jobs.append({"id": pid, "mode": mode, "dir": real, "kbytes": kb,
                         "store": Path(real).parts[-3],
                         "partial": bool(meta.get("partial")),
                         "confirm": str(Path(confirm_dir) / f"{pid}__cuvein__{mode}.json"),
                         "detail": bool(detail_re and re.search(detail_re, pid) and
                                        mode == "scalar-clock")})
    return jobs


def load_csv(path):
    g = collections.defaultdict(list)
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            g[(r["id"], r["mode"])].append(r)
    out = {}
    for k, rs in g.items():
        ev = None
        for r in rs:
            m = re.search(r"(?:^|;)events=(\d+)", r.get("notes", ""))
            if m:
                ev = int(m.group(1))
                break
        w = [float(r["wall_s"]) for r in rs if r["wall_s"]]
        n = [float(r["native_wall_s"]) for r in rs if r["native_wall_s"]]
        out[k] = {"verdicts": sorted({r["verdict"] for r in rs}),
                  "tool_wall": statistics.median(w) if w else None,
                  "native_wall": statistics.median(n) if n else None,
                  "events": ev, "reps": len(rs),
                  "timed_out": any(r["verdict"] in ("TIMEOUT", "ERROR") for r in rs)}
    return out


# ---------------------------------------------------------------------------- report tables

def fmt(x, nd=3):
    if x is None:
        return "missing"
    if isinstance(x, float):
        return f"{x:.{nd}g}" if abs(x) < 1000 else f"{x:,.0f}"
    if isinstance(x, int):
        return f"{x:,}"
    return str(x)


def md(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def frac(r):
    if r.get("reason") or not r.get("rec_all"):
        return None
    return r["rec_open"] / r["rec_all"]


def primary_rows(rows):
    """One recording per program: scalar-clock, vector-clock only where scalar-clock has no
    finished kernel (no analysable row)."""
    by = collections.defaultdict(dict)
    for r in rows:
        by[r["id"]][r["mode"]] = r
    out = {}
    for pid, d in by.items():
        s, v = d.get("scalar-clock"), d.get("vector-clock")
        out[pid] = s if (s and not s.get("reason") and s.get("n_json")) else (v or s)
    return out


def quantiles(xs):
    xs = sorted(xs)
    if not xs:
        return ["missing"] * 5
    q = lambda p: xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]
    return [q(0), q(0.25), q(0.5), q(0.75), q(1)]


def render(rows, csvd, out_md):
    L = []
    for r in rows:
        c = csvd.get((r["id"], r["mode"]), {})
        r["c"] = c
    prim = primary_rows(rows)
    ok = [r for r in rows if not r.get("reason")]
    bad = [r for r in rows if r.get("reason")]
    L.append("## A. Run summary\n")
    L.append(f"(program, mode) recordings in the view: {len(rows)}; analysed: {len(ok)}; "
             f"not analysed: {len(bad)}.\n")
    if bad:
        L.append(md(["program", "mode", "reason"], [[r["id"], r["mode"], r["reason"][:160]] for r in bad]))
        L.append("")
    # --- checks
    L.append("## B. Coverage checks\n")
    ent = sum(r["check_a"]["entries"] for r in ok)
    dis = sum(r["check_a"]["distinct"] for r in ok)
    vio = [(r, v) for r in ok for v in r["check_a"]["violations"]]
    L.append(f"**(a) hb_sync_pass coverage.** (program, mode) recordings checked: {len(ok)} "
             f"(scalar-clock {sum(r['mode'] == 'scalar-clock' for r in ok)}, "
             f"vector-clock {sum(r['mode'] == 'vector-clock' for r in ok)}). hb_sync_pass entries "
             f"checked, summed over launches: {ent:,}; distinct (program, mode, kernel, pc pair): "
             f"{dis:,}. **Violations: {len(vio)}**" +
             (" in " + str(len({(r['id'], r['mode']) for r, _ in vio})) + " recordings." if vio else "."))
    L.append("")
    if vio:
        L.append(md(["program", "mode", "kernel", "json", "pcs", "reason"],
                    [[r["id"], r["mode"], v["kernel"][:60], v["json"],
                      f"{v['pcs'][0]:#x}, {v['pcs'][1]:#x}", v["reason"]] for r, v in vio]))
        L.append("")
    de = sum(r["check_a"]["dist_exceeds"] for r in ok)
    de2 = sum(r["check_a"]["dist_exceeds_open_at_dist"] for r in ok)
    L.append(f"(c) informational: {de:,} distinct hb_sync_pass pairs have a recorded distance wider "
             f"than their component's d; {de2:,} of them are not ordered by dominance at the "
             f"recorded distance.\n")
    chk_b = [r for r in ok if "error" not in r["check_b"]]
    nb = sum(r["check_b"]["checked"] for r in chk_b)
    hs = sum(r["check_b"]["host_skipped"] for r in chk_b)
    exb = [(r, e) for r in chk_b for e in r["check_b"]["exceptions"]]
    nobf = [r for r in ok if "error" in r["check_b"]]
    L.append(f"**(b) Race / Strong-conflict reports are open.** Confirm files read: {len(chk_b)} "
             f"(no file or unreadable: {len(nobf)}). Reports checked (RACE + SC, deduped by the "
             f"harness, host-copy reports excluded: {hs}): {nb:,}. **Exceptions: {len(exb)}** "
             f"in {len({(r['id'], r['mode']) for r, _ in exb})} recordings.")
    L.append("")
    if exb:
        cnt = collections.Counter(e["reason"] for _, e in exb)
        L.append(md(["reason", "reports"], [[k, v] for k, v in cnt.most_common()]))
        L.append("")
        L.append(md(["program", "mode", "kind", "pcs", "type", "reason"],
                    [[r["id"], r["mode"], e["kind"], f"{e['a_pc']:#x}, {e['b_pc']:#x}",
                      e["race_type"], e["reason"]] for r, e in exb]))
        L.append("")
    if nobf:
        L.append("No confirm file: " + ", ".join(f"{r['id']} ({r['mode']})" for r in nobf[:40]) + "\n")
    # --- per suite
    L.append("## C. Per suite\n")
    suites = sorted({r["suite"] for r in prim.values() if r})
    srows = []
    for s in suites:
        rs = [r for r in prim.values() if r and r["suite"] == s]
        a = [r for r in rs if not r.get("reason")]
        zero = [r for r in a if r["open_pcs"] == 0]
        fr = [frac(r) for r in a if frac(r) is not None]
        q = quantiles(fr)
        tot_all = sum(r["rec_all"] for r in a)
        tot_open = sum(r["rec_open"] for r in a)
        srows.append([s, len(rs), len(a), len(zero),
                      *[f"{x:.3f}" if isinstance(x, float) else x for x in q],
                      f"{tot_open / tot_all:.4f}" if tot_all else "missing"])
    L.append(md(["suite", "programs", "analysed", "zero open pcs", "frac min", "p25", "median",
                 "p75", "max", "pooled open/all records"], srows))
    L.append("\nPrimary recording per program = scalar-clock; vector-clock only where scalar-clock "
             "has no analysable kernel. 'frac' = records on open pcs / all non-local memory records "
             "of the recording; programs with no records are left out of the distribution. Pooled "
             "= sum over the suite's programs.\n")
    L.append("Programs with zero open pcs, per suite (the clock would have nothing to do):\n")
    for s in suites:
        z = sorted(r["id"] for r in prim.values() if r and r["suite"] == s and not r.get("reason")
                   and r["open_pcs"] == 0)
        L.append(f"- {s}: {len(z)}" + (" — " + ", ".join(z[:60]) + (" …" if len(z) > 60 else "") if z else ""))
    L.append("")
    # distribution histogram
    L.append("Open-record fraction, histogram of programs (primary recording):\n")
    bins = [0, 1e-12, 0.01, 0.1, 0.25, 0.5, 0.75, 0.99999, 1.0000001]
    names = ["0", "(0, 0.01)", "[0.01, 0.1)", "[0.1, 0.25)", "[0.25, 0.5)", "[0.5, 0.75)",
             "[0.75, 1)", "1"]
    hrows = []
    for s in suites:
        fr = [frac(r) for r in prim.values() if r and r["suite"] == s and frac(r) is not None]
        cnts = [0] * len(names)
        for x in fr:
            if x <= 0:
                cnts[0] += 1
            elif x >= 1:
                cnts[7] += 1
            else:
                for i, (lo, hi) in enumerate(zip([0, 0.01, 0.1, 0.25, 0.5, 0.75],
                                                 [0.01, 0.1, 0.25, 0.5, 0.75, 1])):
                    if lo <= x < hi:
                        cnts[1 + i] += 1
                        break
        hrows.append([s, len(fr), *cnts])
    L.append(md(["suite", "n"] + names, hrows))
    L.append("")
    # --- HeCBench
    L.append("## D. HeCBench (P7, P9), every program and mode\n")
    hr = []
    for r in sorted((r for r in rows if r["suite"] in HECB), key=lambda r: (r["id"], r["mode"])):
        c = r["c"]
        f = frac(r)
        today = c.get("tool_wall") / c["native_wall"] if c.get("tool_wall") and c.get("native_wall") else None
        ev = c.get("events")
        floor = FLOOR_US * 1e-6 * ev / c["native_wall"] if ev and c.get("native_wall") else None
        prod = f * today if (f is not None and today is not None) else None
        var = floor + f * (today - floor) if (f is not None and today is not None and floor is not None) else None
        uspr = c["tool_wall"] / ev * 1e6 if (c.get("tool_wall") and ev) else None
        hr.append([r["id"], r["mode"], ",".join(c.get("verdicts", [])) or "missing",
                   fmt(c.get("tool_wall")), fmt(c.get("native_wall")), fmt(today),
                   fmt(ev), fmt(uspr), fmt(floor) + ("†" if floor is not None else ""),
                   "missing (%s)" % (r["reason"] or "no records") if f is None else f"{f:.4f}",
                   fmt(prod), fmt(var) + ("†" if var is not None else "")])
    L.append(md(["program", "mode", "verdict", "tool wall s", "native s", "today ×", "events",
                 "today µs/rec", "floor ×†", "open-rec frac f", "f·today ×", "floor+f·(today−floor) ×†"], hr))
    L.append("\n† rests on the 0.075 µs/record collector-only cost (X1-follow: measured on heartwall "
             "and knn only, default worker count); the rest is the CSV (median of the reps) and "
             "this analysis. × = wall / native wall. events = the CSV's `events=` "
             "(hb_events_count: memory + barrier/exit/syncwarp records, local excluded). "
             "f uses memory records only. Rows with a TIMEOUT/ERROR verdict in some rep have "
             "no valid events.\n")
    f_h = [frac(r) for r in prim.values() if r and r["suite"] in HECB and frac(r) is not None]
    L.append(f"Median open-record fraction over the {len(f_h)} HeCBench programs with records "
             f"(primary recording): **{statistics.median(f_h):.4f}**." if f_h else "no HeCBench fractions")
    L.append("")
    # --- appendix
    L.append("## Appendix A. Every program, every mode\n")
    arows = []
    for r in sorted(rows, key=lambda r: (r["id"], r["mode"])):
        c = r["c"]
        if r.get("reason"):
            arows.append([r["id"], r["mode"], "missing", "", "", "", "", "", "", "",
                          ",".join(c.get("verdicts", [])), fmt(c.get("tool_wall")),
                          fmt(c.get("native_wall")), r["reason"][:60]])
            continue
        f = frac(r)
        arows.append([r["id"], r["mode"], r["mem_pcs"], r["cand_pairs"], r["settled_pairs"],
                      r["open_pairs"], r["open_pcs"],
                      f"{r['rec_open']:,} / {r['rec_all']:,}", "missing" if f is None else f"{f:.4f}",
                      "yes" if r["open_pcs"] == 0 else "",
                      ",".join(c.get("verdicts", [])) or "missing", fmt(c.get("tool_wall")),
                      fmt(c.get("native_wall")), ""])
    L.append(md(["program", "mode", "mem pcs", "cand pairs", "settled", "open pairs", "open pcs",
                 "records on open / all", "frac", "zero open", "verdict", "tool wall s",
                 "native s", "note"], arows))
    Path(out_md).write_text("\n".join(L) + "\n")


def write_csv(rows, csvd, path):
    cols = ["id", "suite", "mode", "dir", "reason", "elapsed", "node", "n_json", "n_kernels",
            "unmatched_json", "lane_mismatch_json", "edge_off_node", "mem_pcs", "local_pcs",
            "cand_pairs", "settled_pairs", "trivial_pairs", "open_pairs", "open_pairs_dr",
            "open_pairs_sc", "open_pairs_d12_only", "open_pcs", "open_pcs_nod12", "rec_all",
            "rec_open", "rec_open_nod12", "lanes_all", "lanes_open", "hb_events", "hb_lanes"]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols + ["frac_open_rec", "csv_verdicts", "csv_tool_wall_s", "csv_native_wall_s",
                           "csv_events", "check_a_entries", "check_a_violations", "check_b_checked",
                           "check_b_exceptions"])
        for r in sorted(rows, key=lambda r: (r["id"], r["mode"])):
            c = csvd.get((r["id"], r["mode"]), {})
            ca, cb = r.get("check_a", {}), r.get("check_b", {})
            fr = frac(r)
            w.writerow([r.get(k, "") for k in cols] +
                       ["" if fr is None else f"{fr:.6f}", "|".join(c.get("verdicts", [])),
                        c.get("tool_wall", ""), c.get("native_wall", ""), c.get("events", ""),
                        ca.get("entries", ""), len(ca.get("violations", [])) if ca else "",
                        cb.get("checked", ""), len(cb.get("exceptions", [])) if cb else ""])


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("--view", default="/mnt/beegfs/fzheng4/cuvein_traces/final-2026-11-view")
    ap.add_argument("--confirm", default=os.path.expanduser("~/x1b/confirm_final-b-merged"))
    ap.add_argument("--csv", required=True, help="the merged X1b baselines-cuvein.csv")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--detail", default=r"^(P7-(heartwall|pathfinder|srad|nbody|particlefilter)|"
                                        r"P9-(tridiagonal|dxtc2))-cuda$")
    ap.add_argument("--workers", type=int, default=int(os.environ.get("SLURM_CPUS_ON_NODE", 16)))
    ap.add_argument("--key-timeout", type=float, default=7200)
    ap.add_argument("--pair-cap", type=int, default=60_000_000)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--render-only", action="store_true")
    a = ap.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    jl = out / "rows.jsonl"
    csvd = load_csv(a.csv)
    done = {}
    if (a.resume or a.render_only) and jl.exists():
        for ln in open(jl):
            try:
                r = json.loads(ln)
                done[(r["id"], r["mode"])] = r
            except Exception:                         # noqa: BLE001
                pass
    if not a.render_only:
        jobs = plan(a.view, a.confirm, a.only, a.detail)
        for j in jobs:
            j["timeout"], j["pair_cap"] = a.key_timeout, a.pair_cap
        todo = [j for j in jobs if (j["id"], j["mode"]) not in done]
        todo.sort(key=lambda j: -j["kbytes"])
        print(f"{len(jobs)} recordings in the view, {len(todo)} to do, {a.workers} workers",
              flush=True)
        if not a.resume and jl.exists():
            jl.unlink()
        ctx = multiprocessing.get_context("fork")

        def child(job, conn):
            conn.send(_run(job))
            conn.close()

        active, n, queue_ = {}, 0, list(todo)       # conn -> (proc, job, start)
        with open(jl, "a") as fo:
            while queue_ or active:
                while queue_ and len(active) < a.workers:
                    job = queue_.pop(0)
                    rc_, wc_ = ctx.Pipe(duplex=False)
                    p = ctx.Process(target=child, args=(job, wc_))
                    p.start()
                    wc_.close()
                    active[rc_] = (p, job, time.time())
                ready = multiprocessing.connection.wait(list(active), timeout=30)
                now = time.time()
                for conn in list(active):
                    p, job, t0 = active[conn]
                    r = None
                    if conn in ready:
                        try:
                            r = conn.recv()
                        except EOFError:     # the worker died without a result
                            p.join()
                            r = {"id": job["id"], "mode": job["mode"],
                                 "suite": job["id"].split("-", 1)[0],
                                 "reason": f"worker-died(rc={p.exitcode})",
                                 "elapsed": round(now - t0, 1)}
                    elif now - t0 > a.key_timeout + 600:    # hard cap: the analysis never yielded
                        p.kill()
                        r = {"id": job["id"], "mode": job["mode"],
                             "suite": job["id"].split("-", 1)[0],
                             "reason": "analysis-timeout(hard-kill)", "elapsed": round(now - t0, 1)}
                    if r is None:
                        continue
                    p.join()
                    conn.close()
                    del active[conn]
                    n += 1
                    done[(r["id"], r["mode"])] = r
                    fo.write(json.dumps(r, separators=(",", ":")) + "\n")
                    fo.flush()
                    print(f"[{n}/{len(todo)}] {r['id']} {r['mode']} {r.get('reason') or 'ok'} "
                          f"{r['elapsed']}s open_pcs={r.get('open_pcs')} rec={r.get('rec_open')}/"
                          f"{r.get('rec_all')}", flush=True)
    rows = list(done.values())
    for r in rows:
        r["c"] = csvd.get((r["id"], r["mode"]), {})
    write_csv(rows, csvd, out / "rows.csv")
    render(rows, csvd, out / "tables.md")
    det = {f"{r['id']}": r["detail"] for r in rows if r.get("detail")}
    (out / "detail.json").write_text(json.dumps(det, indent=1))
    print(f"wrote {out}/rows.csv tables.md detail.json", flush=True)


if __name__ == "__main__":
    main()

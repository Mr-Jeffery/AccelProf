#!/usr/bin/env python3
"""
Scoped happens-before data-race verdicts: join a kernel CFG (nvdisasm -bbcfg
-poff dot, from getall.sh) with its cuVein pc_dependency_analysis trace
(kernel_N.json).

For every conflicting PC pair (u, v) observed as a trace edge, the pair RACES
at its observed thread distance d iff u and v are NOT ordered at scope >= d, on
the lattice  none < warp < block < grid.

Ordering is one "ordered-by" relation (class HBGraph) built from three
edge-generation rules; the pair's strength is the max scope those rules certify:

 R1 sync dominance (static): a qualifying sync s orders (u, v) at scope(s) iff
    s in postdom(u) & dom(v)  or  s in postdom(v) & dom(u)  — s runs after one
    access and before the other on every path. Qualifying: BAR.SYNC*/BAR.RED*
    (block), WARPSYNC (warp); BAR.ARV* never orders. Same-PC pairs: a qualifying
    sync of scope >= s on every cycle through the PC's region.
 R2 atomic coherence (static x dynamic): two same-address atomics are ordered
    at min of their .STRONG scopes (SM/CTA -> block, GPU/SYS -> grid).
 R3 scoped happens-before chain (static x dynamic, ScoRD model): release fence
    (MEMBAR in postdom(u) & dom(a), scope covering the hop) -> observed atomic-
    atomic sync edge(s) from the trace -> acquire (dependency order behind the
    spin atomic). MEMBAR alone never orders; a store in a CAS critical section
    needs its own acquire fence.

The CFG is used ONLY for sync structure. Memory space, read/write/atomic type
and warp masks come from the trace; the CFG opcode only confirms every traced
PC is a memory instruction (Phase 0 alignment invariant).

Usage:  python sync_dominance.py <kernel_cfg.dot> <kernel_N.json> [-o out.json]
Exit codes: 0 ok; 1 trace/CFG alignment failure; 2 unknown sync opcodes seen.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import networkx as nx
import pydot

NONE, WARP, BLOCK, GRID = range(4)
SCOPES = ["none", "warp", "block", "grid"]
VEXIT = "<EXIT>"

# Memory instructions, by family — used only to check the alignment invariant.
_MEM_OPS = {
    "LD", "LDG", "LDS", "LDL", "LDSM", "LDC",   # loads
    "ST", "STG", "STS", "STL",                  # stores
    "ATOM", "ATOMG", "ATOMS", "RED",            # atomics
    "LDGSTS",                                    # async copy
}
# "*SYNC*"-looking opcodes that are warp reconvergence/scoreboard, not data sync.
_NOT_SYNC = {"BSSY", "BSYNC", "BMOV", "BREAK", "DEPBAR", "WARPGROUP"}
_INSTR = re.compile(r"^\s*([0-9a-fA-F]{4,}):\s+(?:@!?U?P[T\d]+\s+)?(\S+)")


class AlignmentError(Exception):
    """Trace/CFG mismatch — abort loudly, never emit silent verdicts."""


def classify(opcode):
    """Sync/exit classification for region splitting.
    -> ("sync", scope, qualifying, unknown) | "exit" | "mem" | None."""
    base = opcode.split(".")[0]
    if base == "BAR":
        sub = opcode.split(".")[1] if "." in opcode else ""
        if sub.startswith(("SYNC", "RED")):
            return ("sync", BLOCK, True, False)
        if sub.startswith(("ARV", "ARRIVE")):       # arrive-only: not a full barrier
            return ("sync", BLOCK, False, False)
        return ("sync", BLOCK, False, True)         # unknown BAR.* -> CI tripwire
    if base == "WARPSYNC":                          # mask matched dynamically (trace)
        return ("sync", WARP, True, False)
    if base == "MEMBAR":                            # fence: non-qualifying for barrier
        # dominance, but real scope recorded for HB release certification
        return ("sync", GRID if opcode.split(".")[-1] in ("GPU", "SYS") else BLOCK,
                False, False)
    if base in ("EXIT", "RET"):
        return "exit"
    if base in _MEM_OPS:
        return "mem"
    if base not in _NOT_SYNC and "SYNC" in opcode:  # unrecognized *SYNC* -> tripwire
        return ("sync", NONE, False, True)
    return None


_ATOM_BASES = {"ATOM", "ATOMG", "ATOMS", "RED"}
_ATOM_SCOPE = {"CTA": BLOCK, "SM": BLOCK, "GPU": GRID, "SYS": GRID}


def atomic_scope(opcode):
    """Coherence-ordering scope of an atomic RMW; None if not an atomic."""
    parts = opcode.split(".")
    if parts[0] not in _ATOM_BASES:
        return None
    s = parts[parts.index("STRONG") + 1] if "STRONG" in parts else None
    return _ATOM_SCOPE.get(s, NONE)  # unknown/weak scope -> NONE (over-report, sound)


def parse_flags(flags):
    """Trace access flags string -> (space, access)."""
    f = flags.upper()
    access = "atomic" if "ATOMIC" in f else "write" if "WRITE" in f else "read"
    space = "shared" if "SHARED" in f else "global" if "GLOBAL" in f else \
            "local" if "LOCAL" in f else "generic"
    return space, access


def _label_lines(label):
    """Mrecord label -> instruction text lines (\\l-separated, \\x-escaped)."""
    lines, buf, i = [], [], 0
    while i < len(label):
        c = label[i]
        if c == "\\" and i + 1 < len(label):
            if label[i + 1] == "l":
                lines.append("".join(buf))
                buf = []
            else:
                buf.append(label[i + 1])
            i += 2
        else:
            if c not in "{}|\n":
                buf.append(c)
            i += 1
    lines.append("".join(buf))
    return [re.sub(r"<[^<>]*>", "", ln) for ln in lines]


def parse_dot(path):
    """-> {mangled: (blocks, edges, entry)}; blocks: {name: [(pc, opcode)]}."""
    (graph,) = pydot.graph_from_dot_file(str(path))
    kernels = {}
    for sub in graph.get_subgraphs():
        name = sub.get_name().strip('"')
        if not name.startswith("cluster_"):
            continue
        mangled = name[len("cluster_"):]
        blocks = {}
        for node in sub.get_nodes():
            label = node.get_attributes().get("label")
            if label is None:
                continue
            instrs = []
            for line in _label_lines(label.strip('"')):
                m = _INSTR.match(line)
                if m:
                    instrs.append((int(m.group(1), 16), m.group(2)))
            blocks[node.get_name().strip('"')] = instrs
        edges = [(e.get_source().split(":")[0].strip('"'),
                  e.get_destination().split(":")[0].strip('"'))
                 for e in sub.get_edges()]
        entry = mangled if mangled in blocks else next(iter(blocks))
        kernels[mangled] = (blocks, edges, entry)
    if not kernels:
        raise AlignmentError(f"no kernel clusters found in {path}")
    return kernels


class HBGraph:
    """The ordered-by relation over traced memory PCs.

    Built from the sync-split region graph (dominator/post-dominator sets) plus,
    after attach_trace, the dynamic facts (atomic scopes + observed atomic-atomic
    sync edges). Three edge rules certify ordering scope for a PC pair:
      R1 dominance() / loop_scope()  — static barriers/warpsync,
      R2 coherence()                 — same-address atomics,
      R3 chain()                     — release -> observed sync -> acquire.
    ordered() runs the single query max(R1, R2) then R3, per roadmap Phase 1."""

    def __init__(self, blocks, edges, entry):
        self.G = nx.DiGraph()
        self.G.add_node(VEXIT)
        self.atom = {}        # pc -> atomic coherence scope (after attach_trace)
        self.sync_edges = []  # (anc, cur, d) observed atomic sync hops
        self.pc_opcode = {}   # every parsed pc -> opcode (alignment check)
        self.pc_node = {}     # pc -> its region node
        self.syncs = {}       # sync node id -> (pc, opcode, scope, qualifying)
        self.unknown_syncs = []
        first, last = {}, {}
        for bname, instrs in blocks.items():
            cur, n = f"{bname}#0", 0
            first[bname] = cur
            self.G.add_node(cur)
            for pc, opcode in instrs:
                self.pc_opcode[pc] = opcode
                self.pc_node[pc] = cur
                info = classify(opcode)
                if info == "exit":
                    self.G.add_edge(cur, VEXIT)
                elif isinstance(info, tuple):  # sync: own node, region resumes after
                    _, scope, qual, unknown = info
                    sid = f"sync@{pc:#x}"
                    self.syncs[sid] = (pc, opcode, scope, qual)
                    if unknown:
                        self.unknown_syncs.append((pc, opcode))
                    n += 1
                    nxt = f"{bname}#{n}"
                    self.G.add_edge(cur, sid)
                    self.G.add_edge(sid, nxt)
                    cur = nxt
            last[bname] = cur
        for src, dst in edges:
            if src in last and dst in first:
                self.G.add_edge(last[src], first[dst])
        self.qualifying = [s for s, v in self.syncs.items() if v[3]]
        self.dom = self._dom_sets(nx.immediate_dominators(self.G, first[entry]))
        self.postdom = self._dom_sets(
            nx.immediate_dominators(self.G.reverse(), VEXIT))

    @staticmethod
    def _dom_sets(idom):
        """Full dominator sets = ancestors in the immediate-dominator tree."""
        out = {}
        for n in idom:
            s, cur = {n}, n
            while idom[cur] != cur:
                cur = idom[cur]
                s.add(cur)
            out[n] = s
        return out

    def attach_trace(self, atom, sync_edges):
        """Bind the dynamic facts: atom = {pc -> atomic coherence scope},
        sync_edges = validated observed atomic-atomic hops (anc, cur, d)."""
        self.atom = atom
        self.sync_edges = sync_edges

    # -- R1: sync dominance (static) ------------------------------------------
    def dominance(self, u, v):
        """Barrier/warpsync ordering of a cross-PC pair -> (scope, [sync pcs])."""
        ru, rv = self.pc_node[u], self.pc_node[v]
        if ru == rv:
            return NONE, []  # same sync interval: nothing between them
        best, used = NONE, []
        for sid in self.qualifying:
            pc, _, scope, _ = self.syncs[sid]
            if (sid in self.postdom.get(ru, ()) and sid in self.dom.get(rv, ())) or \
               (sid in self.postdom.get(rv, ()) and sid in self.dom.get(ru, ())):
                best = max(best, scope)
                used.append(pc)
        return best, sorted(used)

    def loop_scope(self, pc):
        """R1's cycle form for a same-PC pair: ordered at scope s iff a qualifying
        sync of scope >= s lies on every cycle through the PC's region (1.5)."""
        r = self.pc_node[pc]
        if not self._on_cycle(r, ()):
            return NONE, []  # no loop: distinct threads, same interval
        for sigma in (GRID, BLOCK, WARP):
            cut = {s for s in self.qualifying if self.syncs[s][2] >= sigma}
            if cut and not self._on_cycle(r, cut):
                return sigma, sorted(self.syncs[s][0] for s in cut
                                     if nx.has_path(self.G, r, s)
                                     and nx.has_path(self.G, s, r))
        return NONE, []

    # -- R2: atomic coherence (static x dynamic) ------------------------------
    def coherence(self, u, v):
        """Same-address atomics -> min of their .STRONG scopes; NONE otherwise."""
        return min(self.atom[u], self.atom[v]) if u in self.atom and v in self.atom \
            else NONE

    # -- R3: scoped happens-before chain (static x dynamic) -------------------
    def po(self, u, v):
        """Certified program order u -> v: u's region dominates v's (any thread
        executing v ran u first); same region falls back to offset order."""
        ru, rv = self.pc_node[u], self.pc_node[v]
        return u < v if ru == rv else ru in self.dom.get(rv, ())

    def release_scope(self, u, a):
        """Max MEMBAR scope with fence in postdom(u) & dom(a) — certifies both
        the program order u -> a and the fence between them; NONE if no fence."""
        ru, ra = self.pc_node[u], self.pc_node[a]
        return max((scope for sid, (_, op, scope, _) in self.syncs.items()
                    if op.startswith("MEMBAR") and sid in self.postdom.get(ru, ())
                    and sid in self.dom.get(ra, ())), default=NONE)

    def _cs_fenced(self, x, need):
        """Release-side gate for an ordinary store x: if x sits in a CAS-acquired
        critical section, a fence of scope >= need must sit between the CAS and x.
        Competing (CAS) acquires succeed in schedule-dependent order, so the
        observed chain direction cannot vouch for the other schedule; flag/spin
        handoffs (non-CAS) pin their direction by dataflow and need no fence."""
        return all(self.release_scope(c, x) >= need
                   for c in self.atom
                   if "CAS" in self.pc_opcode[c].split(".") and self.po(c, x))

    def chain(self, anc, cur):
        """Scoped happens-before path anc -> cur: a release side (fence-certified
        for an ordinary store, program order for an atomic), one or more observed
        atomic sync hops, then a dependency-ordered acquire. Returns the chain of
        atomic PCs, or None.

        PC-level: assumes all dynamic instances of a PC are ordered alike — exact
        for one-thread-per-arm and lock-protected patterns; per-thread epochs
        (roadmap Phase 2) are the precise upgrade."""
        hops = {}
        for a1, a2, d in self.sync_edges:
            hops.setdefault(a1, []).append((a2, d))
        anc_atomic = anc in self.atom
        if anc_atomic:  # atomics need no release fence, only certified program order
            starts = [(anc, GRID)]
        else:  # fence scope gates the first sync hop's distance
            starts = [(a, s) for a in self.atom
                      if (s := self.release_scope(anc, a)) > NONE]
        for a0, first_scope in starts:
            stack, seen = [(a0, False, [a0])], set()
            while stack:
                n, synced, path = stack.pop()
                if synced and n != cur and self.po(n, cur):  # acquire: dependency
                    return path
                if (n, synced) in seen:
                    continue
                seen.add((n, synced))
                for a2, d in hops.get(n, ()):
                    if synced or d <= first_scope:
                        stack.append((a2, True, path + [a2]))
                if synced or anc_atomic:  # po hop between atomics, no fence needed
                    for b in self.atom:
                        if b != n and self.po(n, b):
                            stack.append((b, synced, path + [b]))
        return None

    def _on_cycle(self, r, excluded):
        sub = self.G.subgraph(n for n in self.G if n not in excluded)
        return any(nx.has_path(sub, s, r) for s in sub.successors(r))

    # -- the single ordered-by query ------------------------------------------
    def ordered(self, cur, anc, d, cur_read, anc_read, static=True):
        """Is the conflicting pair ordered at scope >= d? Returns a dict with the
        certified strength, the R1 sync pcs, the R2 coherence scope and the R3
        chain — the fields the report needs. verdict = strength >= d or chain.

        static=False for a warp-same-instruction multi-lane write: no static sync
        (R1) or chain (R3) can intervene within one instruction, only R2 applies."""
        if not static:
            strength, syncs = NONE, []
        elif cur == anc:
            strength, syncs = self.loop_scope(cur)              # R1 (cycle form)
        else:
            strength, syncs = self.dominance(cur, anc)          # R1
        coherence = self.coherence(cur, anc)                    # R2
        if coherence > strength:
            strength, syncs = coherence, []
        chain = None
        if static and strength < d:                             # R3
            ok = lambda x, rd: x in self.atom or rd or self._cs_fenced(x, d)
            if ok(anc, anc_read) and ok(cur, cur_read):
                # cross-thread edge direction is temporal only for single-worker
                # replay (accelprof -n 1); stay direction-agnostic otherwise
                chain = self.chain(anc, cur) or self.chain(cur, anc)
        return {"strength": strength, "syncs": syncs,
                "coherence": coherence, "chain": chain}


def _demangle(name):
    if shutil.which("c++filt"):
        return subprocess.run(["c++filt", name], capture_output=True,
                              text=True).stdout.strip() or None
    return None


def select_kernel(kernels, trace_name):
    norm = lambda s: re.sub(r"\s+", "", s)
    for mangled in kernels:
        dm = _demangle(mangled)
        if dm and norm(dm) == norm(trace_name):
            return mangled
    # no demangler: the base identifier appears literally in the mangled symbol
    base = re.split(r"[<(]", trace_name)[0].split()[-1]
    hits = [m for m in kernels if base in m]
    if len(hits) == 1:
        return hits[0]
    raise AlignmentError(f"trace kernel '{trace_name}' not found in CFG "
                         f"(clusters: {list(kernels)})")


def _race_type(cur_access, anc_access):
    cur_w, anc_w = cur_access != "read", anc_access != "read"
    return "WAW" if cur_w and anc_w else "WAR" if cur_w else \
           "RAW" if anc_w else "RAR"


def _hb_class(r1r2_ordered, chain_ordered, dyn_raced):
    """Verdict-matrix cell (roadmap 4.1). Static all-schedule ordering crossed with
    the observed-schedule dynamic HB race:
      * R1 dominance / R2 coherence are all-schedule sound  (r1r2_ordered)
      * R3 chain is PC-level and can over-order (the canary) (chain_ordered)
    dyn_raced from the analyzer's C++ HB engine is the observed-schedule truth.
      structural  raced, and no all-schedule proof orders it (chain over-ordered,
                  or nothing did) -> a real race static missed.
      latent      not raced this schedule, but nothing proves all-schedule ordering
                  -> races under a different schedule.
      model_bug   R1/R2 claim every-schedule race-freedom yet it raced -> a soundness
                  bug in R1/R2 or a trace/CFG misalignment; investigate.
      ordered     not raced and some all-schedule proof orders it."""
    if dyn_raced:
        return "model_bug" if r1r2_ordered else "structural"
    return "ordered" if (r1r2_ordered or chain_ordered) else "latent"


def _observed(dist):
    """Highest inter-thread distance bucket of a trace edge -> (scope, count)."""
    for sc, key in ((GRID, "intra_grid"), (BLOCK, "intra_block"),
                    (WARP, "intra_warp")):
        if dist.get(key, 0) > 0:
            return sc, dist[key]
    return NONE, 0


def analyze(dot_path, trace_path):
    trace = json.loads(Path(trace_path).read_text())
    kernels = parse_dot(dot_path)
    mangled = select_kernel(kernels, trace["kernel"]["kernel_name"])
    eng = HBGraph(*kernels[mangled])

    # space/access come from the trace, keyed by pc
    flags = {n["pc"]: parse_flags(n["flags"]) for n in trace.get("nodes", [])}

    # hard-fail alignment: every traced PC must be a memory op in this CFG
    pcs = set(flags) | {e[k] for e in trace.get("edges", [])
                        for k in ("current_pc", "ancient_pc") if e.get(k) is not None}
    for pc in sorted(pcs):
        if pc not in eng.pc_opcode:
            raise AlignmentError(f"trace PC {pc:#x} not in CFG — trace/cubin mismatch")
        if classify(eng.pc_opcode[pc]) != "mem":
            raise AlignmentError(f"trace PC {pc:#x} is '{eng.pc_opcode[pc]}', "
                                 f"not a memory opcode — PC alignment broken")

    # dynamic facts feeding R2/R3: atomic PCs (coherence scope from the SASS
    # .STRONG suffix) and observed atomic-atomic sync edges — the shadow memory
    # tracks flag/lock addresses like any data, so the sync is in the trace
    atom = {pc: sc for pc in pcs
            if (sc := atomic_scope(eng.pc_opcode[pc])) is not None}
    sync_edges = []
    for e in trace.get("edges", []):
        cur, anc = e["current_pc"], e.get("ancient_pc")
        if e.get("cold_miss") or anc is None or cur not in atom or anc not in atom:
            continue
        d, _ = _observed(e.get("dist", {}))
        if d > NONE and min(atom[anc], atom[cur]) >= d:
            sync_edges.append((anc, cur, d))
    eng.attach_trace(atom, sync_edges)

    # Dynamic happens-before ground truth (the analyzer's C++ HB engine, present when
    # the trace was taken with YOSEMITE_HB_TRACE=1). Crossed with the static legs below
    # into the verdict-matrix class; absent -> the R3 chain is the only observed axis.
    hb_races = trace.get("hb_races")
    raced_pcsets = [frozenset(p for p in (r.get("a_pc"), r.get("b_pc")) if p is not None)
                    for r in hb_races] if hb_races is not None else None

    def hb_pair_raced(a, b):
        pair = frozenset((a, b))
        # exact {a,b} match; a WAR record carries only the writer pc and matches any
        # pair containing it (conservative — the corpus has no WAR to disambiguate).
        return any(s and s <= pair for s in raced_pcsets)

    verdicts, skipped = [], []
    for e in trace.get("edges", []):
        cur, anc = e["current_pc"], e.get("ancient_pc")
        rec = {"current_pc": cur, "ancient_pc": anc}
        if e.get("cold_miss") or anc is None:
            skipped.append({**rec, "reason": "cold_miss"})
            continue
        observed, weight = _observed(e.get("dist", {}))
        same_inst = e.get("dist", {}).get("intra_instance_launch", 0)
        cur_space, cur_access = flags.get(cur, ("generic", "read"))
        anc_space, anc_access = flags.get(anc, ("generic", "read"))
        cur_access = "atomic" if cur in atom else cur_access
        anc_access = "atomic" if anc in atom else anc_access
        if observed == NONE and same_inst == 0:
            skipped.append({**rec, "reason": "intra_thread_only"})
            continue
        if cur_access == "read" and anc_access == "read":
            skipped.append({**rec, "reason": "read_read"})
            continue
        # warp-same-instruction multi-lane write (ITS): no sync can intervene, so
        # no chain — but R2 coherence still applies to a same-inst atomic pair
        same = observed == NONE
        if same:
            observed, weight = WARP, same_inst
        ev = eng.ordered(cur, anc, observed, cur_access == "read",
                         anc_access == "read", static=not same)
        r1r2_ordered = ev["strength"] >= observed        # R1 dominance / R2 coherence
        chain_ordered = ev["chain"] is not None          # R3 PC-level handshake
        if raced_pcsets is not None:
            hb_class = _hb_class(r1r2_ordered, chain_ordered, hb_pair_raced(cur, anc))
            verdict = "ORDERED" if hb_class == "ordered" else "RACE"
        else:
            hb_class = None
            verdict = "ORDERED" if r1r2_ordered or chain_ordered else "RACE"
        verdicts.append({
            "current_pc": cur, "current_pc_hex": hex(cur),
            "ancient_pc": anc, "ancient_pc_hex": hex(anc),
            "opcodes": [eng.pc_opcode[cur], eng.pc_opcode[anc]],
            "space": cur_space if cur_space == anc_space else f"{cur_space}/{anc_space}",
            "race_type": _race_type(cur_access, anc_access),
            "observed_distance": SCOPES[observed],
            "contested_weight": weight,
            "access_size": e.get("current_access_size"),
            "strength": SCOPES[ev["strength"]],
            "ordering_syncs": ev["syncs"],
            "atomic_coherence": SCOPES[ev["coherence"]],
            "hb_chain": [hex(p) for p in ev["chain"]] if ev["chain"] else None,
            "warp_same_inst": same,
            "hb_class": hb_class,
            "verdict": verdict,
        })

    races = sum(v["verdict"] == "RACE" for v in verdicts)
    return {
        "inputs": {"cfg_dot": str(dot_path), "trace_json": str(trace_path)},
        "kernel": {"mangled": mangled, "name": trace["kernel"]["kernel_name"]},
        "verdicts": verdicts,
        "skipped_edges": skipped,
        "syncs": sorted(({"pc": pc, "pc_hex": hex(pc), "opcode": op,
                          "scope": SCOPES[scope], "qualifying": q}
                         for pc, op, scope, q in eng.syncs.values()),
                        key=lambda s: s["pc"]),
        "diagnostics": {
            "unknown_sync_count": len(eng.unknown_syncs),
            "unknown_sync_opcodes": [{"pc": pc, "opcode": op}
                                     for pc, op in eng.unknown_syncs],
        },
        "summary": {"races": races, "ordered": len(verdicts) - races,
                    "skipped": len(skipped),
                    "hb_classes": {c: sum(v["hb_class"] == c for v in verdicts)
                                   for c in ("structural", "latent", "model_bug")}
                                  if raced_pcsets is not None else None},
    }


def render(report, out):
    """Human-readable report text (same layout main prints), as one string."""
    lines = [f"kernel: {report['kernel']['name']}",
             "syncs:  " + (", ".join(
                 f"{s['opcode']}@{s['pc_hex']}[{s['scope']}"
                 f"{'' if s['qualifying'] else ',non-qualifying'}]"
                 for s in report["syncs"]) or "none")]
    for v in report["verdicts"]:
        # A RACE that still carries an hb_chain is a structural race the dynamic HB
        # engine caught: the PC-level chain (release->sync->acquire) holds for the
        # threads that actually handshook, but not for the pair that raced — so the
        # chain was refuted, not the justification. Only ORDERED "via hb(...)".
        if v["ordering_syncs"]:
            via = " via " + ",".join(map(hex, v["ordering_syncs"]))
        elif v["verdict"] == "RACE" and v["hb_chain"]:
            via = " (PC-level hb " + "->".join(v["hb_chain"]) + " refuted by dynamic HB)"
        elif v["hb_chain"]:
            via = " via hb(" + "->".join(v["hb_chain"]) + ")"
        elif v["atomic_coherence"] != "none" and v["strength"] == v["atomic_coherence"]:
            via = f" via atomic({v['atomic_coherence']})"
        else:
            via = ""
        note = " (warp-same-inst)" if v["warp_same_inst"] else ""
        cls = f" {v['hb_class']}" if v.get("hb_class") else ""
        lines.append(f"{v['ancient_pc_hex']} -> {v['current_pc_hex']}  "
                     f"{v['opcodes'][1]}/{v['opcodes'][0]}  {v['space']}  {v['race_type']}  "
                     f"dist={v['observed_distance']}  strength={v['strength']}  "
                     f"{v['verdict']}{cls}{note}{via}")
    for s in report["skipped_edges"]:
        anc = hex(s["ancient_pc"]) if s["ancient_pc"] is not None else "-"
        lines.append(f"skipped: {anc} -> {hex(s['current_pc'])}  ({s['reason']})")
    smry = report["summary"]
    lines.append(f"{smry['races']} race(s), {smry['ordered']} ordered, "
                 f"{smry['skipped']} skipped   -> {out}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("cfg_dot", type=Path)
    ap.add_argument("trace_json", type=Path)
    ap.add_argument("-o", "--output", type=Path,
                    help="output JSON (default: <trace-stem>.races.json)")
    args = ap.parse_args(argv)
    try:
        report = analyze(args.cfg_dot, args.trace_json)
    except AlignmentError as exc:
        print(f"ALIGNMENT FAILURE: {exc}", file=sys.stderr)
        return 1

    out = args.output or args.trace_json.with_name(args.trace_json.stem + ".races.json")
    out.write_text(json.dumps(report, indent=2) + "\n")

    print(render(report, out))
    if report["diagnostics"]["unknown_sync_count"]:
        print(f"ERROR: unknown sync opcodes: "
              f"{report['diagnostics']['unknown_sync_opcodes']}", file=sys.stderr)
    return 2 if report["diagnostics"]["unknown_sync_count"] else 0


if __name__ == "__main__":
    sys.exit(main())

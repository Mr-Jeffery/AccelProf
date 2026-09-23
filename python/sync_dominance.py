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
    access and before the other on every path, and no sync-free path joins the two
    regions (a loop's wrap-around would pair instances from different iterations).
    Qualifying: BAR.SYNC*/BAR.RED* (block), WARPSYNC (warp); BAR.ARV* never orders.
    Same-PC pairs: a qualifying sync of scope >= s on every cycle through the PC's
    region.
 R2 atomic coherence (static x dynamic): two same-address atomics are ordered
    at min of their .STRONG scopes (SM/CTA -> block, GPU/SYS -> grid); a shared-
    memory ATOMS without a scope suffix is block-coherent by construction. A
    cuda::atomic load()/store() is no RMW opcode but a LD|ST.*.STRONG.<scope>; per
    the --strong-ldst policy it is a coherent access for R2 (never for R3).
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
import functools
import json
import os
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
    if s is None and parts[0] == "ATOMS":
        # a shared-memory atomic (atomicAdd_block on __shared__) carries no .STRONG
        # suffix; shared memory is per-CTA, so it is CTA-coherent by construction.
        return BLOCK
    return _ATOM_SCOPE.get(s, NONE)  # unknown/weak scope -> NONE (over-report, sound)


# .STRONG loads/stores. cuda::atomic<T>::load()/store() do not lower to an ATOM* RMW
# but to an ordinary load/store carrying the atomic's coherence scope (seq_cst adds a
# MEMBAR fence in front, relaxed does not): LD|ST.E.STRONG.<scope>. A `volatile`
# access lowers to the SAME qualifier; the only binary-level difference is the opcode
# form -- the cuda::atomic builtins emit the generic LD/ST, a volatile pointer access
# the address-spaced LDG/STG/LDS/STS. Which of them count as language-level atomics
# is therefore a policy:
#   generic  LD/ST.*.STRONG only (default: Indigo/ECL-style atomics are coherent,
#            ScoR-style volatile data stays plain and keeps racing)
#   all      every .STRONG load/store (volatile too; hides ScoR's volatile races)
#   none     RMW atomics only (the pre-existing model)
STRONG_LDST_POLICIES = ("generic", "all", "none")
_STRONG_GENERIC = {"LD", "ST"}
_STRONG_ALL = {"LD", "LDG", "LDS", "LDL", "LDSM", "ST", "STG", "STS", "STL"}


def strong_ldst_policy(policy=None):
    """Resolve the policy: explicit arg > $CUVEIN_STRONG_LDST > 'generic'."""
    policy = policy or os.environ.get("CUVEIN_STRONG_LDST") or "generic"
    if policy not in STRONG_LDST_POLICIES:
        raise ValueError(f"strong-ldst policy '{policy}' not in {STRONG_LDST_POLICIES}")
    return policy


def coherent_scope(opcode, policy=None):
    """Coherence scope of a language-level atomic ACCESS: an atomic RMW, or (per
    policy) a .STRONG load/store; None if the access is plain.

    Used ONLY for pairwise same-address coherence (R2 and the engine's conflict
    check). A coherent load/store is never a release/acquire point: it joins no
    clocks and takes no part in the R3 chain, so it cannot order surrounding
    non-atomic accesses (that would widen the relaxed-atomic unsoundness)."""
    s = atomic_scope(opcode)
    if s is not None:
        return s
    policy = strong_ldst_policy(policy)
    parts = opcode.split(".")
    if policy == "none" or "STRONG" not in parts:
        return None
    if parts[0] not in (_STRONG_GENERIC if policy == "generic" else _STRONG_ALL):
        return None
    i = parts.index("STRONG")
    return _ATOM_SCOPE.get(parts[i + 1] if i + 1 < len(parts) else None, NONE)


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
        self.atom = {}        # pc -> atomic RMW scope (after attach_trace); R3's atomics
        self.coh = {}         # pc -> coherent-access scope (atom + .STRONG ld/st); R2 only
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
        """Full dominator sets = ancestors in the immediate-dominator tree.

        networkx >= 3.x drops the root from immediate_dominators() (older
        versions mapped it to itself), so the walk stops when the current node
        is its own idom OR is absent (the root); the root is then seeded with
        its singleton set to match the pre-3.x semantics callers rely on."""
        out = {}
        for n in idom:
            s, cur = {n}, n
            while cur in idom and idom[cur] != cur:
                cur = idom[cur]
                s.add(cur)
            out[n] = s
            out.setdefault(cur, {cur})
        return out

    def attach_trace(self, atom, sync_edges, coh=None, same_loc=None):
        """Bind the dynamic facts: atom = {pc -> atomic RMW scope} (the release/
        acquire atomics R3 chains over), sync_edges = validated observed atomic-atomic
        hops (anc, cur, d), coh = {pc -> coherent-access scope} for R2 (atom plus the
        .STRONG loads/stores; defaults to atom), same_loc = {frozenset{pc_a, pc_b}}
        atomic pairs observed on one location at ANY distance, intra-thread included
        (the evidence that an EXCH rewrites the word a CAS acquired)."""
        self.atom = atom
        self.sync_edges = sync_edges
        self.coh = atom if coh is None else coh
        self.same_loc = same_loc or set()

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
        if best > NONE:
            # dom/postdom are computed on the cyclic region graph: with a loop, u's
            # instance in iteration k+1 reaches v's instance in iteration k with no
            # sync in between (the wrap-around path skips the barrier). Order only if
            # every path between the two regions crosses a sync of scope >= best.
            cut = {s for s in self.qualifying if self.syncs[s][2] >= best}
            sub = self.G.subgraph(n for n in self.G if n not in cut)
            if nx.has_path(sub, ru, rv) or nx.has_path(sub, rv, ru):
                return NONE, []
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
        """Same-address coherent accesses (atomic RMWs, cuda::atomic loads/stores)
        -> min of their .STRONG scopes; NONE otherwise."""
        return min(self.coh[u], self.coh[v]) if u in self.coh and v in self.coh \
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

    def _past_release(self, acq, cur):
        """Acquire-side gate: cur lies PAST the release of the critical section that
        the CAS `acq` opened — the thread rewrote the same word (an atomic r observed
        on acq's location, acq -po-> r -po-> cur) before reaching cur. Competing CAS
        acquires succeed in schedule-dependent order, so the observed hop orders only
        what is still inside the section: had this thread won the lock first, an
        access after its own unlock would run concurrently with the other section
        (ScoR race_interblock_none-lock_rtraw). Non-CAS flag/spin hand-offs pin their
        direction by dataflow, so everything after the acquire stays ordered.
        $CUVEIN_R3_PAST_RELEASE=0 disables the gate (ablation).
        ponytail: the mirror (an access BEFORE its thread's own acquire) is not gated."""
        if acq is None or "CAS" not in self.pc_opcode[acq].split(".") \
                or os.environ.get("CUVEIN_R3_PAST_RELEASE", "1") == "0":
            return False
        return any(r != acq and r != cur and frozenset((acq, r)) in self.same_loc
                   and self.po(acq, r) and self.po(r, cur) for r in self.atom)

    def chain(self, anc, cur):
        """Scoped happens-before path anc -> cur: a release side (fence-certified
        for an ordinary store, program order for an atomic), one or more observed
        atomic sync hops, then a dependency-ordered acquire whose critical section
        cur has not already left (_past_release). Returns the chain of atomic PCs,
        or None.

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
            # acq = the atomic the latest sync hop landed on (the acquire in force)
            stack, seen = [(a0, False, [a0], None)], set()
            while stack:
                n, synced, path, acq = stack.pop()
                if synced and n != cur and self.po(n, cur) \
                        and not self._past_release(acq, cur):  # acquire: dependency
                    return path
                if (n, synced, acq) in seen:
                    continue
                seen.add((n, synced, acq))
                for a2, d in hops.get(n, ()):
                    if synced or d <= first_scope:
                        stack.append((a2, True, path + [a2], a2))
                if synced or anc_atomic:  # po hop between atomics, no fence needed
                    for b in self.atom:
                        if b != n and self.po(n, b):
                            stack.append((b, synced, path + [b], acq))
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


def thread_distance(t1, t2):
    """Scope distance of two engine tids (block << 10 | warp << 5 | lane)."""
    if t1 >> 10 != t2 >> 10:
        return GRID
    return BLOCK if (t1 >> 5) != (t2 >> 5) else WARP


def barrier_only_pairs(trace, rmw, coh, max_lanes=None, dist_out=None, order_out=None):
    """Offline barrier/syncwarp-ONLY happens-before pass over a dump's `hb_events`:
    the pc pairs {(pc_lo, pc_hi): count} whose conflicts those joins leave unordered
    (the engine's `hb_races_sync_only`, same semantics as hb_oracle's second clock).

    It needs no atomic release/acquire joins, so it is cheap enough for the scalar-clock
    mode: the clock changes only at a sync group, where every participant ends with
    the same joined clock plus its own tick -> one shared base per group, O(threads)
    per barrier. rmw = {pc: scope} atomic RMWs (write semantics), coh = {pc: scope}
    coherent accesses. dist_out, if given, receives {(pc_lo, pc_hi): widest thread
    distance (WARP/BLOCK/GRID) among the pair's unordered conflicts}; order_out
    {(pc_lo, pc_hi): (earlier_pc, later_pc)} of the pair's first conflict in event order.
    -> None if the dump has no hb_events or exceeds max_lanes."""
    events = trace.get("hb_events")
    if not events:
        return None
    if max_lanes is not None and \
            sum(len(e.get("lanes", ())) for e in events) > max_lanes:
        return None
    events = sorted(events, key=lambda e: e["seq"])
    block_tc = trace["kernel"].get("block_thread_count")
    tid_of = lambda b, w, l: (b << 10) | (w << 5) | l
    base, own = {}, {}                 # tid -> shared joined clock / own component
    pending = {}                       # (block, bar_index) -> arrived tids
    last_write, last_reads, pairs = {}, {}, {}

    def sync_group(tids):
        for t in tids:
            own.setdefault(t, 1)
        js, joined = {}, set()
        for t in tids:
            b = base.get(t)
            if b is not None and id(b) not in joined:
                joined.add(id(b))
                for k, c in b.items():
                    if c > js.get(k, 0):
                        js[k] = c
        for t in tids:
            if own[t] > js.get(t, 0):
                js[t] = own[t]
        for t in tids:
            base[t], own[t] = js, js[t] + 1

    def unordered(t, p_tid, p_clk):
        b = base.get(t)
        return p_clk > (b.get(p_tid, 0) if b is not None else 0)

    def coherent(c1, b1, c2, b2):
        if c1 is None or c2 is None:
            return False
        eff = min(c1, c2)
        return eff == GRID or (eff == BLOCK and b1 == b2)

    def hit(p_pc, pc, p_tid, t):
        k = (min(p_pc, pc), max(p_pc, pc))
        pairs[k] = pairs.get(k, 0) + 1
        if dist_out is not None:
            dist_out[k] = max(dist_out.get(k, NONE), thread_distance(p_tid, t))
        if order_out is not None:
            order_out.setdefault(k, (p_pc, pc))

    for e in events:
        typ = e["type"]
        if typ == "syncwarp":
            m = e["sync_mask"]
            sync_group([tid_of(e["block"], e["warp"], k) for k in range(32) if (m >> k) & 1])
            continue
        if typ == "barrier":
            key, m = (e["block"], e["bar_index"]), e["active_mask"]
            arrived = pending.setdefault(key, set())
            arrived.update(tid_of(e["block"], e["warp"], k) for k in range(32) if (m >> k) & 1)
            expected = e.get("thread_count") or block_tc
            if not expected or len(arrived) >= expected:
                sync_group(sorted(arrived))
                del pending[key]
            continue
        pc, blk, space = e["pc"], e["block"], e["space"]
        is_write = typ == "write" or pc in rmw
        my_coh = coh.get(pc)
        for lane in e["lanes"]:
            t = tid_of(blk, e["warp"], lane["lane"])
            loc = (space, blk, lane["addr"]) if space == "shared" else (space, lane["addr"])
            clk = own.setdefault(t, 1)
            w = last_write.get(loc)
            if w and w[0] != t and not coherent(my_coh, blk, w[3], w[4]) \
                    and unordered(t, w[0], w[1]):
                hit(w[2], pc, w[0], t)
            if is_write:
                for rt, (rc, rpc, rcoh, rblk) in last_reads.get(loc, {}).items():
                    if rt != t and not coherent(my_coh, blk, rcoh, rblk) \
                            and unordered(t, rt, rc):
                        hit(rpc, pc, rt, t)
                last_write[loc] = (t, clk, pc, my_coh, blk)
                last_reads[loc] = {}
            else:
                last_reads.setdefault(loc, {})[t] = (clk, pc, my_coh, blk)
    return pairs


@functools.lru_cache(maxsize=None)   # one c++filt spawn per symbol, not per query
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


def _hb_class(r1r2_ordered, chain_ordered, dyn_raced, sync_raced=None):
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
      ordered     not raced and some all-schedule proof orders it.
      barrier-ordered  not raced, no static proof, but barrier/syncwarp joins alone
                  order every observed conflict of the pair (schedule-independent:
                  the barrier-in-loop reduction the PC-level R1 cannot certify)."""
    if dyn_raced:
        return "model_bug" if r1r2_ordered else "structural"
    if r1r2_ordered or chain_ordered:
        return "ordered"
    # No static proof. sync_raced is the engine's second, barrier/syncwarp-ONLY clock
    # (hb_races_sync_only; None when the dump predates it). Barrier joins do not
    # depend on the schedule, so a pair whose every observed conflict they order is
    # not a "lucky schedule": barrier-ordered. A pair they leave unordered was ordered
    # only through atomic release/acquire joins, which ignore fences -> latent.
    return "barrier-ordered" if sync_raced is False else "latent"


def _observed(dist):
    """Highest inter-thread distance bucket of a trace edge -> (scope, count)."""
    for sc, key in ((GRID, "intra_grid"), (BLOCK, "intra_block"),
                    (WARP, "intra_warp")):
        if dist.get(key, 0) > 0:
            return sc, dist[key]
    return NONE, 0


def analyze(dot_path, trace_path, assume_warp_lockstep=False, strong_ldst=None,
            barrier_pass=True, event_candidates=True):
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
    sync_edges, same_loc = [], set()
    for e in trace.get("edges", []):
        cur, anc = e["current_pc"], e.get("ancient_pc")
        if e.get("cold_miss") or anc is None or cur not in atom or anc not in atom:
            continue
        same_loc.add(frozenset((cur, anc)))   # one location, any distance (R3 gate)
        d, _ = _observed(e.get("dist", {}))
        if d > NONE and min(atom[anc], atom[cur]) >= d:
            sync_edges.append((anc, cur, d))
    # R2's coherent accesses: the RMW atomics plus (per policy) .STRONG loads/stores —
    # cuda::atomic load()/store(). They never enter `atom`: not release/acquire points.
    policy = strong_ldst_policy(strong_ldst)
    coh = {pc: sc for pc in pcs
           if (sc := coherent_scope(eng.pc_opcode[pc], policy)) is not None}
    eng.attach_trace(atom, sync_edges, coh, same_loc)

    # Dynamic happens-before ground truth (the analyzer's C++ HB engine, present when
    # the trace was taken with YOSEMITE_HB_TRACE=1). Crossed with the static legs below
    # into the verdict-matrix class; absent -> the R3 chain is the only observed axis.
    hb_races = trace.get("hb_races")
    # exact {a,b} match on the pc pair. Every record now names both pcs (the engine
    # and oracle keep the reader pc for WAR); a subset match over single-pc keys
    # attributed a race to every pair sharing one pc, filling the model_bug cell.
    raced_records = {}  # frozenset{pc_a, pc_b} -> [race records]  (a same-pc race is {pc})
    if hb_races is not None:
        for r in hb_races:
            raced_records.setdefault(frozenset((r["a_pc"], r["b_pc"])), []).append(r)
    raced_pcsets = set(raced_records) if hb_races is not None else None
    # Cross-thread conflicts the EVENT STREAM shows (engine race records / the offline
    # barrier pass), with their widest thread distance. A trace edge remembers only the
    # LAST accessor of a location, so a single-instance conflict can be recorded at
    # intra-thread distance when the last reader happened to be the writer's own
    # thread; this evidence keeps such an edge from being skipped.
    observed_dyn = {}
    for r in hb_races or ():
        if r.get("a_pc") is not None:
            k = frozenset((r["a_pc"], r["b_pc"]))
            observed_dyn[k] = max(observed_dyn.get(k, NONE),
                                  thread_distance(r["a_tid"], r["b_tid"]))
    # dumps from before the reader-pc fix carry WAR records with a_pc null: match those
    # on the writer pc against a read partner (never against write/write pairs).
    legacy_war_writers = {r["b_pc"] for r in hb_races or () if r.get("a_pc") is None}

    def hb_pair_raced(a, b, a_read=False, b_read=False):
        if frozenset((a, b)) in raced_pcsets:
            return True
        return (a in legacy_war_writers and b_read) or (b in legacy_war_writers and a_read)

    # barrier/syncwarp-only race pairs [[pc_a, pc_b, count], ...]; absent in old dumps
    sync_only = trace.get("hb_races_sync_only")
    sync_pcsets = {frozenset((a, b)) for a, b, _ in sync_only} \
        if sync_only is not None else None
    # No engine-side set (scalar-clock dump, or a pre-fix engine): derive it offline from
    # hb_events. The barrier-only clock needs no atomic joins, so the scalar-clock mode
    # gets the same barrier-ordered evidence without running the exact engine.
    # $CUVEIN_BARRIER_PASS=0 disables it; dumps above $CUVEIN_BARRIER_PASS_MAX_LANES
    # lane-accesses (default 5M) stay static-only.
    offline_memo = []

    def offline_pass():
        """-> (pairs, dist, order) of the offline barrier-only pass, or None. Memoized."""
        if not offline_memo:
            res = None
            if barrier_pass and os.environ.get("CUVEIN_BARRIER_PASS", "1") != "0":
                rmw_all = {pc: sc for pc, op in eng.pc_opcode.items()
                           if (sc := atomic_scope(op)) is not None}
                coh_all = {pc: sc for pc, op in eng.pc_opcode.items()
                           if (sc := coherent_scope(op, policy)) is not None}
                dist, order = {}, {}
                pairs = barrier_only_pairs(
                    trace, rmw_all, coh_all,
                    int(os.environ.get("CUVEIN_BARRIER_PASS_MAX_LANES", "5000000")),
                    dist, order)
                if pairs is not None:
                    res = (pairs, dist, order)
            offline_memo.append(res)
        return offline_memo[0]

    if sync_pcsets is None and offline_pass() is not None:
        offline, offline_dist, _ = offline_pass()
        sync_pcsets = {frozenset(k) for k in offline}
        for k, d in offline_dist.items():
            observed_dyn[frozenset(k)] = max(observed_dyn.get(frozenset(k), NONE), d)

    # Event-stream candidates: the conflicting pc pairs the event stream shows that
    # barriers/syncwarps leave unordered (engine: hb_races_sync_only + hb_races; trace-
    # only: the offline pass). A trace edge remembers only the LAST accessor of a
    # location, so a pair can have no edge at all (read by A, read by B, write by B:
    # the write's edge names B's own read and A's read is gone) — such pairs are judged
    # after the edges, from the event stream alone. $CUVEIN_EVENT_CANDIDATES=0 disables.
    use_candidates = event_candidates and \
        os.environ.get("CUVEIN_EVENT_CANDIDATES", "1") != "0"
    event_pairs = ((sync_pcsets or set()) | (raced_pcsets or set())) \
        if use_candidates else set()

    # Benign-race evidence (static, PC-granular): the set of write/atomic pcs each
    # read pc was observed to conflict with. A read whose every conflicting writer is
    # an atomic RMW reads an atomically-maintained location (graph-analytics idiom:
    # plain read of a parent pointer another thread CAS-updates) — a real HB-unordered
    # access the algorithm tolerates. Tagged and re-bucketed, never hidden.
    # ponytail: PC-granular; the exact per-location "never plainly written" bit
    # belongs in the engine's location shadow.
    writers = {}
    for e in trace.get("edges", []):
        cur, anc = e["current_pc"], e.get("ancient_pc")
        if e.get("cold_miss") or anc is None:
            continue
        d, _ = _observed(e.get("dist", {}))
        if d == NONE and not e.get("dist", {}).get("intra_instance_launch", 0):
            continue
        acc = {pc: ("atomic" if pc in atom else flags.get(pc, ("generic", "read"))[1])
               for pc in (cur, anc)}
        for r, w in ((cur, anc), (anc, cur)):
            if acc[r] == "read" and acc[w] != "read":
                writers.setdefault(r, set()).add(w)
    # ... plus the writers only the event stream shows (else a read whose EDGE writers
    # are all atomics would be tagged benign although a plain writer conflicts with it)
    for k in event_pairs:
        a, b = (tuple(k) * 2)[:2]
        acc = {pc: ("atomic" if pc in atom else flags.get(pc, ("generic", "read"))[1])
               for pc in (a, b)}
        for r, w in ((a, b), (b, a)):
            if acc[r] == "read" and acc[w] != "read":
                writers.setdefault(r, set()).add(w)

    verdicts, skipped = [], []

    def judge(cur, anc, observed, weight, same_inst, rescued, access_size, from_events):
        """Verdict for one conflicting pc pair (anc earlier, cur later), observed at
        thread distance `observed` (NONE = warp-same-instruction, weight same_inst)."""
        rec = {"current_pc": cur, "ancient_pc": anc}
        cur_space, cur_access = flags.get(cur, ("generic", "read"))
        anc_space, anc_access = flags.get(anc, ("generic", "read"))
        cur_access = "atomic" if cur in atom else cur_access
        anc_access = "atomic" if anc in atom else anc_access
        if cur_access == "read" and anc_access == "read":
            skipped.append({**rec, "reason": "read_read"})
            return
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
            hb_class = _hb_class(
                r1r2_ordered, chain_ordered,
                hb_pair_raced(cur, anc, cur_access == "read", anc_access == "read"),
                None if sync_pcsets is None else frozenset((cur, anc)) in sync_pcsets)
            verdict = "ORDERED" if hb_class in ("ordered", "barrier-ordered") else "RACE"
        else:
            # static leg only (no engine): a pair without a static proof is still
            # ordered when barrier/syncwarp joins order every observed conflict.
            if r1r2_ordered or chain_ordered:
                hb_class, verdict = None, "ORDERED"
            elif sync_pcsets is not None and frozenset((cur, anc)) not in sync_pcsets:
                hb_class, verdict = "barrier-ordered", "ORDERED"
            else:
                hb_class, verdict = None, "RACE"
        race_type = _race_type(cur_access, anc_access)
        benign = assumption = None
        if verdict == "RACE" and race_type in ("RAW", "WAR"):
            read_pc = cur if cur_access == "read" else anc
            ws = writers.get(read_pc, set())
            if ws and ws <= atom.keys():
                benign, hb_class = "atomic-maintained-read", "benign"
        if assume_warp_lockstep and hb_class == "structural" and observed == WARP \
                and not same:
            # Lanes of ONE warp at two pcs in program order are ordered by lock-step
            # execution on pre-ITS hardware (the volatile warp-synchronous idiom).
            # Not a proof under independent thread scheduling: opt-in, and the
            # verdict carries the assumption.
            # Program order for a lock-step warp = anc's region reaches cur's with no
            # path back (a loop would interleave iterations); same region -> offset
            # order. Divergent siblings (neither reaches the other) stay races: that
            # is the ITS-sensitive class the divergent-siblings regression pins.
            ra, rc = eng.pc_node[anc], eng.pc_node[cur]
            in_order = (anc < cur) if ra == rc else \
                (nx.has_path(eng.G, ra, rc) and not nx.has_path(eng.G, rc, ra))
            recs = raced_records.get(frozenset((cur, anc)), [])
            if recs and in_order \
                    and all((r["a_tid"] >> 5) == (r["b_tid"] >> 5) for r in recs):
                hb_class, verdict, assumption = "warp-po-ordered", "ORDERED", "warp-lockstep"
        verdicts.append({
            "current_pc": cur, "current_pc_hex": hex(cur),
            "ancient_pc": anc, "ancient_pc_hex": hex(anc),
            "opcodes": [eng.pc_opcode[cur], eng.pc_opcode[anc]],
            "space": cur_space if cur_space == anc_space else f"{cur_space}/{anc_space}",
            "race_type": race_type,
            "observed_distance": SCOPES[observed],
            "contested_weight": weight,
            "access_size": access_size,
            "strength": SCOPES[ev["strength"]],
            "ordering_syncs": ev["syncs"],
            "atomic_coherence": SCOPES[ev["coherence"]],
            "hb_chain": [hex(p) for p in ev["chain"]] if ev["chain"] else None,
            "warp_same_inst": same,
            "edge_rescued": rescued,
            "event_candidate": from_events,
            "hb_class": hb_class,
            "benign": benign,
            "assumption": assumption,
            "verdict": verdict,
        })


    for e in trace.get("edges", []):
        cur, anc = e["current_pc"], e.get("ancient_pc")
        rec = {"current_pc": cur, "ancient_pc": anc}
        if e.get("cold_miss") or anc is None:
            skipped.append({**rec, "reason": "cold_miss"})
            continue
        observed, weight = _observed(e.get("dist", {}))
        same_inst = e.get("dist", {}).get("intra_instance_launch", 0)
        rescued = False
        if observed == NONE and same_inst == 0:
            observed = observed_dyn.get(frozenset((cur, anc)), NONE) if cur != anc else NONE
            if observed == NONE:
                skipped.append({**rec, "reason": "intra_thread_only"})
                continue
            rescued, weight = True, 1   # cross-thread per the event stream, not the edge
        judge(cur, anc, observed, weight, same_inst, rescued,
              e.get("current_access_size"), False)

    # event-stream candidates no edge produced a verdict for (see event_pairs above)
    cand_diag = None
    missing = event_pairs - {frozenset((v["current_pc"], v["ancient_pc"])) for v in verdicts}
    if missing:
        ev_info = {}   # pair -> (anc, cur, distance, conflicts)
        for k, recs in raced_records.items():       # engine race records carry tids
            if recs[0].get("a_pc") is not None:
                ev_info[k] = (recs[0]["a_pc"], recs[0]["b_pc"], observed_dyn.get(k, NONE),
                              len(recs))
        off = offline_pass()    # lazy in vector-clock mode: distance + orientation of the rest
        if off is not None:
            for k2, n in off[0].items():
                ev_info.setdefault(frozenset(k2), (*off[2][k2], off[1][k2], n))
        cand_diag = {"pairs": len(missing), "judged": 0, "no_event_evidence": 0}
        for k in sorted(missing, key=sorted):
            info = ev_info.get(k)
            if info is None or info[2] == NONE or any(pc not in flags for pc in k):
                cand_diag["no_event_evidence"] += 1
                continue
            anc, cur, dist, n = info
            judge(cur, anc, dist, n, 0, False, None, True)
            cand_diag["judged"] += 1

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
            # event-stream pairs without an edge verdict: how many, judged, unusable
            "event_candidates": cand_diag,
        },
        "summary": {"races": races, "ordered": len(verdicts) - races,
                    "skipped": len(skipped),
                    "hb_classes": {c: sum(v["hb_class"] == c for v in verdicts)
                                   for c in ("structural", "latent", "model_bug",
                                             "benign", "warp-po-ordered",
                                             "barrier-ordered")}
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
        elif v.get("hb_class") == "barrier-ordered":
            via = " via observed barrier/syncwarp joins"
        else:
            via = ""
        note = " (warp-same-inst)" if v["warp_same_inst"] else ""
        if v.get("edge_rescued"):
            note += " (cross-thread per event stream)"
        if v.get("event_candidate"):
            note += " (candidate from the event stream; no dependency edge)"
        if v.get("benign"):
            note += f" benign({v['benign']})"
        if v.get("assumption"):
            note += f" [assumes {v['assumption']}]"
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
    ap.add_argument("--strong-ldst", choices=STRONG_LDST_POLICIES,
                    help="which .STRONG loads/stores are language-level atomics "
                         "(default: $CUVEIN_STRONG_LDST or 'generic')")
    ap.add_argument("--no-event-candidates", action="store_true",
                    help="judge trace edges only; do not add the conflicting pairs only "
                         "the hb_events stream shows (also $CUVEIN_EVENT_CANDIDATES=0)")
    ap.add_argument("--assume-warp-lockstep", action="store_true",
                    help="reclassify same-warp program-ordered structural races as "
                         "ordered (pre-ITS lock-step assumption; not a proof)")
    args = ap.parse_args(argv)
    try:
        report = analyze(args.cfg_dot, args.trace_json,
                         assume_warp_lockstep=args.assume_warp_lockstep,
                         strong_ldst=args.strong_ldst,
                         event_candidates=not args.no_event_candidates)
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

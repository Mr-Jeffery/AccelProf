#!/usr/bin/env python3
"""
Dominance-based data-race verdicts: join a kernel CFG (nvdisasm -bbcfg -poff
dot, from getall.sh) with its cuVein pc_dependency_analysis trace (kernel_N.json).

The CFG is used ONLY for sync structure. It is split into sync-delimited
regions (each sync instruction is its own graph node). For every conflicting
PC pair (u, v) observed as a trace edge:

    strength(u, v) = max{ scope(s) : s qualifying sync,
                          s in postdom(u) & dom(v)  or  s in postdom(v) & dom(u) }

on the lattice none < warp < block < grid.  RACE iff strength < the edge's
observed topological distance.  Qualifying: BAR.SYNC*/BAR.RED* (block),
WARPSYNC (warp).  BAR.ARV*, MEMBAR* never order anything in v1 (over-reports,
never under-reports).  Same-PC pairs are ordered iff a qualifying sync lies on
every cycle through the PC's region.

Memory space, read/write/atomic type and warp masks come from the trace, not
from SASS; the CFG opcode is only used to confirm every traced PC is a memory
instruction (Phase 0 alignment invariant).

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
    if base == "MEMBAR":                            # fence: non-qualifying in v1
        return ("sync", NONE, False, False)
    if base in ("EXIT", "RET"):
        return "exit"
    if base in _MEM_OPS:
        return "mem"
    if base not in _NOT_SYNC and "SYNC" in opcode:  # unrecognized *SYNC* -> tripwire
        return ("sync", NONE, False, True)
    return None


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


class Engine:
    """Sync-split region graph + dominator/post-dominator strength queries."""

    def __init__(self, blocks, edges, entry):
        self.G = nx.DiGraph()
        self.G.add_node(VEXIT)
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

    def strength(self, u, v):
        """Ordering strength of PC pair -> (scope, [ordering sync pcs])."""
        if u == v:
            return self.loop_strength(u)
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

    def _on_cycle(self, r, excluded):
        sub = self.G.subgraph(n for n in self.G if n not in excluded)
        return any(nx.has_path(sub, s, r) for s in sub.successors(r))

    def loop_strength(self, pc):
        """Same-PC pair: ordered at scope s iff a qualifying sync of scope >= s
        lies on every cycle through the PC's region (roadmap 1.5)."""
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


def analyze(dot_path, trace_path):
    trace = json.loads(Path(trace_path).read_text())
    kernels = parse_dot(dot_path)
    mangled = select_kernel(kernels, trace["kernel"]["kernel_name"])
    eng = Engine(*kernels[mangled])

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

    verdicts, skipped = [], []
    for e in trace.get("edges", []):
        cur, anc = e["current_pc"], e.get("ancient_pc")
        rec = {"current_pc": cur, "ancient_pc": anc}
        if e.get("cold_miss") or anc is None:
            skipped.append({**rec, "reason": "cold_miss"})
            continue
        dist = e.get("dist", {})
        observed, weight = NONE, 0
        for sc, key in ((GRID, "intra_grid"), (BLOCK, "intra_block"),
                        (WARP, "intra_warp")):
            if dist.get(key, 0) > 0:
                observed, weight = sc, dist[key]
                break
        same_inst = dist.get("intra_instance_launch", 0)
        cur_space, cur_access = flags.get(cur, ("generic", "read"))
        anc_space, anc_access = flags.get(anc, ("generic", "read"))
        if observed == NONE and same_inst == 0:
            skipped.append({**rec, "reason": "intra_thread_only"})
            continue
        if cur_access == "read" and anc_access == "read":
            skipped.append({**rec, "reason": "read_read"})
            continue
        if observed == NONE:  # only warp-same-instruction traffic, write involved:
            # multi-lane write in one warp instruction — no sync can intervene
            strength, used, observed, weight, same = NONE, [], WARP, same_inst, True
        else:
            (strength, used), same = eng.strength(cur, anc), False
        verdicts.append({
            "current_pc": cur, "current_pc_hex": hex(cur),
            "ancient_pc": anc, "ancient_pc_hex": hex(anc),
            "opcodes": [eng.pc_opcode[cur], eng.pc_opcode[anc]],
            "space": cur_space if cur_space == anc_space else f"{cur_space}/{anc_space}",
            "race_type": _race_type(cur_access, anc_access),
            "observed_distance": SCOPES[observed],
            "contested_weight": weight,
            "access_size": e.get("current_access_size"),
            "strength": SCOPES[strength],
            "ordering_syncs": used,
            "warp_same_inst": same,
            "verdict": "RACE" if strength < observed else "ORDERED",
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
                    "skipped": len(skipped)},
    }


def render(report, out):
    """Human-readable report text (same layout main prints), as one string."""
    lines = [f"kernel: {report['kernel']['name']}",
             "syncs:  " + (", ".join(
                 f"{s['opcode']}@{s['pc_hex']}[{s['scope']}"
                 f"{'' if s['qualifying'] else ',non-qualifying'}]"
                 for s in report["syncs"]) or "none")]
    for v in report["verdicts"]:
        via = " via " + ",".join(map(hex, v["ordering_syncs"])) if v["ordering_syncs"] else ""
        note = " (warp-same-inst)" if v["warp_same_inst"] else ""
        lines.append(f"{v['ancient_pc_hex']} -> {v['current_pc_hex']}  "
                     f"{v['opcodes'][1]}/{v['opcodes'][0]}  {v['space']}  {v['race_type']}  "
                     f"dist={v['observed_distance']}  strength={v['strength']}  "
                     f"{v['verdict']}{note}{via}")
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

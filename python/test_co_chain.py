"""C6 step 1: the chain-closure switch of the verdict step (sync_dominance.analyze(chain_closure=),
run_cuvein._analyze_reports(chain_closure=), parallel.py analyze --chain-closure,
$CUVEIN_CHAIN_CLOSURE=1). Default off, output unchanged when off.

The collector keeps ONE last accessor per word, so a read in between hides a conflict: block 1
reads (pc A), block 0 reads (pc B, edge B<-A), block 0 writes (pc C, edge C<-B) -- no edge A->C.
With the switch on, a chain A -> h1 -> ... -> hk -> C (hk >= 1, inner pcs all reads) derives the
pair (A, C) at the chain's widest hop (ultrametric bound). C6b: the bound is the WIDEST hop over
all chains (C6 took the narrowest, a minimax), and every edge is judged at max(its own distance,
its chain bound) -- a wider chain bound is a rescue (chain_rescue), also for a cross-thread edge.

Fixtures: the real rtraw recording of testdata/r3_closure (hb_* keys stripped = a collector-only
dump), synthetic kernels (a generated one-block .dot of LDG/STG and a hand-written kernel JSON), and
testdata/verdict_parallel/bfs100n for the byte-identity checks. CPU only (no GPU, no BeeGFS).
    .env/bin/python -m pytest python/test_co_chain.py -q
"""
import csv
import glob
import io
import json
import os
import re
import shutil
import sys
from pathlib import Path

import pytest

import sync_dominance as sd

_ROOT = Path(__file__).resolve().parents[1]
_TD = Path(__file__).resolve().parent / "testdata"
_BFS = _TD / "verdict_parallel" / "bfs100n"
_RTRAW_DOT = _TD / "r3_closure" / "race_interblock_none-lock_rtraw.sm_89.dot"
_RTRAW_JSON = _TD / "r3_closure" / "vector_clock_c58_run3.json"

sys.path.insert(0, str(_ROOT / "eval" / "baselines"))
import run_cuvein as rc  # noqa: E402
import parallel  # noqa: E402

assert rc.sd is sd and Path(sd.__file__).resolve().parent == _ROOT / "python", \
    f"run_cuvein imported {rc.sd.__file__}, not {_ROOT}/python (set CUVEIN_HOME={_ROOT})"

NONE, WARP, BLOCK, GRID = sd.NONE, sd.WARP, sd.BLOCK, sd.GRID
_DKEY = {"thread": "intra_thread", "warp": "intra_warp", "block": "intra_block",
         "grid": "intra_grid", "inst": "intra_instance_launch"}


@pytest.fixture(autouse=True)
def _no_env(monkeypatch):
    monkeypatch.delenv("CUVEIN_CHAIN_CLOSURE", raising=False)
    # M5: these tests encode C6/C6b's counts, i.e. the read-only chain rule; the atomic-hop tests
    # below pass chain_atomic_hop explicitly, and the env test sets the variable itself
    monkeypatch.setenv("CUVEIN_CHAIN_ATOMIC_HOP", "0")


# ---------------------------------------------------------------- synthetic kernels
def _dot(ops):
    """One-block CFG (kernel _Z5ktestv): ops = {pc: 'R' | 'W'} -> LDG.E / STG.E at those pcs, NOP
    elsewhere, EXIT last."""
    bs = "\\"

    def esc(t):
        return t.replace(" ", bs + " ").replace("[", bs + "[").replace("]", bs + "]")
    last = max(ops) + 0x10
    lines = []
    for pc in range(0, last, 0x10):
        t = {"R": "LDG.E R2, [R4.64]", "W": "STG.E [R4.64], R2",
             "A": "ATOMG.E.ADD.STRONG.GPU PT, RZ, [R4.64], R2"}.get(ops.get(pc), "NOP")
        lines.append(f"{pc:04x}:{bs} {bs} {bs} {esc(t)}{bs} ;{bs}l")
    m = "_Z5ktestv"
    head = (f"<entry>\t.global\t\t{m}{bs}l\t.type\t\t{m},@function{bs}l"
            f"\t.size\t\t{m},(.L_x_1{bs} -{bs} {m}){bs}l\t.other\t\t{m},{bs}<no{bs} object{bs}>{bs}l"
            f"{m}:{bs}l.text.{m}:{bs}l")
    tail = f"|<exit0>{last:04x}:{bs} {bs} {bs} EXIT{bs} ;{bs}l"
    label = "{" + head + "".join(lines) + tail + "}"
    return ('digraph f {\nsubgraph "cluster_' + m + '" {\n'
            'node [fontname="Courier",fontsize=10,shape=Mrecord];\n"' + m + '"\n[label="'
            + label + '"]\n}\n}\n')


def _kernel_json(ops, edges):
    """edges = [(cur, anc, dist-name)]; anc None = a cold miss."""
    return {"tool": "pc_dependency_analysis",
            "kernel": {"kernel_id": 0, "kernel_name": "ktest()", "device_id": 0, "kernel_pc": 0,
                       "grid_dim": [2, 1, 1], "block_dim": [64, 1, 1]},
            "nodes": [{"pc": pc, "flags": {"R": "READ GLOBAL", "A": "ATOMIC GLOBAL"}.get(k, "WRITE GLOBAL")}
                      for pc, k in sorted(ops.items())],
            "edges": [{"current_pc": c, "ancient_pc": a, "cold_miss": a is None,
                       "current_access_size": 4, "dist": {_DKEY[d]: 1}} for c, a, d in edges]}


def _synth(tmp, name, ops, edges):
    d = Path(tmp) / name
    d.mkdir()
    (d / "k.dot").write_text(_dot(ops))
    kj = d / "kernel_0.json"
    kj.write_text(json.dumps(_kernel_json(ops, edges)))
    return str(d / "k.dot"), str(kj)


def _rtraw(tmp):
    """The real rtraw recording as a collector-only dump (no hb_* keys)."""
    t = json.loads(_RTRAW_JSON.read_text())
    t = {k: v for k, v in t.items() if not k.startswith("hb_") and k != "coherence_profile"}
    kj = Path(tmp) / "rtraw_kernel_0.json"
    kj.write_text(json.dumps(t))
    return str(_RTRAW_DOT), str(kj)


def _canon(x):
    return json.dumps(x, sort_keys=True, default=repr)


def _tags(rep):
    return {(v["ancient_pc"], v["current_pc"]): v for v in rep["verdicts"]}


A, B, C, D, E = 0x10, 0x20, 0x30, 0x40, 0x50


# ---------------------------------------------------------------- 1. rtraw
def test_rtraw_extended_pair_is_derived(tmp_path):
    dot, kj = _rtraw(tmp_path)
    t = json.loads(Path(kj).read_text())
    assert not [k for k in t if k.startswith("hb_")]
    off = sd.analyze(dot, kj)
    on = sd.analyze(dot, kj, chain_closure=True)
    assert (0x140, 0x340) not in {(v["ancient_pc"], v["current_pc"]) for v in off["verdicts"]}
    v = _tags(on)[(0x140, 0x340)]                 # block 1's read 0x140 vs block 0's write 0x340
    assert v["chain"] is True and v["chain_rescue"] is False
    assert v["chain_path"] == ["0x140", "0x2c0", "0x340"]
    assert v["observed_distance"] == "grid" and v["race_type"] == "WAR"
    assert v["contested_weight"] == 1 and v["event_candidate"] is False
    assert v["verdict"] in ("RACE", "SC", "ORDERED")
    cc = on["diagnostics"]["chain_closure"]
    assert cc["derived"] == 1 and cc["rescued"] == 0 and cc["capped"] is False and cc["hops"] == 7
    assert set(cc) == {"hops", "derived", "rescued", "closure_s", "capped"}


# ---------------------------------------------------------------- 2. WAW through one read
def test_waw_through_one_read_is_derived(tmp_path):
    ops = {A: "W", B: "R", C: "W"}
    dot, kj = _synth(tmp_path, "waw", ops, [(B, A, "block"), (C, B, "thread")])
    assert [v["verdict"] for v in sd.analyze(dot, kj)["verdicts"]] == ["RACE"]  # B<-A only
    on = sd.analyze(dot, kj, chain_closure=True)
    v = _tags(on)[(A, C)]
    assert v["race_type"] == "WAW" and v["verdict"] == "RACE" and v["chain"] is True
    assert v["observed_distance"] == "block" and v["chain_path"] == ["0x10", "0x20", "0x30"]
    # the edge verdict B<-A is untouched, tagged as not chain-sourced, with no path
    e = _tags(on)[(A, B)]
    assert e["chain"] is False and e["chain_rescue"] is False and "chain_path" not in e
    assert on["diagnostics"]["chain_closure"]["derived"] == 1


def test_same_pc_pair_a_equals_c(tmp_path):
    """W at pc a, read by another thread, W at pc a again: the pair (a, a)."""
    ops = {A: "W", B: "R"}
    dot, kj = _synth(tmp_path, "aa", ops, [(B, A, "warp"), (A, B, "thread")])
    on = sd.analyze(dot, kj, chain_closure=True)
    v = _tags(on)[(A, A)]
    assert v["chain"] is True and v["chain_path"] == ["0x10", "0x20", "0x10"]
    assert v["observed_distance"] == "warp" and v["race_type"] == "WAW"
    assert not [x for x in sd.analyze(dot, kj)["verdicts"] if (x["ancient_pc"], x["current_pc"]) == (A, A)]


# ---------------------------------------------------------------- 3. pure read chain
def test_pure_read_chain_yields_nothing(tmp_path):
    ops = {A: "R", B: "R", C: "R"}
    dot, kj = _synth(tmp_path, "rr", ops, [(B, A, "grid"), (C, B, "grid")])
    on = sd.analyze(dot, kj, chain_closure=True)
    assert on["verdicts"] == [] and on["diagnostics"]["chain_closure"]["derived"] == 0
    assert _canon({k: v for k, v in on.items() if k != "diagnostics"}) == \
        _canon({k: v for k, v in sd.analyze(dot, kj).items() if k != "diagnostics"})


def test_a_write_or_atomic_ends_a_chain():
    hops = {A: {B: GRID}, B: {C: GRID}}
    rd = lambda pc: pc != B                       # B is a write: no chain passes through it
    assert sd.chain_closure_pairs(hops, rd, lambda a, c: True, 10) == {}
    assert sd.chain_closure_pairs(hops, lambda pc: True, lambda a, c: True, 10)[(A, C)][0] == GRID


# ---------------------------------------------------------------- 4b. M5: atomic-atomic hops
def test_atomic_atomic_load_chain_derives_the_pair(tmp_path):
    """M5: A and B are atomics, B is entered from A by an atomic-against-atomic step, C is a load:
    the chain A -> B -> C (no edge A -> C) derives (A, C) at the chain's widest hop. With
    chain_atomic_hop=False (CUVEIN_CHAIN_ATOMIC_HOP=0) the chain stops at B, as before."""
    ops = {A: "A", B: "A", C: "R"}
    dot, kj = _synth(tmp_path, "aal", ops, [(B, A, "block"), (C, B, "grid")])
    on = sd.analyze(dot, kj, chain_closure=True, chain_atomic_hop=True)
    v = _tags(on)[(A, C)]
    assert v["chain"] is True and v["chain_rescue"] is False
    assert v["chain_path"] == ["0x10", "0x20", "0x30"] and v["observed_distance"] == "grid"
    assert on["diagnostics"]["chain_closure"]["derived"] == 1
    off = sd.analyze(dot, kj, chain_closure=True, chain_atomic_hop=False)
    assert (A, C) not in _tags(off) and off["diagnostics"]["chain_closure"]["derived"] == 0


def test_atomic_store_load_chain_still_has_no_pair(tmp_path):
    """M5: a plain store in the middle still ends a chain, with the switch on."""
    ops = {A: "A", B: "W", C: "R"}
    dot, kj = _synth(tmp_path, "asl", ops, [(B, A, "block"), (C, B, "grid")])
    on = sd.analyze(dot, kj, chain_closure=True, chain_atomic_hop=True)
    assert (A, C) not in _tags(on) and on["diagnostics"]["chain_closure"]["derived"] == 0
    # the step into an atomic hop must itself be atomic against atomic: a read -> atomic step
    # (A read, B read, C atomic hop, D read) does not pass C
    hops = {A: {B: GRID}, B: {C: GRID}, C: {D: GRID}}
    out = sd.chain_closure_pairs(hops, lambda pc: pc in (A, B, D), lambda a, c: True, 10,
                                 is_atomic=lambda pc: pc == C)
    assert (A, D) not in out and (B, D) not in out


def test_atomic_hop_env_and_param_resolution(monkeypatch):
    monkeypatch.delenv("CUVEIN_CHAIN_ATOMIC_HOP", raising=False)      # the default: on
    assert sd.chain_atomic_hop_enabled() is True and sd.chain_atomic_hop_enabled(None) is True
    assert sd.chain_atomic_hop_enabled(False) is False
    monkeypatch.setenv("CUVEIN_CHAIN_ATOMIC_HOP", "0")
    assert sd.chain_atomic_hop_enabled(None) is False and sd.chain_atomic_hop_enabled(True) is True
    monkeypatch.setenv("CUVEIN_CHAIN_ATOMIC_HOP", "1")
    assert sd.chain_atomic_hop_enabled(None) is True


def test_rtraw_atomic_hops_add_pairs_and_keep_the_read_chain_pair(tmp_path):
    """M5 on the real rtraw recording (a lock: atomics against atomics): the switch adds derived
    pairs, loses none, and the read-chain pair of test 1 is still there; off is C6b's count."""
    dot, kj = _rtraw(tmp_path)
    off = sd.analyze(dot, kj, chain_closure=True, chain_atomic_hop=False)
    on = sd.analyze(dot, kj, chain_closure=True, chain_atomic_hop=True)
    k_off = {k for k, v in _tags(off).items() if v["chain"]}
    k_on = {k for k, v in _tags(on).items() if v["chain"]}
    assert k_off == {(0x140, 0x340)} and k_on >= k_off      # derived pairs the judge drops carry no record
    assert off["diagnostics"]["chain_closure"]["derived"] == 1
    assert on["diagnostics"]["chain_closure"]["derived"] == 4

# ---------------------------------------------------------------- 5. ultrametric bound
def test_three_hops_mixed_distances_take_the_widest():
    hops = {A: {B: WARP}, B: {C: GRID}, C: {D: BLOCK}}
    out = sd.chain_closure_pairs(hops, lambda pc: pc in (B, C), lambda a, c: a == A, 10)
    assert out[(A, C)] == (GRID, [A, B, C]) and out[(A, D)] == (GRID, [A, B, C, D])
    assert (A, B) not in out                       # one hop: an edge, not a chain


def test_widest_bound_over_chains():
    """C6b (was test_narrowest_bound_over_chains, which asserted C6's minimax: BLOCK via C, and
    the second pair dropped): the bound is the widest hop over every chain."""
    hops = {A: {B: GRID, C: BLOCK}, B: {D: GRID}, C: {D: BLOCK}}
    out = sd.chain_closure_pairs(hops, lambda pc: pc in (B, C), lambda a, c: True, 10)
    assert out[(A, D)] == (GRID, [A, B, D])
    # an all-intra-thread chain no longer hides a cross-thread one
    hops = {A: {B: NONE, C: GRID}, B: {D: NONE}, C: {D: GRID}}
    assert sd.chain_closure_pairs(hops, lambda pc: pc in (B, C), lambda a, c: True, 10)[(A, D)] \
        == (GRID, [A, C, D])
    # only all-intra-thread chains: not cross-thread, dropped (as in C6)
    hops = {A: {B: NONE}, B: {D: NONE}}
    assert (A, D) not in sd.chain_closure_pairs(hops, lambda pc: pc == B, lambda a, c: True, 10)


def test_widest_is_the_widest_hop_reachable_from_a_and_reaching_c():
    """Equivalent form of the bound: the widest hop (u, v) with u reachable from a and c reachable
    from v through reads -- here the GRID hop C -> E sits on a detour a chain to D can take."""
    hops = {A: {B: WARP}, B: {C: WARP, D: WARP}, C: {E: GRID}, E: {B: WARP}}
    out = sd.chain_closure_pairs(hops, lambda pc: pc in (B, C, E), lambda a, c: c == D, 10)
    assert out[(A, D)] == (GRID, [A, B, C, E, B, D])


def test_two_chains_warp_and_grid_judged_at_grid(tmp_path):
    ops = {A: "W", B: "R", C: "R", D: "W"}
    edges = [(B, A, "warp"), (D, B, "warp"), (C, A, "grid"), (D, C, "warp")]
    dot, kj = _synth(tmp_path, "warpgrid", ops, edges)
    v = _tags(sd.analyze(dot, kj, chain_closure=True))[(A, D)]
    assert v["chain"] is True and v["observed_distance"] == "grid"
    assert v["chain_path"] == ["0x10", "0x30", "0x40"]


def test_intra_warp_edge_with_a_grid_chain_is_judged_at_grid(tmp_path):
    """An edge recorded at intra_warp with a grid chain between its ends: judged at grid and
    tagged chain_rescue (C6 judged it at its own warp distance); its weight stays the edge's."""
    ops = {A: "W", B: "R", C: "W"}
    edges = [(B, A, "grid"), (C, B, "grid"), (C, A, "warp")]
    dot, kj = _synth(tmp_path, "warpedge", ops, edges)
    off = _tags(sd.analyze(dot, kj))[(A, C)]
    assert off["observed_distance"] == "warp"
    on = sd.analyze(dot, kj, chain_closure=True)
    v = _tags(on)[(A, C)]
    assert v["observed_distance"] == "grid" and v["chain_rescue"] is True and v["chain"] is False
    assert v["chain_path"] == ["0x10", "0x20", "0x30"]
    assert v["edge_rescued"] is False and v["contested_weight"] == 1 and v["race_type"] == "WAW"
    assert on["diagnostics"]["chain_closure"]["rescued"] == 1
    assert on["diagnostics"]["chain_closure"]["derived"] == 0
    # an edge whose own distance is at least the chain bound is untouched
    dot2, kj2 = _synth(tmp_path, "gridedge", ops, [(B, A, "block"), (C, B, "block"), (C, A, "grid")])
    v2 = _tags(sd.analyze(dot2, kj2, chain_closure=True))[(A, C)]
    assert v2["chain_rescue"] is False and v2["observed_distance"] == "grid"


def test_ultrametric_bound_through_analyze(tmp_path):
    ops = {A: "W", B: "R", C: "R", D: "W"}
    edges = [(B, A, "warp"), (C, B, "grid"), (D, C, "block")]
    dot, kj = _synth(tmp_path, "ultra", ops, edges)
    on = _tags(sd.analyze(dot, kj, chain_closure=True))
    assert on[(A, D)]["observed_distance"] == "grid" and on[(A, D)]["chain"]
    assert on[(A, C)]["observed_distance"] == "grid" and on[(A, C)]["chain"]
    assert on[(A, B)]["chain"] is False and on[(A, B)]["observed_distance"] == "warp"


def test_widest_over_two_chains_through_analyze(tmp_path):
    """C6b (was test_narrowest_over_two_chains_through_analyze: block via C under C6's minimax)."""
    ops = {A: "W", B: "R", C: "R", D: "W"}
    edges = [(B, A, "grid"), (D, B, "grid"), (C, A, "block"), (D, C, "block")]
    dot, kj = _synth(tmp_path, "twochains", ops, edges)
    v = _tags(sd.analyze(dot, kj, chain_closure=True))[(A, D)]
    assert v["observed_distance"] == "grid" and v["chain_path"] == ["0x10", "0x20", "0x40"]


def test_same_instruction_self_edge_is_a_warp_hop(tmp_path):
    """(pc, pc) with only intra_instance_launch counts as WARP as a hop. C6b (this test asserted
    C6's minimax before: a self loop never narrowed a bound, so (A, C) was dropped as intra-thread
    by the walk that skips the loop): the widest walk takes the loop, A -> B -> B -> C crosses
    another lane of B's warp instruction, so (A, C) is derived at WARP."""
    ops = {A: "W", B: "R", C: "W"}
    edges = [(B, A, "thread"), (B, B, "inst"), (C, B, "thread")]
    dot, kj = _synth(tmp_path, "selfedge", ops, edges)
    on = sd.analyze(dot, kj, chain_closure=True)
    assert on["diagnostics"]["chain_closure"]["hops"] == 3
    d = _tags(on)[(A, C)]
    assert d["chain"] is True and d["observed_distance"] == "warp" and d["race_type"] == "WAW"
    assert d["chain_path"] == ["0x10", "0x20", "0x20", "0x30"]
    assert (B, B) not in _tags(on)            # the read-read self edge is skipped, as today
    # ... and as a hop it makes the intra-thread edge A -> B cross-thread (A, then B on another
    # lane of the same warp instruction): a rescue at WARP
    r = _tags(on)[(A, B)]
    assert r["chain_rescue"] is True and r["observed_distance"] == "warp" \
        and r["chain_path"] == ["0x10", "0x20", "0x20"]
    assert sd.chain_closure_pairs({A: {B: NONE}, B: {B: WARP, C: NONE}},
                                  lambda pc: pc == B, lambda a, c: a == A, 10) == \
        {(A, B): (WARP, [A, B, B]), (A, C): (WARP, [A, B, B, C])}
    assert sd.chain_closure_pairs({A: {B: BLOCK}, B: {B: GRID, C: BLOCK}},
                                  lambda pc: pc == B, lambda a, c: a == A, 10)[(A, C)] == \
        (GRID, [A, B, B, C])


# ---------------------------------------------------------------- rescue
def test_intra_thread_edge_rescued_by_a_cross_thread_chain(tmp_path):
    ops = {A: "W", B: "R", C: "W"}
    edges = [(B, A, "block"), (C, B, "grid"), (C, A, "thread")]
    dot, kj = _synth(tmp_path, "rescue", ops, edges)
    off = sd.analyze(dot, kj)
    assert {(s["ancient_pc"], s["current_pc"]): s["reason"] for s in off["skipped_edges"]}[(A, C)] \
        == "intra_thread_only"
    on = sd.analyze(dot, kj, chain_closure=True)
    v = _tags(on)[(A, C)]
    assert v["chain_rescue"] is True and v["chain"] is False and v["edge_rescued"] is True
    assert v["observed_distance"] == "grid" and v["contested_weight"] == 1
    assert v["chain_path"] == ["0x10", "0x20", "0x30"]
    cc = on["diagnostics"]["chain_closure"]
    assert cc["rescued"] == 1 and cc["derived"] == 0
    assert all(s["reason"] != "intra_thread_only" for s in on["skipped_edges"])
    # edges that produce a verdict today are untouched
    keep = [{k: v for k, v in x.items() if k not in ("chain", "chain_rescue", "chain_path")}
            for x in on["verdicts"] if not x["chain"] and not x["chain_rescue"]]
    assert _canon(keep) == _canon(off["verdicts"])


# ---------------------------------------------------------------- 4. off is unchanged
def _fixtures(tmp_path):
    out = [("rtraw",) + _rtraw(tmp_path)]
    out.append(("waw",) + _synth(tmp_path, "w", {A: "W", B: "R", C: "W"},
                                 [(B, A, "block"), (C, B, "thread")]))
    for mode in ("vector-clock", "scalar-clock"):
        dots = sorted(glob.glob(str(_BFS / "dots" / "*.dot")))
        for kj in sorted(glob.glob(str(_BFS / mode / "kernel_*.json"))):
            for dot in dots:
                try:
                    sd.analyze(dot, kj)
                except sd.AlignmentError:
                    continue
                out.append((f"{mode}/{os.path.basename(kj)}", dot, kj))
                break
    return out


def test_switch_off_is_byte_identical(tmp_path):
    fx = _fixtures(tmp_path)
    assert len(fx) >= 18
    for name, dot, kj in fx:
        base = _canon(sd.analyze(dot, kj))
        assert _canon(sd.analyze(dot, kj, chain_closure=False)) == base, name
        assert '"chain' not in base and "chain_closure" not in base, name   # nothing added
        on = sd.analyze(dot, kj, chain_closure=True)
        assert "chain_closure" in on["diagnostics"]
        # on: every other verdict is exactly today's (edges that produce a verdict and that no
        # wider chain rescues are untouched; C6b: a rescued edge may have a verdict today too)
        kept = [{k: v for k, v in x.items() if k not in ("chain", "chain_rescue", "chain_path")}
                for x in on["verdicts"] if not x["chain"] and not x["chain_rescue"]]
        resc = {(x["ancient_pc"], x["current_pc"]) for x in on["verdicts"] if x["chain_rescue"]}
        off_v = [x for x in json.loads(base)["verdicts"]
                 if (x["ancient_pc"], x["current_pc"]) not in resc]
        assert _canon(kept) == _canon(off_v), name


def test_analyze_reports_off_is_unchanged(tmp_path):
    for mode in ("vector-clock", "scalar-clock"):
        d, dots = str(_BFS / mode), str(_BFS / "dots")
        default = _canon(rc._analyze_reports(d, dots, workers=1))
        st = {}
        assert _canon(rc._analyze_reports(d, dots, workers=1, chain_closure=False,
                                          stats_out=st)) == default and st == {}
        assert "chain_" not in default
        assert "chain_" not in _canon(rc._analyze_reports(d, dots, workers=8))


def test_env_and_param_resolution(monkeypatch):
    assert rc.chain_closure_enabled() is False and rc.chain_closure_enabled(None) is False
    assert rc.chain_closure_enabled(True) is True
    monkeypatch.setenv("CUVEIN_CHAIN_CLOSURE", "1")
    assert rc.chain_closure_enabled(None) is True and rc.chain_closure_enabled(False) is False
    monkeypatch.setenv("CUVEIN_CHAIN_CLOSURE", "0")
    assert rc.chain_closure_enabled(None) is False
    monkeypatch.setenv("CUVEIN_CHAIN_CLOSURE", "true")
    assert rc.chain_closure_enabled(None) is False        # only "1"


# ---------------------------------------------------------------- 6. serial == N=1 == N=8
_RUNS = {"serial-1": dict(workers=1, cache=False),
         "cached-1": dict(workers=1, cache=True),
         "cached-8": dict(workers=8, cache=True)}


def _store(tmp_path):
    """A dump dir of 5 kernel JSONs over two CFGs (synthetic + rtraw) and its dots dir."""
    d, dots = tmp_path / "dump", tmp_path / "dots"
    d.mkdir()
    dots.mkdir()
    rdot, rkj = _rtraw(tmp_path)
    shutil.copy(rdot, dots / "1_rtraw.dot")
    ops = {A: "W", B: "R", C: "W", D: "R", E: "W"}
    (dots / "0_synth.dot").write_text(_dot(ops))
    docs = [json.loads(Path(rkj).read_text()),
            _kernel_json(ops, [(B, A, "block"), (C, B, "thread")]),
            _kernel_json(ops, [(B, A, "warp"), (C, B, "grid"), (D, C, "block"), (C, A, "thread"),
                               (E, B, "block"), (E, D, "block")]),
            json.loads(Path(rkj).read_text()),
            _kernel_json(ops, [(B, A, "grid"), (D, B, "grid")])]
    for i, doc in enumerate(docs):
        (d / f"kernel_{i}.json").write_text(json.dumps(doc))
    return str(d), str(dots)


def _canon_stats(res, st):
    st = dict(st, closure_s=0, kernels=[dict(k, closure_s=0) for k in st["kernels"]])
    return _canon([res, st])


def test_switch_on_identical_serial_n1_n8(tmp_path):
    d, dots = _store(tmp_path)
    out = {}
    for k, kw in _RUNS.items():
        st = {}
        res = rc._analyze_reports(d, dots, chain_closure=True, stats_out=st, **kw)
        out[k] = _canon_stats(res, st)
    assert out["cached-1"] == out["serial-1"] and out["cached-8"] == out["serial-1"]
    ids, pcs, raw = rc._analyze_reports(d, dots, workers=1, chain_closure=True, stats_out=st)
    assert [x["kernel_json"] for x in st["kernels"]] == sorted(glob.glob(f"{d}/kernel_*.json"))
    assert st["hops"] == sum(x["hops"] for x in st["kernels"]) > 0
    assert st["derived"] == sum(x["derived"] for x in st["kernels"])
    assert [x["derived"] for x in st["kernels"]] == [1, 1, 2, 1, 1] and st["rescued"] == 1
    assert st["maxk"] == 2 and st["derived"] == 6
    # the raw records say where each report came from
    assert raw and all(r["chain_src"] in ("edge", "chain", "chain_rescue") and "chain_path" in r
                       for r in raw)
    assert {r["chain_src"] for r in raw} >= {"edge", "chain"}
    # the same through the env switch
    os.environ["CUVEIN_CHAIN_CLOSURE"] = "1"
    try:
        assert _canon(rc._analyze_reports(d, dots, workers=8)) == \
            _canon(rc._analyze_reports(d, dots, workers=1, chain_closure=True))
    finally:
        del os.environ["CUVEIN_CHAIN_CLOSURE"]


def test_bfs_on_identical_serial_n1_n8():
    for mode in ("vector-clock", "scalar-clock"):
        out = {}
        for k, kw in _RUNS.items():
            st = {}
            res = rc._analyze_reports(str(_BFS / mode), str(_BFS / "dots"), chain_closure=True,
                                      stats_out=st, **kw)
            out[k] = _canon_stats(res, st)
        assert out["cached-1"] == out["serial-1"] and out["cached-8"] == out["serial-1"], mode


# ---------------------------------------------------------------- cap
def test_chain_cap_error(tmp_path, monkeypatch):
    d, dots = _store(tmp_path)
    monkeypatch.setattr(sd, "CHAIN_CAP", 1)         # the kernel_2 above derives 2+ pairs
    for k, kw in _RUNS.items():
        with pytest.raises(sd.ChainCapError) as ei:
            rc._analyze_reports(d, dots, chain_closure=True, **kw)
        msg = str(ei.value)
        assert msg.startswith("chain-cap") and "ktest()" in msg and "kernel_" in msg \
            and "2 derived pairs" in msg, (k, msg)
        # off: the cap is never consulted
        rc._analyze_reports(d, dots, **kw)
    with pytest.raises(RuntimeError) as ci:         # the capped (forked-child) path: ERROR row text
        parallel._analyze_capped(d, dots, 600, -1, 4, True)
    assert "chain-cap" in str(ci.value) and "ChainCapError" in str(ci.value)


# ---------------------------------------------------------------- harness rows and the jsonl
_TIMER = re.compile(r";analysis_s=[0-9.]+;analysis_workers=\d+;analysis_kjsons=\d+")


def _rows(idir, tmp_path, tag, **kw):
    cdir = tmp_path / f"confirm-{tag}"
    cdir.mkdir()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=parallel.blib.COLUMNS)
    w.writeheader()
    parallel.analyze_one(str(idir), w, str(cdir), analysis_workers=2, **kw)
    return list(csv.DictReader(io.StringIO(buf.getvalue())))


def test_analyze_one_notes_and_jsonl(tmp_path, monkeypatch):
    idir = tmp_path / "store" / "bfs100n"
    shutil.copytree(_BFS, idir)
    monkeypatch.setattr(parallel, "MODES", ("vector-clock", "scalar-clock"))
    off = _rows(idir, tmp_path, "off")
    assert off and not any("chain" in r["notes"] for r in off)
    log = tmp_path / "chain-kernels-t.jsonl"
    for cap_s in (0, 600):                           # in-process and forked-child paths
        log.write_text("")
        on = _rows(idir, tmp_path, f"on{cap_s}", chain_closure=True, chain_log=str(log),
                   analysis_cap=cap_s)
        assert len(on) == len(off)
        pat = re.compile(r";chain=1;chain_hops=(\d+);chain_derived=(\d+);chain_rescued=(\d+)"
                         r";chain_s=(\d+\.\d{3});chain_maxk=(\d+)$")
        for r in on:
            m = pat.search(r["notes"])
            assert m, r["notes"]
        lines = [json.loads(x) for x in log.read_text().splitlines()]
        assert lines and all(set(x) == {"id", "mode", "kernel_json", "hops", "derived", "rescued",
                                        "closure_s", "capped"} for x in lines)
        assert sum(x["hops"] for x in lines if x["mode"] == "vector-clock") == \
            int(pat.search(on[0]["notes"]).group(1))
        assert [x["kernel_json"] for x in lines if x["mode"] == "vector-clock"] == \
            sorted(glob.glob(str(idir / "vector-clock" / "kernel_*.json")))
    # off + env: the row is annotated too (the env switch reached _analyze_reports)
    monkeypatch.setenv("CUVEIN_CHAIN_CLOSURE", "1")
    assert all(";chain=1;chain_hops=" in r["notes"] for r in _rows(idir, tmp_path, "env"))

"""Three substitutions of design/proof/hb_proof.tex section 7 on real kernels -- pinned as strict
xfails by T6 (c), fixed by T9 -- plus T9's D12 case. Each kernel is built and traced here
(getall.sh, vector-clock mode); pairs are asserted by role, not by pc offset; the scalar-clock
verdict is the same dump without HbClock's keys (what YOSEMITE_HB_MODE=scalar-clock
writes). Every case also asserts HbClock == hb_oracle == design/algorithms_check.py's
Detect(T, vec) with the I1/I2 switches off (the proof's reference).

  I1  python/testdata/write_after_unlock_other_schedule.cu -- the ScoR rtraw lock pattern
      with block 0 first: block 0's write after its unlock races block 1's read under the
      lock. Tick-before-publish hides it (Proposition "Missed class of I1"). The data is
      volatile, so since T10 (default --strong-ldst token) both accesses are strong at sys
      scope and the reportable pair is an SC, not a DR; the class is asserted per policy.
  I2  python/testdata/strong_stores_barrier_weak_load.cu -- Remark "Why one bucket per key":
      two unordered strong stores, a barrier, a weak load; one last write per location hides
      the first store from the load, in both clocks.
  I5  python/testdata/local_mem_blocks.cu -- thread-private local arrays. The collector's
      thread-id fold of a local address is lost to a 32-bit shift, so every thread's access
      at one offset was one location (8,096 spurious records). T9 (D14) takes local memory
      out of the HB model: no local record in hb_events, none replayed from an older dump.
  D12 python/testdata/strong_store_strong_load.cu -- an unordered relaxed cuda::atomic store
      and load: an SC pair, class `sc` in vector-clock mode, never `model_bug`.
  A2  (T14, design/a2_flag.md) python/testdata/lock_contention_a2.cu -- the rtraw lock idiom
      on plain data: race-free with 16 contending warps, every report the trace shows is an A2
      inversion and must carry a2_uncertain; a control kernel's genuine race (no window
      overlaps) must not. Plus hand-made traces and a randomized check against every
      window-consistent coherence order (no GPU).

Part of the green set (CLAUDE.md A4) since T9; the kernels need a GPU node.
    .env/bin/python -m pytest python/test_hb_substitutions.py -rxX
"""
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import hb_oracle
import sync_dominance as sd

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "design"))
import algorithms_check as ac  # noqa: E402

_SRC = _ROOT / "python" / "testdata"


def _trace(tmp_path_factory, name):
    """(dots, kernel JSON) of one vector-clock run of testdata/<name>.cu."""
    if shutil.which("nvcc") is None:
        pytest.skip("no nvcc (run on a GPU node)")
    d = tmp_path_factory.mktemp(name)
    binary = d / name
    b = subprocess.run(["nvcc", "-arch=native", "-lineinfo", "--cudart", "shared",
                        str(_SRC / f"{name}.cu"), "-o", str(binary)], capture_output=True)
    if b.returncode != 0:
        pytest.skip(f"build failed: {b.stderr.decode()[-300:]}")
    subprocess.run(["bash", str(_ROOT / "getall.sh"), str(binary)], cwd=_ROOT,
                   capture_output=True, timeout=600)
    dots = sorted((d / f"{name}_extracted_cubins").glob("*.dot"))
    traces = sorted(d.glob(f"dependency_{name}*/kernel_*.json"))
    if not dots or not traces:
        pytest.skip("no trace produced (GPU / collector unavailable)")
    return dots, traces[-1]


def _load(trace):
    return json.loads(Path(trace).read_text())


def _mem(t):
    return [e for e in sorted(t["hb_events"], key=lambda e: e["seq"]) if "lanes" in e]


def _verdict(dots, trace, pcs):
    for dot in dots:
        try:
            rep = sd.analyze(dot, trace)
            break
        except sd.AlignmentError:
            continue
    else:
        raise AssertionError("no CFG aligns with the trace")
    return [v for v in rep["verdicts"] if {v["current_pc"], v["ancient_pc"]} == set(pcs)]


def _hb_clock_equals_specification(dots, trace):
    """HbClock == specification (records with class, and the second clock), and the oracle ==
    Detect(T, vec) with the I1/I2 switches off (record pairs with DR/SC)."""
    key = lambda r: (r.get("a_pc"), r["b_pc"], r["kind"], r.get("class"), r["space"], r.get("dist"),
                     r.get("async"), r.get("count"), r.get("a2_uncertain"))
    t = _load(trace)
    dot, _, _ = ac.tables(dots, t)
    rep = hb_oracle.analyze(dot, trace, records=True)
    oracle = {key(r) for r in rep["races"]}
    ref = set(ac.reference(dots, trace))
    return {key(r) for r in t.get("hb_races", [])} == oracle \
        and t.get("hb_races_sync_only") == rep["races_sync_only"] \
        and {tuple(r) for r in rep["race_records"]} == ref


def _scalar_clock(trace, tmp_path):
    """The dump as scalar-clock mode writes it: no HbClock keys."""
    t = copy.deepcopy(_load(trace))
    for k in ("hb_races", "hb_races_sync_only", "coherence_profile"):
        t.pop(k, None)
    out = Path(tmp_path) / ("sc_" + Path(trace).name)
    out.write_text(json.dumps(t))
    return out


# --- I1: write after unlock, block 0 first ---------------------------------------------

@pytest.fixture(scope="module")
def i1(tmp_path_factory):
    dots, trace = _trace(tmp_path_factory, "write_after_unlock_other_schedule")
    t = _load(trace)
    _, atom, coh = ac.tables(dots, t)
    ev = _mem(t)
    b0, b1 = [e for e in ev if e["block"] == 0], [e for e in ev if e["block"] == 1]
    if not b0 or not b1 or b0[-1]["seq"] > b1[0]["seq"]:
        pytest.skip("schedule not reached: block 0 did not finish before block 1 started")
    unlock = [e for e in b0 if e["pc"] in atom][-1]
    write = next(e for e in b0 if e["seq"] > unlock["seq"] and e["pc"] not in atom)
    addr = write["lanes"][0]["addr"]
    read = next(e for e in b1 if e["type"] == "read" and e["lanes"][0]["addr"] == addr)
    # T10: the class of the pair under the active policy (the two blocks differ, so the
    # pair is morally strong iff both pcs are strong at grid scope: volatile under token)
    cls = "SC" if min(coh.get(write["pc"], -1), coh.get(read["pc"], -1)) == sd.GRID else "DR"
    return dots, trace, write, read, cls


def test_write_after_unlock_reference_reports_it(i1):
    dots, trace, write, read, cls = i1
    ref = {(r[2], r[1] >> 10, r[4], r[3] >> 10, r[5]) for r in ac.reference(dots, trace)}
    assert ref == {(write["pc"], 0, read["pc"], 1, cls)}


def test_write_after_unlock_hb_clock_matches_specification(i1):
    assert _hb_clock_equals_specification(*i1[:2])


def test_write_after_unlock_other_schedule(i1):
    # I1 fixed (T9): publish-then-tick reports the releaser's post-release write -- a DR
    # under the pre-T10 generic policy, an SC under token (both accesses volatile, T10)
    dots, trace, write, read, cls = i1
    assert any(r["a_pc"] == write["pc"] and r["b_pc"] == read["pc"] and r["kind"] == "RAW"
               and r["class"] == cls for r in _load(trace).get("hb_races", []))
    [v] = _verdict(dots, trace, (write["pc"], read["pc"]))
    assert (v["verdict"], v["hb_class"]) == \
        (("RACE", "structural") if cls == "DR" else ("SC", "sc"))


def test_write_after_unlock_scalar_clock(i1, tmp_path):
    dots, trace, write, read, cls = i1
    [v] = _verdict(dots, _scalar_clock(trace, tmp_path), (write["pc"], read["pc"]))
    assert v["verdict"] == ("RACE" if cls == "DR" else "SC")


# --- I2: two strong stores, a barrier, a weak load ---------------------------------------

@pytest.fixture(scope="module")
def i2(tmp_path_factory):
    dots, trace = _trace(tmp_path_factory, "strong_stores_barrier_weak_load")
    t = _load(trace)
    _, _, coh = ac.tables(dots, t)
    ev = _mem(t)
    a = next(e for e in ev if e["block"] == 1 and e["type"] == "write")
    x = a["lanes"][0]["addr"]
    b = next(e for e in ev if e["block"] == 0 and e["warp"] == 0 and e["type"] == "write"
             and e["lanes"][0]["addr"] == x)
    c = next(e for e in ev if e["block"] == 0 and e["warp"] == 1 and e["type"] == "read"
             and e["lanes"][0]["addr"] == x)
    assert a["pc"] in coh and b["pc"] in coh and c["pc"] not in coh, \
        "the stores must be coherent (strong) and the load weak under --strong-ldst generic"
    if not a["seq"] < b["seq"] < c["seq"]:
        pytest.skip("schedule not reached: A's store did not precede B's")
    return dots, trace, a, b, c


def test_bucket_kernel_reference_reports_dr_and_sc(i2):
    dots, trace, a, b, c = i2
    ref = {(r[2], r[4], r[5]) for r in ac.reference(dots, trace)}
    assert ref == {(a["pc"], c["pc"], "DR"), (a["pc"], b["pc"], "SC")}


def test_bucket_kernel_hb_clock_matches_specification(i2):
    assert _hb_clock_equals_specification(*i2[:2])


def test_strong_stores_barrier_weak_load(i2):
    # I2 fixed (T9): buckets keep A's store; (A, C) is a DR, (A, B) an SC, in both clocks
    dots, trace, a, b, c = i2
    t = _load(trace)
    cls = {(frozenset((r["a_pc"], r["b_pc"])), r["class"]) for r in t.get("hb_races", [])}
    assert (frozenset((a["pc"], c["pc"])), "DR") in cls
    assert (frozenset((a["pc"], b["pc"])), "SC") in cls
    sync = {frozenset((x, y)) for x, y, _ in t["hb_races_sync_only"]}
    assert frozenset((a["pc"], c["pc"])) in sync and frozenset((b["pc"], c["pc"])) not in sync
    [v] = _verdict(dots, trace, (a["pc"], c["pc"]))
    assert v["verdict"] == "RACE" and v["conflict_class"] == "DR"


def test_strong_stores_barrier_weak_load_scalar_clock(i2, tmp_path):
    # the offline barrier-only pass has the buckets too: (A, C) is a candidate and a RACE
    dots, trace, a, b, c = i2
    [v] = _verdict(dots, _scalar_clock(trace, tmp_path), (a["pc"], c["pc"]))
    assert v["verdict"] == "RACE" and v["conflict_class"] == "DR"


# --- I5: local memory ---------------------------------------------------------------------

@pytest.fixture(scope="module")
def i5(tmp_path_factory):
    dots, trace = _trace(tmp_path_factory, "local_mem_blocks")
    t = _load(trace)
    _, _, _ = ac.tables(dots, t)
    ops = set()
    for dot in dots:
        for blocks, _, _ in sd.parse_dot(dot).values():
            ops |= {op.split(".")[0] for ins in blocks.values() for _, op in ins}
    if not {"LDL", "STL"} & ops:
        pytest.skip("the array was not placed in local memory (no LDL/STL in the SASS)")
    return dots, trace, t, [e for e in _mem(t) if e["space"] == "local"]


def test_local_memory_verdict_is_clean(i5):
    # the dependency side records no local pcs, so no local pair reaches the verdict layer
    dots, trace, _, _ = i5
    for dot in dots:
        try:
            assert sd.analyze(dot, trace)["summary"]["races"] == 0
            return
        except sd.AlignmentError:
            continue
    raise AssertionError("no CFG aligns with the trace")


def test_local_memory_is_thread_private(i5):
    # I5 fixed (T9, D14): local memory is outside the HB model -- the HB trace carries no
    # local record and HbClock reports no local race
    _, _, t, loc = i5
    assert not loc
    assert not [r for r in t.get("hb_races", []) if r["space"] == "local"]


def test_local_records_of_an_older_dump_are_ignored(i5):
    # an older dump carries local records: the oracle and the offline pass skip them, so it
    # replays as a new one. Graft every global record's lanes onto a local twin at one
    # shared offset (every thread one "location" -- what the old collector produced).
    dots, trace, t, _ = i5
    dot, atom, coh = ac.tables(dots, t)
    old = copy.deepcopy(t)
    seq = max(e["seq"] for e in old["hb_events"]) + 1
    for e in list(old["hb_events"]):
        if "lanes" in e:
            twin = dict(e, seq=seq, space="local",
                        lanes=[dict(ln, addr=0x10) for ln in e["lanes"]])
            old["hb_events"].append(twin)
            seq += 1
    path = Path(trace).with_name("old_style_" + Path(trace).name)
    path.write_text(json.dumps(old))
    new, replay = hb_oracle.analyze(dot, trace), hb_oracle.analyze(dot, path)
    assert replay["races"] == new["races"]
    assert replay["races_sync_only"] == new["races_sync_only"]
    assert sd.barrier_only_pairs(old, atom, coh) == sd.barrier_only_pairs(t, atom, coh)


# --- D12: an unordered strong store / strong load is `sc`, never model_bug ---------------

@pytest.fixture(scope="module")
def d12(tmp_path_factory):
    dots, trace = _trace(tmp_path_factory, "strong_store_strong_load")
    t = _load(trace)
    _, _, coh = ac.tables(dots, t)
    ev = _mem(t)
    st = next(e for e in ev if e["block"] == 1 and e["type"] == "write")
    ld = next(e for e in ev if e["block"] == 0 and e["type"] == "read"
              and e["lanes"][0]["addr"] == st["lanes"][0]["addr"])
    assert st["pc"] in coh and ld["pc"] in coh, \
        "the store and the load must be strong under --strong-ldst generic"
    if st["seq"] > ld["seq"]:
        pytest.skip("schedule not reached: the load ran before the store")
    return dots, trace, st, ld


def test_strong_store_strong_load_hb_clock_matches_specification(d12):
    assert _hb_clock_equals_specification(*d12[:2])


def test_strong_store_strong_load_is_sc(d12):
    dots, trace, st, ld = d12
    recs = [r for r in _load(trace).get("hb_races", [])
            if {r["a_pc"], r["b_pc"]} == {st["pc"], ld["pc"]}]
    assert recs and all(r["class"] == "SC" for r in recs)
    [v] = _verdict(dots, trace, (st["pc"], ld["pc"]))
    assert v["hb_class"] == "sc" and v["verdict"] == "SC" and v["conflict_class"] == "SC"


def test_strong_store_strong_load_scalar_clock(d12, tmp_path):
    dots, trace, st, ld = d12
    [v] = _verdict(dots, _scalar_clock(trace, tmp_path), (st["pc"], ld["pc"]))
    assert v["hb_class"] == "sc" and v["verdict"] == "SC"


# --- T14: the a2_uncertain flag (design/a2_flag.md) ---------------------------------------
# Hand-made traces in the oracle's real record format (no GPU). One thread per (block, warp),
# lane 0, unless a lane mask is given; pc 0x40 is a block barrier.

_A2_OPS = {   # pc: (opcode, location, record type); one location per pc
    0x10: ("ATOMG.E.CAS.STRONG.GPU", 0x2000, "write"),
    0x20: ("ATOMG.E.EXCH.STRONG.GPU", 0x2000, "write"),
    0x38: ("ATOMG.E.ADD", 0x2000, "write"),               # scope none: never morally strong
    0x58: ("ATOMG.E.ADD.STRONG.SM", 0x2000, "write"),     # block scope
    0x50: ("ATOMG.E.CAS.STRONG.GPU", 0x2100, "write"),
    0x18: ("LDG.E", 0x1000, "read"), 0x28: ("STG.E", 0x1000, "write"),
    0x60: ("LDG.E", 0x2000, "read"), 0x30: ("STG.E", 0x2000, "write"),
    0x68: ("LDG.E", 0x3000, "read"), 0x70: ("STG.E", 0x3000, "write"),
    0x78: ("LD.E.STRONG.GPU", 0x3000, "read"),            # strong (every --strong-ldst policy
    0x88: ("ST.E.STRONG.GPU", 0x3000, "write"),           # but none): SC pairs among them
}
_CAS, _EXCH, _ADDN, _LDX, _STX, _STF, _LDF, _LDY, _BAR = \
    0x10, 0x20, 0x38, 0x18, 0x28, 0x30, 0x60, 0x68, 0x40


def _a2_dump(tmp_path, events, block_tc=32):
    """events: (block, warp, pc[, lane mask]) in seq order -> (dot, dump) paths."""
    ins = sorted((pc, op) for pc, (op, _, _) in _A2_OPS.items()) + \
        [(_BAR, "BAR.SYNC.DEFER_BLOCKING"), (0x80, "EXIT")]
    body = "\\l".join(f"{pc:04x}: {op} ;" for pc, op in ins) + "\\l"
    ev = []
    for s, (block, warp, pc, *m) in enumerate(events, 1):
        mask = m[0] if m else 1
        if pc == _BAR:
            ev.append({"seq": s, "type": "barrier", "block": block, "warp": warp, "pc": pc,
                       "bar_index": 0, "thread_count": 0, "active_mask": mask})
            continue
        _, addr, typ = _A2_OPS[pc]
        ev.append({"seq": s, "type": typ, "block": block, "warp": warp, "pc": pc,
                   "space": "global", "size": 4, "active_mask": mask,
                   "lanes": [{"lane": k, "addr": addr} for k in range(32) if mask >> k & 1]})
    d, t = Path(tmp_path) / "a2.dot", Path(tmp_path) / "a2.json"
    if not d.exists():                      # once: sd.parse_dot caches by file
        d.write_text('digraph "x" {\n subgraph "cluster_k" {\n'
                     f'  "k" [shape=Mrecord, label="{{{body}}}"];\n }}\n}}\n')
    t.write_text(json.dumps({"kernel": {"kernel_name": "k", "block_thread_count": block_tc},
                             "hb_events": ev}))
    return d, t


def _a2_flags(tmp_path, events, block_tc=32):
    """{(a_pc, b_pc): [instances, flagged]} of the oracle on a hand-made trace (plain data and
    RMWs only: every pair is a DR)."""
    out = {}
    for r in hb_oracle.analyze(*map(str, _a2_dump(tmp_path, events, block_tc)))["races"]:
        assert r["class"] == "DR"
        c = out.setdefault((r["a_pc"], r["b_pc"]), [0, 0])
        c[0] += r["count"]
        c[1] += r["a2_uncertain"]
    return out


_A, _B = 0, 1   # blocks; warp 0


def test_a2_inverted_handoff_is_flagged(tmp_path):
    # T9's matrix-multiplication shape: B's CAS is recorded before A's unlock it read from;
    # the critical sections are unordered on the trace, and every instance is flagged
    got = _a2_flags(tmp_path, [(_A, 0, _CAS), (_A, 0, _LDX), (_A, 0, _STX), (_B, 0, _CAS),
                               (_A, 0, _EXCH), (_B, 0, _LDX), (_B, 0, _STX), (_B, 0, _EXCH)])
    assert got and all(n == f > 0 for n, f in got.values()), got


def test_a2_no_overlap_is_exact(tmp_path):
    # no two windows on the lock overlap: the flag is 0 -- here on the rtraw race (a write
    # after its own unlock against the next holder's read), a race of every schedule order
    got = _a2_flags(tmp_path, [(_A, 0, _CAS), (_A, 0, _LDX), (_A, 0, _EXCH), (_A, 0, _STX),
                               (_B, 0, _CAS), (_B, 0, _LDX), (_B, 0, _EXCH)])
    assert got == {(_STX, _LDX): [1, 0]}


@pytest.mark.parametrize("closed", [False, True])
def test_a2_held_on_the_later_rmw(tmp_path, closed):
    # (A's plain store to the lock word, B's CAS) is a DR; A's own CAS inside B's window can
    # precede B's CAS in coherence order, which orders the pair -- decided when B's window
    # closes (flagged), and not if A's CAS comes after it (not flagged)
    ev = [(_A, 0, _STF), (_B, 0, _CAS), (_A, 0, _CAS), (_B, 0, _LDX)]
    if closed:
        ev = [ev[0], ev[1], ev[3], ev[2]]
    assert _a2_flags(tmp_path, ev) == {(_STF, _CAS): [1, 0 if closed else 1]}


@pytest.mark.parametrize("closed", [False, True])
def test_a2_held_on_the_earlier_rmw(tmp_path, closed):
    # (A's CAS, B's plain read of the lock word) is a DR while A's window is open; B's CAS
    # inside that window can precede A's in coherence order (flagged when A's window closes)
    ev = [(_A, 0, _CAS), (_B, 0, _LDF), (_B, 0, _CAS), (_A, 0, _LDX)]
    if closed:
        ev = [ev[0], ev[1], ev[3], ev[2]]
    assert _a2_flags(tmp_path, ev) == {(_CAS, _LDF): [1, 0 if closed else 1]}


def test_a2_scope_mismatch_is_not_flagged(tmp_path):
    # block-scope RMWs of two blocks on one word (ScoR race_interblock_blkatom): never morally
    # strong, so no coherence order chains them -- their DR stays unflagged although the
    # windows overlap (the flag joins only along ms-connectivity inside a cluster)
    blk = 0x58                              # ATOMG.E.ADD.STRONG.SM
    ev = [(_A, 0, blk), (_B, 0, blk), (_A, 0, _LDX), (_B, 0, _LDX)]
    assert _a2_flags(tmp_path, ev) == {(blk, blk): [1, 0]}


def test_a2_block_leader_lock_through_barriers(tmp_path):
    # thread 0 of each block takes the lock, __syncthreads, a worker (warp 1) touches x,
    # __syncthreads, thread 0 unlocks; B's CAS recorded before X's unlock. The workers hold
    # no RMW -- the brief's thread-pair rule would miss them (design/a2_flag.md section 2)
    full = 0xffffffff
    ev = [(_A, 0, _CAS), (_A, 0, _BAR, full), (_A, 1, _BAR, full), (_A, 1, _STX),
          (_A, 0, _BAR, full), (_A, 1, _BAR, full), (_B, 0, _CAS), (_A, 0, _EXCH),
          (_B, 0, _BAR, full), (_B, 1, _BAR, full), (_B, 1, _LDX),
          (_B, 0, _BAR, full), (_B, 1, _BAR, full), (_B, 0, _EXCH)]
    assert _a2_flags(tmp_path, ev, block_tc=64) == {(_STX, _LDX): [1, 1]}
    ev[6], ev[7] = ev[7], ev[6]             # the unlock recorded first: ordered, no report
    assert _a2_flags(tmp_path, ev, block_tc=64) == {}


def _a2_reference(thr, order):
    """Brute force: {(record, record)} ordered by ->hb for SOME window-consistent coherence
    order (every permutation of each location's RMWs that puts r before q whenever r's window
    closed before q was recorded); records as (tid, pc, epoch), which fixes their HB relation
    to other threads. Trusting gate, no barriers."""
    import itertools
    from collections import defaultdict
    n = len(order)
    tid = [hb_oracle.tid_of(*thr[i], 0) for i, _ in order]
    scope = {pc: sd.atomic_scope(op) for pc, (op, _, _) in _A2_OPS.items()}
    ep, cur = [], defaultdict(lambda: 1)
    for k, (_, pc) in enumerate(order):
        ep.append(cur[tid[k]])
        cur[tid[k]] += scope[pc] is not None
    nxt = [next((j for j in range(k + 1, n) if tid[j] == tid[k]), n + 1) for k in range(n)]
    locs = defaultdict(list)
    for k, (_, pc) in enumerate(order):
        if scope[pc] is not None:
            locs[_A2_OPS[pc][1]].append(k)

    def ms(a, b):
        s = min(scope[order[a][1]], scope[order[b][1]])
        return s == sd.GRID or (s == sd.BLOCK and thr[order[a][0]][0] == thr[order[b][0]][0])
    cos = [[p for p in itertools.permutations(ks)
            if not any(nxt[p[j]] <= p[i] for i in range(len(p)) for j in range(i + 1, len(p)))]
           for ks in locs.values()]
    ordered = set()
    for combo in itertools.product(*cos):
        succ = defaultdict(set)
        for k in range(n):
            if nxt[k] < n:
                succ[k].add(nxt[k])
        for co in combo:
            for a, b in zip(co, co[1:]):
                if ms(a, b):
                    succ[a].add(b)
        for s in range(n):
            seen, st = set(), [s]
            while st:
                for y in succ[st.pop()] - seen:
                    seen.add(y)
                    st.append(y)
            ordered |= {((tid[s], order[s][1], ep[s]), (tid[y], order[y][1], ep[y])) for y in seen}
    return ordered


def test_a2_only_over_flags_randomized(tmp_path):
    # 400 random traces (2-4 threads in 1-2 blocks; grid, block and none-scope RMWs on two
    # words; plain accesses to the words and to data, strong ones to data): no reported
    # instance (DR or SC) that some window-consistent coherence order orders is left
    # unflagged (design/a2_flag.md, "Only over-flags"); the oracle's per-record counts add up
    # to its aggregated ones
    import random
    rng = random.Random(14)
    unflagged = flagged = over = sc = 0
    for _ in range(400):
        while True:                         # at most 6 RMWs per word: 720 orders to enumerate
            thr = [(rng.choice((0, 1)), w) for w in range(rng.choice((2, 3, 3, 4)))]
            left = [[rng.choice(list(_A2_OPS)) for _ in range(rng.randint(2, 5))] for _ in thr]
            per = [_A2_OPS[pc][1] for p in left for pc in p if sd.atomic_scope(_A2_OPS[pc][0]) is not None]
            if max((per.count(x) for x in per), default=0) <= 6:
                break
        order = []
        while any(left):
            i = rng.choice([k for k in range(len(thr)) if left[k]])
            order.append((i, left[i].pop(0)))
        d, t = _a2_dump(tmp_path, [(*thr[i], pc) for i, pc in order])
        rep = hb_oracle.analyze(str(d), str(t), records=True)
        races = rep["races"]
        sc += sum(r["count"] for r in races if r["class"] == "SC")
        assert sum(r["count"] for r in races) == sum(x[-1] for x in rep["a2_records"])
        assert sum(r["a2_uncertain"] for r in races) == \
            sum(x[-1] for x in rep["a2_records"] if x[-2])
        ref = _a2_reference(thr, order)
        for a_t, a_pc, a_ep, b_t, b_pc, b_ep, flag, cnt in rep["a2_records"]:
            a, b = (a_t, a_pc, a_ep), (b_t, b_pc, b_ep)
            some = (a, b) in ref or (b, a) in ref
            assert flag or not some, (thr, order, a, b)
            unflagged += cnt * (not flag)
            flagged += cnt * flag
            over += cnt * (flag and not some)
    assert unflagged and flagged and sc and over < flagged   # all kinds occur; not all over-flags


@pytest.fixture(scope="module")
def a2lock(tmp_path_factory):
    """(dots, {"kcontend": trace, "kcontrol": trace}) of one run of lock_contention_a2.cu."""
    dots, last = _trace(tmp_path_factory, "lock_contention_a2")
    ks = {}
    for tr in sorted(Path(last).parent.glob("kernel_*.json")):
        ks[_load(tr)["kernel"]["kernel_name"].split("(")[0]] = tr
    assert set(ks) == {"kcontend", "kcontrol"}, ks
    return dots, ks


def _a2_verdicts(dots, trace):
    for dot in dots:
        try:
            return sd.analyze(dot, trace)["verdicts"]
        except sd.AlignmentError:
            continue
    raise AssertionError("no CFG aligns with the trace")


def test_lock_contention_hb_clock_matches_specification(a2lock):
    dots, ks = a2lock
    assert all(_hb_clock_equals_specification(dots, tr) for tr in ks.values())


def test_lock_contention_every_dr_is_a2_uncertain(a2lock):
    # step 5 of T14: on the race-free lock with 16 contending warps every report the trace
    # shows is an A2 inversion -- the flagged count > 0, no unflagged instance, and every Race
    # verdict rests on A2 alone (pair-level a2_uncertain True). Plain data: the pairs are DR.
    dots, ks = a2lock
    t = _load(ks["kcontend"])
    assert t.get("hb_a2") == 1
    races = t.get("hb_races", [])
    assert all(r["class"] == "DR" for r in races)
    assert sum(r["a2_uncertain"] for r in races) > 0, "no inversion recorded in this run"
    assert sum(r["count"] - r["a2_uncertain"] for r in races) == 0
    vs = [v for v in _a2_verdicts(dots, ks["kcontend"]) if v["verdict"] == "RACE"]
    assert vs and all(v["matrix_class"] == "structural" and v["a2_uncertain"] is True for v in vs)


def test_lock_control_race_is_not_a2_uncertain(a2lock):
    # a race of every coherence order (a write after the writer's own unlock, read by the next
    # holder) with every window on the lock closed before the reader's CAS: reported, and not
    # flagged -- the flag does not blanket every report of a lock program
    dots, ks = a2lock
    t = _load(ks["kcontrol"])
    ev = _mem(t)
    b0, b1 = [e for e in ev if e["block"] == 0], [e for e in ev if e["block"] == 1]
    if not b0 or not b1 or b0[-1]["seq"] > b1[0]["seq"]:
        pytest.skip("schedule not reached: block 0 did not finish before block 1 started")
    races = t.get("hb_races", [])
    assert races and all(r["class"] == "DR" and r["a2_uncertain"] == 0 for r in races)
    vs = [v for v in _a2_verdicts(dots, ks["kcontrol"]) if v["verdict"] == "RACE"]
    assert vs and all(v["a2_uncertain"] is False for v in vs)

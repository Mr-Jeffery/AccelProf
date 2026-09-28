"""Three substitutions of design/proof/hb_proof.tex section 7 on real kernels -- pinned as strict
xfails by T6 (c), fixed by T9 -- plus T9's D12 case. Each kernel is built and traced here
(getall.sh, vector-clock mode); pairs are asserted by role, not by pc offset; the scalar-clock
verdict is the same dump without the engine's keys (what YOSEMITE_HB_MODE=scalar-clock
writes). Every case also asserts engine == hb_oracle == design/algorithms_check.py's
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

Part of the green set (CLAUDE.md A4) since T9; needs a GPU node.
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


def _engine_equals_oracle(dots, trace):
    """engine == oracle (records with class, and the second clock), and the oracle ==
    Detect(T, vec) with the I1/I2 switches off (record pairs with DR/SC)."""
    key = lambda r: (r.get("a_pc"), r["b_pc"], r["kind"], r.get("class"), r["space"], r.get("dist"),
                     r.get("async"), r.get("count"))
    t = _load(trace)
    dot, _, _ = ac.tables(dots, t)
    rep = hb_oracle.analyze(dot, trace, records=True)
    oracle = {key(r) for r in rep["races"]}
    ref = set(ac.reference(dots, trace))
    return {key(r) for r in t.get("hb_races", [])} == oracle \
        and t.get("hb_races_sync_only") == rep["races_sync_only"] \
        and {tuple(r) for r in rep["race_records"]} == ref


def _scalar_clock(trace, tmp_path):
    """The dump as scalar-clock mode writes it: no engine keys."""
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


def test_write_after_unlock_engine_matches_oracle(i1):
    assert _engine_equals_oracle(*i1[:2])


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


def test_bucket_kernel_engine_matches_oracle(i2):
    assert _engine_equals_oracle(*i2[:2])


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
    # local record and the engine reports no local race
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


def test_strong_store_strong_load_engine_matches_oracle(d12):
    assert _engine_equals_oracle(*d12[:2])


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

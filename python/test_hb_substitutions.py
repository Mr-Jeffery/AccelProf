"""T6 (c): three substitutions of design/proof/hb_proof.tex section 7 on real kernels, as strict
xfails that the fixes flip (T9). Each kernel is built and traced here (getall.sh,
vector-clock mode); pairs are asserted by role, not by pc offset. Every xfail has a passing
control: design/algorithms_check.py's Detect(T, vec) with the switches off (the proof's
reference) reports the pair on the same trace, so the kernel exercises the case.

  I1  python/testdata/write_after_unlock_other_schedule.cu -- the ScoR rtraw lock pattern
      with block 0 first: block 0's write after its unlock races block 1's read under the
      lock. Tick-before-publish hides it (Proposition "Missed class of I1").
  I2  python/testdata/strong_stores_barrier_weak_load.cu -- Remark "Why one bucket per key":
      two unordered strong stores, a barrier, a weak load; one last write per location hides
      the first store from the load, in both clocks.
  I5  python/testdata/local_mem_blocks.cu -- thread-private local arrays. The collector's
      thread-id fold of a local address is lost to a 32-bit shift, so every thread's access
      at one offset is one location; the verdict layer drops them (the dependency side
      records no local pcs), the race records remain.

Not part of the green set; needs a GPU node.
    .env/bin/python -m pytest python/test_hb_substitutions.py -rxX
"""
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
    key = lambda r: (r["addr"], r["a_tid"], r.get("a_pc"), r["b_tid"], r["b_pc"], r["kind"])
    dot, _, _ = ac.tables(dots, _load(trace))
    oracle = {key(r) for r in hb_oracle.analyze(dot, trace)["races"]}
    return {key(r) for r in _load(trace).get("hb_races", [])} == oracle


# --- I1: write after unlock, block 0 first ---------------------------------------------

@pytest.fixture(scope="module")
def i1(tmp_path_factory):
    dots, trace = _trace(tmp_path_factory, "write_after_unlock_other_schedule")
    t = _load(trace)
    _, atom, _ = ac.tables(dots, t)
    ev = _mem(t)
    b0, b1 = [e for e in ev if e["block"] == 0], [e for e in ev if e["block"] == 1]
    if not b0 or not b1 or b0[-1]["seq"] > b1[0]["seq"]:
        pytest.skip("schedule not reached: block 0 did not finish before block 1 started")
    unlock = [e for e in b0 if e["pc"] in atom][-1]
    write = next(e for e in b0 if e["seq"] > unlock["seq"] and e["pc"] not in atom)
    addr = write["lanes"][0]["addr"]
    read = next(e for e in b1 if e["type"] == "read" and e["lanes"][0]["addr"] == addr)
    return dots, trace, write, read


def test_write_after_unlock_reference_reports_it(i1):
    dots, trace, write, read = i1
    ref = {(r[2], r[1] >> 10, r[4], r[3] >> 10, r[5]) for r in ac.reference(dots, trace)}
    assert ref == {(write["pc"], 0, read["pc"], 1, "DR")}


def test_write_after_unlock_engine_matches_oracle(i1):
    assert _engine_equals_oracle(*i1[:2])


@pytest.mark.xfail(strict=True, reason="I1: tick before publish hides the releaser's "
                   "post-release write (hb_proof.tex section 7); T9 publishes then ticks")
def test_write_after_unlock_other_schedule(i1):
    dots, trace, write, read = i1
    assert any(r["a_pc"] == write["pc"] and r["b_pc"] == read["pc"] and r["kind"] == "RAW"
               for r in _load(trace).get("hb_races", []))
    [v] = _verdict(dots, trace, (write["pc"], read["pc"]))
    assert v["verdict"] == "RACE" and v["hb_class"] == "structural"


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


@pytest.mark.xfail(strict=True, reason="I2: one last write per location; the barrier-ordered "
                   "second store hides the first (Remark 'Why one bucket per key'); T9 buckets")
def test_strong_stores_barrier_weak_load(i2):
    dots, trace, a, b, c = i2
    assert any({r["a_pc"], r["b_pc"]} == {a["pc"], c["pc"]}
               for r in _load(trace).get("hb_races", []))


# --- I5: local memory ---------------------------------------------------------------------

@pytest.fixture(scope="module")
def i5(tmp_path_factory):
    dots, trace = _trace(tmp_path_factory, "local_mem_blocks")
    t = _load(trace)
    loc = [e for e in _mem(t) if e["space"] == "local"]
    if not loc:
        pytest.skip("no local-memory accesses traced (the array was not placed in local memory)")
    return dots, trace, t, loc


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


@pytest.mark.xfail(strict=True, reason="I5: local addresses carry no thread id (the "
                   "collector's (flat tid << 54) fold is a 32-bit shift) and are keyed "
                   "(local, addr); T9 keys local memory per thread")
def test_local_memory_is_thread_private(i5):
    _, _, t, _ = i5
    assert not [r for r in t.get("hb_races", []) if r["space"] == "local"]

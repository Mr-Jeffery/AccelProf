"""Exit-aware barrier instance assembly (T3b; T3's eval/CRS_CUDA_TRIAGE.md; hb_proof.tex
Definition "Instances", Algorithm 1's Complete, the fifth monitor check).

A thread that has exited no longer takes part in a CTA barrier: a plain __syncthreads()
completes when the block's non-exited threads have arrived. The collector's per-warp exit
records (`type: "exit"`, the exiting lanes in `active_mask`; dump marker `hb_exits: 1`) take
the exited threads out of the expected count of every later whole-block segment of their
block and re-check its open segments (Complete on exit); a counted barrier keeps its n.
HbEngine, hb_oracle.py, sync_dominance.barrier_only_pairs and design/algorithms_check.py
implement it identically.

Two parts:
  * synthetic dumps (no GPU): the model's cases one by one, with the TV checks
    (TV-record-after-exit, TV-barrier-completion-order on an exit, TV-barrier-pending-at-end)
    and a dump without exit records that keeps the pre-T3b reading;
  * real kernels (GPU node): python/testdata/barrier_exited_threads.cu -- the HeCBench
    crs-cuda idiom, threads 125..127 of each 128-thread block return before the loop's
    __syncthreads() -- and the positive control python/testdata/barrier_exit_after.cu, where
    threads exit AFTER a barrier they took part in.

    .env/bin/python -m pytest python/test_barrier_exit.py -rxXs
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

_TESTDATA = _ROOT / "python" / "testdata"
_DOT = _TESTDATA / "norace_interwarp_barrier_raw.sm_86.dot"
_KERNEL = "_Z5kmainPj"
_FULL = 0xFFFFFFFF
_LOW29 = (1 << 29) - 1          # lanes 0..28
_TOP3 = _FULL & ~_LOW29         # lanes 29..31


# --------------------------------------------------------------------------- #
# Synthetic dumps: 64 threads per block (warps 0 and 1), plain __syncthreads   #
# --------------------------------------------------------------------------- #
def _mem(seq, warp, pc, typ, mask=_FULL, addr=lambda k: 4 * k):
    return {"seq": seq, "block": 0, "warp": warp, "pc": pc, "type": typ, "space": "shared",
            "size": 4, "active_mask": mask,
            "lanes": [{"lane": k, "addr": addr(k)} for k in range(32) if (mask >> k) & 1]}


def _bar(seq, warp, mask=_FULL, count=0, bar=0):
    return {"seq": seq, "block": 0, "warp": warp, "pc": 0x60, "type": "barrier",
            "thread_count": count, "bar_index": bar, "active_mask": mask}


def _exit(seq, warp, mask):
    return {"seq": seq, "block": 0, "warp": warp, "pc": 0x90, "type": "exit",
            "active_mask": mask}


def _dump(tmp_path, events, exits_marker=True, name="trace.json"):
    t = {"kernel": {"kernel_name": _KERNEL, "block_thread_count": 64}, "hb_events": events}
    if exits_marker:
        t["hb_exits"] = 1
    p = tmp_path / name
    p.write_text(json.dumps(t))
    return p


def _all_three(path):
    """(oracle races, oracle sync pairs, offline sync pairs, offline tv) of one dump; the
    simulator's Detect (I1/I2 off since T9) must give the oracle's race records on it."""
    rep = hb_oracle.analyze(_DOT, path, records=True)
    trace = json.loads(Path(path).read_text())
    tv = []
    off = sd.barrier_only_pairs(trace, {}, {}, tv_out=tv)
    sim = ac.detect(trace["hb_events"], 64, {}, {})      # since T9: the switches off
    assert {tuple(r) for r in rep["race_records"]} == set(sim)
    osync = {(a, b): n for a, b, n in rep["races_sync_only"]}
    assert osync == off, "offline barrier-only pass != the oracle's second clock"
    return rep["races"], osync, tv


def test_exit_before_the_barrier_lowers_the_count(tmp_path):
    # warp 1's lanes 29..31 return first; the barrier completes with the 61 that remain
    ev = [_exit(0, 1, _TOP3), _mem(1, 0, 0x50, "write"), _bar(2, 0), _bar(3, 1, _LOW29),
          _mem(4, 1, 0x80, "read", _LOW29)]
    races, sync, tv = _all_three(_dump(tmp_path, ev))
    assert races == [] and sync == {} and tv == []


def test_exit_completes_a_pending_instance(tmp_path):
    # the exit is recorded after every other thread arrived: it completes the instance
    ev = [_mem(0, 0, 0x50, "write"), _bar(1, 0), _bar(2, 1, _LOW29), _exit(3, 1, _TOP3),
          _mem(4, 1, 0x80, "read", _LOW29)]
    races, sync, tv = _all_three(_dump(tmp_path, ev))
    assert races == [] and sync == {} and tv == []


def test_thread_that_exits_after_the_barrier_took_part(tmp_path):
    # positive control: lanes 29..31 of warp 1 write, arrive, then exit; warp 0 reads their
    # slots after the barrier (ordered: they arrived); a second barrier completes with 61 and
    # orders those reads before warp 1's overwrites of the same slots
    ev = [_mem(0, 1, 0x50, "write"), _bar(1, 0), _bar(2, 1), _exit(3, 1, _TOP3),
          _mem(4, 0, 0x80, "read", addr=lambda k: 4 * (k | 29)),
          _bar(5, 0, bar=1), _bar(6, 1, _LOW29, bar=1),
          _mem(7, 1, 0x84, "write", 0x7, addr=lambda k: 4 * (29 + k))]
    races, sync, tv = _all_three(_dump(tmp_path, ev))
    assert races == [] and sync == {} and tv == []


def test_pre_exit_write_is_not_released_by_the_barrier(tmp_path):
    # soundness control: a thread that exits before a barrier never joins it, so its write
    # stays unordered against another warp's post-barrier read of the same location
    ev = [_mem(0, 1, 0x50, "write", _TOP3), _exit(1, 1, _TOP3), _bar(2, 0),
          _bar(3, 1, _LOW29), _mem(4, 0, 0x80, "read", addr=lambda k: 4 * (k | 29))]
    races, sync, tv = _all_three(_dump(tmp_path, ev))
    assert {r["kind"] for r in races} == {"RAW"}
    assert {(r["a_tid"] >> 5, r["b_tid"] >> 5) for r in races} == {(1, 0)}
    assert sync == {(0x50, 0x80): sum(r["count"] for r in races)} and tv == []


def test_counted_barrier_keeps_its_count(tmp_path):
    # bar.sync 1, 64: exits do not lower an explicit count, so 61 arrivals stay open
    ev = [_exit(0, 1, _TOP3), _bar(1, 0, count=64, bar=1), _bar(2, 1, _LOW29, count=64, bar=1)]
    with pytest.raises(sd.AlignmentError, match="TV-barrier-pending-at-end"):
        hb_oracle.analyze(_DOT, _dump(tmp_path, ev))
    tv = []
    sd.barrier_only_pairs(json.loads(_dump(tmp_path, ev).read_text()), {}, {}, tv_out=tv)
    assert len(tv) == 1 and tv[0].startswith("TV-barrier-pending-at-end")


def test_pending_at_end_only_with_the_marker(tmp_path):
    # a dump without exit records (pre-T3b collector) keeps the old reading: an early-exit
    # kernel's segments stay open there, so the end-of-kernel check does not run
    ev = [_mem(0, 0, 0x50, "write"), _bar(1, 0)]
    with pytest.raises(sd.AlignmentError, match="TV-barrier-pending-at-end"):
        hb_oracle.analyze(_DOT, _dump(tmp_path, ev))
    rep = hb_oracle.analyze(_DOT, _dump(tmp_path, ev, exits_marker=False, name="old.json"))
    assert rep["races"] == []
    tv = []
    old = json.loads((tmp_path / "old.json").read_text())
    assert sd.barrier_only_pairs(old, {}, {}, tv_out=tv) == {} and tv == []


def test_old_dump_without_exit_records_keeps_its_verdict(tmp_path, monkeypatch):
    # the crs-cuda shape without its exit record: the instance never completes (the pre-T3b
    # reading, strict oracle raises; replayed with the checks off it reports the pair)
    ev = [_mem(0, 0, 0x50, "write"), _bar(1, 0), _bar(2, 1, _LOW29),
          _mem(3, 1, 0x80, "read", _LOW29)]
    p = _dump(tmp_path, ev, exits_marker=False)
    with pytest.raises(sd.AlignmentError, match="TV-barrier-completion-order"):
        hb_oracle.analyze(_DOT, p)
    monkeypatch.setenv("YOSEMITE_HB_STRICT", "0")
    races, sync, tv = _all_three(p)
    assert sum(r["count"] for r in races) == 29 and sync == {(0x50, 0x80): 29} and tv == []


def test_tv_record_after_exit(tmp_path):
    ev = [_exit(0, 1, _TOP3), _mem(1, 1, 0x50, "write", _FULL)]
    with pytest.raises(sd.AlignmentError, match="TV-record-after-exit"):
        hb_oracle.analyze(_DOT, _dump(tmp_path, ev))
    ev = [_exit(0, 1, _TOP3), _bar(1, 1)]
    with pytest.raises(sd.AlignmentError, match="TV-record-after-exit"):
        hb_oracle.analyze(_DOT, _dump(tmp_path, ev, name="t2.json"))


def test_tv_exit_while_pending_at_a_barrier(tmp_path):
    # W2: a thread blocked at an open segment cannot exit before it completes
    ev = [_bar(0, 1), _exit(1, 1, _TOP3)]
    with pytest.raises(sd.AlignmentError, match="TV-barrier-completion-order"):
        hb_oracle.analyze(_DOT, _dump(tmp_path, ev))


# --------------------------------------------------------------------------- #
# Real kernels (GPU node): the crs-cuda reproducer and the positive control    #
# --------------------------------------------------------------------------- #
def _build_and_trace(tmp_path_factory, name):
    """(dots, kernel JSON) of one vector-clock run of testdata/<name>.cu."""
    if shutil.which("nvcc") is None:
        pytest.skip("no nvcc (run on a GPU node)")
    d = tmp_path_factory.mktemp(name)
    binary = d / name
    b = subprocess.run(["nvcc", "-arch=native", "-lineinfo", "--cudart", "shared",
                        str(_TESTDATA / f"{name}.cu"), "-o", str(binary)], capture_output=True)
    if b.returncode != 0:
        pytest.skip(f"build failed: {b.stderr.decode()[-300:]}")
    subprocess.run(["bash", str(_ROOT / "getall.sh"), str(binary)], cwd=_ROOT,
                   capture_output=True, timeout=600)
    dots = sorted((d / f"{name}_extracted_cubins").glob("*.dot"))
    traces = sorted(d.glob(f"dependency_{name}*/kernel_*.json"))
    if not dots or not traces:
        pytest.skip("no trace produced (GPU / collector unavailable)")
    tj = json.loads(traces[-1].read_text())
    if not tj.get("hb_exits"):
        pytest.skip("the traced runtime predates T3b (no hb_exits marker, no exit records)")
    return dots, traces[-1]


@pytest.fixture(scope="module")
def artifacts(tmp_path_factory):
    return _build_and_trace(tmp_path_factory, "barrier_exited_threads")


@pytest.fixture(scope="module")
def control(tmp_path_factory):
    return _build_and_trace(tmp_path_factory, "barrier_exit_after")


def _load(trace):
    return json.loads(Path(trace).read_text())


def _first(fn, dots, trace):
    for dot in dots:
        try:
            return fn(dot, trace)
        except sd.AlignmentError as e:
            if str(e).startswith("TV-"):
                raise
            continue
    raise AssertionError("no CFG aligns with the trace")


def _key(r):   # hb_races is aggregated (T9): addr and tids name one example instance
    return (r.get("a_pc"), r["b_pc"], r["kind"], r.get("class"), r["space"], r.get("dist"),
            r.get("async"), r.get("count"))


def _threads(t, pred):
    seen = {}
    for e in t["hb_events"]:
        if not pred(e):
            continue
        lanes = [ln["lane"] for ln in e["lanes"]] if "lanes" in e else \
            [k for k in range(32) if (e.get("active_mask", 0) >> k) & 1]
        seen.setdefault(e["block"], set()).update((e["warp"] << 5) | ln for ln in lanes)
    return seen


def test_threads_really_exit_before_the_barrier(artifacts):
    # guard: 3 of 128 threads per block never reach a barrier or an access, and every
    # thread of the block has exactly one exit record
    t = _load(artifacts[1])
    assert t["kernel"]["block_thread_count"] == 128 and t["hb_exits"] == 1
    active = _threads(t, lambda e: e["type"] != "exit")
    assert all(len(s) == 125 for s in active.values()), {b: len(s) for b, s in active.items()}
    exits = _threads(t, lambda e: e["type"] == "exit")
    assert all(len(exits[b]) == 128 for b in active), {b: len(s) for b, s in exits.items()}


def test_engine_reports_no_race(artifacts):
    assert _load(artifacts[1]).get("hb_races") == []


def test_no_trace_validity_violation(artifacts):
    # includes TV-barrier-pending-at-end, which the engine records whatever the strict flag
    assert _load(artifacts[1]).get("tv_violation") is None


def test_vector_clock_verdict_is_clean(artifacts):
    rep = _first(sd.analyze, *artifacts)
    assert rep["summary"]["races"] == 0 and rep["diagnostics"]["tv_violation"] is None


def test_scalar_clock_verdict_is_clean(artifacts, tmp_path):
    # the same dump read as scalar-clock mode reads it: the offline barrier pass runs, with
    # its end-of-kernel check
    dots, trace = artifacts
    t = _load(trace)
    for k in ("hb_races", "hb_races_sync_only", "tv_violation"):
        t.pop(k, None)
    sc = tmp_path / "kernel_sc.json"
    sc.write_text(json.dumps(t))
    rep = _first(sd.analyze, dots, sc)
    assert rep["summary"]["races"] == 0 and rep["diagnostics"]["tv_violation"] is None


def test_oracle_accepts_the_trace(artifacts):
    assert _first(hb_oracle.analyze, *artifacts)["races"] == []


def test_oracle_agrees_with_the_engine(artifacts):
    dots, trace = artifacts
    t = _load(trace)
    rep = _first(hb_oracle.analyze, dots, trace)
    assert {_key(r) for r in t["hb_races"]} == {_key(r) for r in rep["races"]}
    assert t["hb_races_sync_only"] == rep["races_sync_only"]


def test_offline_pass_matches_the_engine(artifacts):
    t = _load(artifacts[1])
    tv = []
    assert sd.barrier_only_pairs(t, {}, {}, tv_out=tv) == \
        {(a, b): n for a, b, n in t["hb_races_sync_only"]} and tv == []


def test_without_exit_records_the_old_reading_returns(artifacts, tmp_path, monkeypatch):
    # the kernel exercises the fix: drop the exit records and the marker (what a pre-T3b
    # collector dumped) and the replay reports the store -> barrier -> load pairs again
    dots, trace = artifacts
    t = _load(trace)
    t["hb_events"] = [e for e in t["hb_events"] if e["type"] != "exit"]
    t.pop("hb_exits")
    old = tmp_path / "kernel_old.json"
    old.write_text(json.dumps(t))
    monkeypatch.setenv("YOSEMITE_HB_STRICT", "0")
    assert _first(hb_oracle.analyze, dots, old)["races"] != []


def test_control_exits_after_the_first_barrier(control):
    # guard: threads 60..63 of each block exit after arriving at the first barrier
    t = _load(control[1])
    ev = sorted(t["hb_events"], key=lambda e: e["seq"])
    for blk in {e["block"] for e in ev}:
        arr1 = [e["seq"] for e in ev if e["block"] == blk and e["type"] == "barrier"
                and e["warp"] == 1 and (e["active_mask"] >> 28) & 0xF == 0xF]
        ex = [e["seq"] for e in ev if e["block"] == blk and e["type"] == "exit"
              and e["warp"] == 1 and (e["active_mask"] >> 28) & 0xF == 0xF]
        assert arr1 and ex and arr1[0] < ex[0], (blk, arr1, ex)


def test_control_is_clean(control):
    dots, trace = control
    t = _load(trace)
    assert t.get("hb_races") == [] and t.get("tv_violation") is None
    rep = _first(hb_oracle.analyze, dots, trace)
    assert rep["races"] == [] and t["hb_races_sync_only"] == rep["races_sync_only"]
    assert _first(sd.analyze, dots, trace)["summary"]["races"] == 0


def test_control_needs_the_exit_records(control, tmp_path, monkeypatch):
    # without them the second barrier never completes: the reads and the overwrites race
    dots, trace = control
    t = _load(trace)
    t["hb_events"] = [e for e in t["hb_events"] if e["type"] != "exit"]
    t.pop("hb_exits")
    old = tmp_path / "kernel_old.json"
    old.write_text(json.dumps(t))
    monkeypatch.setenv("YOSEMITE_HB_STRICT", "0")
    assert _first(hb_oracle.analyze, dots, old)["races"] != []

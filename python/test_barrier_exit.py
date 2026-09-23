"""T3 (eval/CRS_CUDA_TRIAGE.md): threads that exit before a __syncthreads() -- the HeCBench
crs-cuda idiom, reduced to python/testdata/barrier_exited_threads.cu (128 threads per block,
threads 125..127 return first). The barrier completes for the threads that remain, so the
program is race-free. The engine and hb_oracle.py assemble a plain __syncthreads() instance
until block_thread_count threads have arrived; exited threads never arrive, the instance never
fires, the engine records TV-barrier-completion-order when a released warp runs on, and every
store -> barrier -> load pair is reported as a race. The xfail(strict) cases flip when the
barrier model accounts for exited threads (the proposal in the triage report). Not part of
the green set; needs a GPU node.

    .env/bin/python -m pytest python/test_barrier_exit.py -rxX
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

import hb_oracle
import sync_dominance as sd

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "python" / "testdata" / "barrier_exited_threads.cu"


@pytest.fixture(scope="module")
def artifacts(tmp_path_factory):
    """(dots, kernel JSON) of one vector-clock run, built and traced in a temp dir."""
    if shutil.which("nvcc") is None:
        pytest.skip("no nvcc (run on a GPU node)")
    d = tmp_path_factory.mktemp("barrier_exit")
    binary = d / "barrier_exited_threads"
    b = subprocess.run(["nvcc", "-arch=native", "-lineinfo", "--cudart", "shared",
                        str(_SRC), "-o", str(binary)], capture_output=True)
    if b.returncode != 0:
        pytest.skip(f"build failed: {b.stderr.decode()[-300:]}")
    subprocess.run(["bash", str(_ROOT / "getall.sh"), str(binary)], cwd=_ROOT,
                   capture_output=True, timeout=600)
    dots = sorted((d / "barrier_exited_threads_extracted_cubins").glob("*.dot"))
    traces = sorted(d.glob("dependency_barrier_exited_threads*/kernel_*.json"))
    if not dots or not traces:
        pytest.skip("no trace produced (GPU / collector unavailable)")
    return dots, traces[-1]


def _analyze(dots, trace):
    for dot in dots:
        try:
            return sd.analyze(dot, trace)
        except sd.AlignmentError:
            continue
    raise AssertionError("no CFG aligns with the trace")


def test_threads_really_exit_before_the_barrier(artifacts):
    # guard: 3 of 128 threads per block never reach a barrier or an access
    _, trace = artifacts
    t = json.loads(Path(trace).read_text())
    assert t["kernel"]["block_thread_count"] == 128
    seen = {}
    for e in t["hb_events"]:
        lanes = [ln["lane"] for ln in e.get("lanes", ())] if "lanes" in e else \
            [k for k in range(32) if (e.get("active_mask", 0) >> k) & 1]
        seen.setdefault(e["block"], set()).update((e["warp"] << 5) | ln for ln in lanes)
    assert all(len(s) == 125 for s in seen.values()), {b: len(s) for b, s in seen.items()}


@pytest.mark.xfail(strict=True, reason="T3: barrier instance waits for block_thread_count "
                   "arrivals; exited threads never arrive (CRS_CUDA_TRIAGE.md)")
def test_engine_reports_no_race(artifacts):
    _, trace = artifacts
    assert json.loads(Path(trace).read_text()).get("hb_races") == []


@pytest.mark.xfail(strict=True, reason="T3: TV-barrier-completion-order fires when the "
                   "hardware releases a barrier the model still holds open")
def test_no_trace_validity_violation(artifacts):
    _, trace = artifacts
    assert json.loads(Path(trace).read_text()).get("tv_violation") is None


@pytest.mark.xfail(strict=True, reason="T3: vector-clock verdict carries the engine's races")
def test_vector_clock_verdict_is_clean(artifacts):
    dots, trace = artifacts
    assert _analyze(dots, trace)["summary"]["races"] == 0


def test_scalar_clock_verdict_is_clean(artifacts, tmp_path):
    # the static leg proves store -> __syncthreads -> load by dominance, so the pairs the
    # (equally affected) offline barrier pass leaves unordered are ORDERED anyway
    dots, trace = artifacts
    t = json.loads(Path(trace).read_text())
    for k in ("hb_races", "hb_races_sync_only", "tv_violation"):
        t.pop(k, None)
    sc = tmp_path / "kernel_sc.json"
    sc.write_text(json.dumps(t))
    assert _analyze(dots, sc)["summary"]["races"] == 0


def _oracle(dots, trace):
    for dot in dots:
        try:
            return hb_oracle.analyze(dot, trace)
        except sd.AlignmentError as e:
            if str(e).startswith("TV-"):
                raise
            continue
    raise AssertionError("no CFG aligns with the trace")


@pytest.mark.xfail(strict=True, raises=sd.AlignmentError,
                   reason="T3: the oracle's TV-barrier-completion-order check raises on it")
def test_oracle_accepts_the_trace(artifacts):
    _oracle(*artifacts)


def test_oracle_agrees_with_the_engine(artifacts, monkeypatch):
    # engine == oracle holds here too: both model the barrier the same (wrong) way. With the
    # TV checks off (YOSEMITE_HB_STRICT=0) the oracle replays the trace like the engine does.
    monkeypatch.setenv("YOSEMITE_HB_STRICT", "0")
    dots, trace = artifacts
    key = lambda r: (r["addr"], r["a_tid"], r.get("a_pc"), r["b_tid"], r["b_pc"], r["kind"])
    engine = {key(r) for r in json.loads(Path(trace).read_text()).get("hb_races", [])}
    oracle = {key(r) for r in _oracle(dots, trace)["races"]}
    assert engine == oracle

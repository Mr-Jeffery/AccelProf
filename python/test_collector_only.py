"""C1: collector-only mode (YOSEMITE_HB_TRACE unset). No HbClock is constructed and the kernel JSON
carries the PCDepGraph (nodes, edges) and no hb_* key, so sync_dominance.analyze() takes the static
leg alone: R1 dominance, R3's PC-level chain, R2's coherence class. A conflicting pair no certificate
orders is a RACE (an SC when its class is strong), and nothing the sync pass would have supplied
(hb_sync_pass, hb_rmw_points, hb_races, event candidates) is read as "ordered".

testdata/collector_only.cu is recorded once in collector-only mode and once in scalar-clock mode:
  co_straight   write / __syncthreads / cross-warp read   -> ORDERED by dominance in both modes
  co_loop_red   barrier inside the loop, the pairs loop-carried around it
                                                          -> RACE in collector-only mode; scalar-clock's
                                                             barrier-only pass orders it
  co_loop_tile  write / barrier / read / barrier in a loop -> ORDERED by dominance in both modes
  co_missing    no barrier                                -> RACE in both modes

Needs a GPU node and nvcc (skips elsewhere):
    .env/bin/python -m pytest python/test_collector_only.py -rxX
"""
import glob
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import sync_dominance as sd

_SRC = Path(__file__).resolve().parent / "testdata" / "collector_only.cu"
_APH = os.environ.get("ACCEL_PROF_HOME") or "/home/fzheng4/AccelProf"
_MODES = ("collector-only", "scalar-clock")


def _record(binary, d, mode):
    """One accelprof run of the binary in its own directory -> (dots, {kernel: trace path})."""
    run = d / mode
    run.mkdir()
    exe = run / "co"
    shutil.copy2(binary, exe)
    ext = run / "co_extracted_cubins"
    ext.mkdir()
    subprocess.run(["cuobjdump", "-xelf", "all", str(exe)], cwd=ext, capture_output=True, check=True)
    for c in ext.glob("*.cubin"):
        dot = subprocess.run(["nvdisasm", "-bbcfg", "-poff", c.name], cwd=ext, capture_output=True,
                             check=True).stdout
        (ext / (c.stem + ".dot")).write_bytes(dot)
    py = Path(_APH) / ".env" / "bin" / "python"
    subprocess.run([str(py), str(Path(_APH) / "python" / "atomic_scope_sidecar.py"),
                    *[x.name for x in ext.glob("*.dot")], "-o", "atomic_scope.txt"],
                   cwd=ext, capture_output=True, check=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("YOSEMITE_", "CUVEIN_"))}
    env.update(ACCEL_PROF_HOME=_APH, YOSEMITE_ATOMIC_SCOPE_FILE=str(ext / "atomic_scope.txt"),
               PATH=f"{_APH}/bin:" + os.environ["PATH"])
    if mode == "scalar-clock":
        env.update(YOSEMITE_HB_TRACE="1", YOSEMITE_HB_MODE="scalar-clock")
    subprocess.run(["accelprof", "-t", "pc_dependency_analysis", "-n", "1", "./co"], cwd=run, env=env,
                   capture_output=True, timeout=600)
    traces = sorted(glob.glob(str(run / "dependency_co*" / "kernel_*.json")))
    dots = sorted(ext.glob("*.dot"))
    if not dots or not traces:
        pytest.skip("no trace produced (GPU / collector unavailable)")
    by_name = {}
    for t in traces:
        by_name[json.loads(Path(t).read_text())["kernel"]["kernel_name"].split("(")[0]] = t
    return dots, by_name


@pytest.fixture(scope="module")
def rec(tmp_path_factory):
    if shutil.which("nvcc") is None or not (Path(_APH) / "lib" / "libcompute_sanitizer.so").exists():
        pytest.skip("no nvcc or no installed collector (run on a GPU node)")
    d = tmp_path_factory.mktemp("collector_only")
    b = subprocess.run(["nvcc", "-arch=native", "-lineinfo", "--cudart", "shared", str(_SRC),
                        "-o", str(d / "co")], capture_output=True)
    if b.returncode != 0:
        pytest.skip(f"build failed: {b.stderr.decode()[-300:]}")
    return {m: _record(d / "co", d, m) for m in _MODES}


def _report(rec, mode, kernel):
    dots, traces = rec[mode]
    for dot in dots:
        try:
            return sd.analyze(dot, traces[kernel])
        except sd.AlignmentError:
            continue
    raise AssertionError("no CFG aligns with the trace")


def _verdicts(rec, mode, kernel):
    return [v["verdict"] for v in _report(rec, mode, kernel)["verdicts"]]


def test_collector_only_json_has_the_graph_and_no_hb_keys(rec):
    _, traces = rec["collector-only"]
    for kernel, path in traces.items():
        t = json.loads(Path(path).read_text())
        assert t["nodes"] and "edges" in t, kernel
        assert [k for k in t if k.startswith("hb_")] == [], kernel
        assert "tv_violation" not in t or t["tv_violation"] is None
    _, traces = rec["scalar-clock"]
    assert any(k.startswith("hb_") for k in json.loads(Path(next(iter(traces.values()))).read_text()))


def test_barrier_dominance_orders_in_collector_only(rec):
    assert set(_verdicts(rec, "collector-only", "co_straight")) == {"ORDERED"}
    assert set(_verdicts(rec, "scalar-clock", "co_straight")) == {"ORDERED"}


def test_two_barrier_tile_loop_is_ordered_by_dominance(rec):
    assert set(_verdicts(rec, "collector-only", "co_loop_tile")) == {"ORDERED"}
    assert set(_verdicts(rec, "scalar-clock", "co_loop_tile")) == {"ORDERED"}


def test_loop_carried_pair_races_in_collector_only_and_scalar_clock_orders_it(rec):
    co = _report(rec, "collector-only", "co_loop_red")
    assert co["summary"]["races"] >= 1
    assert all(v["hb_class"] is None for v in co["verdicts"])        # no class: no HB evidence read
    sc = _report(rec, "scalar-clock", "co_loop_red")
    assert sc["summary"]["races"] == 0
    assert any(v["hb_class"] == "barrier-ordered" for v in sc["verdicts"])


def test_missing_barrier_races_in_both_modes(rec):
    for mode in _MODES:
        assert "RACE" in _verdicts(rec, mode, "co_missing"), mode

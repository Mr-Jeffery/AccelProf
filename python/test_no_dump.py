"""T4 (design/no_dump.md): no-dump mode -- both clocks during the run, aggregates only.

Two kernels of the green set are recorded four ways each with the worktree's runtime
(getall.sh: vector-clock / scalar-clock mode, with the hb_events dump and without,
YOSEMITE_HB_DUMP=0):
  strong_stores_barrier_weak_load.cu  (I2: barriers, strong stores, a weak load)
  write_after_unlock_other_schedule.cu (I1: a lock hand-off, forced order since T18)
and the dump's aggregates are checked against what the verdict layer derives from the
records of the SAME recording (design/no_dump.md section 6):
  1. hb_sync_pass == sync_dominance.barrier_only_pairs (pairs, widest distance, first
     orientation), both modes; in vector-clock mode hb_races_sync_only == its triples;
  2. hb_rmw_points == sync_dominance.trace_rmw_points;
  3. analyze() from the records == analyze() from the aggregates (CUVEIN_PREFER_AGGREGATES=1),
     every verdict field.
A no-dump recording has no hb_events, the counts, and analyze() runs on it; its verdicts
equal the dump recording's (the forced-order kernel; the barrier kernel's race set does not
depend on the schedule either). D4: YOSEMITE_HB_HOST_MEMCPY with YOSEMITE_HB_DUMP=0 is refused.

Needs a GPU node and nvcc; part of the green set since T4.
    .env/bin/python -m pytest python/test_no_dump.py -rxX
"""
import copy
import glob
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import hb_oracle
import sync_dominance as sd

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "python" / "testdata"
KERNELS = ("strong_stores_barrier_weak_load", "write_after_unlock_other_schedule")
RUNS = (("vector-clock", 1), ("vector-clock", 0), ("scalar-clock", 1), ("scalar-clock", 0))


def _build(d, name):
    if shutil.which("nvcc") is None:
        pytest.skip("no nvcc (run on a GPU node)")
    binary = d / name
    b = subprocess.run(["nvcc", "-arch=native", "-lineinfo", "--cudart", "shared",
                        str(_SRC / f"{name}.cu"), "-o", str(binary)], capture_output=True)
    if b.returncode != 0:
        pytest.skip(f"build failed: {b.stderr.decode()[-300:]}")
    return binary


def _record(binary, d, mode, dump):
    """One getall.sh run of the binary in its own directory -> (dots, kernel JSON)."""
    run = d / f"{mode}-dump{dump}"
    run.mkdir()
    exe = run / binary.name
    shutil.copy2(binary, exe)
    env = dict(os.environ, YOSEMITE_HB_MODE=mode, YOSEMITE_HB_DUMP=str(dump))
    env.pop("YOSEMITE_HB_NO_ENGINE", None)
    subprocess.run(["bash", str(_ROOT / "getall.sh"), str(exe)], cwd=_ROOT, env=env,
                   capture_output=True, timeout=600)
    dots = sorted((run / f"{binary.name}_extracted_cubins").glob("*.dot"))
    traces = sorted(run.glob(f"dependency_{binary.name}*/kernel_*.json"))
    if not dots or not traces:
        pytest.skip("no trace produced (GPU / collector unavailable)")
    return dots, traces[-1]


@pytest.fixture(scope="module", params=KERNELS)
def rec(request, tmp_path_factory):
    """{(mode, dump): (dots, trace path)} of one kernel, plus its name."""
    name = request.param
    d = tmp_path_factory.mktemp(name)
    binary = _build(d, name)
    return name, {k: _record(binary, d, *k) for k in RUNS}


def _load(trace):
    return json.loads(Path(trace).read_text())


def _eng(dots, t):
    for dot in dots:
        kernels = sd.parse_dot(dot)
        try:
            mangled = sd.select_kernel(kernels, t["kernel"]["kernel_name"])
        except sd.AlignmentError:
            continue
        return sd.HBGraph(*kernels[mangled])
    raise AssertionError("no CFG holds the trace's kernel")


def _analyze(dots, trace, prefer_aggregates=False):
    env = {"CUVEIN_PREFER_AGGREGATES": "1"} if prefer_aggregates else {}
    old = {k: os.environ.get(k) for k in ("CUVEIN_PREFER_AGGREGATES",)}
    os.environ.pop("CUVEIN_PREFER_AGGREGATES", None)
    os.environ.update(env)
    try:
        for dot in dots:
            try:
                return sd.analyze(dot, trace)
            except sd.AlignmentError:
                continue
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    raise AssertionError("no CFG aligns with the trace")


def _vkey(v, full):
    """A verdict's content: the pair and its verdict/class (two recordings), or every field
    the report carries (one recording, two paths)."""
    k = (frozenset((v["current_pc"], v["ancient_pc"])), v["verdict"], v.get("hb_class"),
         v.get("conflict_class"), v["race_type"])
    if full:
        k += (v.get("matrix_class"), v["observed_distance"], v["contested_weight"],
              bool(v.get("event_candidate")), bool(v.get("edge_rescued")),
              v.get("a2_uncertain"), v.get("model_bug"),
              tuple(v["hb_chain"]) if v.get("hb_chain") else None, v["strength"])
    return k


def _offline(dots, t):
    """(pairs, dist, order) of barrier_only_pairs and (release, acquire) of trace_rmw_points
    from the records, the lane cutoff lifted."""
    eng = _eng(dots, t)
    policy = sd.strong_ldst_policy()
    rmw_all = {pc: sc for pc, op in eng.pc_opcode.items() if (sc := sd.atomic_scope(op)) is not None}
    coh_all = {pc: sc for pc, op in eng.pc_opcode.items()
               if (sc := sd.coherent_scope(op, policy)) is not None}
    dist, order = {}, {}
    plain = {k: v for k, v in t.items() if k not in ("hb_sync_pass", "hb_rmw_points")}
    pairs = sd.barrier_only_pairs(plain, rmw_all, coh_all, None, dist, order,
                                  sd.dump_async_pcs(eng, t))
    rel, acq = sd.trace_rmw_points(plain, set(rmw_all), None)
    return (pairs, dist, order), (rel, acq)


# --- the dump recordings: the aggregates against the records of the same recording ---------

@pytest.mark.parametrize("mode", ("vector-clock", "scalar-clock"))
def test_dump_carries_the_aggregates(rec, mode):
    name, runs = rec
    t = _load(runs[(mode, 1)][1])
    assert t.get("hb_events"), f"{name}/{mode}: the dump recording has no hb_events"
    assert "hb_aggregates" not in t
    assert t["hb_events_count"] == len(t["hb_events"]) == sd.event_count(t)
    assert t["hb_lanes_count"] == sum(len(e.get("lanes", ())) for e in t["hb_events"]) == sd.lane_count(t)
    assert "hb_sync_pass" in t and "hb_rmw_points" in t
    if mode == "vector-clock":
        assert "hb_races" in t and "hb_races_sync_only" in t
    else:   # the sync instance writes none of the vector clock's keys
        for k in ("hb_races", "hb_races_sync_only", "hb_a2", "hb_gate", "coherence_profile"):
            assert k not in t, f"{name}/scalar-clock: {k} written"


@pytest.mark.parametrize("mode", ("vector-clock", "scalar-clock"))
def test_sync_instance_equals_offline_pass(rec, mode):
    name, runs = rec
    dots, trace = runs[(mode, 1)]
    t = _load(trace)
    (pairs, dist, order), _ = _offline(dots, t)
    assert sd.aggregated_sync_pass(t) == (pairs, dist, order), f"{name}/{mode}"
    if mode == "vector-clock":
        assert t["hb_races_sync_only"] == [[a, b, n] for a, b, n, *_ in t["hb_sync_pass"]]
    assert "tv_violation" not in t, f"{name}/{mode}: {t.get('tv_violation')}"


@pytest.mark.parametrize("mode", ("vector-clock", "scalar-clock"))
def test_rmw_points_equal_trace_rmw_points(rec, mode):
    name, runs = rec
    dots, trace = runs[(mode, 1)]
    t = _load(trace)
    _, (rel, acq) = _offline(dots, t)
    assert sd.aggregated_rmw_points(t) == (rel, acq), f"{name}/{mode}"


@pytest.mark.parametrize("mode", ("vector-clock", "scalar-clock"))
def test_verdicts_from_aggregates_equal_verdicts_from_records(rec, mode):
    name, runs = rec
    dots, trace = runs[(mode, 1)]
    a = _analyze(dots, trace)
    b = _analyze(dots, trace, prefer_aggregates=True)
    assert sorted(map(str, (_vkey(v, True) for v in a["verdicts"]))) == \
        sorted(map(str, (_vkey(v, True) for v in b["verdicts"]))), f"{name}/{mode}"
    assert a["skipped_edges"] == b["skipped_edges"]
    assert a["diagnostics"]["event_candidates"] == b["diagnostics"]["event_candidates"]


# --- the no-dump recordings ----------------------------------------------------------------

@pytest.mark.parametrize("mode", ("vector-clock", "scalar-clock"))
def test_no_dump_recording_has_aggregates_only(rec, mode):
    name, runs = rec
    dots, trace = runs[(mode, 0)]
    t = _load(trace)
    assert "hb_events" not in t, f"{name}/{mode}: hb_events written under YOSEMITE_HB_DUMP=0"
    assert t.get("hb_aggregates") == 1
    assert t["hb_events_count"] > 0 and t["hb_lanes_count"] > 0
    assert sd.event_count(t) == t["hb_events_count"]
    assert "hb_sync_pass" in t and "hb_rmw_points" in t
    assert ("hb_races" in t) == (mode == "vector-clock")
    rep = _analyze(dots, trace)
    assert rep["verdicts"], f"{name}/{mode}: no verdict from the aggregates"
    with pytest.raises(sd.AlignmentError):      # the specification needs the records
        hb_oracle.analyze(dots[0], trace)


@pytest.mark.parametrize("mode", ("vector-clock", "scalar-clock"))
def test_no_dump_verdicts_equal_dump_verdicts(rec, mode):
    name, runs = rec
    a = _analyze(*runs[(mode, 1)])
    b = _analyze(*runs[(mode, 0)])
    assert sorted(map(str, (_vkey(v, False) for v in a["verdicts"]))) == \
        sorted(map(str, (_vkey(v, False) for v in b["verdicts"]))), f"{name}/{mode}"


def test_no_dump_sizes(rec):
    """What the switch is for: the no-dump file is a fraction of the dump's."""
    name, runs = rec
    big = os.path.getsize(runs[("vector-clock", 1)][1])
    small = os.path.getsize(runs[("vector-clock", 0)][1])
    assert small < big, f"{name}: {small} >= {big}"


def test_host_memcpy_needs_the_dump(tmp_path):
    """D4: YOSEMITE_HB_HOST_MEMCPY=1 with YOSEMITE_HB_DUMP=0 is refused at start."""
    binary = _build(tmp_path, KERNELS[0])
    env = dict(os.environ, YOSEMITE_HB_TRACE="1", YOSEMITE_HB_DUMP="0",
               YOSEMITE_HB_HOST_MEMCPY="1", ACCEL_PROF_HOME=str(_ROOT),
               PATH=f"{_ROOT}/bin:" + os.environ.get("PATH", ""))
    p = subprocess.run(["accelprof", "-t", "pc_dependency_analysis", "-n", "1", f"./{binary.name}"],
                       cwd=tmp_path, env=env, capture_output=True, timeout=600)
    assert p.returncode != 0
    assert not glob.glob(str(tmp_path / f"dependency_{binary.name}*/kernel_*.json"))

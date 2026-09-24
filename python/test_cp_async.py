"""T1a (eval/CP_ASYNC_REPORT.md): cp.async (LDGSTS) copies and the waits that complete them,
end to end. python/testdata/cp_async_wait.cu in nine builds, each built for the GPU running the
suite and traced with getall.sh (vector-clock); the scalar-clock view is the same dump without
the engine's keys.
  racy / fixed      the read before / after cp.async.wait_all
  groups            two commit groups, wait_group 1: the first is complete, the second in flight
  barrier(_fixed)   a __syncthreads() between the copy and a read of the other warp's element,
                    the wait after the read (before the barrier): a barrier completes no copy
  barrier_own       the same with the thread's own element
  twice(_fixed)     two copies of one thread into one element, without (with) a wait between
  mbarrier          a copy completed through a cuda::barrier: not modelled, so the kernel keeps
                    the pre-T1a reading (no race on the copy)
Asserted by semantics -- pcs are found through the CFG's opcodes, never hard-coded -- so the
test holds across architectures and CUDA versions. Needs a GPU node; part of the green set.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

import hb_oracle as ho
import sync_dominance as sd

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "python" / "testdata" / "cp_async_wait.cu"
VARIANTS = {"racy": [], "fixed": ["-DFIXED"], "groups": ["-DGROUPS"],
            "barrier": ["-DBARRIER"], "barrier_fixed": ["-DBARRIER", "-DFIXED"],
            "barrier_own": ["-DBARRIER", "-DOWN"],
            "twice": ["-DTWICE"], "twice_fixed": ["-DTWICE", "-DFIXED"],
            "mbarrier": ["-DMBARRIER"]}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """variant -> (dots, kernel JSON) of one vector-clock run each."""
    if shutil.which("nvcc") is None:
        pytest.skip("no nvcc (run on a GPU node)")
    out = {}
    for v, flags in VARIANTS.items():
        d = tmp_path_factory.mktemp(f"cp_async_{v}")
        binary = d / f"cp_async_{v}"
        b = subprocess.run(["nvcc", "-arch=native", "-lineinfo", "--cudart", "shared", *flags,
                            str(_SRC), "-o", str(binary)], capture_output=True)
        if b.returncode != 0:
            pytest.skip(f"build failed: {b.stderr.decode()[-300:]}")
        subprocess.run(["bash", str(_ROOT / "getall.sh"), str(binary)], cwd=_ROOT,
                       capture_output=True, timeout=600)
        dots = sorted((d / f"cp_async_{v}_extracted_cubins").glob("*.dot"))
        traces = sorted(d.glob(f"dependency_cp_async_{v}*/kernel_*.json"))
        if not dots or not traces:
            pytest.skip("no trace produced (GPU / collector unavailable)")
        out[v] = (dots, traces[-1])
    # A runtime older than T1a (an older libsanalyzer, collector or pc_dependency fatbin)
    # records neither commit/wait events nor the hb_async marker: nothing here applies.
    # One without the other is a partial install and fails the tests below.
    tj = json.loads(Path(out["racy"][1]).read_text())
    if "hb_async" not in tj and not any(e["type"].startswith("pipeline_")
                                        for e in tj.get("hb_events", [])):
        pytest.skip("the traced runtime predates T1a (no hb_async marker, no pipeline "
                    "events): install the T1a libsanalyzer, collector and pc_dependency fatbin")
    return out


def _try(fn, dots, *args, **kw):
    for dot in dots:
        try:
            return fn(dot, *args, **kw)
        except sd.AlignmentError as e:
            if str(e).startswith("TV-"):
                raise
    raise AssertionError("no CFG aligns with the trace")


def _ops(dots, trace):
    """pc -> opcode of the traced kernel, and its LDGSTS / LDS pcs in pc order."""
    rep = _try(ho.analyze, dots, trace)
    ops = sd.HBGraph(*sd.parse_dot(rep["inputs"]["cfg_dot"])[rep["kernel"]["mangled"]]).pc_opcode
    pick = lambda base: sorted(pc for pc, op in ops.items() if op.split(".")[0] == base)
    return ops, pick("LDGSTS"), pick("LDS"), rep


def _pairs(races):
    return {(r["a_pc"], r["b_pc"], r["kind"], r.get("async")) for r in races}


def _expected(v, copies, loads):
    """The engine's race records ((a_pc, b_pc, kind, async)) that involve a copy."""
    if v in ("racy", "barrier", "barrier_own"):     # the copy vs the unwaited read
        return {(copies[0], loads[0], "RAW", "a")}
    if v == "groups":                               # group B still in flight at wait_group 1
        return {(copies[1], loads[1], "RAW", "a")}
    if v == "twice":                                # the two copies of one thread
        return {(copies[0], copies[1], "WAW", "ab")}
    return set()                                    # fixed, *_fixed, mbarrier


def _copy_pairs(pairs, copies):
    return {p for p in pairs if p[0] in copies or p[1] in copies}


@pytest.mark.parametrize("v", list(VARIANTS))
def test_commit_and_wait_are_recorded(built, v):
    # tripwire of the design: PIPELINE_COMMIT / PIPELINE_WAIT fire for LDGDEPBAR / DEPBAR.LE
    _, trace = built[v]
    tj = json.loads(Path(trace).read_text())
    ev = tj["hb_events"]
    waits = sorted({e["groups"] for e in ev if e["type"] == "pipeline_wait"})
    assert tj.get("hb_async") == 1                  # the dump says so
    if v == "mbarrier":                             # completed through the mbarrier instead
        assert not any(e["type"].startswith("pipeline_") for e in ev)
        return
    assert any(e["type"] == "pipeline_commit" for e in ev)
    assert waits == ([0, 1] if v == "groups" else [0])


@pytest.mark.parametrize("v", list(VARIANTS))
def test_engine_races(built, v):
    dots, trace = built[v]
    _, copies, loads, _ = _ops(dots, trace)
    races = _pairs(json.loads(Path(trace).read_text())["hb_races"])
    assert _copy_pairs(races, set(copies)) == _expected(v, copies, loads)
    if v != "mbarrier":     # (the cuda::barrier's own polling of its state word races too)
        assert races == _expected(v, copies, loads)


@pytest.mark.parametrize("v", list(VARIANTS))
def test_engine_matches_oracle(built, v):
    dots, trace = built[v]
    tj = json.loads(Path(trace).read_text())
    rep = _try(ho.analyze, dots, trace)
    key = lambda r: (r["addr"], r["a_tid"], r["a_pc"], r["b_tid"], r["b_pc"], r["kind"], r.get("async"))
    assert sorted(map(key, tj["hb_races"])) == sorted(map(key, rep["races"]))
    assert tj["hb_races_sync_only"] == rep["races_sync_only"]


@pytest.mark.parametrize("v", list(VARIANTS))
def test_offline_pass_matches_oracle(built, v):
    dots, trace = built[v]
    _, _, _, rep = _ops(dots, trace)
    g = sd.HBGraph(*sd.parse_dot(rep["inputs"]["cfg_dot"])[rep["kernel"]["mangled"]])
    rmw = {pc: s for pc, op in g.pc_opcode.items() if (s := sd.atomic_scope(op)) is not None}
    coh = {pc: s for pc, op in g.pc_opcode.items() if (s := sd.coherent_scope(op)) is not None}
    tj = json.loads(Path(trace).read_text())
    fast = sd.barrier_only_pairs(tj, rmw, coh, async_pc=sd.dump_async_pcs(g, tj))
    assert sorted([a, b, n] for (a, b), n in fast.items()) == rep["races_sync_only"]


def _race_verdicts(dots, trace, tmp_path, mode, **kw):
    t = json.loads(Path(trace).read_text())
    if mode == "scalar-clock":
        for k in ("hb_races", "hb_races_sync_only"):
            t.pop(k, None)
    p = tmp_path / f"k_{mode}.json"
    p.write_text(json.dumps(t))
    return {(r["ancient_pc"], r["current_pc"]) for r in _try(sd.analyze, dots, p, **kw)["verdicts"]
            if r["verdict"] == "RACE"}


@pytest.mark.parametrize("v", list(VARIANTS))
@pytest.mark.parametrize("mode", ["vector-clock", "scalar-clock"])
def test_verdict(built, v, mode, tmp_path):
    # both modes, including a barrier between the copy and the read: the static rules may
    # not order a pair whose earlier access is a copy (it completes only at the wait)
    dots, trace = built[v]
    _, copies, loads, _ = _ops(dots, trace)
    races = _race_verdicts(dots, trace, tmp_path, mode)
    want = {(a, b) for a, b, _, _ in _expected(v, copies, loads)}
    assert {p for p in races if p[0] in copies or p[1] in copies} == want


@pytest.mark.parametrize("v", ["racy", "barrier_own", "twice"])
def test_lockstep_orders_no_copy(built, v, tmp_path):
    # --assume-warp-lockstep orders same-warp pairs in program order; a copy is performed by
    # the thread's async agent, not in the lane's program order, so its races stay
    dots, trace = built[v]
    _, copies, loads, _ = _ops(dots, trace)
    races = _race_verdicts(dots, trace, tmp_path, "vector-clock", assume_warp_lockstep=True)
    assert {p for p in races if p[0] in copies or p[1] in copies} == \
        {(a, b) for a, b, _, _ in _expected(v, copies, loads)}


def test_mbarrier_copies_keep_the_pre_t1a_reading(built):
    # a copy completed through an mbarrier (cp.async.mbarrier.arrive = ARRIVES.LDGSTSBAR) is
    # not modelled: the kernel's LDGSTS pcs are not async, for the engine (sidecar) and the
    # oracle / offline pass (CFG) alike
    dots, trace = built["mbarrier"]
    ops, copies, _, rep = _ops(dots, trace)
    assert copies and any(op.startswith("ARRIVES.LDGSTSBAR") for op in ops.values())
    g = sd.HBGraph(*sd.parse_dot(rep["inputs"]["cfg_dot"])[rep["kernel"]["mangled"]])
    assert sd.async_pcs(g) == set()
    sidecar = Path(dots[0]).parent / "atomic_scope.txt"     # getall.sh writes it by the dots
    assert sidecar.exists() and "# async" not in sidecar.read_text()


@pytest.mark.parametrize("v", list(VARIANTS))
def test_dump_without_marker_keeps_the_pre_t1a_reading(built, v, tmp_path):
    # A dump from a pre-T1a collector: LDGSTS accesses, no commit/wait records, no hb_async
    # marker. The agent model would leave every copy in flight (the fixed builds would
    # race); without the marker the copy stays the issuing thread's own access, so no build
    # races on a copy -- the pre-T1a verdict, false negatives of the racy builds included
    # (found on the kept pre-T1a stores, eval/CP_ASYNC_REPORT.md).
    dots, trace = built[v]
    _, copies, _, _ = _ops(dots, trace)
    t = json.loads(Path(trace).read_text())
    t.pop("hb_async")
    t["hb_events"] = [e for e in t["hb_events"]
                      if e["type"] not in ("pipeline_commit", "pipeline_wait")]
    for k in ("hb_races", "hb_races_sync_only"):
        t.pop(k, None)
    p = tmp_path / "k.json"
    p.write_text(json.dumps(t))
    assert _copy_pairs(_pairs(_try(ho.analyze, dots, p)["races"]), set(copies)) == set()
    assert [r for r in _try(sd.analyze, dots, p)["verdicts"] if r["verdict"] == "RACE"
            and (r["ancient_pc"] in copies or r["current_pc"] in copies)] == []

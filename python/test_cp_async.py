"""T1a (eval/CP_ASYNC_REPORT.md): cp.async (LDGSTS) copies and the waits that complete them,
end to end. python/testdata/cp_async_wait.cu in three builds -- racy (the read comes before
cp.async.wait_all), fixed (after it) and groups (two commit groups, wait_group 1: the first is
complete, the second may still be in flight). Each is built for the GPU running the suite and
traced with getall.sh (vector-clock); the scalar-clock view is the same dump without the
engine's keys. Asserted by semantics -- pcs are found through the CFG's opcodes, never
hard-coded -- so the test holds across architectures and CUDA versions.
Needs a GPU node; part of the green set.
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
VARIANTS = {"racy": [], "fixed": ["-DFIXED"], "groups": ["-DGROUPS"]}


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


@pytest.mark.parametrize("v", list(VARIANTS))
def test_commit_and_wait_are_recorded(built, v):
    # tripwire of the design: PIPELINE_COMMIT / PIPELINE_WAIT fire for LDGDEPBAR / DEPBAR.LE
    _, trace = built[v]
    ev = json.loads(Path(trace).read_text())["hb_events"]
    waits = sorted({e["groups"] for e in ev if e["type"] == "pipeline_wait"})
    assert any(e["type"] == "pipeline_commit" for e in ev)
    assert waits == ([0, 1] if v == "groups" else [0])
    assert json.loads(Path(trace).read_text()).get("hb_async") == 1   # the dump says so


@pytest.mark.parametrize("v", list(VARIANTS))
def test_engine_races(built, v):
    dots, trace = built[v]
    _, copies, loads, _ = _ops(dots, trace)
    races = _pairs(json.loads(Path(trace).read_text())["hb_races"])
    if v == "racy":      # the copy (async side a) vs the thread's early read
        assert races == {(copies[0], loads[0], "RAW", "a")}
    elif v == "fixed":
        assert races == set()
    else:                # group B still in flight at wait_group 1; group A complete
        assert races == {(copies[1], loads[1], "RAW", "a")}


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


@pytest.mark.parametrize("v", list(VARIANTS))
@pytest.mark.parametrize("mode", ["vector-clock", "scalar-clock"])
def test_verdict(built, v, mode, tmp_path):
    dots, trace = built[v]
    _, copies, loads, _ = _ops(dots, trace)
    t = json.loads(Path(trace).read_text())
    if mode == "scalar-clock":
        for k in ("hb_races", "hb_races_sync_only"):
            t.pop(k, None)
    p = tmp_path / "k.json"
    p.write_text(json.dumps(t))
    races = {(r["ancient_pc"], r["current_pc"]) for r in _try(sd.analyze, dots, p)["verdicts"]
             if r["verdict"] == "RACE"}
    want = {(copies[0], loads[0])} if v == "racy" else set() if v == "fixed" \
        else {(copies[1], loads[1])}
    assert races == want


@pytest.mark.parametrize("v", list(VARIANTS))
def test_dump_without_marker_keeps_the_pre_t1a_reading(built, v, tmp_path):
    # A dump from a pre-T1a collector: LDGSTS accesses, no commit/wait records, no hb_async
    # marker. The agent model would leave every copy in flight (the fixed build would
    # race); without the marker the copy stays the issuing thread's own access, so none of
    # the three builds races -- the pre-T1a verdict, false negative of the racy build
    # included (found on the kept pre-T1a stores, eval/CP_ASYNC_REPORT.md).
    dots, trace = built[v]
    t = json.loads(Path(trace).read_text())
    t.pop("hb_async")
    t["hb_events"] = [e for e in t["hb_events"]
                      if e["type"] not in ("pipeline_commit", "pipeline_wait")]
    for k in ("hb_races", "hb_races_sync_only"):
        t.pop(k, None)
    p = tmp_path / "k.json"
    p.write_text(json.dumps(t))
    assert _try(ho.analyze, dots, p)["races"] == []
    assert [r for r in _try(sd.analyze, dots, p)["verdicts"] if r["verdict"] == "RACE"] == []

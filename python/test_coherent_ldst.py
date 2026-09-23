"""Coherent load/store (RC1) and barrier-ordered (RC2) litmus — see eval/FP_DIAGNOSIS.md.

testdata/coherent_ldst.cu holds one kernel per case. Verdicts come from the full
pipeline (sync_dominance.analyze over the vector-clock dump produced by getall.sh:
static R1/R2/R3 crossed with the C++ engine's hb_races / hb_races_sync_only), and the
engine must equal the Python oracle on both race sets. Also pins the toolchain
lowering the default --strong-ldst=generic policy relies on: cuda::atomic load/store
-> generic LD/ST.*.STRONG, volatile -> address-spaced LDG/STG.*.STRONG.

Builds on demand; skips without GPU / nvcc, mirroring test_atomic_memory_model.
"""
import json
import subprocess
from pathlib import Path

import pytest

import hb_oracle as ho
import sync_dominance as sd

_ROOT = Path(__file__).resolve().parents[1]
_SRC = Path(__file__).resolve().parent / "testdata" / "coherent_ldst.cu"
_KERNELS = ("atomic_seqcst", "atomic_relaxed", "atomic_rmw_load", "atomic_vs_plain",
            "volatile_pair", "reduce_barrier", "reduce_nobarrier")
_NORACE = ("atomic_seqcst", "atomic_relaxed", "atomic_rmw_load", "reduce_barrier")
_RACE = ("atomic_vs_plain", "volatile_pair", "reduce_nobarrier")


def _artifacts():
    """(dots, {kernel: trace}) built on demand; None if no source/GPU/build."""
    if not _SRC.is_file():
        return None
    work = _ROOT / "cuHadron" / "_coherent_ldst"      # a gitignored scratch area
    work.mkdir(parents=True, exist_ok=True)
    binary = work / "coh.out"
    ext = work / "coh_extracted_cubins"

    def _collect():
        dots = sorted(ext.glob("*.dot"))
        deps = sorted(work.glob("dependency_coh*"))
        by_name = {}
        for t in (sorted(deps[-1].glob("kernel_*.json")) if deps else []):
            nm = json.loads(t.read_text())["kernel"]["kernel_name"]
            for k in _KERNELS:
                if nm.startswith(k + "("):
                    by_name[k] = t
        return dots, by_name

    stale = binary.exists() and binary.stat().st_mtime < _SRC.stat().st_mtime
    dots, by_name = _collect()
    if not stale and dots and set(_KERNELS) <= by_name.keys():
        return dots, by_name

    build = subprocess.run(
        ["nvcc", "-arch=native", "-lineinfo", "--cudart", "shared",
         str(_SRC), "-o", str(binary)], cwd=work, capture_output=True)
    if build.returncode != 0 or not binary.exists():
        return None
    subprocess.run(["bash", str(_ROOT / "getall.sh"), str(binary.resolve())],
                   cwd=_ROOT, capture_output=True, timeout=600)
    dots, by_name = _collect()
    return (dots, by_name) if dots and set(_KERNELS) <= by_name.keys() else None


def _try_dots(fn, dots, trace):
    for dot in dots:
        try:
            return fn(dot, trace)
        except sd.AlignmentError:
            continue
    raise AssertionError(f"no CFG aligns with {trace}")


def _art_or_skip():
    art = _artifacts()
    if art is None:
        pytest.skip("no GPU / nvcc / source to build coherent_ldst")
    return art


def _races(report):
    return [v for v in report["verdicts"] if v["verdict"] == "RACE"]


@pytest.mark.parametrize("kernel", _NORACE)
def test_norace(kernel):
    dots, by = _art_or_skip()
    report = _try_dots(sd.analyze, dots, by[kernel])
    assert not _races(report), f"{kernel}: expected race-free, got {_races(report)}"


@pytest.mark.parametrize("kernel", _RACE)
def test_race(kernel):
    dots, by = _art_or_skip()
    report = _try_dots(sd.analyze, dots, by[kernel])
    assert _races(report), f"{kernel}: expected >=1 race, got none"


def test_reduction_is_barrier_ordered_not_static():
    """The point of RC2: no static proof exists for the in-loop reduction pair, the
    verdict comes from the barrier-only clock (class barrier-ordered)."""
    dots, by = _art_or_skip()
    report = _try_dots(sd.analyze, dots, by["reduce_barrier"])
    classes = {v["hb_class"] for v in report["verdicts"] if v["space"] == "shared"}
    assert "barrier-ordered" in classes, classes
    assert not classes & {"structural", "latent", "model_bug"}, classes


def test_lowering_assumption():
    """generic policy rests on: cuda::atomic load/store -> LD/ST.*.STRONG (generic
    form), volatile -> LDG/STG.*.STRONG. If the toolchain changes this, fail loudly."""
    dots, by = _art_or_skip()

    def traced_ops(kernel):
        rep = _try_dots(sd.analyze, dots, by[kernel])
        trace = json.loads(by[kernel].read_text())
        kern = sd.parse_dot(rep["inputs"]["cfg_dot"])[rep["kernel"]["mangled"]]
        ops = sd.HBGraph(*kern).pc_opcode
        return {ops[n["pc"]] for n in trace["nodes"]}

    for k in ("atomic_seqcst", "atomic_relaxed"):
        strong = {op for op in traced_ops(k) if "STRONG" in op.split(".")}
        assert strong and all(op.split(".")[0] in ("LD", "ST") for op in strong), (k, strong)
    strong = {op for op in traced_ops("volatile_pair") if "STRONG" in op.split(".")}
    assert strong and not any(op.split(".")[0] in ("LD", "ST") for op in strong), strong


def _race_key(r):
    return (r["addr"], r["a_tid"], r.get("a_pc"), r["b_tid"], r["b_pc"], r["kind"])


@pytest.mark.parametrize("kernel", _KERNELS)
def test_engine_matches_oracle(kernel):
    dots, by = _art_or_skip()
    tj = json.loads(by[kernel].read_text())
    if "hb_events" not in tj:
        pytest.skip("trace has no hb_events (YOSEMITE_HB_TRACE was off)")
    report = _try_dots(ho.analyze, dots, by[kernel])
    assert sorted({_race_key(r) for r in tj.get("hb_races", [])}) == \
        sorted({_race_key(r) for r in report["races"]}), kernel
    assert tj.get("hb_races_sync_only") == report["races_sync_only"], kernel


def _offline_pairs(dots, trace):
    rep = _try_dots(ho.analyze, dots, trace)
    kern = sd.parse_dot(rep["inputs"]["cfg_dot"])[rep["kernel"]["mangled"]]
    ops = sd.HBGraph(*kern).pc_opcode
    rmw = {pc: s for pc, op in ops.items() if (s := sd.atomic_scope(op)) is not None}
    coh = {pc: s for pc, op in ops.items() if (s := sd.coherent_scope(op)) is not None}
    tj = json.loads(trace.read_text())
    asy = sd.dump_async_pcs(sd.HBGraph(*kern), tj)
    pairs = sd.barrier_only_pairs(tj, rmw, coh, async_pc=asy)
    return sorted([a, b, n] for (a, b), n in pairs.items()), rep["races_sync_only"]


@pytest.mark.parametrize("kernel", _KERNELS)
def test_offline_barrier_pass_matches_oracle(kernel):
    """sync_dominance.barrier_only_pairs (shared-base clock, used for scalar-clock dumps)
    must equal the oracle's barrier-only second clock."""
    dots, by = _art_or_skip()
    fast, oracle = _offline_pairs(dots, by[kernel])
    assert fast == oracle, kernel


def _scalar_clock_copy(trace, tmp_path):
    """The same dump as YOSEMITE_HB_MODE=scalar-clock would write it: no engine keys."""
    tj = json.loads(trace.read_text())
    for k in ("hb_races", "hb_races_sync_only", "coherence_profile"):
        tj.pop(k, None)
    out = tmp_path / trace.name
    out.write_text(json.dumps(tj))
    return out


@pytest.mark.parametrize("kernel", _KERNELS)
def test_scalar_clock_verdict(kernel, tmp_path):
    """Scalar-clock mode (static leg + offline barrier pass over hb_events) reaches the
    same program verdict: the in-loop reduction is barrier-ordered without the engine,
    and with the pass disabled it falls back to the static-only RACE."""
    dots, by = _art_or_skip()
    trace = _scalar_clock_copy(by[kernel], tmp_path)
    report = _try_dots(sd.analyze, dots, trace)
    assert bool(_races(report)) == (kernel in _RACE), (kernel, _races(report))
    if kernel == "reduce_barrier":
        static_only = _try_dots(lambda d, t: sd.analyze(d, t, barrier_pass=False), dots, trace)
        assert _races(static_only), "static leg alone cannot prove the in-loop reduction"

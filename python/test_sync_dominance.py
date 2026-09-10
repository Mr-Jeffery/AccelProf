"""Corpus check for sync_dominance. Run: pytest python/test_sync_dominance.py

The ScoR corpus test drives every microbenchmark binary through getall.sh
(nvdisasm CFG + accelprof pc_dependency trace) and then sync_dominance.analyze.

Atomic coherence scope and the scoped happens-before closure are modelled, so
the suite is asserted in both directions:
  * `race_*`   -> at least one RACE  (a miss is a false negative = a real bug)
  * `norace_*` -> zero RACEs         (a hit is a false positive)
  * every binary -> pipeline aligns, no unknown sync opcodes
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import hb_oracle as ho
import sync_dominance as sd

_ROOT = Path(__file__).resolve().parents[1]
_BIN = _ROOT / "ScoR/microbenchmarks/bin"
_ART = _ROOT / "ScoR/microbenchmarks/artifacts"   # getall.sh output, moved out of bin/
_LOG = _ART / "sync_dominance.log"


def _binaries():
    if not _BIN.is_dir():
        return []
    return sorted(p for p in _BIN.iterdir()
                  if p.is_file() and os.access(p, os.X_OK)
                  and (p.name.startswith("race_") or p.name.startswith("norace_")))


def _find(dest):
    dots = sorted(dest.glob("**/*.dot"))
    deps = sorted(dest.glob("dependency_*"))
    traces = sorted(deps[-1].glob("kernel_*.json")) if deps else []
    return dots, traces


def _artifacts(binary):
    """(dots, traces) for a binary under artifacts/<name>/, generating them via
    getall.sh (into bin/) and moving them into the subfolder. None if no trace
    was produced (no GPU / build missing)."""
    dest = _ART / binary.name
    dots, traces = _find(dest)
    if dots and traces:
        return dots, traces

    ext = _BIN / f"{binary.name}_extracted_cubins"
    deps = sorted(_BIN.glob(f"dependency_{binary.name}_*"))
    if not (ext.is_dir() and list(ext.glob("*.dot")) and deps):
        subprocess.run(["bash", str(_ROOT / "getall.sh"), str(binary.resolve())],
                       cwd=_ROOT, capture_output=True, timeout=600)
        deps = sorted(_BIN.glob(f"dependency_{binary.name}_*"))

    dest.mkdir(parents=True, exist_ok=True)
    for d in [ext, *deps, *_BIN.glob(f"{binary.name}.accelprof.log")]:
        if d.exists():
            shutil.move(str(d), str(dest / d.name))
    dots, traces = _find(dest)
    return (dots, traces) if dots and traces else None


@pytest.fixture(scope="session")
def logfile():
    _ART.mkdir(parents=True, exist_ok=True)
    _LOG.write_text("")
    return _LOG


@pytest.mark.parametrize("binary", _binaries(), ids=lambda p: p.name)
def test_scor_microbenchmark(binary, logfile):
    art = _artifacts(binary)
    if art is None:
        pytest.skip("corpus not generated (no GPU / accelprof unavailable)")
    dots, traces = art

    races = 0
    with open(logfile, "a") as log:
        log.write(f"\n===== {binary.name} =====\n")
        for trace in traces:
            report = None
            for dot in dots:  # pick the cubin whose CFG holds this kernel
                try:
                    report = sd.analyze(dot, trace)
                    break
                except sd.AlignmentError:
                    continue
            assert report is not None, f"no CFG aligns with {trace.name}"
            out = trace.with_name(trace.stem + ".races.json")
            log.write(sd.render(report, out) + "\n")
            assert report["diagnostics"]["unknown_sync_count"] == 0, \
                f"unknown sync opcodes in {binary.name}"
            races += report["summary"]["races"]

    if binary.name.startswith("race_"):
        assert races >= 1, f"false negative: {binary.name} reported no race"
    else:
        assert races == 0, f"false positive: {binary.name} reported {races} race(s)"


def _race_key(r):
    return (r["addr"], r["a_tid"], r.get("a_pc"), r["b_tid"], r["b_pc"], r["kind"])


@pytest.mark.parametrize("binary", _binaries(), ids=lambda p: p.name)
def test_hb_engine_matches_oracle(binary):
    """The analyzer's streaming C++ HB engine (hb_races in the trace) must equal the
    full vector-clock Python oracle (hb_oracle) on every corpus binary — the oracle is
    the executable correctness spec for the scalable engine (roadmap Phase 2)."""
    art = _artifacts(binary)
    if art is None:
        pytest.skip("corpus not generated (no GPU / accelprof unavailable)")
    dots, traces = art
    for trace in traces:
        tj = json.loads(trace.read_text())
        if "hb_events" not in tj:
            pytest.skip("trace has no hb_events (YOSEMITE_HB_TRACE was off)")
        engine = sorted({_race_key(r) for r in tj.get("hb_races", [])})
        report = None
        for dot in dots:  # pick the cubin whose CFG holds this kernel
            try:
                report = ho.analyze(dot, trace)
                break
            except sd.AlignmentError:
                continue
        assert report is not None, f"no CFG aligns with {trace.name}"
        oracle = sorted({_race_key(r) for r in report["races"]})
        assert engine == oracle, (
            f"{binary.name}/{trace.name}: "
            f"engine-only={[k for k in engine if k not in oracle]} "
            f"oracle-only={[k for k in oracle if k not in engine]}")


_ISW = _ROOT / "cuHadron/intersubwarp"


def _intersubwarp_artifacts():
    """(dots, trace) for cuHadron intersubwarp shared_readwrite_race, built and
    traced on demand (mirrors _artifacts). None if source/GPU/build unavailable.

    The benchmark is compiled for whatever GPU runs the suite (-arch=native) so
    the test carries no hardcoded arch or PC offsets, and with --cudart shared so
    accelprof's LD_PRELOADed libcompute_sanitizer.so can resolve cudart symbols."""
    src = _ISW / "shared_readwrite_race.cu"
    if not src.is_file():
        return None
    binary = _ISW / "shared_readwrite_race.out"
    ext = _ISW / "shared_readwrite_race_extracted_cubins"

    def _collect():
        dots = sorted(ext.glob("*.dot"))
        deps = sorted(_ISW.glob("dependency_shared_readwrite_race*"))
        traces = sorted(deps[-1].glob("kernel_*.json")) if deps else []
        return dots, (traces[-1] if traces else None)

    dots, trace = _collect()
    if dots and trace:
        return dots, trace

    build = subprocess.run(
        ["nvcc", "-arch=native", "-lineinfo", "--cudart", "shared",
         str(src), "-o", str(binary)], cwd=_ISW, capture_output=True)
    if build.returncode != 0 or not binary.exists():
        return None
    subprocess.run(["bash", str(_ROOT / "getall.sh"), str(binary.resolve())],
                   cwd=_ROOT, capture_output=True, timeout=600)
    dots, trace = _collect()
    return (dots, trace) if dots and trace else None


def test_intersubwarp_readwrite():
    """Inter-subwarp shared-memory read/write race (cuHadron). Asserted by
    semantics, not PC offsets, so it holds across CUDA versions and archs:
      * exactly one race, at warp distance, unsynchronized, on shared memory,
        read-vs-write; and
      * a block-barrier-ordered pair exists (the init store the __syncthreads()
        orders before the read — the false-positive control)."""
    art = _intersubwarp_artifacts()
    if art is None:
        pytest.skip("cuHadron intersubwarp corpus unavailable (no GPU / build)")
    dots, trace = art

    report = None
    for dot in dots:  # pick the cubin whose CFG holds this kernel
        try:
            report = sd.analyze(dot, trace)
            break
        except sd.AlignmentError:
            continue
    assert report is not None, "no cubin CFG aligns with the trace"

    assert report["diagnostics"]["unknown_sync_count"] == 0
    assert report["summary"]["races"] == 1

    races = [v for v in report["verdicts"] if v["verdict"] == "RACE"]
    assert len(races) == 1
    race = races[0]
    assert race["observed_distance"] == "warp"   # inter-subwarp -> same warp
    assert race["strength"] == "none"            # no qualifying sync between them
    assert race["space"] == "shared"             # __shared__ race
    assert race["race_type"] in ("RAW", "WAR")   # read-vs-write

    # false-positive control: init store ordered before the read by a block barrier
    ordered = [v for v in report["verdicts"]
               if v["verdict"] == "ORDERED" and v["strength"] == "block"
               and v["ordering_syncs"]]
    assert ordered, "expected a barrier-ordered pair"

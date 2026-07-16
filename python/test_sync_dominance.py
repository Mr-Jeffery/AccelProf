"""Corpus check for sync_dominance. Run: pytest python/test_sync_dominance.py

The ScoR corpus test drives every microbenchmark binary through getall.sh
(nvdisasm CFG + accelprof pc_dependency trace) and then sync_dominance.analyze.

sync_dominance v1 over-reports (never under-reports): atomics, fences and locks
are NOT modelled as ordering, so many `norace_*` benchmarks are flagged as races
on purpose. The only sound assertion is therefore one-directional:
  * `race_*`   -> at least one RACE   (a miss here is a false negative = a real bug)
  * every binary -> pipeline aligns, no unknown sync opcodes
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

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

    # soundness: a labelled race must be reported (norace may over-report, so no
    # 0-race assertion there — v1 does not model atomics/fences/locks as ordering)
    if binary.name.startswith("race_"):
        assert races >= 1, f"false negative: {binary.name} reported no race"


_DIR = _ROOT / "cuHadron/intersubwarp/" \
    "shared_readwrite_race.sm86_extracted_cubins"
_DOT = _DIR / "shared_readwrite_race.sm_86.dot"
_TRACE = next(_DIR.glob("dependency_*/kernel_0.json"), None) if _DIR.exists() else None


@pytest.mark.skipif(not (_DOT.exists() and _TRACE), reason="corpus not present")
def test_intersubwarp_readwrite():
    report = sd.analyze(_DOT, _TRACE)
    v = {(x["ancient_pc"], x["current_pc"]): x for x in report["verdicts"]}

    # injected inter-subwarp read/write race: no qualifying sync between them
    race = v[(0x120, 0x1c0)]
    assert race["verdict"] == "RACE"
    assert race["strength"] == "none"
    assert race["observed_distance"] == "warp"

    # false-positive control: init store ordered before the read by BAR.SYNC@0x60
    ordered = v[(0x40, 0x120)]
    assert ordered["verdict"] == "ORDERED"
    assert ordered["strength"] == "block"
    assert ordered["ordering_syncs"] == [0x60]

    assert report["diagnostics"]["unknown_sync_count"] == 0
    assert report["summary"]["races"] == 1

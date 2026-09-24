"""Phase 2 memory-model discriminator (relaxed vs release/acquire atomics).

The HB certificate requires that every HB edge the model creates is honored by the
hardware. For an atomic release/acquire that means a RELAXED / unfenced atomic must NOT
synchronize surrounding non-atomic accesses -- otherwise the model hides a real race
(a false negative = unsound).

testdata/atomic_mm_handoff.cu is one kernel in two versions that differ in exactly one
thing, the flag atomics' memory order:
  handoff_strong  : release/acquire + __threadfence()  -> the data read IS PTX-ordered
                    after the data write        -> NORACE (sound control; must hold).
  handoff_relaxed : memory_order_relaxed, no fence     -> the data read is NOT PTX-ordered
                    -> a genuine race           -> the model MUST report a race.

FINDING (RTX 4060 Ti, sm_89, CUDA 13.2): on this toolchain BOTH the relaxed and the
release/acquire device-scope atomics disassemble to the identical opcode
`ATOM.E.{EXCH,ADD}.STRONG.GPU`; the ONLY SASS difference is that handoff_strong carries
`MEMBAR.SC.GPU` + `MEMBAR.ALL.GPU` fences that handoff_relaxed lacks. `.STRONG` is a
coherence-SCOPE marker, not a release/acquire-ordering marker. sync_dominance.atomic_scope
keys the synchronizing scope on `.STRONG.<scope>` alone, so it gives the RELAXED flag the
same GRID scope as the strong one, and the runtime HB model (oracle + engine) orders the
non-atomic data access in BOTH -> handoff_relaxed is reported NORACE = a false negative.

=> The model is currently UNSOUND on unfenced/relaxed atomics that publish non-atomic
   state. The relaxed-should-race assertion is therefore marked xfail(strict) so it (a)
   documents the known unsoundness and (b) turns into a FAILURE the moment a fix makes the
   race visible, prompting this xfail to be removed. See the Phase 2 report.

The sound control (handoff_strong -> norace) is a plain assertion and must always hold.
Uses the Python oracle (self-contained: no atomic-scope sidecar / YOSEMITE env needed);
builds on demand and skips if no GPU / nvcc, mirroring test_intersubwarp_readwrite.
"""
import json
import subprocess
from pathlib import Path

import pytest

import hb_oracle as ho
import sync_dominance as sd

_ROOT = Path(__file__).resolve().parents[1]
_SRC = Path(__file__).resolve().parent / "testdata" / "atomic_mm_handoff.cu"


def _artifacts():
    """(dots, {kernel_substr: trace}) built on demand; None if no source/GPU/build."""
    if not _SRC.is_file():
        return None
    work = _ROOT / "cuHadron" / "_mm_handoff"      # a gitignored scratch area
    work.mkdir(parents=True, exist_ok=True)
    binary = work / "mm.out"
    ext = work / "mm_extracted_cubins"

    def _collect():
        dots = sorted(ext.glob("*.dot"))
        deps = sorted(work.glob("dependency_mm*"))
        traces = sorted(deps[-1].glob("kernel_*.json")) if deps else []
        by_name = {}
        for t in traces:
            nm = json.loads(t.read_text())["kernel"]["kernel_name"]
            if "strong" in nm:
                by_name["strong"] = t
            elif "relaxed" in nm:
                by_name["relaxed"] = t
        return dots, by_name

    dots, by_name = _collect()
    if dots and {"strong", "relaxed"} <= by_name.keys():
        return dots, by_name

    build = subprocess.run(
        ["nvcc", "-arch=native", "-lineinfo", "--cudart", "shared",
         str(_SRC), "-o", str(binary)], cwd=work, capture_output=True)
    if build.returncode != 0 or not binary.exists():
        return None
    subprocess.run(["bash", str(_ROOT / "getall.sh"), str(binary.resolve())],
                   cwd=_ROOT, capture_output=True, timeout=600)
    dots, by_name = _collect()
    return (dots, by_name) if dots and {"strong", "relaxed"} <= by_name.keys() else None


def _oracle(dots, trace):
    for dot in dots:
        try:
            return ho.analyze(dot, trace)
        except sd.AlignmentError:
            continue
    raise AssertionError(f"no CFG aligns with {trace}")


def _data_races(report):
    # races on the contested non-atomic global g_data (RAW/WAR/WAW), not the flag atomics
    return [r for r in report["races"] if r["kind"] in ("RAW", "WAR", "WAW")]


def test_strong_handoff_is_norace():
    """SOUND control: a proper release/acquire + fence handoff must order the data read
    after the data write -> zero races. Must always hold."""
    art = _artifacts()
    if art is None:
        pytest.skip("no GPU / nvcc / source to build atomic_mm_handoff")
    dots, by = art
    report = _oracle(dots, by["strong"])
    assert report["summary"]["races"] == 0, \
        f"release/acquire handoff must be race-free, got {report['races']}"


@pytest.mark.xfail(strict=True, reason="KNOWN UNSOUND (Phase 2): .STRONG is a coherence-"
                   "scope marker present on relaxed atomics too; atomic_scope treats the "
                   "unfenced relaxed flag as synchronizing, hiding this real race. Remove "
                   "this xfail when the fence-aware scope fix lands.")
def test_relaxed_handoff_should_race():
    """A relaxed/unfenced atomic must NOT order the surrounding non-atomic access, so the
    data read genuinely races the data write. Currently the model reports norace (unsound)
    -> xfail. Flips to a failure (prompting xfail removal) once the model is fixed."""
    art = _artifacts()
    if art is None:
        pytest.skip("no GPU / nvcc / source to build atomic_mm_handoff")
    dots, by = art
    report = _oracle(dots, by["relaxed"])
    assert len(_data_races(report)) >= 1, \
        "relaxed handoff: data read is not PTX-ordered after the write and must race"

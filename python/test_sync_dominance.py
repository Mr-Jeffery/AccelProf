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

        # Barrier/syncwarp-only clock: the pairs (and conflict counts) it leaves
        # unordered decide latent vs barrier-ordered, so they must agree too.
        assert tj.get("hb_races_sync_only") == report["races_sync_only"], (
            f"{binary.name}/{trace.name}: hb_races_sync_only mismatch "
            f"engine={tj.get('hb_races_sync_only')} oracle={report['races_sync_only']}")

        # ... and so must the static analyzer's offline barrier-only pass (what the
        # trace-only mode uses in place of the engine's set).
        kern = sd.parse_dot(report["inputs"]["cfg_dot"])[report["kernel"]["mangled"]]
        ops = sd.HBGraph(*kern).pc_opcode
        rmw = {pc: s for pc, op in ops.items() if (s := sd.atomic_scope(op)) is not None}
        coh = {pc: s for pc, op in ops.items() if (s := sd.coherent_scope(op)) is not None}
        fast = sorted([a, b, n] for (a, b), n in sd.barrier_only_pairs(tj, rmw, coh).items())
        assert fast == report["races_sync_only"], f"{binary.name}/{trace.name}: offline pass"

        # Coherence profile Pi (Phase 3): the engine's per-address atomic-order hashes
        # must equal the oracle's (both use the same FNV-1a over (tid, atomic-index)).
        eng_pi = {int(a): v["hash"] for a, v in tj.get("coherence_profile", {}).items()}
        orc_pi = {int(a, 16): v["hash"] for a, v in report.get("coherence_profile", {}).items()}
        assert eng_pi == orc_pi, (
            f"{binary.name}/{trace.name}: coherence_profile mismatch "
            f"engine-only={ {a: h for a, h in eng_pi.items() if orc_pi.get(a) != h} } "
            f"oracle-only={ {a: h for a, h in orc_pi.items() if eng_pi.get(a) != h} }")


# PC-level false negative of the static leg by design (one release pc multiplexes two
# handshakes; only the address-keyed engine separates them) — not a trace-only target.
_TRACE_ONLY_KNOWN_FN = set()


@pytest.mark.parametrize("binary", _binaries(), ids=lambda p: p.name)
def test_scor_microbenchmark_trace_only(binary, tmp_path):
    """Trace-only mode = the same dump without the engine's keys (what
    YOSEMITE_HB_NO_ENGINE writes): static leg + offline barrier-only pass. It must keep
    the litmus verdicts — the barrier pass may only turn barrier-ordered pairs into
    ORDERED, never a fence/lock/atomic-omission race."""
    art = _artifacts(binary)
    if art is None:
        pytest.skip("corpus not generated (no GPU / accelprof unavailable)")
    dots, traces = art
    races = engine_races = 0
    for trace in traces:
        tj = json.loads(trace.read_text())
        for k in ("hb_races", "hb_races_sync_only", "coherence_profile"):
            tj.pop(k, None)
        stripped = tmp_path / trace.name
        stripped.write_text(json.dumps(tj))
        for dot in dots:
            try:
                races += sd.analyze(dot, stripped)["summary"]["races"]
                engine_races += sd.analyze(dot, trace)["summary"]["races"]
                break
            except sd.AlignmentError:
                continue
    if binary.name.startswith("norace_"):
        assert races == 0, f"trace-only false positive: {binary.name}"
    elif binary.name not in _TRACE_ONLY_KNOWN_FN:
        assert races >= 1, f"trace-only false negative: {binary.name} " \
                           f"(engine mode reports {engine_races})"


def test_write_after_unlock_is_event_candidate(tmp_path, monkeypatch):
    """ScoR race_interblock_none-lock_rtraw: block 0 writes data AFTER its unlock, block 1
    reads it under the lock. Asserted by roles, not pc offsets:
      * the racing pair has no dependency edge (the last-accessor shadow hides block 1's
        read behind block 0's own), so it must come from the event stream;
      * R3 must not order it — the write is past its thread's own release of the
        CAS-acquired lock (the hop direction is schedule-dependent);
      * engine mode classes it latent (this schedule's lock hand-off ordered it);
      * each half alone is not enough: either knob off -> the race is missed again."""
    binary = _BIN / "race_interblock_none-lock_rtraw"
    art = _artifacts(binary) if binary.exists() else None
    if art is None:
        pytest.skip("corpus not generated (no GPU / accelprof unavailable)")
    dots, traces = art
    for k in ("CUVEIN_EVENT_CANDIDATES", "CUVEIN_R3_PAST_RELEASE"):
        monkeypatch.delenv(k, raising=False)

    def both_modes(trace):
        tj = json.loads(trace.read_text())
        for k in ("hb_races", "hb_races_sync_only", "coherence_profile"):
            tj.pop(k, None)
        stripped = tmp_path / trace.name
        stripped.write_text(json.dumps(tj))
        return (("engine", trace), ("trace-only", stripped))

    for mode, trace in both_modes(traces[-1]):
        rep = sd.analyze(dots[0], trace)
        races = [v for v in rep["verdicts"] if v["verdict"] == "RACE"]
        assert len(races) == 1, f"{mode}: {races}"
        race = races[0]
        assert race["event_candidate"] and not race["edge_rescued"]
        assert race["race_type"] in ("WAR", "RAW") and race["space"] == "global"
        assert race["observed_distance"] == "grid" and race["hb_chain"] is None
        assert race["hb_class"] == ("latent" if mode == "engine" else None)
        edges = {frozenset((e["current_pc"], e.get("ancient_pc")))
                 for e in json.loads(Path(trace).read_text())["edges"]}
        assert frozenset((race["current_pc"], race["ancient_pc"])) not in edges
        # the lock-protected pairs stay ordered (R3 inside the critical section)
        assert all(v["verdict"] == "ORDERED" for v in rep["verdicts"] if v is not race)

        assert sd.analyze(dots[0], trace, event_candidates=False)["summary"]["races"] == 0
        monkeypatch.setenv("CUVEIN_R3_PAST_RELEASE", "0")
        assert sd.analyze(dots[0], trace)["summary"]["races"] == 0
        monkeypatch.delenv("CUVEIN_R3_PAST_RELEASE")


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

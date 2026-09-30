"""Corpus check for sync_dominance. Run: pytest python/test_sync_dominance.py

The ScoR corpus test drives every microbenchmark binary through getall.sh
(nvdisasm CFG + accelprof pc_dependency trace) and then sync_dominance.analyze.

Atomic coherence scope and the scoped happens-before closure are modelled, so
the suite is asserted in both directions:
  * `race_*`   -> at least one RACE  (a miss is a false negative = a real bug); since T10
                  the races between two strong accesses (_PTX_STRONG_RACES: volatile data)
                  are reported as unordered strong conflicts instead -- SC, no RACE
  * `norace_*` -> zero RACEs and zero SC (a hit is a false positive)
  * every binary -> pipeline aligns, no unknown sync opcodes
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import hb_modes
import hb_oracle as ho
import sync_dominance as sd

_ROOT = Path(__file__).resolve().parents[1]
_BIN = _ROOT / "ScoR/microbenchmarks/bin"
_ART = _ROOT / "ScoR/microbenchmarks/artifacts"   # getall.sh output, moved out of bin/
_LOG = _ART / "sync_dominance.log"

# T10 (D9): the ScoR races whose two accesses are both strong. ScoR's data is `volatile`,
# which lowers to LDG/STG.E.STRONG.SYS (PTX relaxed.sys): under the default strength policy
# (`token`) such an access is strong, so a race between two of them -- or between one and an
# atomic whose scope covers the other thread -- is an unordered strong conflict (hb_proof.tex
# Definition "Verdicts"), reported as SC and never as a RACE. ScoR labels it a race: its model
# (ScoRD) treats volatile data as ordinary data. Taken from the sources; independent of the
# schedule, since every conflicting access of these kernels is strong at a covering scope.
# The other two race_* kernels are scope races (a block-scope atomic or lock used across
# blocks) and keep a DR under every policy. Under a pre-T10 policy (generic: volatile weak)
# every race_* kernel reports a RACE.
_PTX_STRONG_RACES = {
    "race_interblock_blkfence_raw", "race_interblock_fence_rtraw",
    "race_interblock_lock-blkfence_waw", "race_interblock_lock-no-stf_waw",
    "race_interblock_lock-no-tf_waw", "race_interblock_none-atom_waw",
    "race_interblock_none-lock_rtraw", "race_interblock_none-lock_waw",
    "race_interwarp_blklock-no-stf_waw", "race_interwarp_blklock-no-tf_waw",
    "race_interwarp_dev-blklock-no-stf_waw", "race_interwarp_dev-blklock-no-tf_waw",
    "race_interwarp_none-atom_waw", "race_interwarp_none-blkatom_waw",
    "race_interwarp_none-blklock_waw", "race_interwarp_none-lock_waw",
}


# T12 (D11; design/instance_gate.md): the ScoR kernels labelled race-free that PTX section 8.7.1
# does not order. In each, the consumer spins on the flag with a RELAXED atomic
# (atomicExch/atomicAdd) and has no fence after the spin, so the hand-off has no acquire
# pattern and the instance gate adds no (ATOM) edge; the producer side is fenced. ScoR's model
# (ScoRD, HRF-indirect) orders them by the dependency on the spin. With volatile data the pair
# is morally strong (reported as SC, informational); hrd-indirect's data accesses are RMWs of
# block scope used across blocks, not morally strong, so its pairs are data races. Reported,
# footnoted in make_tables.py, never relabelled. Scalar-clock mode (R3: a flag hand-off needs
# no acquire fence -- ScoRD's reading) keeps them silent.
_PTX_UNFENCED_NORACE = {
    "norace_interblock_fence_raw": "spin atomicExch(&flag,0) without a fence before data[0]",
    "norace_interwarp_fence_raw": "spin atomicExch(&flag,0) without a fence before data[0]",
    "norace_interwarp_blkfence_raw": "spin atomicExch(&flag,0) without a fence before data[0]",
    "norace_interwarp-block_fence_hrf-indirect":
        "spins atomicAdd(&flag,0) without a fence before data[0]",
    "norace_interwarp-block_fence-atom_hrd-indirect":
        "spins atomicAdd(&flag,0) without a fence before the block-scope atomicExch on data[0]",
}


def _gate_is_instance():
    return sd.gate_mode() == "instance"


def _volatile_is_strong():
    """Is a volatile (address-spaced .STRONG) access strong under the active policy?"""
    return sd.strong_ldst_policy() in ("token", "all")


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

    races = sc = 0
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
            sc += report["summary"]["sc"]

    if binary.name.startswith("race_"):
        if _volatile_is_strong() and binary.name in _PTX_STRONG_RACES:
            # T10: reported, as an unordered strong conflict (a miss has sc == 0 as well)
            assert races == 0 and sc >= 1, (f"{binary.name}: expected the labelled race as SC "
                                            f"only, got {races} race(s) and {sc} SC")
        else:
            assert races >= 1, f"false negative: {binary.name} reported no race"
    elif _gate_is_instance() and binary.name in _PTX_UNFENCED_NORACE:
        # T12 (D11): unordered under PTX -- reported (DR or SC by class), not suppressed
        assert races + sc >= 1, (f"{binary.name}: PTX leaves it unordered "
                                 f"({_PTX_UNFENCED_NORACE[binary.name]}) and the instance "
                                 f"gate must report it")
    else:
        assert races == 0, f"false positive: {binary.name} reported {races} race(s)"
        assert sc == 0, f"{binary.name}: {sc} unordered strong conflict(s) on a race-free kernel"


def _race_key(r):
    # hb_races is aggregated per (pc pair, kind, class, space, distance, async) with a count
    # (T9); the example record's addr/tids depend on iteration order and are not compared
    return (r.get("a_pc"), r["b_pc"], r["kind"], r.get("class"), r["space"], r.get("dist"),
            r.get("async"), r.get("count"), r.get("a2_uncertain"))   # a2_uncertain: T14


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

        # ... and so must the static analyzer's offline barrier-only pass (what
        # scalar-clock mode uses in place of the engine's set).
        kern = sd.parse_dot(report["inputs"]["cfg_dot"])[report["kernel"]["mangled"]]
        ops = sd.HBGraph(*kern).pc_opcode
        rmw = {pc: s for pc, op in ops.items() if (s := sd.atomic_scope(op)) is not None}
        coh = {pc: s for pc, op in ops.items() if (s := sd.coherent_scope(op)) is not None}
        asy = sd.dump_async_pcs(sd.HBGraph(*kern), tj)
        fast = sorted([a, b, n] for (a, b), n in
                      sd.barrier_only_pairs(tj, rmw, coh, async_pc=asy).items())
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
# handshakes; only the address-keyed engine separates them) — not a scalar-clock target.
_SCALAR_CLOCK_KNOWN_FN = set()


@pytest.mark.parametrize("binary", _binaries(), ids=lambda p: p.name)
def test_scor_microbenchmark_scalar_clock(binary, tmp_path):
    """Scalar-clock mode = the same dump without the engine's keys (what
    YOSEMITE_HB_MODE=scalar-clock writes): static leg + offline barrier-only pass. It must keep
    the litmus verdicts — the barrier pass may only turn barrier-ordered pairs into
    ORDERED, never a fence/lock/atomic-omission race."""
    art = _artifacts(binary)
    if art is None:
        pytest.skip("corpus not generated (no GPU / accelprof unavailable)")
    dots, traces = art
    races = engine_races = sc = 0
    for trace in traces:
        tj = json.loads(trace.read_text())
        for k in ("hb_races", "hb_races_sync_only", "coherence_profile"):
            tj.pop(k, None)
        stripped = tmp_path / trace.name
        stripped.write_text(json.dumps(tj))
        for dot in dots:
            try:
                rep = sd.analyze(dot, stripped)
                races += rep["summary"]["races"]
                sc += rep["summary"]["sc"]
                engine_races += sd.analyze(dot, trace)["summary"]["races"]
                break
            except sd.AlignmentError:
                continue
    if binary.name.startswith("norace_"):
        assert races == 0, f"scalar-clock false positive: {binary.name}"
    elif _volatile_is_strong() and binary.name in _PTX_STRONG_RACES:
        # T10: the class is R2's here (both pcs strong at a covering scope): SC, no RACE
        assert races == 0 and sc >= 1, (f"scalar-clock: {binary.name}: expected SC only, got "
                                        f"{races} race(s) and {sc} SC")
    elif binary.name not in _SCALAR_CLOCK_KNOWN_FN:
        assert races >= 1, f"scalar-clock false negative: {binary.name} " \
                           f"(vector-clock mode reports {engine_races})"


def test_write_after_unlock_is_event_candidate(tmp_path, monkeypatch):
    """ScoR race_interblock_none-lock_rtraw: block 0 writes data AFTER its unlock, block 1
    reads it under the lock. Asserted by roles, not pc offsets:
      * the racing pair has no dependency edge (the last-accessor shadow hides block 1's
        read behind block 0's own), so it must come from the event stream;
      * R3 must not order it — the write is past its thread's own release of the
        CAS-acquired lock (the hop direction is schedule-dependent);
      * vector-clock mode classes it latent (this schedule's lock hand-off ordered it);
      * each half alone is not enough: either knob off -> the race is missed again.
    T10: the data is volatile, so under the default policy both accesses are strong and the
    pair is reported as an unordered strong conflict (SC; latent-sc / sc), not as a RACE."""
    binary = _BIN / "race_interblock_none-lock_rtraw"
    art = _artifacts(binary) if binary.exists() else None
    if art is None:
        pytest.skip("corpus not generated (no GPU / accelprof unavailable)")
    dots, traces = art
    for k in ("CUVEIN_EVENT_CANDIDATES", "CUVEIN_R3_PAST_RELEASE"):
        monkeypatch.delenv(k, raising=False)
    strong = _volatile_is_strong()
    want = "SC" if strong else "RACE"
    cls = {hb_modes.VECTOR_CLOCK: "latent-sc" if strong else "latent",
           hb_modes.SCALAR_CLOCK: "sc" if strong else None}
    reported = lambda rep: rep["summary"]["races"] + rep["summary"]["sc"]

    def both_modes(trace):
        tj = json.loads(trace.read_text())
        for k in ("hb_races", "hb_races_sync_only", "coherence_profile"):
            tj.pop(k, None)
        stripped = tmp_path / trace.name
        stripped.write_text(json.dumps(tj))
        return ((hb_modes.VECTOR_CLOCK, trace), (hb_modes.SCALAR_CLOCK, stripped))

    for mode, trace in both_modes(traces[-1]):
        rep = sd.analyze(dots[0], trace)
        races = [v for v in rep["verdicts"] if v["verdict"] in ("RACE", "SC")]
        assert len(races) == 1, f"{mode}: {races}"
        race = races[0]
        assert race["verdict"] == want, f"{mode}: {race['verdict']} (policy {sd.strong_ldst_policy()})"
        assert race["event_candidate"] and not race["edge_rescued"]
        assert race["race_type"] in ("WAR", "RAW") and race["space"] == "global"
        assert race["observed_distance"] == "grid" and race["hb_chain"] is None
        assert race["hb_class"] == cls[mode]
        edges = {frozenset((e["current_pc"], e.get("ancient_pc")))
                 for e in json.loads(Path(trace).read_text())["edges"]}
        assert frozenset((race["current_pc"], race["ancient_pc"])) not in edges
        # the lock-protected pairs stay ordered (R3 inside the critical section)
        assert all(v["verdict"] == "ORDERED" for v in rep["verdicts"] if v is not race)

        assert reported(sd.analyze(dots[0], trace, event_candidates=False)) == 0
        monkeypatch.setenv("CUVEIN_R3_PAST_RELEASE", "0")
        assert reported(sd.analyze(dots[0], trace)) == 0
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

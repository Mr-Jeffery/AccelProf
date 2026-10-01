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
T18: the verdict criterion is A2-aware (python/a2_aware.py). The collector records an atomic
at issue, so the lock litmus lands in a schedule the collector build decides, and an
RMW-window overlap there can add a report no label anticipates. The reports that are not
a2_uncertain must match the label; an extra report must carry a2_uncertain equal to its count.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import a2_aware
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

    races = sc = f_races = f_sc = 0            # unflagged / a2_uncertain, per verdict
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
            r, s_, fr, fs = a2_aware.counts(report)
            races += r; sc += s_; f_races += fr; f_sc += fs

    _check_label(binary.name, races, sc, f_races, f_sc)


def _check_label(name, races, sc, f_races, f_sc, mode="", scalar=False):
    """The A2-aware label criterion. races/sc count the unflagged reports, f_* the
    a2_uncertain ones (flag == count at the verdict level)."""
    tag = f"{mode}{name}"
    if name.startswith("race_"):
        if _volatile_is_strong() and name in _PTX_STRONG_RACES:
            # T10: reported as an unordered strong conflict, never an unflagged RACE; a miss
            # has no SC either. An extra a2_uncertain DR beside it is the A2 schedule.
            assert races == 0 and sc + f_sc >= 1, (
                f"{tag}: expected the labelled race as SC only, got {races} unflagged race(s), "
                f"{sc} unflagged SC, {f_races} flagged race(s), {f_sc} flagged SC")
        else:
            assert races + f_races >= 1, f"false negative: {tag} reported no race"
    elif scalar and name.startswith("norace_"):
        # scalar-clock mode keeps the T12 unfenced litmus silent (R3: ScoRD's reading) and
        # asserts no SC on race-free kernels, as before T18
        assert races == 0, f"scalar-clock false positive: {name} ({races} unflagged race(s))"
    elif _gate_is_instance() and name in _PTX_UNFENCED_NORACE:
        # T12 (D11): unordered under PTX -- reported (DR or SC by class), not suppressed
        assert races + sc + f_races + f_sc >= 1, (
            f"{tag}: PTX leaves it unordered ({_PTX_UNFENCED_NORACE[name]}) and the instance "
            f"gate must report it")
    else:
        # race-free: every report must be A2-uncertain (the flag equals the count)
        assert races == 0, f"false positive: {tag} reported {races} unflagged race(s)"
        assert sc == 0, (f"{tag}: {sc} unflagged strong conflict(s) on a race-free kernel "
                         f"({f_races} race(s), {f_sc} SC carry a2_uncertain)")


def _race_key(r):
    # hb_races is aggregated per (pc pair, kind, class, space, distance, async) with a count
    # (T9); the example record's addr/tids depend on iteration order and are not compared
    return (r.get("a_pc"), r["b_pc"], r["kind"], r.get("class"), r["space"], r.get("dist"),
            r.get("async"), r.get("count"), r.get("a2_uncertain"))   # a2_uncertain: T14


@pytest.mark.parametrize("binary", _binaries(), ids=lambda p: p.name)
def test_hb_clock_matches_specification(binary):
    """HbClock (hb_races in the trace) must equal the
    full vector-clock Python oracle (hb_oracle) on every corpus binary — the oracle is
    the executable correctness spec for HbClock (roadmap Phase 2)."""
    art = _artifacts(binary)
    if art is None:
        pytest.skip("corpus not generated (no GPU / accelprof unavailable)")
    dots, traces = art
    for trace in traces:
        tj = json.loads(trace.read_text())
        if "hb_events" not in tj:
            pytest.skip("trace has no hb_events (YOSEMITE_HB_TRACE was off)")
        hbc = sorted({_race_key(r) for r in tj.get("hb_races", [])})
        report = None
        for dot in dots:  # pick the cubin whose CFG holds this kernel
            try:
                report = ho.analyze(dot, trace)
                break
            except sd.AlignmentError:
                continue
        assert report is not None, f"no CFG aligns with {trace.name}"
        oracle = sorted({_race_key(r) for r in report["races"]})
        assert hbc == oracle, (
            f"{binary.name}/{trace.name}: "
            f"hb-clock-only={[k for k in hbc if k not in oracle]} "
            f"oracle-only={[k for k in oracle if k not in hbc]}")

        # Barrier/syncwarp-only clock: the pairs (and conflict counts) it leaves
        # unordered decide latent vs barrier-ordered, so they must agree too.
        assert tj.get("hb_races_sync_only") == report["races_sync_only"], (
            f"{binary.name}/{trace.name}: hb_races_sync_only mismatch "
            f"hb_clock={tj.get('hb_races_sync_only')} oracle={report['races_sync_only']}")

        # ... and so must the static analyzer's offline barrier-only pass (what
        # scalar-clock mode uses in place of HbClock's set).
        kern = sd.parse_dot(report["inputs"]["cfg_dot"])[report["kernel"]["mangled"]]
        ops = sd.HBGraph(*kern).pc_opcode
        rmw = {pc: s for pc, op in ops.items() if (s := sd.atomic_scope(op)) is not None}
        coh = {pc: s for pc, op in ops.items() if (s := sd.coherent_scope(op)) is not None}
        asy = sd.dump_async_pcs(sd.HBGraph(*kern), tj)
        fast = sorted([a, b, n] for (a, b), n in
                      sd.barrier_only_pairs(tj, rmw, coh, async_pc=asy).items())
        assert fast == report["races_sync_only"], f"{binary.name}/{trace.name}: offline pass"

        # Coherence profile Pi (Phase 3): HbClock's per-address atomic-order hashes
        # must equal the oracle's (both use the same FNV-1a over (tid, atomic-index)).
        eng_pi = {int(a): v["hash"] for a, v in tj.get("coherence_profile", {}).items()}
        orc_pi = {int(a, 16): v["hash"] for a, v in report.get("coherence_profile", {}).items()}
        assert eng_pi == orc_pi, (
            f"{binary.name}/{trace.name}: coherence_profile mismatch "
            f"hb-clock-only={ {a: h for a, h in eng_pi.items() if orc_pi.get(a) != h} } "
            f"oracle-only={ {a: h for a, h in orc_pi.items() if eng_pi.get(a) != h} }")


# PC-level false negative of the static leg by design (one release pc multiplexes two
# handshakes; only the address-keyed HbClock separates them) — not a scalar-clock target.
_SCALAR_CLOCK_KNOWN_FN = set()


@pytest.mark.parametrize("binary", _binaries(), ids=lambda p: p.name)
def test_scor_microbenchmark_scalar_clock(binary, tmp_path):
    """Scalar-clock mode = the same dump without HbClock's keys (what
    YOSEMITE_HB_MODE=scalar-clock writes): static leg + offline barrier-only pass. It must keep
    the litmus verdicts — the barrier pass may only turn barrier-ordered pairs into
    ORDERED, never a fence/lock/atomic-omission race."""
    art = _artifacts(binary)
    if art is None:
        pytest.skip("corpus not generated (no GPU / accelprof unavailable)")
    dots, traces = art
    races = vc_races = sc = f_races = f_sc = 0
    for trace in traces:
        tj = json.loads(trace.read_text())
        for k in ("hb_races", "hb_races_sync_only", "coherence_profile"):
            tj.pop(k, None)
        stripped = tmp_path / trace.name
        stripped.write_text(json.dumps(tj))
        for dot in dots:
            try:
                vrep = sd.analyze(dot, trace)
                rep = sd.analyze(dot, stripped)
                # T18: the a2_uncertain flag is a property of the trace's RMW windows; the
                # scalar-clock dump has no hb_races, so take it from the same trace's
                # vector-clock analysis
                r, s_, fr, fs = a2_aware.counts(rep, a2_aware.flagged_pairs(vrep))
                races += r; sc += s_; f_races += fr; f_sc += fs
                vc_races += vrep["summary"]["races"]
                break
            except sd.AlignmentError:
                continue
    if binary.name in _SCALAR_CLOCK_KNOWN_FN:
        return
    _check_label(binary.name, races, sc, f_races, f_sc, mode="scalar-clock: ", scalar=True)


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
    def unflagged(rep, flagged):
        # T18: reports that are not a2_uncertain (an A2 schedule may add flagged ones)
        r, s_, _, _ = a2_aware.counts(rep, flagged)
        return r + s_

    def both_modes(trace):
        tj = json.loads(trace.read_text())
        for k in ("hb_races", "hb_races_sync_only", "coherence_profile"):
            tj.pop(k, None)
        stripped = tmp_path / trace.name
        stripped.write_text(json.dumps(tj))
        return ((hb_modes.VECTOR_CLOCK, trace), (hb_modes.SCALAR_CLOCK, stripped))

    flagged = a2_aware.flagged_pairs(sd.analyze(dots[0], traces[-1]))
    for mode, trace in both_modes(traces[-1]):
        rep = sd.analyze(dots[0], trace)
        # the labelled race, by role: the event-stream WAR/RAW pair on global memory; every
        # other report must be a2_uncertain (flag == count), whatever schedule the collector
        # landed the lock in
        reps = [v for v in rep["verdicts"] if v["verdict"] in ("RACE", "SC")]
        races = [v for v in reps if v["event_candidate"] and v["race_type"] in ("WAR", "RAW")
                 and v["space"] == "global"]
        assert len(races) == 1, f"{mode}: {reps}"
        race = races[0]
        extra = [v for v in reps if v is not race]
        assert all(_pair_flagged(v, flagged) for v in extra), \
            f"{mode}: extra report(s) without a2_uncertain: " \
            f"{[(v['race_type'], v['verdict'], v['a2_uncertain']) for v in extra if not _pair_flagged(v, flagged)]}"
        assert race["verdict"] == want, f"{mode}: {race['verdict']} (policy {sd.strong_ldst_policy()})"
        assert race["event_candidate"] and not race["edge_rescued"]
        assert race["race_type"] in ("WAR", "RAW") and race["space"] == "global"
        assert race["observed_distance"] == "grid" and race["hb_chain"] is None
        assert race["hb_class"] == cls[mode]
        edges = {frozenset((e["current_pc"], e.get("ancient_pc")))
                 for e in json.loads(Path(trace).read_text())["edges"]}
        assert frozenset((race["current_pc"], race["ancient_pc"])) not in edges
        # the lock-protected pairs stay ordered (R3 inside the critical section)
        assert all(v["verdict"] == "ORDERED" or v in extra
                   for v in rep["verdicts"] if v is not race)

        assert unflagged(sd.analyze(dots[0], trace, event_candidates=False), flagged) == 0
        monkeypatch.setenv("CUVEIN_R3_PAST_RELEASE", "0")
        assert unflagged(sd.analyze(dots[0], trace), flagged) == 0
        monkeypatch.delenv("CUVEIN_R3_PAST_RELEASE")


def _pair_flagged(v, flagged):
    return v.get("a2_uncertain") is True or frozenset((v["current_pc"], v["ancient_pc"])) in flagged


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

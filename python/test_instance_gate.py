"""T12: the instance gate (hb_proof.tex Definition "Gate"; design/instance_gate.md).

Unit tests of sync_dominance.HBGraph.fenced / gate_table on hand-built CFGs (no GPU), and on
the ScoR litmus corpus (built by the green set's getall.sh runs; skipped without it): the
oracle's DEFERRED acquire equals Detect(T, vec) with the gate evaluated directly (look-ahead),
and the sidecar's gate lines are the oracle's table.
"""
import itertools
import json
import sys
from pathlib import Path

import pytest

import atomic_scope_sidecar
import hb_oracle as ho
import sync_dominance as sd

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "design"))


def _ins(pc, op, pred=False):
    i = sd._Ins((pc, op))
    if pred:
        i.pred = True
    return i


def _graph(blocks, edges):
    return sd.HBGraph({b: [_ins(*x) for x in ins] for b, ins in blocks.items()}, edges,
                      next(iter(blocks)))


def _lock(fence_ok=True, fence_rel=True, pred=False):
    """do { if (CAS(lock,0,1) == 0) { fence; x = ...; fence; EXCH(lock,0); done } } while (!done)
    -- the success-edge idiom: the acquire fence is on the success branch only."""
    return _graph({
        "B0": [(0x10, "ATOMG.E.CAS.STRONG.GPU"), (0x20, "ISETP.NE.AND"), (0x30, "BRA")],
        "B1": ([(0x40, "MEMBAR.SC.GPU", pred), (0x50, "CCTL.IVALL", pred)] if fence_ok else [])
              + [(0x60, "LDG.E"), (0x70, "STG.E")]
              + ([(0x80, "MEMBAR.SC.GPU")] if fence_rel else [])
              + [(0x90, "ATOMG.E.EXCH.STRONG.GPU"), (0xa0, "EXIT")],
        "B2": [(0xb0, "BRA")],
    }, [("B0", "B1"), ("B0", "B2"), ("B2", "B0")])


def test_success_edge_fence_acquires():
    g = _lock()
    assert g.fenced(0x10, 0x60, sd.GRID, "acq")        # successful CAS -> protected load
    assert not g.fenced(0x10, 0x10, sd.GRID, "acq")    # a failed CAS acquires nothing
    assert g.fenced(0x70, 0x90, sd.GRID, "rel")        # store -> fence -> unlock
    assert not g.fenced(0x90, 0xa0, sd.GRID, "acq")    # nothing after the unlock


def test_missing_fences():
    assert not _lock(fence_ok=False).fenced(0x10, 0x60, sd.GRID, "acq")
    assert not _lock(fence_rel=False).fenced(0x70, 0x90, sd.GRID, "rel")


def test_guarded_fence_does_not_count():
    assert not _lock(pred=True).fenced(0x10, 0x60, sd.GRID, "acq")


def test_inventory_sides_and_scopes():
    assert sd.fence_scope("MEMBAR.SC.CTA", "rel") == sd.BLOCK
    assert sd.fence_scope("MEMBAR.ALL.GPU", "acq") == sd.GRID
    assert sd.fence_scope("MEMBAR.SC.SYS", "rel") == sd.GRID
    assert sd.fence_scope("CCTL.IVALL", "acq") == sd.GRID
    assert sd.fence_scope("CCTL.IVALL", "rel") == sd.NONE          # acquire side only
    assert sd.fence_scope("BAR.SYNC.DEFER_BLOCKING", "rel") == sd.BLOCK
    assert sd.fence_scope("ERRBAR", "rel") == sd.NONE
    assert sd.fence_scope("WARPSYNC", "acq") == sd.NONE
    # a cta fence is not enough for a gpu-scope RMW
    g = _graph({"B0": [(0x10, "STG.E"), (0x20, "MEMBAR.SC.CTA"),
                       (0x30, "ATOMG.E.EXCH.STRONG.GPU"), (0x40, "EXIT")]}, [])
    assert g.fenced(0x10, 0x30, sd.BLOCK, "rel") and not g.fenced(0x10, 0x30, sd.GRID, "rel")


def test_barrier_endpoint_counts_at_cta_scope():
    g = _graph({"B0": [(0x10, "BAR.SYNC.DEFER_BLOCKING"), (0x20, "ATOMS.CAS"),
                       (0x30, "BAR.SYNC.DEFER_BLOCKING"), (0x40, "EXIT")]}, [])
    assert g.fenced(0x10, 0x20, sd.BLOCK, "rel")         # previous record = the barrier
    assert g.fenced(0x20, 0x30, sd.BLOCK, "acq")         # next record = the barrier
    assert not g.fenced(0x10, 0x20, sd.GRID, "rel")
    assert not g.fenced(0x99, 0x20, sd.BLOCK, "rel")     # an unknown pc is unfenced


def test_gate_table_equals_fenced():
    for g in (_lock(), _lock(fence_ok=False), _lock(fence_rel=False), _lock(pred=True)):
        dom = g.record_pcs()
        for r, (s, rel, acq) in g.gate_table().items():
            for p in dom:
                assert (p in rel) == g.fenced(p, r, s, "rel"), (hex(r), hex(p))
                assert (p in acq) == g.fenced(r, p, s, "acq"), (hex(r), hex(p))


def _scor():
    art = _ROOT / "ScoR/microbenchmarks/artifacts"
    return sorted(p for p in art.iterdir() if p.is_dir()) if art.is_dir() else []


@pytest.mark.parametrize("d", _scor(), ids=lambda p: p.name)
def test_deferred_acquire_equals_direct_gate(d):
    """Detect(T, vec) with rel/acq read off the trace (look-ahead) == the oracle, which defers
    the acquire to the thread's next record as HbClock must (hb_proof.tex section 3)."""
    import algorithms_check as ac
    dots = sorted(d.glob("**/*.dot"))
    traces = sorted(d.glob("dependency_*/kernel_*.json"))
    if not dots or not traces:
        pytest.skip("litmus not generated")
    for tr in traces:
        r = ac.check(dots, tr, gate="instance")
        assert r["vec_equal"] and r["sync_equal"] and not r["code_not_ref"], (tr, r)


@pytest.mark.parametrize("d", _scor()[:6], ids=lambda p: p.name)
def test_sidecar_gate_lines_are_the_oracle_table(d, tmp_path):
    dots = sorted(d.glob("**/*.dot"))
    if not dots:
        pytest.skip("litmus not generated")
    out = tmp_path / "scope.txt"
    atomic_scope_sidecar.main([*map(str, dots), "-o", str(out), "--gate", "instance"])
    lines = [ln.split() for ln in out.read_text().splitlines() if ln.startswith("# gate ")]
    got = {(int(x[2]), x[3], x[4]): {int(p) for p in x[5:]} for x in lines}
    for dot in dots:
        for mangled, kern in sd.parse_dot(dot).items():
            key = atomic_scope_sidecar.kernel_key(mangled)
            for r, (s, rel, acq) in sd.HBGraph(*kern).gate_table().items():
                if s > sd.NONE:
                    assert got[(r, "rel", key)] == set(rel)
                    assert got[(r, "acq", key)] == set(acq)


# ---- R3 (hb_proof.tex section 5, as amended by T12): hand-built lock and flag CFGs -----------
# One lock kernel whose pcs every thread shares:
#   0x10 x = ... ; [0x20 fence] ; do { 0x30 CAS(lock) } while (fail) ; 0x50 fence ; 0x60 CCTL ;
#   0x70 read x ; 0x80 write x ; 0x90 fence ; 0xa0 EXCH(lock, 0) (unlock) ; 0xb0 write x ; exit
# The trace facts R3 reads are given by hand: the observed atomic hops, the atomics seen on one
# location, and each access's PO-next / PO-previous RMW over its observed instances.

def _r3_lock(fence_before_lock=True, hops=((0xa0, 0x30), (0x30, 0x30)), rp=None, ap=None):
    g = _graph({
        "B0": [(0x10, "STG.E")] + ([(0x20, "MEMBAR.SC.GPU")] if fence_before_lock else []),
        "B1": [(0x30, "ATOMG.E.CAS.STRONG.GPU"), (0x38, "ISETP.NE.AND"), (0x3c, "BRA")],
        "B2": [(0x50, "MEMBAR.SC.GPU"), (0x60, "CCTL.IVALL"), (0x70, "LDG.E"), (0x80, "STG.E"),
               (0x90, "MEMBAR.SC.GPU"), (0xa0, "ATOMG.E.EXCH.STRONG.GPU"), (0xb0, "STG.E"),
               (0xc0, "EXIT")],
    }, [("B0", "B1"), ("B1", "B1"), ("B1", "B2")])
    atom = {0x30: sd.GRID, 0xa0: sd.GRID}
    g.attach_trace(atom, [(a, b, sd.GRID) for a, b in hops], atom,
                   {frozenset((0x30, 0xa0)), frozenset((0x30,))},
                   rp if rp is not None else {0x10: frozenset({0x30}), 0x70: frozenset({0xa0}),
                                             0x80: frozenset({0xa0}), 0xb0: frozenset()},
                   ap if ap is not None else {0x10: frozenset(), 0x70: frozenset({0x30}),
                                             0x80: frozenset({0x30}), 0xb0: frozenset({0xa0})})
    return g


def test_r3_certifies_the_lock_hand_off():
    """x written in one thread's section, read in the next owner's: release at the unlock
    (fenced), hop unlock -> the next owner's CAS, which is the read's PO-previous RMW."""
    assert _r3_lock().chain(0x80, 0x70) == [0xa0, 0x30]


def test_r3_declines_write_before_lock(monkeypatch):
    """x = ...; lock; ... in one thread against a read inside another thread's section: the
    observed order (writer locked first) is schedule-dependent. Without a fence before the
    lock there is no release point; with one, the first hop leaves from the CAS the writer
    executes after x (or from its unlock, on the CAS's location): _before_acquire."""
    assert _r3_lock(fence_before_lock=False).chain(0x10, 0x70) is None     # no release fence
    g = _r3_lock(fence_before_lock=True)
    assert g.chain(0x10, 0x70) is None and g.chain(0x70, 0x10) is None
    monkeypatch.setenv("CUVEIN_R3_BEFORE_ACQUIRE", "0")                    # the decline matters
    assert g.chain(0x10, 0x70) is not None


def test_r3_declines_rtraw(monkeypatch):
    """lock; read x; unlock in one thread, lock; ...; unlock; x = ... in the other (the ScoR
    rtraw kernel): the write after the unlock has no release point, and from the read the
    chain lands on the writer's unlock -- its PO-previous RMW -- past the release."""
    g = _r3_lock()
    assert g.chain(0x70, 0xb0) is None and g.chain(0xb0, 0x70) is None
    monkeypatch.setenv("CUVEIN_R3_PAST_RELEASE", "0")
    assert g.chain(0x70, 0xb0) is not None                                 # the decline matters


def test_r3_declines_rtraw_with_many_threads():
    """With many threads on the same pcs the aggregated edges also hold a failed CAS -> another
    thread's unlock hop, so the chain can land DIRECTLY on the writer's unlock (a non-CAS RMW
    on the CAS's location). Before T12, _past_release ignored a non-CAS landing and R3
    certified this race."""
    g = _r3_lock(hops=((0xa0, 0x30), (0x30, 0x30), (0x30, 0xa0)))
    assert g.chain(0x70, 0xb0) is None


def test_r3_certifies_a_fenced_flag_hand_off():
    """data = ...; fence; EXCH(flag, 1) / while (EXCH(flag, 0) == 0); CCTL; read data: a
    location no CAS touches is a dataflow hand-off -- the spin's landing is no release."""
    g = _graph({
        "P": [(0x100, "STG.E"), (0x110, "MEMBAR.SC.GPU"), (0x120, "ATOMG.E.EXCH.STRONG.GPU"),
              (0x128, "EXIT")],
        "C0": [(0x130, "ATOMG.E.EXCH.STRONG.GPU"), (0x138, "BRA")],
        "C1": [(0x140, "CCTL.IVALL"), (0x150, "LDG.E"), (0x160, "EXIT")],
    }, [("P", "C0"), ("C0", "C0"), ("C0", "C1")])
    atom = {0x120: sd.GRID, 0x130: sd.GRID}
    g.attach_trace(atom, [(0x120, 0x130, sd.GRID)], atom, {frozenset((0x120, 0x130))},
                   {0x100: frozenset({0x120})}, {0x150: frozenset({0x130})})
    assert g.chain(0x100, 0x150) == [0x120, 0x130]


def test_r1_certifies_no_same_pc_pair(monkeypatch):
    """R1 (hb_proof.tex section 5): every path between the two regions crosses a barrier -- for
    one region the empty path crosses none. The code's former cycle form (a barrier on every
    cycle through the pc's region) orders instances in different iterations only, not two
    threads in one barrier segment (P4 uts-norace-small)."""
    g = _graph({"L": [(0x10, "STG.E"), (0x20, "BAR.SYNC.DEFER_BLOCKING"), (0x30, "BRA")],
                "X": [(0x40, "EXIT")]}, [("L", "L"), ("L", "X")])
    assert g.ordered(0x10, 0x10, sd.BLOCK, False, False)["strength"] == sd.NONE
    monkeypatch.setenv("CUVEIN_R1_LOOP_SCOPE", "1")                        # the former form
    assert g.ordered(0x10, 0x10, sd.BLOCK, False, False)["strength"] == sd.BLOCK


def test_model_bug_is_an_annotation():
    """A pair R1 orders and hb_races saw racing keeps its class's verdict: SC -> Strong
    conflict, DR -> Race; the annotation is judge()'s model_bug field."""
    assert sd._hb_class(True, False, True, True, strong=True) == "sc"
    assert sd._hb_class(True, False, True, True, strong=False) == "structural"
    assert sd.CLASS_VERDICT["sc"] == "SC" and sd.CLASS_VERDICT["structural"] == "RACE"


def test_dump_gate(monkeypatch):
    """A dump without `hb_gate` (every pre-T12 dump) replays under the trusting gate unless
    told otherwise; HbClock's marker selects the gate otherwise; an explicit arg wins."""
    monkeypatch.delenv("CUVEIN_GATE", raising=False)
    assert sd.dump_gate({}) == "trusting"
    assert sd.dump_gate({"hb_gate": "instance"}) == "instance"
    assert sd.dump_gate({"hb_gate": "instance"}, "trusting") == "trusting"
    monkeypatch.setenv("CUVEIN_GATE", "instance")
    assert sd.dump_gate({}) == "instance"


# ---- GPU: HbClock's deferred acquire (testdata/gate_held.cu) ----------------------------
_HELD_SRC = Path(__file__).resolve().parent / "testdata" / "gate_held.cu"


def _held_artifacts():
    """(dots, {"fenced"|"unfenced": trace}) built on demand; None without nvcc / a GPU."""
    import shutil
    import subprocess
    work = _ROOT / "cuHadron" / "_gate_held"          # a gitignored scratch area
    work.mkdir(parents=True, exist_ok=True)
    binary = work / "gate_held.out"

    def collect():
        dots = sorted((work / "gate_held_extracted_cubins").glob("*.dot"))
        deps = sorted(work.glob("dependency_gate_held*"))
        by = {}
        for t in (sorted(deps[-1].glob("kernel_*.json")) if deps else []):
            nm = json.loads(t.read_text())["kernel"]["kernel_name"]
            by["unfenced" if "unfenced" in nm else "fenced"] = t
        return dots, by

    dots, by = collect()
    if dots and {"fenced", "unfenced"} <= by.keys() and \
            binary.stat().st_mtime >= _HELD_SRC.stat().st_mtime:
        return dots, by
    if shutil.which("nvcc") is None:
        return None
    b = subprocess.run(["nvcc", "-arch=native", "-lineinfo", "--cudart", "shared",
                        str(_HELD_SRC), "-o", str(binary)], cwd=work, capture_output=True)
    if b.returncode != 0:
        return None
    subprocess.run(["bash", str(_ROOT / "getall.sh"), str(binary.resolve())],
                   cwd=_ROOT, capture_output=True, timeout=600)
    dots, by = collect()
    return (dots, by) if dots and {"fenced", "unfenced"} <= by.keys() else None


def _key(r):
    return (r.get("a_pc"), r["b_pc"], r["kind"], r.get("class"), r["space"], r.get("dist"),
            r.get("async"), r.get("count"), r.get("a2_uncertain"))


@pytest.mark.parametrize("variant", ["fenced", "unfenced"])
def test_held_conflict_hb_clock_matches_specification(variant):
    """The CAS thread's Check finds thread 0's plain store of the lock word ordered only by the
    pending acquire: held, then dropped (a fence after the CAS: acq = 1) or reported (none:
    acq = 0). HbClock (hb_races, recorded under the instance gate) equals the oracle."""
    art = _held_artifacts()
    if art is None:
        pytest.skip("no GPU / nvcc / accelprof to build and trace gate_held")
    dots, by = art
    tj = json.loads(by[variant].read_text())
    assert tj.get("hb_gate") == "instance", "the dump was not recorded under the instance gate"
    rep = None
    for dot in dots:
        try:
            rep = ho.analyze(dot, by[variant])
            break
        except sd.AlignmentError:
            continue
    assert rep is not None
    assert sorted(map(_key, tj["hb_races"])) == sorted(map(_key, rep["races"]))
    g = rep["summary"]["gate"]
    assert g.get("held", 0) >= 1, g                   # the path under test was taken
    kern = sd.parse_dot(rep["inputs"]["cfg_dot"])[rep["kernel"]["mangled"]]
    ops = sd.HBGraph(*kern).pc_opcode
    cas = [r for r in rep["races"] if "CAS" in ops[r["b_pc"]].split(".")
           and ops[r["a_pc"]].split(".")[0] in ("ST", "STG")]
    if variant == "fenced":
        assert g.get("held_reported", 0) == 0 and not cas, (g, cas)
    else:
        assert g.get("held_reported", 0) >= 1 and cas, (g, rep["races"])


# ---- GPU: R3's write-before-lock decline on a real trace (testdata/write_before_lock.cu) ------

def _t12_trace(name):
    """(dots, [kernel JSON]) of testdata/<name>.cu, built and traced once (vector-clock mode),
    cached in cuHadron/_t12_<name>; None without nvcc / a GPU."""
    import shutil
    import subprocess
    src = Path(__file__).resolve().parent / "testdata" / f"{name}.cu"
    work = _ROOT / "cuHadron" / f"_t12_{name}"
    work.mkdir(parents=True, exist_ok=True)
    binary = work / name

    def collect():
        dots = sorted((work / f"{name}_extracted_cubins").glob("*.dot"))
        deps = sorted(work.glob(f"dependency_{name}*"))
        return dots, (sorted(deps[-1].glob("kernel_*.json")) if deps else [])

    dots, traces = collect()
    if dots and traces and binary.stat().st_mtime >= src.stat().st_mtime:
        return dots, traces
    if shutil.which("nvcc") is None:
        return None
    b = subprocess.run(["nvcc", "-arch=native", "-lineinfo", "--cudart", "shared", str(src),
                        "-o", str(binary)], cwd=work, capture_output=True)
    if b.returncode != 0:
        return None
    subprocess.run(["bash", str(_ROOT / "getall.sh"), str(binary.resolve())], cwd=_ROOT,
                   capture_output=True, timeout=600)
    dots, traces = collect()
    return (dots, traces) if dots and traces else None


def _pair_verdicts(dots, trace, pcs):
    for dot in dots:
        try:
            rep = sd.analyze(dot, trace)
            break
        except sd.AlignmentError:
            continue
    else:
        raise AssertionError("no CFG aligns")
    return [v for v in rep["verdicts"] if {v["current_pc"], v["ancient_pc"]} == set(pcs)]


def test_r3_declines_write_before_lock_on_a_real_trace(monkeypatch, tmp_path):
    art = _t12_trace("write_before_lock")
    if art is None:
        pytest.skip("no GPU / nvcc / accelprof to build and trace write_before_lock")
    dots, traces = art
    t = json.loads(traces[0].read_text())
    mem = [e for e in sorted(t["hb_events"], key=lambda e: e["seq"]) if "lanes" in e]
    for dot in dots:                                        # the cubin that holds the kernel
        kern = sd.parse_dot(dot)
        try:
            g = sd.HBGraph(*kern[sd.select_kernel(kern, t["kernel"]["kernel_name"])])
            break
        except sd.AlignmentError:
            continue
    else:
        raise AssertionError("no CFG aligns")
    rmw = {pc for pc, op in g.pc_opcode.items() if sd.atomic_scope(op) is not None}
    b0 = [e for e in mem if e["block"] == 0]
    b1 = [e for e in mem if e["block"] == 1]
    if max(e["seq"] for e in b0 if e["pc"] in rmw) > min(e["seq"] for e in b1 if e["pc"] in rmw):
        pytest.skip("schedule not reached: block 1 touched the lock before block 0 was done")
    write = next(e for e in b0 if e["pc"] not in rmw)
    read = next(e for e in b1 if e["type"] == "read" and e["pc"] not in rmw
                and e["lanes"][0]["addr"] == write["lanes"][0]["addr"])
    pair = (write["pc"], read["pc"])
    for r in ho.analyze(dot, traces[0])["races"]:          # ordered in this run: no report
        assert {r["a_pc"], r["b_pc"]} != set(pair), r
    sc = tmp_path / "scalar.json"                           # the scalar-clock view of the dump
    sc.write_text(json.dumps({k: v for k, v in t.items()
                              if k not in ("hb_races", "hb_races_sync_only", "coherence_profile")}))
    vv, vs = _pair_verdicts(dots, traces[0], pair), _pair_verdicts(dots, sc, pair)
    assert vv and all(v["hb_chain"] is None and v["hb_class"] == "latent" for v in vv), vv
    assert vs and all(v["hb_chain"] is None and v["verdict"] == "RACE" for v in vs), vs
    monkeypatch.setenv("CUVEIN_R3_BEFORE_ACQUIRE", "0")    # without the decline R3 certifies it
    assert all(v["verdict"] == "ORDERED" and v["hb_chain"] for v in
               _pair_verdicts(dots, traces[0], pair) + _pair_verdicts(dots, sc, pair))

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
    the acquire to the thread's next record as HbEngine must (hb_proof.tex section 3)."""
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


def test_dump_gate(monkeypatch):
    """A dump without `hb_gate` (every pre-T12 dump) replays under the trusting gate unless
    told otherwise; the engine's marker selects the gate otherwise; an explicit arg wins."""
    monkeypatch.delenv("CUVEIN_GATE", raising=False)
    assert sd.dump_gate({}) == "trusting"
    assert sd.dump_gate({"hb_gate": "instance"}) == "instance"
    assert sd.dump_gate({"hb_gate": "instance"}, "trusting") == "trusting"
    monkeypatch.setenv("CUVEIN_GATE", "instance")
    assert sd.dump_gate({}) == "instance"


# ---- GPU: the engine's deferred acquire (testdata/gate_held.cu) ----------------------------
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
def test_held_conflict_engine_matches_oracle(variant):
    """The CAS thread's Check finds thread 0's plain store of the lock word ordered only by the
    pending acquire: held, then dropped (a fence after the CAS: acq = 1) or reported (none:
    acq = 0). The engine (hb_races, recorded under the instance gate) equals the oracle."""
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

"""R1 (barrier dominance) is judged at the widest distance of the pair, not at the distance its
trace edges happen to record (M2, eval/MODEL_BUG_PAIRS.md on study/model-bug-pairs).

A trace edge keeps only the LAST accessor of a location, so a pair can have every edge inside one
block while two of its instances conflict across blocks with an access in between. A block barrier
between the two pcs covers the block distance and orders nothing across blocks. Found on three
production kernels (CUB top-k, RAFT select_k, Kokkos ParallelReduce): strength block, observed
block, the unordered instance grid/global; scalar-clock mode said ORDERED (R1 first), vector-clock
mode said RACE with the model_bug annotation.

After the fix R1 certifies a pair only if its strength covers
  max(edge distance, widest hb_races instance, widest barrier-pass instance),
in both modes. $CUVEIN_R1_OBSERVED_ONLY=1 restores the old rule (ablation).

Synthetic kernel, CPU only:  0x10 STG (W) ; 0x20 BAR.SYNC ; 0x30 LDG (R), one edge R<-W at block
distance.
    .env/bin/python -m pytest python/test_r1_distance.py -q
"""
import json
from pathlib import Path

import pytest

import sync_dominance as sd

NONE, WARP, BLOCK, GRID = sd.NONE, sd.WARP, sd.BLOCK, sd.GRID
W, BAR, R = 0x10, 0x20, 0x30
T_B0, T_B0W1, T_B1 = 0, 1 << 5, 1 << 10          # block 0 warp 0 / block 0 warp 1 / block 1


@pytest.fixture(autouse=True)
def _no_env(monkeypatch):
    for k in ("CUVEIN_R1_OBSERVED_ONLY", "CUVEIN_CHAIN_CLOSURE", "CUVEIN_PREFER_RECORDS"):
        monkeypatch.delenv(k, raising=False)


def _dot():
    bs = "\\"

    def esc(t):
        return t.replace(" ", bs + " ").replace("[", bs + "[").replace("]", bs + "]")
    ops = {W: "STG.E [R4.64], R2", BAR: "BAR.SYNC.DEFER_BLOCKING 0x0", R: "LDG.E R2, [R4.64]"}
    last = R + 0x10
    lines = [f"{pc:04x}:{bs} {bs} {bs} {esc(ops.get(pc, 'NOP'))}{bs} ;{bs}l"
             for pc in range(0, last, 0x10)]
    m = "_Z5ktestv"
    head = (f"<entry>\t.global\t\t{m}{bs}l\t.type\t\t{m},@function{bs}l"
            f"\t.size\t\t{m},(.L_x_1{bs} -{bs} {m}){bs}l\t.other\t\t{m},{bs}<no{bs} object{bs}>{bs}l"
            f"{m}:{bs}l.text.{m}:{bs}l")
    tail = f"|<exit0>{last:04x}:{bs} {bs} {bs} EXIT{bs} ;{bs}l"
    return ('digraph f {\nsubgraph "cluster_' + m + '" {\n'
            'node [fontname="Courier",fontsize=10,shape=Mrecord];\n"' + m + '"\n[label="{'
            + head + "".join(lines) + tail + '}"]\n}\n}\n')


def _trace(**hb):
    t = {"tool": "pc_dependency_analysis",
         "kernel": {"kernel_id": 0, "kernel_name": "ktest()", "device_id": 0, "kernel_pc": 0,
                    "grid_dim": [2, 1, 1], "block_dim": [64, 1, 1]},
         "nodes": [{"pc": W, "flags": "WRITE GLOBAL"}, {"pc": R, "flags": "READ GLOBAL"}],
         "edges": [{"current_pc": R, "ancient_pc": W, "cold_miss": False,
                    "current_access_size": 4, "dist": {"intra_block": 1}}]}
    t.update(hb)
    return t


def _race(a_tid, b_tid):
    return {"a_pc": W, "b_pc": R, "a_tid": a_tid, "b_tid": b_tid, "kind": "RAW",
            "class": "DR", "space": "global", "count": 1}


def _verdict(tmp_path, name, **hb):
    d = Path(tmp_path) / name
    d.mkdir()
    (d / "k.dot").write_text(_dot())
    (d / "kernel_0.json").write_text(json.dumps(_trace(**hb)))
    rep = sd.analyze(str(d / "k.dot"), str(d / "kernel_0.json"))
    vs = [v for v in rep["verdicts"] if {v["current_pc"], v["ancient_pc"]} == {W, R}]
    assert len(vs) == 1, rep["verdicts"]
    return vs[0]


def _sync_pass(dist):
    return {"hb_sync_pass": [[W, R, 1, dist, W, R]], "hb_rmw_points": {}, "hb_events_count": 4,
            "hb_lanes_count": 4}


# ---------------------------------------------------------------- the barrier does certify
def test_no_dynamic_evidence_is_ordered_by_r1(tmp_path):
    v = _verdict(tmp_path, "static")
    assert (v["verdict"], v["strength"], v["observed_distance"]) == ("ORDERED", "block", "block")


def test_scalar_clock_all_instances_ordered(tmp_path):
    v = _verdict(tmp_path, "sc-clean", hb_sync_pass=[], hb_rmw_points={}, hb_events_count=4,
                 hb_lanes_count=4)
    assert v["verdict"] == "ORDERED"


# ---------------------------------------------------------------- the M2 pairs
def test_scalar_clock_reports_a_grid_instance_past_a_block_barrier(tmp_path):
    """Scalar-clock recording: the barrier pass left an instance unordered at grid distance."""
    v = _verdict(tmp_path, "sc-grid", **_sync_pass(GRID))
    assert v["verdict"] == "RACE", v


def test_vector_clock_reports_it_without_model_bug(tmp_path):
    """Vector-clock recording of the same run: reported before the fix too, but annotated as a
    defect of R1; R1 never covered the grid instance, so it is no model_bug."""
    v = _verdict(tmp_path, "vc-grid", hb_races=[_race(T_B0, T_B1)],
                 hb_races_sync_only=[[W, R, 1]], **_sync_pass(GRID))
    assert v["verdict"] == "RACE" and v["hb_class"] == "structural", v
    assert not v["model_bug"], v


def test_vector_clock_marks_a_handoff_ordered_grid_instance_latent(tmp_path):
    """No hb_races instance (the full clock ordered it in this run), the barrier pass has it at
    grid distance: nothing proves the order for every schedule, so Latent, not Ordered by R1."""
    v = _verdict(tmp_path, "vc-latent", hb_races=[], hb_races_sync_only=[[W, R, 1]],
                 **_sync_pass(GRID))
    assert v["hb_class"] == "latent" and v["verdict"] == "RACE", v


# ---------------------------------------------------------------- model_bug stays a defect detector
def test_model_bug_kept_when_the_race_is_within_r1_distance(tmp_path):
    """An unordered instance at block distance contradicts a block barrier: still a model_bug."""
    v = _verdict(tmp_path, "vc-block", hb_races=[_race(T_B0, T_B0W1)],
                 hb_races_sync_only=[[W, R, 1]], **_sync_pass(BLOCK))
    assert v["verdict"] == "RACE" and v["model_bug"], v


def test_ablation_restores_the_old_rule(tmp_path, monkeypatch):
    monkeypatch.setenv("CUVEIN_R1_OBSERVED_ONLY", "1")
    v = _verdict(tmp_path, "sc-grid-old", **_sync_pass(GRID))
    assert v["verdict"] == "ORDERED", v
    v = _verdict(tmp_path, "vc-grid-old", hb_races=[_race(T_B0, T_B1)],
                 hb_races_sync_only=[[W, R, 1]], **_sync_pass(GRID))
    assert v["verdict"] == "RACE" and v["model_bug"], v

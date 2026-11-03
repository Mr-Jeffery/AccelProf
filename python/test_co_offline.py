"""C4: the barrier-ordered rule as a switch (sync_dominance.analyze(barrier_order=...), $CUVEIN_BARRIER_ORDER=0).

"Collector-only, re-scored" (CO-R) = the verdict layer on a scalar-clock kernel JSON with the static leg's
"barrier-ordered" branch skipped: a pair no certificate (R1 dominance, R3 chain, R2) orders is RACE / SC.
The candidates (edges, event-stream candidates), the edge rescue and the RMW points are unchanged.

  * switch on (the default): output byte-identical to the verdict layer before the switch existed
    (testdata/co_offline/golden_*.json, produced by f551ca0's sync_dominance.py on the same inputs);
  * switch off: a barrier-ordered pair becomes RACE / SC; every other pair keeps every field of its verdict
    (dominance- and chain-ordered pairs, event-stream candidates, rescued edges).

CPU fixtures, no GPU and no recording: X4's dumps (testdata/r3_closure) and three small real scalar-clock kernel
JSONs copied unchanged from X1b's store (testdata/co_offline/fixtures). The four recorded fixtures of
test_collector_only.py (co_straight, co_loop_red, co_loop_tile, co_missing) are checked too and skip where that
file's `rec` fixture skips (it needs a GPU node and nvcc).
"""
import json
from pathlib import Path

import pytest

import sync_dominance as sd
from test_collector_only import rec  # noqa: F401  (fixture; skips without a GPU)

_TD = Path(__file__).resolve().parent / "testdata"
_R3C = _TD / "r3_closure"
_R3C_DOT = _R3C / "race_interblock_none-lock_rtraw.sm_89.dot"
_GOLD = _TD / "co_offline"
# Real scalar-clock kernel JSONs (X1b's final-2026-11 store) with their CFGs, chosen because the switch has
# something to do in them:
#   barrier_ordered  P1 CC (V, Data, Pull, Persist, RaceBug, Block) kernel_12: pairs only the barrier-ordered
#                    rule orders
#   extended_edge    P1 BFS (E, Topo, Persist, RaceBug) kernel_1: a race that is an event-stream candidate
#   rescued_edge     P1 BFS (V, Data, Push, RaceBug, Warp) kernel_12: a race whose edge the event stream's
#                    distance lifts
_FX = _GOLD / "fixtures"
_ENV = ("CUVEIN_BARRIER_ORDER", "CUVEIN_EVENT_CANDIDATES", "CUVEIN_BARRIER_PASS", "CUVEIN_PREFER_RECORDS",
        "CUVEIN_PREFER_AGGREGATES", "CUVEIN_R3_PAST_RELEASE", "CUVEIN_R3_LANDING",
        "CUVEIN_R3_BEFORE_ACQUIRE", "CUVEIN_R3_LOC_CLOSURE")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in _ENV:
        monkeypatch.delenv(k, raising=False)


def _fixtures():
    """name -> (dot path, kernel JSON path)."""
    out = {d.name: (next(d.glob("*.dot")), d / "kernel_0.json") for d in sorted(_FX.iterdir())}
    out["r3c_scalar_clock_recording"] = (_R3C_DOT, _R3C / "scalar_clock_c58_run20.json")
    out["r3c_vector_clock_recording"] = (_R3C_DOT, _R3C / "vector_clock_c58_run3.json")
    return out


def _analyze(name, **kw):
    dot, p = _fixtures()[name]
    return sd.analyze(dot, p, **kw)


def _scrub(x):
    """absolute paths (the report names its inputs) -> basenames, so the golden files are location-free"""
    if isinstance(x, dict):
        return {k: _scrub(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_scrub(v) for v in x]
    return Path(x).name if isinstance(x, str) and x.startswith("/") else x


def _dump(rep):
    return json.dumps(_scrub(rep), sort_keys=True, indent=1)


def _byname(rep):
    return {(v["current_pc"], v["ancient_pc"]): v for v in rep["verdicts"]}


# ------------------------------------------------------------------------- switch on: unchanged
@pytest.mark.parametrize("name", sorted(_fixtures()))
def test_switch_on_is_byte_identical_to_the_verdict_layer_before_the_switch(name, monkeypatch):
    gold = (_GOLD / f"golden_{name}.json").read_text()
    assert _dump(_analyze(name)) == gold
    assert _dump(_analyze(name, barrier_order=True)) == gold
    monkeypatch.setenv("CUVEIN_BARRIER_ORDER", "1")
    assert _dump(_analyze(name)) == gold


# ------------------------------------------------------------------------- switch off
def _flips(name):
    """-> (on, off) verdict dicts keyed by pc pair; asserts the invariant: a pair that was not
    barrier-ordered keeps every field of its verdict with the switch off."""
    on = _byname(_analyze(name))
    off = _byname(_analyze(name, barrier_order=False))
    assert on.keys() == off.keys()
    for k, v in on.items():
        if v["hb_class"] != "barrier-ordered":
            assert off[k] == v, (name, k)
    return on, off


def test_switch_off_makes_barrier_ordered_pairs_races():
    on, off = _flips("barrier_ordered")
    bo = [k for k, v in on.items() if v["hb_class"] == "barrier-ordered"]
    assert bo, "the fixture must contain barrier-ordered pairs"
    for k in bo:
        assert on[k]["verdict"] == "ORDERED"
        assert off[k]["verdict"] in ("RACE", "SC") and off[k]["hb_class"] != "barrier-ordered", k
        assert off[k]["race_type"] == on[k]["race_type"]
    # whatever dominance or a chain ordered stays ordered (_flips: every other pair is unchanged to the field)
    assert all(off[k]["verdict"] == "ORDERED" for k, v in on.items()
               if v["verdict"] == "ORDERED" and v["hb_class"] != "barrier-ordered")


def test_env_var_is_the_same_switch(monkeypatch):
    off = _dump(_analyze("barrier_ordered", barrier_order=False))
    monkeypatch.setenv("CUVEIN_BARRIER_ORDER", "0")
    assert _dump(_analyze("barrier_ordered")) == off


def test_extended_edge_race_stays_a_race_switch_off():
    """The race is an event-stream candidate: no edge of the dump names it (an edge remembers only the
    last accessor)."""
    on, off = _flips("extended_edge")
    ext = [k for k, v in on.items() if v["verdict"] == "RACE" and v["event_candidate"]]
    assert ext
    assert all(off[k]["verdict"] == "RACE" and off[k]["event_candidate"] for k in ext)


def test_rescued_edge_race_stays_a_race_switch_off():
    """An edge recorded at a smaller thread distance than the event stream shows; the rescue lifts it."""
    on, off = _flips("rescued_edge")
    resc = [k for k, v in on.items() if v["verdict"] == "RACE" and v["edge_rescued"]]
    assert resc
    assert all(off[k]["verdict"] == "RACE" and off[k]["edge_rescued"] for k in resc)


@pytest.mark.parametrize("name", ["r3c_scalar_clock_recording", "r3c_vector_clock_recording"])
def test_the_r3_closure_pair_is_reported_switch_off(name):
    on, off = _flips(name)
    k = (0x340, 0x140) if (0x340, 0x140) in on else (0x140, 0x340)
    assert on[k]["verdict"] == off[k]["verdict"] and on[k]["verdict"] in ("RACE", "SC")


def test_serial_runs_are_deterministic_switch_off():
    for name in ("barrier_ordered", "r3c_scalar_clock_recording"):
        assert _dump(_analyze(name, barrier_order=False)) == _dump(_analyze(name, barrier_order=False))


# ------------------------------------------------------------ the recorded fixtures of test_collector_only.py
def _vs(rec, kernel, **kw):  # noqa: F811
    dots, traces = rec["scalar-clock"]
    for dot in dots:
        try:
            return sd.analyze(dot, traces[kernel], **kw)["verdicts"]
        except sd.AlignmentError:
            continue
    raise AssertionError("no CFG aligns with the trace")


def test_recorded_loop_carried_pair_is_a_race_switch_off(rec):  # noqa: F811
    on, off = _vs(rec, "co_loop_red"), _vs(rec, "co_loop_red", barrier_order=False)
    assert not any(v["verdict"] == "RACE" for v in on)
    assert any(v["hb_class"] == "barrier-ordered" for v in on)
    assert any(v["verdict"] == "RACE" and v["race_type"] == "RAW" for v in off)


@pytest.mark.parametrize("kernel", ["co_straight", "co_loop_tile"])
def test_recorded_dominance_fixtures_stay_ordered_switch_off(rec, kernel):  # noqa: F811
    assert {v["verdict"] for v in _vs(rec, kernel, barrier_order=False)} == {"ORDERED"}


def test_recorded_missing_barrier_stays_a_race_switch_off(rec):  # noqa: F811
    assert "RACE" in {v["verdict"] for v in _vs(rec, "co_missing", barrier_order=False)}

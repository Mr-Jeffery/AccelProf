"""Warp-barrier instance assembly (T24; eval/SYNCWARP_INSTANCE.md, eval/X5_BYTE_PAIRS.md section 4,
hb_proof.tex Definition "Instances", the warp barrier).

A warp diverged at a WARPSYNC executes it once per convergence group, and the trace carries one
`syncwarp` record per group: sync_mask the full mask, active_mask the group's lanes. The instance
completes when the groups' lanes cover sync_mask minus the warp's exited lanes (and the lanes past
the block's last thread), at the last group's record or at the exit of the last missing lane, and
then joins those lanes. Joining every lane of sync_mask at EACH record (the reading before T24)
orders a lane's pre-arrival accesses after the arrived lanes' pre-barrier accesses: a false
happens-before edge. HbClock, hb_oracle.py and sync_dominance.barrier_only_pairs implement the
assembly identically, with the W2 analogue (TV-syncwarp-completion-order) and the end-of-kernel
check (TV-syncwarp-pending-at-end). design/algorithms_check.py is not changed by T24 and is not
compared here.

Two parts:
  * synthetic dumps (no GPU): the cases one by one, oracle against barrier_only_pairs;
  * real kernels (GPU node): python/testdata/syncwarp_diverged_waw.cu -- the shape of ECL-CC's
    cc_vertex_data without its first __syncwarp(), the remaining one reached in two groups, so
    the clear/set WAW on updated[warp] is a data race, reported in both modes -- and the positive
    control python/testdata/syncwarp_converged_clean.cu (the first __syncwarp() back, converged:
    CLEAN in both modes).

    .env/bin/python -m pytest python/test_syncwarp.py -rxXs
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import hb_oracle
import sync_dominance as sd

_ROOT = Path(__file__).resolve().parents[1]
_TESTDATA = _ROOT / "python" / "testdata"
_DOT = _TESTDATA / "norace_interwarp_barrier_raw.sm_86.dot"
_KERNEL = "_Z5kmainPj"
_FULL = 0xFFFFFFFF
_LO16 = 0x0000FFFF
_HI16 = 0xFFFF0000


# --------------------------------------------------------------------------- #
# Synthetic dumps: 64 threads per block (warps 0 and 1)                        #
# --------------------------------------------------------------------------- #
def _mem(seq, pc, typ, mask, warp=0, addr=lambda k: 0):
    return {"seq": seq, "block": 0, "warp": warp, "pc": pc, "type": typ, "space": "shared",
            "size": 1, "active_mask": mask,
            "lanes": [{"lane": k, "addr": addr(k)} for k in range(32) if (mask >> k) & 1]}


def _sw(seq, active, sync=_FULL, warp=0, pc=0x60):
    return {"seq": seq, "block": 0, "warp": warp, "pc": pc, "type": "syncwarp",
            "sync_mask": sync, "active_mask": active}


def _exit(seq, mask, warp=0):
    return {"seq": seq, "block": 0, "warp": warp, "pc": 0x90, "type": "exit", "active_mask": mask}


def _dump(tmp_path, events, threads=64, exits_marker=True, name="trace.json"):
    t = {"kernel": {"kernel_name": _KERNEL, "block_thread_count": threads}, "hb_events": events}
    if exits_marker:
        t["hb_exits"] = 1
    p = tmp_path / name
    p.write_text(json.dumps(t))
    return p


def _both(path):
    """(oracle races, oracle sync pairs, offline tv) of one dump; the offline barrier-only pass
    must give the oracle's second clock."""
    rep = hb_oracle.analyze(_DOT, path)
    tv = []
    off = sd.barrier_only_pairs(json.loads(Path(path).read_text()), {}, {}, tv_out=tv)
    osync = {(a, b): n for a, b, n in rep["races_sync_only"]}
    assert osync == off, "offline barrier-only pass != the oracle's second clock"
    return rep["races"], osync, tv


# lane 0 clears the flag before the first group's record; lane 16 sets it before the second's
_CLEAR, _SET, _READ = 0x50, 0x84, 0x80


def test_diverged_instance_joins_at_its_completion(tmp_path):
    # X5b's counterfactual: the clear/set WAW is unordered (each before its own group's arrival);
    # the read after the completed instance is ordered after both
    ev = [_mem(0, _CLEAR, "write", 1 << 0), _sw(1, _LO16), _mem(2, _SET, "write", 1 << 16),
          _sw(3, _HI16), _mem(4, _READ, "read", _FULL)]
    races, sync, tv = _both(_dump(tmp_path, ev))
    assert [(r["kind"], r["count"]) for r in races] == [("WAW", 1)]
    assert sync == {(_CLEAR, _SET): 1} and tv == []


def test_three_groups(tmp_path):
    ev = [_mem(0, _CLEAR, "write", 1 << 0), _sw(1, 0x000000FF), _mem(2, _SET, "write", 1 << 8),
          _sw(3, 0x0000FF00), _sw(4, _HI16), _mem(5, _READ, "read", _FULL)]
    races, sync, tv = _both(_dump(tmp_path, ev))
    assert sync == {(_CLEAR, _SET): 1} and tv == []


def test_converged_syncwarp_orders(tmp_path):
    # the fast path: one record holds every expected lane and joins at once
    ev = [_mem(0, _CLEAR, "write", 1 << 0), _sw(1, _FULL), _mem(2, _SET, "write", 1 << 16),
          _sw(3, _FULL), _mem(4, _READ, "read", _FULL)]
    assert _both(_dump(tmp_path, ev)) == ([], {}, [])


def test_completed_instance_orders_later_accesses(tmp_path):
    # both groups' pre-arrival writes are ordered before every lane's later read and write
    ev = [_mem(0, _CLEAR, "write", 1 << 0), _sw(1, _LO16), _mem(2, _SET, "write", 1 << 16),
          _sw(3, _HI16), _mem(4, _READ, "read", _FULL), _sw(5, _FULL),
          _mem(6, 0x88, "write", 1 << 5)]
    races, sync, tv = _both(_dump(tmp_path, ev))
    assert sync == {(_CLEAR, _SET): 1} and tv == []


def test_exit_of_a_missing_lane_completes_the_instance(tmp_path):
    # lanes 16..31 exit without arriving (lane 16 wrote slot 1 first): the instance completes at
    # the exit with lanes 0..15 and does not join the exited lanes, so lane 16's write stays
    # unordered against lane 1's later read (RAW); lane 0's pre-arrival write does not
    ev = [_mem(0, _CLEAR, "write", 1 << 0), _mem(1, _SET, "write", 1 << 16, addr=lambda k: 1),
          _sw(2, _LO16), _exit(3, _HI16), _mem(4, _READ, "read", 1 << 1, addr=lambda k: 0),
          _mem(5, 0x88, "read", 1 << 1, addr=lambda k: 1)]
    races, sync, tv = _both(_dump(tmp_path, ev))
    assert {(r["kind"], r["count"]) for r in races} == {("RAW", 1)}
    assert sync == {(_SET, 0x88): 1} and tv == []


def test_lanes_exited_before_the_syncwarp(tmp_path):
    # W3 reads the record's active lanes: a sync_mask naming exited lanes is valid, and the
    # converged record of the remaining lanes completes the instance by itself
    ev = [_exit(0, _HI16), _mem(1, _CLEAR, "write", 1 << 0), _sw(2, _LO16),
          _mem(3, _SET, "write", 1 << 1)]
    assert _both(_dump(tmp_path, ev)) == ([], {}, [])


def test_lanes_past_the_block_end_are_not_expected(tmp_path):
    # 48 threads: warp 1 has lanes 0..15 only; __syncwarp() with the full mask completes with them
    ev = [_mem(0, _CLEAR, "write", 1 << 0, warp=1), _sw(1, _LO16, warp=1),
          _mem(2, _SET, "write", 1 << 1, warp=1)]
    assert _both(_dump(tmp_path, ev, threads=48)) == ([], {}, [])


def test_tv_record_of_an_arrived_lane(tmp_path):
    # W2 for a warp barrier: lane 1 has arrived; a record of it before the instance completes
    ev = [_sw(0, _LO16), _mem(1, _SET, "write", 1 << 1)]
    with pytest.raises(sd.AlignmentError, match="TV-syncwarp-completion-order"):
        hb_oracle.analyze(_DOT, _dump(tmp_path, ev))
    ev = [_sw(0, _LO16), _sw(1, _LO16)]            # a second arrival of the same lanes
    with pytest.raises(sd.AlignmentError, match="TV-syncwarp-completion-order"):
        hb_oracle.analyze(_DOT, _dump(tmp_path, ev, name="t2.json"))


def test_tv_exit_of_an_arrived_lane(tmp_path):
    ev = [_sw(0, _LO16), _exit(1, 1 << 3)]
    with pytest.raises(sd.AlignmentError, match="TV-syncwarp-completion-order"):
        hb_oracle.analyze(_DOT, _dump(tmp_path, ev))


def test_tv_syncwarp_pending_at_end(tmp_path):
    ev = [_sw(0, _LO16)]
    with pytest.raises(sd.AlignmentError, match="TV-syncwarp-pending-at-end"):
        hb_oracle.analyze(_DOT, _dump(tmp_path, ev))
    tv = []
    sd.barrier_only_pairs(json.loads(_dump(tmp_path, ev).read_text()), {}, {}, tv_out=tv)
    assert len(tv) == 1 and tv[0].startswith("TV-syncwarp-pending-at-end")


def test_instances_per_warp_and_pc(tmp_path):
    # two warps diverged at one pc, interleaved: each warp's instance is its own
    one = lambda k: 1                              # warp 1's flag
    ev = [_mem(0, _CLEAR, "write", 1 << 0, warp=0), _mem(1, _CLEAR, "write", 1 << 0, 1, one),
          _sw(2, _LO16, warp=0), _sw(3, _LO16, warp=1),
          _mem(4, _SET, "write", 1 << 16, warp=0), _sw(5, _HI16, warp=0),
          _sw(6, _HI16, warp=1), _mem(7, _SET, "write", 1 << 16, 1, one)]
    races, sync, tv = _both(_dump(tmp_path, ev))
    # warp 0's set is unordered with its clear; warp 1's set follows its completed instance
    assert sync == {(_CLEAR, _SET): 1} and tv == []


# --------------------------------------------------------------------------- #
# Real kernels (GPU node): the counterfactual and the positive control          #
# --------------------------------------------------------------------------- #
_MODES = ("vector-clock", "scalar-clock")


def _record(tmp_path_factory, name, mode):
    """(dots, kernel JSON) of one run of testdata/<name>.cu in `mode`, dump on."""
    if shutil.which("nvcc") is None:
        pytest.skip("no nvcc (run on a GPU node)")
    d = tmp_path_factory.mktemp(f"{name}-{mode}")
    binary = d / name
    b = subprocess.run(["nvcc", "-arch=native", "-lineinfo", "--cudart", "shared",
                        str(_TESTDATA / f"{name}.cu"), "-o", str(binary)], capture_output=True)
    if b.returncode != 0:
        pytest.skip(f"build failed: {b.stderr.decode()[-300:]}")
    env = dict(os.environ, YOSEMITE_HB_MODE=mode, YOSEMITE_HB_DUMP="1")
    env.pop("YOSEMITE_HB_NO_ENGINE", None)
    subprocess.run(["bash", str(_ROOT / "getall.sh"), str(binary)], cwd=_ROOT, env=env,
                   capture_output=True, timeout=900)
    dots = sorted((d / f"{name}_extracted_cubins").glob("*.dot"))
    traces = sorted(d.glob(f"dependency_{name}*/kernel_*.json"))
    if not dots or not traces:
        pytest.skip("no trace produced (GPU / collector unavailable)")
    t = json.loads(traces[-1].read_text())
    if not t.get("hb_exits") or not t.get("hb_events"):
        pytest.skip("the traced runtime has no exit records or no dump")
    return dots, traces[-1], t


@pytest.fixture(scope="module", params=_MODES)
def race(request, tmp_path_factory):
    return (request.param, *_record(tmp_path_factory, "syncwarp_diverged_waw", request.param))


@pytest.fixture(scope="module", params=_MODES)
def control(request, tmp_path_factory):
    return (request.param, *_record(tmp_path_factory, "syncwarp_converged_clean", request.param))


def _first(fn, dots, trace):
    for dot in dots:
        try:
            return fn(dot, trace)
        except sd.AlignmentError as e:
            if str(e).startswith("TV-"):
                raise
            continue
    raise AssertionError("no CFG aligns with the trace")


def _key(r):   # hb_races is aggregated (T9): addr and tids name one example instance
    return (r.get("a_pc"), r["b_pc"], r["kind"], r.get("class"), r["space"], r.get("dist"),
            r.get("async"), r.get("count"), r.get("a2_uncertain"))


def _roles(t):
    """the kernel's clear, set and read pcs, by role: the shared write by lane 0, the shared write
    by lane 16, the shared read."""
    roles = {}
    for e in t["hb_events"]:
        if e.get("space") != "shared":
            continue
        lanes = {ln["lane"] for ln in e["lanes"]}
        role = "read" if e["type"] == "read" else "clear" if lanes == {0} else \
            "set" if lanes == {16} else "other"
        roles.setdefault(role, set()).add(e["pc"])
    assert set(roles) == {"clear", "set", "read"} and all(len(v) == 1 for v in roles.values()), roles
    return {k: next(iter(v)) for k, v in roles.items()}


def _diverged_instances(t):
    """per (block, warp): the syncwarp records at the pc whose records are partial, and the seq of
    the clear and the set."""
    roles = _roles(t)
    ev = sorted(t["hb_events"], key=lambda e: e["seq"])
    part = {e["pc"] for e in ev if e["type"] == "syncwarp" and e["active_mask"] != e["sync_mask"]}
    assert len(part) == 1, part
    out = {}
    for e in ev:
        w = out.setdefault((e["block"], e["warp"]), {"sw": [], "clear": None, "set": None})
        if e["type"] == "syncwarp" and e["pc"] in part:
            w["sw"].append((e["seq"], e["active_mask"], e["sync_mask"]))
        elif e.get("space") == "shared" and e["pc"] == roles["clear"]:
            w["clear"] = e["seq"]
        elif e.get("space") == "shared" and e["pc"] == roles["set"]:
            w["set"] = e["seq"]
    return out


def test_warpsync_runs_in_two_records(race):
    # guard: in every warp the helper's WARPSYNC is one instance of two records (lanes 0..15,
    # then 16..31), lane 0's clear precedes the first and lane 16's set lies between them
    _, _, _, t = race
    inst = _diverged_instances(t)
    assert len(inst) == 8, sorted(inst)        # 4 blocks x 2 warps
    for k, w in inst.items():
        assert [(a, s) for _, a, s in w["sw"]] == [(_LO16, _FULL), (_HI16, _FULL)], (k, w)
        assert w["clear"] < w["sw"][0][0] < w["set"] < w["sw"][1][0], (k, w)


def test_the_waw_is_reported(race):
    mode, dots, trace, t = race
    roles = _roles(t)
    pair = (min(roles["clear"], roles["set"]), max(roles["clear"], roles["set"]))
    assert t.get("tv_violation") is None, t.get("tv_violation")
    if mode == "vector-clock":
        assert {(min(r["a_pc"], r["b_pc"]), max(r["a_pc"], r["b_pc"]), r["kind"], r["space"])
                for r in t["hb_races"]} == {(*pair, "WAW", "shared")}, t["hb_races"]
        assert [tuple(x[:2]) for x in t["hb_races_sync_only"]] == [pair]
    else:
        gp, _, _ = sd.aggregated_sync_pass(t)
        assert set(gp) == {pair}, gp
    rep = _first(sd.analyze, dots, trace)
    race_pairs = {frozenset((v["current_pc"], v["ancient_pc"])) for v in rep["verdicts"]
                  if v["verdict"] == "RACE"}
    assert race_pairs == {frozenset(pair)}, (mode, rep["summary"])


def test_hb_clock_matches_specification(race):
    mode, dots, trace, t = race
    if mode != "vector-clock":
        pytest.skip("the specification is compared on the vector-clock recording")
    rep = _first(hb_oracle.analyze, dots, trace)
    assert {_key(r) for r in t["hb_races"]} == {_key(r) for r in rep["races"]}
    assert t["hb_races_sync_only"] == rep["races_sync_only"]


def test_aggregates_equal_records(race):
    mode, _, _, t = race
    tv = []
    plain = {k: v for k, v in t.items() if k not in ("hb_sync_pass", "hb_rmw_points")}
    off = sd.barrier_only_pairs(plain, {}, {}, tv_out=tv)
    if mode == "vector-clock":
        assert off == {(a, b): n for a, b, n in t["hb_races_sync_only"]}
    else:
        gp, _, _ = sd.aggregated_sync_pass(t)
        assert set(gp) == set(off) and all(1 <= gp[k] <= off[k] for k in gp), (gp, off)
    assert tv == []


def test_control_is_clean(control):
    mode, dots, trace, t = control
    inst = _diverged_instances(t)              # the second __syncwarp() is still diverged
    assert all(len(w["sw"]) == 2 for w in inst.values()), inst
    assert t.get("tv_violation") is None
    if mode == "vector-clock":
        assert t["hb_races"] == [] and t["hb_races_sync_only"] == []
        rep = _first(hb_oracle.analyze, dots, trace)
        assert rep["races"] == [] and rep["races_sync_only"] == []
    else:
        assert sd.aggregated_sync_pass(t)[0] == {}
    plain = {k: v for k, v in t.items() if k not in ("hb_sync_pass", "hb_rmw_points")}
    assert sd.barrier_only_pairs(plain, {}, {}) == {}
    assert _first(sd.analyze, dots, trace)["summary"]["races"] == 0

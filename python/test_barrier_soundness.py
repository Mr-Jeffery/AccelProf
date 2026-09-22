"""Soundness regression guard for the block-wide __syncthreads happens-before edge,
plus the Phase-1 trace-validity (TV) runtime invariants.

A block barrier (BAR.SYNC) emits ONE arrival record per warp. If the HB model joins
only the lanes of a SINGLE warp (the bug fixed by block-barrier instance assembly),
warp 0's pre-barrier shared write and another warp's post-barrier read get no
cross-warp happens-before edge, so the most common CUDA idiom (warp 0 loads a tile ->
__syncthreads -> other warps consume it) is reported as a spurious RAW race. That is a
false positive = unsoundness.

test_hb_engine_matches_oracle CANNOT catch this: hb_oracle and HbEngine share the model,
so if the per-warp bug returns in both, engine==oracle still holds. These tests therefore
assert ABSOLUTE verdicts (exact race count on a known trace) and include a POSITIVE control
(a genuine race that must still be reported), so a "reports 0 on everything" regression
cannot pass, and a "raises on everything" regression cannot pass either.

Traces are built to the exact hb_events schema (validated against a real accelprof
YOSEMITE_HB_TRACE run): per-warp memory records expand active lanes; each warp emits one
barrier record (thread_count=0 for a plain __syncthreads => whole block from
block_thread_count, bar_index the static barrier id, active_mask the arrived lanes).
"""
import json

import pytest

import hb_oracle as ho
import sync_dominance as sd

from pathlib import Path

_DOT = Path(__file__).resolve().parent / "testdata" / "norace_interwarp_barrier_raw.sm_86.dot"
_FULL = 0xFFFFFFFF
_KERNEL = "_Z5kmainPj"


def _lanes(stride=4):
    return [{"lane": k, "addr": stride * k} for k in range(32)]


def _analyze(tmp_path, events, block_tc=64):
    trace = {"kernel": {"kernel_name": _KERNEL, "block_thread_count": block_tc},
             "hb_events": events}
    p = tmp_path / "trace.json"
    p.write_text(json.dumps(trace))
    return ho.analyze(_DOT, p)


# --------------------------------------------------------------------------- #
# Multi-warp barrier soundness: norace control + positive control             #
# --------------------------------------------------------------------------- #
def test_multiwarp_barrier_orders_crosswarp(tmp_path):
    """NORACE control: warp 0 writes tile[] pre-barrier; warp 1 reads it post-barrier.
    __syncthreads orders the two -> exactly zero races when the barrier joins across
    warps. Fails the moment the barrier stops joining across warps (per-warp regress)."""
    events = [
        {"seq": 0, "block": 0, "warp": 0, "pc": 0x50, "type": "write",
         "space": "shared", "size": 4, "active_mask": _FULL, "lanes": _lanes()},
        {"seq": 1, "block": 0, "warp": 0, "pc": 0x60, "type": "barrier",
         "thread_count": 0, "bar_index": 0, "active_mask": _FULL},
        {"seq": 2, "block": 0, "warp": 1, "pc": 0x60, "type": "barrier",
         "thread_count": 0, "bar_index": 0, "active_mask": _FULL},
        {"seq": 3, "block": 0, "warp": 1, "pc": 0x80, "type": "read",
         "space": "shared", "size": 4, "active_mask": _FULL, "lanes": _lanes()},
    ]
    report = _analyze(tmp_path, events)
    assert report["summary"]["races"] == 0, (
        "__syncthreads must order warp 0's pre-barrier write before warp 1's "
        f"post-barrier read; per-warp barrier join regressed: {report['races']}")


def test_postbarrier_crosswarp_write_write_races(tmp_path):
    """POSITIVE control: after a single __syncthreads, warp 0 and warp 1 BOTH write
    tile[] with NO second barrier ordering them. They are concurrent -> a genuine
    cross-warp WAW race that must still be reported (guards against a "reports 0 on
    everything" / over-synchronizing regression)."""
    events = [
        {"seq": 0, "block": 0, "warp": 0, "pc": 0x60, "type": "barrier",
         "thread_count": 0, "bar_index": 0, "active_mask": _FULL},
        {"seq": 1, "block": 0, "warp": 1, "pc": 0x60, "type": "barrier",
         "thread_count": 0, "bar_index": 0, "active_mask": _FULL},
        {"seq": 2, "block": 0, "warp": 0, "pc": 0x70, "type": "write",
         "space": "shared", "size": 4, "active_mask": _FULL, "lanes": _lanes()},
        {"seq": 3, "block": 0, "warp": 1, "pc": 0x74, "type": "write",
         "space": "shared", "size": 4, "active_mask": _FULL, "lanes": _lanes()},
    ]
    report = _analyze(tmp_path, events)
    assert report["summary"]["races"] >= 1, (
        "two post-barrier cross-warp writes to the same tile[] are concurrent and "
        "must race; a 'reports 0' regression would pass a norace-only test")
    assert all(r["kind"] == "WAW" for r in report["races"]), \
        f"expected WAW races, got {[r['kind'] for r in report['races']]}"


# --------------------------------------------------------------------------- #
# Phase-1 trace-validity invariants: each violation must raise AlignmentError  #
# (the norace control above is the "valid trace does NOT raise" counterpart)   #
# --------------------------------------------------------------------------- #
def test_tv_seq_monotonic_fires(tmp_path):
    """TV-seq-monotonic: a duplicate/rewound seq must raise, not be silently consumed."""
    events = [
        {"seq": 5, "block": 0, "warp": 0, "pc": 0x50, "type": "read",
         "space": "shared", "size": 4, "active_mask": _FULL, "lanes": _lanes()},
        {"seq": 5, "block": 0, "warp": 0, "pc": 0x54, "type": "read",
         "space": "shared", "size": 4, "active_mask": _FULL, "lanes": _lanes()},
    ]
    with pytest.raises(sd.AlignmentError, match="TV-seq-monotonic"):
        _analyze(tmp_path, events)


def test_tv_barrier_overfill_fires(tmp_path):
    """TV-barrier-overfill: arrivals exceeding the expected participant count (here a
    wrong thread_count=16 with a full 32-lane warp) must raise."""
    events = [
        {"seq": 0, "block": 0, "warp": 0, "pc": 0x60, "type": "barrier",
         "thread_count": 16, "bar_index": 0, "active_mask": _FULL},
    ]
    with pytest.raises(sd.AlignmentError, match="TV-barrier-overfill"):
        _analyze(tmp_path, events)


def test_tv_completion_order_fires(tmp_path):
    """TV-barrier-completion-order: a warp blocked at a not-yet-complete barrier must
    not issue a post-barrier access before the instance fires. Here block_tc=64 so the
    instance stays pending after warp 0's lone arrival; warp 0 then reads -> raise."""
    events = [
        {"seq": 0, "block": 0, "warp": 0, "pc": 0x60, "type": "barrier",
         "thread_count": 0, "bar_index": 0, "active_mask": _FULL},
        {"seq": 1, "block": 0, "warp": 0, "pc": 0x80, "type": "read",
         "space": "shared", "size": 4, "active_mask": _FULL, "lanes": _lanes()},
    ]
    with pytest.raises(sd.AlignmentError, match="TV-barrier-completion-order"):
        _analyze(tmp_path, events, block_tc=64)


def test_tv_expected_nonzero_multiwarp_fires(tmp_path):
    """TV-expected-nonzero-multiwarp: with the expected count unknown (thread_count=0
    AND block_thread_count=0), a second warp arriving at the same barrier would degrade
    to the unsound per-warp path -> raise."""
    events = [
        {"seq": 0, "block": 0, "warp": 0, "pc": 0x60, "type": "barrier",
         "thread_count": 0, "bar_index": 0, "active_mask": _FULL},
        {"seq": 1, "block": 0, "warp": 1, "pc": 0x60, "type": "barrier",
         "thread_count": 0, "bar_index": 0, "active_mask": _FULL},
    ]
    with pytest.raises(sd.AlignmentError, match="TV-expected-nonzero-multiwarp"):
        _analyze(tmp_path, events, block_tc=0)


def test_valid_multiwarp_trace_does_not_raise(tmp_path):
    """Counterpart to the TV tests: the norace fixture is a well-formed trace and must
    pass every TV check cleanly (guards against a 'raises on everything' regression)."""
    events = [
        {"seq": 0, "block": 0, "warp": 0, "pc": 0x50, "type": "write",
         "space": "shared", "size": 4, "active_mask": _FULL, "lanes": _lanes()},
        {"seq": 1, "block": 0, "warp": 0, "pc": 0x60, "type": "barrier",
         "thread_count": 0, "bar_index": 0, "active_mask": _FULL},
        {"seq": 2, "block": 0, "warp": 1, "pc": 0x60, "type": "barrier",
         "thread_count": 0, "bar_index": 0, "active_mask": _FULL},
        {"seq": 3, "block": 0, "warp": 1, "pc": 0x80, "type": "read",
         "space": "shared", "size": 4, "active_mask": _FULL, "lanes": _lanes()},
    ]
    report = _analyze(tmp_path, events)  # must not raise
    assert report["summary"]["races"] == 0

"""Soundness regression guard for the block-wide __syncthreads happens-before edge.

A block barrier (BAR.SYNC) emits ONE arrival record per warp. If the HB model joins
only the lanes of a SINGLE warp (the bug fixed by block-barrier instance assembly),
warp 0's pre-barrier shared write and another warp's post-barrier read get no
cross-warp happens-before edge, so the most common CUDA idiom (warp 0 loads a tile ->
__syncthreads -> other warps consume it) is reported as a spurious RAW race. That is a
false positive = unsoundness.

test_hb_engine_matches_oracle CANNOT catch this: hb_oracle and HbEngine share the model,
so if the per-warp bug returns in both, engine==oracle still holds. This test therefore
asserts the ABSOLUTE verdict (zero races) on a 2-warp, single-block, barrier-ordered
trace -- it fails the moment the barrier stops joining across warps.

The trace is built to the exact hb_events schema (validated against a real
accelprof YOSEMITE_HB_TRACE run): per-warp memory records expand active lanes; each
warp emits one barrier record (thread_count=0 for a plain __syncthreads => whole
block, bar_index=0, active_mask=full); arrivals precede the post-barrier read.
"""
import json

import hb_oracle as ho

from pathlib import Path

_DOT = Path(__file__).resolve().parent / "testdata" / "norace_interwarp_barrier_raw.sm_86.dot"
_FULL = 0xFFFFFFFF


def _barrier_trace(path):
    """kmain (_Z5kmainPj): warp 0 STS@0x50 tile[lane]; BAR.SYNC@0x60; warp 1 LDS@0x80
    tile[lane]. Cross-warp RAW that __syncthreads orders -> zero races when sound."""
    lanes = [{"lane": k, "addr": 4 * k} for k in range(32)]  # tile[k] at byte 4k
    events = [
        {"seq": 0, "block": 0, "warp": 0, "pc": 0x50, "type": "write",
         "space": "shared", "size": 4, "active_mask": _FULL, "lanes": lanes},
        {"seq": 1, "block": 0, "warp": 0, "pc": 0x60, "type": "barrier",
         "thread_count": 0, "bar_index": 0, "active_mask": _FULL},
        {"seq": 2, "block": 0, "warp": 1, "pc": 0x60, "type": "barrier",
         "thread_count": 0, "bar_index": 0, "active_mask": _FULL},
        {"seq": 3, "block": 0, "warp": 1, "pc": 0x80, "type": "read",
         "space": "shared", "size": 4, "active_mask": _FULL, "lanes": lanes},
    ]
    trace = {"kernel": {"kernel_name": "_Z5kmainPj", "block_thread_count": 64},
             "hb_events": events}
    path.write_text(json.dumps(trace))
    return path


def test_multiwarp_barrier_orders_crosswarp(tmp_path):
    report = ho.analyze(_DOT, _barrier_trace(tmp_path / "trace.json"))
    # sanity: the trace actually exercises the multi-warp barrier join path
    warps = {e["warp"] for e in json.loads((tmp_path / "trace.json").read_text())["hb_events"]
             if e["type"] == "barrier"}
    assert warps == {0, 1}, "fixture must have two warps arriving at the barrier"
    assert report["summary"]["races"] == 0, (
        "__syncthreads must order warp 0's pre-barrier write before warp 1's "
        f"post-barrier read; per-warp barrier join regressed: {report['races']}")

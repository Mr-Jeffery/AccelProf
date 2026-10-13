"""T2: the host-level happens-before pass (python/host_hb.py) on synthetic host-op logs.
No GPU: each case writes a host_ops.json and tiny kernel_<id>.json dumps and checks which
operation pairs race (design/host_memcpy_model.md §2-4)."""
import json
import os

import host_hb

BUF, OTHER, HOST = 0x7F0000000000, 0x7F0000100000, 0x7E0000000000
S1, S2, LEG = 11, 22, 99          # stream handles; LEG is the legacy default stream


def _kernel(tmp, kid, accesses):
    ev = [{"seq": i, "type": t, "space": "global", "size": 4, "block": 0, "warp": 0,
           "pc": 0x10 * (i + 1), "active_mask": 1, "lanes": [{"lane": 0, "addr": a}]}
          for i, (t, a) in enumerate(accesses)]
    with open(os.path.join(tmp, f"kernel_{kid}.json"), "w") as f:
        json.dump({"kernel": {"kernel_name": f"k{kid}"}, "hb_events": ev}, f)


def _run(tmp, ops):
    for i, o in enumerate(ops):
        o.setdefault("seq", i)
        o.setdefault("stream_ptr", 0x1000 + o.get("stream", 0) if o.get("stream") != LEG else 0)
    with open(os.path.join(tmp, "host_ops.json"), "w") as f:
        json.dump({"host_ops": ops}, f)
    return host_hb.races(str(tmp))


def _streams(nonblocking=True):
    fl = 1 if nonblocking else 0
    return [{"kind": "stream_create", "stream": S1, "flags": fl},
            {"kind": "stream_create", "stream": S2, "flags": fl}]


def _h2d(stream, dst=BUF, is_async=1, src=HOST):
    return {"kind": "memcpy", "stream": stream, "src": src, "dst": dst, "size": 64,
            "is_async": is_async, "direction": host_hb.H2D}


def _d2h(stream, src=BUF, is_async=1):
    return {"kind": "memcpy", "stream": stream, "src": src, "dst": HOST, "size": 64,
            "is_async": is_async, "direction": host_hb.D2H}


def _launch(stream, kid):
    return {"kind": "launch", "stream": stream, "monitored": True, "kernel_id": kid, "kernel": f"k{kid}"}


def _kinds(res):
    return sorted((r["race_type"], r["a"]["kind"], r["b"]["kind"]) for r in res["races"])


def test_copy_then_kernel_on_other_stream_races(tmp_path):
    _kernel(tmp_path, 0, [("read", BUF)])
    res = _run(tmp_path, _streams() + [_h2d(S1), _launch(S2, 0)])
    assert _kinds(res) == [("RAW", "memcpy", "launch")]
    assert res["races"][0]["b_pc"] == 0x10 and res["races"][0]["addr"] == BUF


def test_event_wait_orders_copy_before_kernel(tmp_path):
    _kernel(tmp_path, 0, [("read", BUF)])
    ops = _streams() + [_h2d(S1), {"kind": "event_record", "stream": S1, "event": 5},
                        {"kind": "stream_wait", "stream": S2, "event": 5}, _launch(S2, 0)]
    assert _run(tmp_path, ops)["races"] == []


def test_stream_synchronize_orders(tmp_path):
    _kernel(tmp_path, 0, [("read", BUF)])
    ops = _streams() + [_h2d(S1), {"kind": "stream_sync", "stream": S1}, _launch(S2, 0)]
    assert _run(tmp_path, ops)["races"] == []


def test_kernel_then_copy_races(tmp_path):
    # the shipped cuHadron tests' shape: the copy is issued after the racing kernel
    _kernel(tmp_path, 0, [("write", BUF)])
    res = _run(tmp_path, _streams() + [_launch(S1, 0), _d2h(S2)])
    assert _kinds(res) == [("RAW", "launch", "memcpy")]
    assert res["races"][0]["a_pc"] == 0x10


def test_kernel_then_copy_fixed_by_event(tmp_path):
    _kernel(tmp_path, 0, [("write", BUF)])
    ops = _streams() + [_launch(S1, 0), {"kind": "event_record", "stream": S1, "event": 7},
                        {"kind": "stream_wait", "stream": S2, "event": 7}, _d2h(S2)]
    assert _run(tmp_path, ops)["races"] == []


def test_device_synchronize_orders(tmp_path):
    _kernel(tmp_path, 0, [("write", BUF)])
    ops = _streams() + [_launch(S1, 0), {"kind": "ctx_sync", "stream": 0}, _d2h(S2)]
    assert _run(tmp_path, ops)["races"] == []


def test_same_stream_is_ordered_and_disjoint_ranges_do_not_race(tmp_path):
    _kernel(tmp_path, 0, [("read", BUF)])
    _kernel(tmp_path, 1, [("read", OTHER)])
    ops = _streams() + [_h2d(S1), _launch(S1, 0), _launch(S2, 1)]
    assert _run(tmp_path, ops)["races"] == []


def test_legacy_default_stream_orders_blocking_but_not_nonblocking(tmp_path):
    _kernel(tmp_path, 0, [("write", BUF)])
    blocking = _streams(nonblocking=False) + [_launch(LEG, 0), _d2h(S1)]
    assert _run(tmp_path, blocking)["races"] == []
    nonblocking = _streams(nonblocking=True) + [_launch(LEG, 0), _d2h(S1)]
    assert _kinds(_run(tmp_path, nonblocking)) == [("RAW", "launch", "memcpy")]


def test_blocking_copy_orders_the_host(tmp_path):
    # a synchronous D2H copy returns after completion: later work anywhere is ordered after it
    _kernel(tmp_path, 0, [("write", BUF)])
    ops = _streams() + [_d2h(LEG, is_async=0), _launch(S1, 0)]
    assert _run(tmp_path, ops)["races"] == []


def test_pageable_sync_h2d_does_not_order_but_pinned_does(tmp_path):
    # sync H2D from pageable memory returns after staging; the DMA may still be writing
    _kernel(tmp_path, 0, [("read", BUF)])
    pageable = _streams() + [_h2d(LEG, is_async=0), _launch(S1, 0)]
    assert _kinds(_run(tmp_path, pageable)) == [("RAW", "memcpy", "launch")]
    pinned = _streams() + [{"kind": "host_alloc", "stream": 0, "addr": HOST, "size": 4096, "flags": 0},
                           _h2d(LEG, is_async=0), _launch(S1, 0)]
    assert _run(tmp_path, pinned)["races"] == []


def test_kernels_on_two_streams_race(tmp_path):
    _kernel(tmp_path, 0, [("write", BUF)])
    _kernel(tmp_path, 1, [("write", BUF), ("read", OTHER)])
    res = _run(tmp_path, _streams() + [_launch(S1, 0), _launch(S2, 1)])
    assert _kinds(res) == [("WAW", "launch", "launch")]


def test_unmonitored_launch_is_reported_not_guessed(tmp_path):
    ops = _streams() + [_h2d(S1), {"kind": "launch", "stream": S2, "monitored": False, "kernel_id": None}]
    res = _run(tmp_path, ops)
    assert res["races"] == [] and res["diagnostics"]["unmonitored_launches"] == 1


def test_spec_only_tag_for_synchronous_api_calls(tmp_path):
    # the cuHadron inter-kernel fixed builds: a pageable synchronous H2D copy on the legacy
    # stream, then a kernel on a non-blocking stream -- a race under the documented
    # semantics (the DMA may still be running), none if synchronous calls complete on return
    _kernel(tmp_path, 0, [("write", BUF)])
    res = _run(tmp_path, _streams() + [_h2d(LEG, is_async=0), _launch(S1, 0)])
    assert [(r["race_type"], r["spec_only"]) for r in res["races"]] == [("WAW", True)]
    # cudaMemset (host-asynchronous) on the legacy stream, then a non-blocking-stream kernel
    ops = _streams() + [{"kind": "memset", "stream": LEG, "dst": BUF, "width": 64, "height": 1,
                         "is_async": 0}, _launch(S1, 0)]
    assert [(r["race_type"], r["spec_only"]) for r in _run(tmp_path, ops)["races"]] == [("WAW", True)]
    # an asynchronous copy is never excused
    res = _run(tmp_path, _streams() + [_h2d(S2), _launch(S1, 0)])
    assert [r["spec_only"] for r in res["races"]] == [False]

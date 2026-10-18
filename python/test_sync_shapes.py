"""T22 cont. (eval/SHARDED_SYNC.md): method regression for the two location shapes X1-follow found
behind the scalar-clock slowdowns, recorded in scalar-clock mode with the dump on (getall.sh):
  flag_writers.cu    bfs's `*d_over = 1`: one flag word written by every thread of 16 blocks
                     (scalar-clock Check's early exit, Fix 2);
  broadcast_read.cu  nbody's `p[j]`: 1,024 particle words each read by all 1,024 threads, then one
                     store to m[0] (the adaptive tail of a broadcast-read location, Fix 1).
Asserted, from the kernel JSON: hb_sync_pass holds exactly the expected pairs, by role (the
opcodes' access kinds, not pc offsets), at grid distance; it equals barrier_only_pairs over the
same recording's records in pairs, distances and first pcs, with each count 1 <= aggregate <=
records; and for the flag the aggregate count is below the records' (the exit ran). Runs at
whatever YOSEMITE_HB_SHARDS the environment sets (the green set's configurations).

Needs a GPU node and nvcc.
    .env/bin/python -m pytest python/test_sync_shapes.py -rxX
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import sync_dominance as sd

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "python" / "testdata"


def _record(name, d):
    """Build testdata/<name>.cu and record it in scalar-clock mode with the dump -> (dots, trace)."""
    if shutil.which("nvcc") is None:
        pytest.skip("no nvcc (run on a GPU node)")
    binary = d / name
    b = subprocess.run(["nvcc", "-arch=native", "-lineinfo", "--cudart", "shared",
                        str(_SRC / f"{name}.cu"), "-o", str(binary)], capture_output=True)
    if b.returncode != 0:
        pytest.skip(f"build failed: {b.stderr.decode()[-300:]}")
    env = dict(os.environ, YOSEMITE_HB_MODE="scalar-clock", YOSEMITE_HB_DUMP="1")
    env.pop("YOSEMITE_HB_NO_ENGINE", None)
    subprocess.run(["bash", str(_ROOT / "getall.sh"), str(binary)], cwd=_ROOT, env=env,
                   capture_output=True, timeout=900)
    dots = sorted((d / f"{name}_extracted_cubins").glob("*.dot"))
    traces = sorted(d.glob(f"dependency_{name}*/kernel_*.json"))
    if not dots or not traces:
        pytest.skip("no trace produced (GPU / collector unavailable)")
    return dots, traces[-1]


def _records_pass(dots, t):
    """barrier_only_pairs over the records, the lane cutoff lifted -> (pairs, dist, order)."""
    for dot in dots:
        kernels = sd.parse_dot(dot)
        try:
            eng = sd.HBGraph(*kernels[sd.select_kernel(kernels, t["kernel"]["kernel_name"])])
        except sd.AlignmentError:
            continue
        policy = sd.strong_ldst_policy()
        rmw = {pc: s for pc, op in eng.pc_opcode.items() if (s := sd.atomic_scope(op)) is not None}
        coh = {pc: s for pc, op in eng.pc_opcode.items()
               if (s := sd.coherent_scope(op, policy)) is not None}
        plain = {k: v for k, v in t.items() if k not in ("hb_sync_pass", "hb_rmw_points")}
        dist, order = {}, {}
        pairs = sd.barrier_only_pairs(plain, rmw, coh, None, dist, order, sd.dump_async_pcs(eng, t))
        return pairs, dist, order
    raise AssertionError("no CFG holds the trace's kernel")


@pytest.fixture(scope="module", params=("flag_writers", "broadcast_read"))
def shape(request, tmp_path_factory):
    name = request.param
    dots, trace = _record(name, tmp_path_factory.mktemp(name))
    t = json.loads(Path(trace).read_text())
    assert t.get("hb_events"), f"{name}: the recording has no hb_events"
    assert "hb_sync_pass" in t and "tv_violation" not in t, name
    access = {n["pc"]: sd.parse_flags(n["flags"])[1] for n in t.get("nodes", [])}
    return name, dots, t, access


def test_expected_pairs_and_distances(shape):
    name, _, t, access = shape
    rows = {(a, b): (n, d) for a, b, n, d, *_ in t["hb_sync_pass"]}
    grid = sd.GRID
    if name == "flag_writers":
        same = [k for k in rows if k[0] == k[1]]
        assert len(rows) == 2 and len(same) == 1, f"{name}: {t['hb_sync_pass']}"
        w = same[0][0]
        (other,) = [k for k in rows if k != same[0]]
        r = other[0] if other[1] == w else other[1]
        assert w in other and access.get(w) == "write" and access.get(r) == "read", (name, rows, access)
        assert rows[same[0]][1] == grid and rows[other][1] == grid, (name, rows)
    else:
        assert len(rows) == 1, f"{name}: {t['hb_sync_pass']}"
        ((a, b),) = rows
        assert {access.get(a), access.get(b)} == {"read", "write"}, (name, rows, access)
        assert rows[(a, b)][1] == grid, (name, rows)


def test_aggregates_equal_records_counts_le(shape):
    name, dots, t, _ = shape
    pairs, dist, order = _records_pass(dots, t)
    gp, gd, go = sd.aggregated_sync_pass(t)
    assert set(gp) == set(pairs) and gd == dist and go == order, name
    assert all(1 <= gp[k] <= pairs[k] for k in gp), (name, gp, pairs)
    if name == "flag_writers":   # the flag's writers: one instance per write, not one per writer pair
        ((k, n),) = [(k, n) for k, n in gp.items() if k[0] == k[1]]
        assert n < pairs[k], (name, n, pairs[k])

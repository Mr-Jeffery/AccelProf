"""X7 (eval/VERDICT_PARALLEL.md): the verdict step's static-graph cache and kernel-JSON pool
change no output.

Fixture testdata/verdict_parallel/bfs100n: one stored multi-launch recording from the final
sweep (final-2026-11, P1-BFS_CUDA_E_..._RaceBug_...-default-100n: 12 vector-clock and 12
scalar-clock kernel JSONs over two kernels, one .dot), copied verbatim, plus two wrong .dot
files that sort before the right one, so every launch takes the alignment path the cache
remembers:
  0_other_program.dot  another program's CFG: select_kernel fails for the bfs kernel (no such
                       kernel) and succeeds for init (base-name match), whose pc check fails;
  1_misaligned.dot     the right CFG with every LDG renamed NOP: select_kernel succeeds and
                       the per-launch pc alignment check fails.
The program is analysed at N = 1 serial (the pre-X7 path: no cache), N = 1 cached and N = 8
cached; the merged output, every per-kernel report, analyze_one's rows (modulo the A1 timer
tokens) and its confirm files must be identical. CPU only (no GPU, no BeeGFS).
    .env/bin/python -m pytest python/test_verdict_parallel.py -q
"""
import csv
import glob
import io
import json
import os
import re
import shutil
import sys
from pathlib import Path

import pytest

import sync_dominance as sd

_ROOT = Path(__file__).resolve().parents[1]
_FIX = Path(__file__).resolve().parent / "testdata" / "verdict_parallel" / "bfs100n"
_MODES = ("vector-clock", "scalar-clock")

sys.path.insert(0, str(_ROOT / "eval" / "baselines"))
import run_cuvein as rc  # noqa: E402
import parallel  # noqa: E402

# the harness must judge with THIS checkout's sync_dominance (blib puts $CUVEIN_HOME/python first)
assert rc.sd is sd and Path(sd.__file__).resolve().parent == _ROOT / "python", \
    f"run_cuvein imported {rc.sd.__file__}, not {_ROOT}/python (set CUVEIN_HOME={_ROOT})"

_RUNS = {"serial-1": dict(workers=1, cache=False),
         "cached-1": dict(workers=1, cache=True),
         "cached-8": dict(workers=8, cache=True)}


def _canon(res):
    ids, pcs, raw = res
    return json.dumps([ids, sorted(pcs), raw], sort_keys=True, default=repr)


def test_fixture_exercises_the_cache():
    dots = sorted(p.name for p in (_FIX / "dots").glob("*.dot"))
    assert dots[:2] == ["0_other_program.dot", "1_misaligned.dot"] and len(dots) == 3
    for mode in _MODES:
        kjs = sorted((_FIX / mode).glob("kernel_*.json"))
        names = {json.loads(k.read_text())["kernel"]["kernel_name"] for k in kjs}
        assert len(kjs) >= 8 and len(names) >= 2, (mode, len(kjs), names)


@pytest.mark.parametrize("mode", _MODES)
def test_merged_output_identical(mode):
    out = {k: _canon(rc._analyze_reports(str(_FIX / mode), str(_FIX / "dots"), **kw))
           for k, kw in _RUNS.items()}
    assert json.loads(out["serial-1"])[0], "the fixture should report races"
    assert out["cached-1"] == out["serial-1"]
    assert out["cached-8"] == out["serial-1"]


@pytest.mark.parametrize("mode", _MODES)
def test_per_kernel_reports_identical(mode):
    """Every kernel JSON's full analyze() report, cached vs uncached, field by field."""
    dots = sorted(glob.glob(str(_FIX / "dots" / "*.dot")))
    kjs = sorted(glob.glob(str(_FIX / mode / "kernel_*.json")))

    def reports():
        out = []
        for kj in kjs:
            for dot in dots:
                try:
                    out.append(sd.analyze(dot, kj))
                    break
                except sd.AlignmentError as e:
                    out.append(("align", os.path.basename(dot), str(e)))
        return json.dumps(out, sort_keys=True, default=repr)

    plain = reports()
    # both wrong .dot files were tried and refused on every launch
    assert plain.count('"0_other_program.dot"') == len(kjs) == plain.count('"1_misaligned.dot"')
    with sd.graph_cache():
        cached = reports()
        cached_again = reports()      # second pass: everything from the cache
    assert cached == plain and cached_again == plain


def _same_static(a, b):
    """The static fields of two HBGraphs are equal (the region graph by nodes and edges)."""
    for f in sd.HBGraph._STATIC:
        x, y = getattr(a, f), getattr(b, f)
        if f == "G":
            if set(x.nodes()) != set(y.nodes()) or set(x.edges()) != set(y.edges()):
                return f
        elif x != y:
            return f
    return None


def test_static_part_never_written_and_trace_state_fresh():
    """The cached prototypes equal a fresh build after a whole analysis, and the HBGraph each
    launch gets is a new object with unattached per-trace state."""
    mode_dir = _FIX / "vector-clock"
    with sd.graph_cache():
        rc._analyze_reports(str(mode_dir), str(_FIX / "dots"), workers=1, cache=True)
        cache = sd._GRAPH_CACHE
        assert cache["static"], "no static graph was cached"
        assert len(cache["dot"]) == 3
        for (dot, mangled), proto in cache["static"].items():
            fresh = sd.HBGraph(*sd._parse_dot(dot)[mangled])
            assert _same_static(proto, fresh) is None, (dot, mangled, _same_static(proto, fresh))
            assert proto.atom == {} and proto.sync_edges == [] and proto._reach == {}
            assert not hasattr(proto, "same_loc")      # a prototype is never attached
        name = "bfs(ECLgraph, int const*, int*, int*)"   # 11 of the 12 launches; the other
        # program's CFG has no bfs kernel (its init kernel matches by base name and fails the
        # pc check instead, like 1_misaligned.dot)
        right = str(_FIX / "dots" / sorted(p.name for p in (_FIX / "dots").glob("*.dot"))[2])
        _, g1 = sd.kernel_graph(right, name)
        g1.attach_trace({1: 3}, [(1, 2, 3)])
        g1._reach[("x",)] = {1}
        _, g2 = sd.kernel_graph(right, name)
        assert g2 is not g1 and g2.G is g1.G
        assert g2.atom == {} and g2.sync_edges == [] and g2._reach == {} \
            and g2.release_points is None and not hasattr(g2, "same_loc")
        # the wrong .dot files: one cached select failure, one per-launch pc check failure
        assert cache["select"][(os.path.abspath(str(_FIX / "dots" / "0_other_program.dot")),
                                name)][1] is not None
        assert cache["select"][(os.path.abspath(str(_FIX / "dots" / "1_misaligned.dot")),
                                name)][1] is None
    assert sd._GRAPH_CACHE is None


_TIMER = re.compile(r";analysis_s=[0-9.]+;analysis_workers=\d+;analysis_kjsons=\d+")


def test_analyze_one_rows_and_confirm_identical(tmp_path, monkeypatch):
    """The harness entry point: rows identical modulo the A1 timer tokens (which every analysed
    row carries), confirm files byte-identical."""
    idir = tmp_path / "store" / "bfs100n"
    shutil.copytree(_FIX, idir)
    monkeypatch.setattr(parallel, "MODES", _MODES)
    rows, confirms = {}, {}
    for k, kw in _RUNS.items():
        monkeypatch.setenv("CUVEIN_GRAPH_CACHE", "1" if kw["cache"] else "0")
        cdir = tmp_path / f"confirm-{k}"
        cdir.mkdir()
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=parallel.blib.COLUMNS)
        w.writeheader()
        parallel.analyze_one(str(idir), w, str(cdir), analysis_workers=kw["workers"])
        text = buf.getvalue()
        assert len(_TIMER.findall(text)) == text.count("\n") - 1 > 0, text
        assert f"analysis_workers={kw['workers']};" in text
        rows[k] = _TIMER.sub("", text)
        confirms[k] = {p.name: p.read_bytes() for p in sorted(cdir.iterdir())}
    assert len(confirms["serial-1"]) == 2
    for k in ("cached-1", "cached-8"):
        assert rows[k] == rows["serial-1"], k
        assert confirms[k] == confirms["serial-1"], k


def test_capped_pool_identical(tmp_path):
    """_analyze_capped (forked child, caps) with a pool: the serial result."""
    mode_dir, dots = str(_FIX / "vector-clock"), str(_FIX / "dots")
    serial = _canon(rc._analyze_reports(mode_dir, dots, workers=1, cache=False))
    res, reason = parallel._analyze_capped(mode_dir, dots, 600, -1, 8)
    assert reason == "" and _canon(res) == serial


def test_exception_same_type_message_and_place(tmp_path):
    """A truncated kernel JSON (a partial dump's last file) fails the pool exactly as the serial
    loop: same exception type and message, inline and through _analyze_capped."""
    d = tmp_path / "vector-clock"
    shutil.copytree(_FIX / "vector-clock", d)
    k = d / "kernel_5.json"
    k.write_text(k.read_text()[:777])
    dots = str(_FIX / "dots")
    got = {}
    for k_, kw in _RUNS.items():
        with pytest.raises(ValueError) as ei:
            rc._analyze_reports(str(d), dots, **kw)
        got[k_] = (type(ei.value), str(ei.value))
        with pytest.raises(Exception) as ci:
            parallel._analyze_capped(str(d), dots, 600, -1, kw["workers"])
        got[k_ + "-capped"] = (type(ci.value), str(ci.value))
    assert got["serial-1"][0] is json.JSONDecodeError
    for k_ in _RUNS:
        assert got[k_] == got["serial-1"], k_
        assert got[k_ + "-capped"] == got["serial-1-capped"], k_


def test_capped_pool_timeout_kills_the_group(monkeypatch):
    """Past the cap the child and all its pool workers are killed (no worker outlives it)."""
    import time

    def slow(kj, dots):
        time.sleep(120)

    monkeypatch.setattr(rc, "_kernel_report", slow)      # inherited by the forked processes
    pids = []
    real_kill = parallel._kill_group
    monkeypatch.setattr(parallel, "_kill_group", lambda p: (pids.append(p.pid), real_kill(p)))
    t0 = time.time()
    res, reason = parallel._analyze_capped(str(_FIX / "vector-clock"), str(_FIX / "dots"),
                                           3, -1, 4)
    assert reason == "analysis-timeout" and res == ([], set(), [])
    assert time.time() - t0 < 30 and pids
    for _ in range(50):                                  # killed members are reaped by init
        if parallel._group_rss_bytes(pids[0]) == 0 and not _members(pids[0]):
            break
        time.sleep(0.1)
    assert not _members(pids[0])


def _members(pgid):
    out = []
    for d in os.listdir("/proc"):
        if d.isdigit():
            try:
                rest = Path(f"/proc/{d}/stat").read_text().rsplit(")", 1)[1].split()
            except (OSError, IndexError):
                continue
            if int(rest[2]) == pgid and rest[0] != "Z":
                out.append(int(d))
    return out

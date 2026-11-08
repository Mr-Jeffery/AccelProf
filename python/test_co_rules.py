"""C6b step 1: the collector-only verdict rules (b) cp.async and (c) the atomic chain --
sync_dominance.analyze(co_async=, co_r3=), run_cuvein._analyze_reports(co_async=, co_r3=),
parallel.py analyze --co-async / --co-r3, $CUVEIN_CO_ASYNC=1 / $CUVEIN_CO_R3. Default off
(co_r3 'cfg'), output byte-identical when off; on a dump with any hb_* key (vector-clock,
scalar-clock) they change nothing.

(b) co_async: an LDGSTS copy belongs to its thread's async agent (T1a, async_pcs; a kernel with
ARRIVES.LDGSTSBAR keeps the pre-T1a reading). An edge with a same-thread instance whose earlier
access is a copy is a cross-agent candidate, reported (tag `async`) unless a `DEPBAR.LE SB0, 0x0`
lies on every CFG path from the copy to the later access; a non-zero count never orders it.
(c) co_r3: 'cfg' = region dominance (today), 'strict' = cfg and none of scalar-clock's
CFG-decidable declines (the _past_release landing check, write-before-lock) fires, 'off' = no
certificate. Verdicts that exist only because the certificate was withheld: `atomic_chain_off`.

Fixtures: synthetic kernels (hand-built CFGs), testdata/r3_closure (rtraw, A2-inverted schedule,
hb_* keys stripped) and testdata/co_rules (kernel JSONs + dots copied from the C1 collector-only
store final-2026-11-co: cuHadron memcpy/shared_readwrite_race racy and fixed, ScoR
race_interblock_none-lock_rtraw, matrix-multiplication-norace small). CPU only.
    .env/bin/python -m pytest python/test_co_rules.py -q
"""
import csv
import io
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

import sync_dominance as sd

_ROOT = Path(__file__).resolve().parents[1]
_TD = Path(__file__).resolve().parent / "testdata"
_CO = _TD / "co_rules"
_R3C_DOT = _TD / "r3_closure" / "race_interblock_none-lock_rtraw.sm_89.dot"
_R3C_JSON = _TD / "r3_closure" / "vector_clock_c58_run3.json"

sys.path.insert(0, str(_ROOT / "eval" / "baselines"))
import run_cuvein as rc  # noqa: E402
import parallel  # noqa: E402

assert rc.sd is sd and Path(sd.__file__).resolve().parent == _ROOT / "python", \
    f"run_cuvein imported {rc.sd.__file__}, not {_ROOT}/python (set CUVEIN_HOME={_ROOT})"

NONE, WARP, BLOCK, GRID = sd.NONE, sd.WARP, sd.BLOCK, sd.GRID
_DKEY = {"thread": "intra_thread", "warp": "intra_warp", "block": "intra_block",
         "grid": "intra_grid", "inst": "intra_instance_launch"}


@pytest.fixture(autouse=True)
def _no_env(monkeypatch):
    for v in ("CUVEIN_CO_ASYNC", "CUVEIN_CO_R3", "CUVEIN_CHAIN_CLOSURE"):
        monkeypatch.delenv(v, raising=False)


def _canon(x):
    return json.dumps(x, sort_keys=True, default=repr)


def _tags(rep):
    return {(v["ancient_pc"], v["current_pc"]): v for v in rep["verdicts"]}


# ---------------------------------------------------------------- hand-built CFGs
_M = "_Z5ktestv"


def _esc(t):
    bs = "\\"
    return t.replace(" ", bs + " ").replace("[", bs + "[").replace("]", bs + "]") \
        .replace("{", bs + "{").replace("}", bs + "}")


def _dot(blocks, edges=()):
    """blocks = [(name, [(pc, 'SASS text'), ...]), ...], the first is the entry (named like the
    kernel); edges = [(src, dst)] between block names."""
    bs = "\\"
    nodes = []
    for i, (name, ins) in enumerate(blocks):
        name = _M if i == 0 else name
        body = "".join(f"{pc:04x}:{bs} {bs} {bs} {_esc(t)}{bs} ;{bs}l" for pc, t in ins)
        nodes.append(f'"{name}"\n[label="{{{body}}}"]\n')
    es = "".join(f'"{_M if s == blocks[0][0] else s}" -> "{_M if d == blocks[0][0] else d}"\n'
                 for s, d in edges)
    return ('digraph f {\nsubgraph "cluster_' + _M + '" {\n'
            'node [fontname="Courier",fontsize=10,shape=Mrecord];\n' + "".join(nodes) + es
            + '}\n}\n')


def _kj(flags, edges, extra=None):
    """flags = {pc: 'WRITE SHARED' ...}; edges = [(cur, anc, (dist names...))]."""
    doc = {"tool": "pc_dependency_analysis",
           "kernel": {"kernel_id": 0, "kernel_name": "ktest()", "device_id": 0, "kernel_pc": 0,
                      "grid_dim": [1, 1, 1], "block_dim": [64, 1, 1]},
           "nodes": [{"pc": pc, "flags": f} for pc, f in sorted(flags.items())],
           "edges": [{"current_pc": c, "ancient_pc": a, "cold_miss": False,
                      "current_access_size": 4,
                      "dist": {_DKEY[d]: 1 for d in ((ds,) if isinstance(ds, str) else ds)}}
                     for c, a, ds in edges]}
    doc.update(extra or {})
    return doc


def _write(tmp, name, dot_text, doc):
    d = Path(tmp) / name
    d.mkdir()
    (d / "k.dot").write_text(dot_text)
    (d / "kernel_0.json").write_text(json.dumps(doc))
    return str(d / "k.dot"), str(d / "kernel_0.json")


CP, LDS, CP2 = 0x10, 0x60, 0x30
COPY = "LDGSTS.E.BYPASS.LTC128B.128 [R5], [R2.64]"
FL = {CP: "WRITE SHARED", LDS: "READ SHARED"}


def _straight(wait, extra=()):
    """copy @0x10, commit, [wait @0x40], read of the copy's buffer @0x60, exit."""
    ins = [(0x00, "S2R R0, SR_TID.X"), (CP, COPY), (0x20, "LDGDEPBAR")] + list(extra)
    if wait is not None:
        ins.append((0x40, wait))
    ins += [(0x50, "NOP"), (LDS, "LDS R4, [R5]"), (0x70, "EXIT")]
    return _dot([("b0", sorted(ins))])


def _co(tmp, name, dot_text, edges, flags=FL, extra=None):
    return _write(tmp, name, dot_text, _kj(flags, edges, extra))


# ---------------------------------------------------------------- (b) cp.async
def test_copy_then_read_without_wait_is_reported(tmp_path):
    dot, kj = _co(tmp_path, "nowait", _straight(None), [(LDS, CP, "thread")])
    off = sd.analyze(dot, kj)
    assert off["verdicts"] == [] and off["skipped_edges"][0]["reason"] == "intra_thread_only"
    on = sd.analyze(dot, kj, co_async=True)
    v = _tags(on)[(CP, LDS)]
    assert v["verdict"] == "RACE" and v["race_type"] == "RAW" and v["async"] is True
    assert v["observed_distance"] == "warp" and v["strength"] == "none" and v["hb_chain"] is None
    assert on["diagnostics"]["co_rules"] == {"async": True, "async_pcs": 1, "r3": "cfg",
                                             "async_reports": 1, "r3_withheld": 0}


def test_wait_all_orders_the_copy(tmp_path):
    dot, kj = _co(tmp_path, "waitall", _straight("DEPBAR.LE SB0, 0x0"), [(LDS, CP, "thread")])
    on = sd.analyze(dot, kj, co_async=True)
    assert on["verdicts"] == [] and on["skipped_edges"][0]["reason"] == "intra_thread_only"
    assert on["diagnostics"]["co_rules"]["async_reports"] == 0


def test_wait_with_a_nonzero_count_never_orders(tmp_path):
    dot, kj = _co(tmp_path, "wait1", _straight("DEPBAR.LE SB0, 0x1"), [(LDS, CP, "thread")])
    v = _tags(sd.analyze(dot, kj, co_async=True))[(CP, LDS)]
    assert v["verdict"] == "RACE" and v["async"] is True


def test_double_buffer_depbar_le_1_is_reported(tmp_path):
    """Double buffering: copy buffer 0, commit, copy buffer 1, commit, wait_group 1, read buffer 0.
    wait_group 1 does complete buffer 0's group at run time, but the rule credits only a wait for
    all groups: reported."""
    ins = [(0x00, "S2R R0, SR_TID.X"), (CP, COPY), (0x20, "LDGDEPBAR"),
           (CP2, "LDGSTS.E.BYPASS.LTC128B.128 [R7], [R2.64+0x200]"), (0x38, "LDGDEPBAR"),
           (0x40, "DEPBAR.LE SB0, 0x1"), (0x50, "NOP"), (LDS, "LDS R4, [R5]"), (0x70, "EXIT")]
    flags = {**FL, CP2: "WRITE SHARED"}
    dot, kj = _co(tmp_path, "dbuf", _dot([("b0", ins)]), [(LDS, CP, "thread"), (CP2, CP, "thread")],
                  flags)
    on = sd.analyze(dot, kj, co_async=True)
    t = _tags(on)
    assert t[(CP, LDS)]["verdict"] == "RACE" and t[(CP, LDS)]["async"] is True
    assert (CP, CP2) not in t            # two copies of one thread: one agent, not a candidate
    assert sd.analyze(dot, kj)["verdicts"] == []


def test_wait_on_one_branch_only_is_reported(tmp_path):
    """The wait must lie on EVERY path from the copy to the read."""
    def kern(waits):
        b0 = [(0x00, "S2R R0, SR_TID.X"), (CP, COPY), (0x20, "LDGDEPBAR"), (0x28, "@P0 BRA 0x50")]
        b1 = [(0x30, waits[0]), (0x40, "BRA 0x58")]
        b2 = [(0x50, waits[1])]
        b3 = [(0x58, "NOP"), (LDS, "LDS R4, [R5]"), (0x70, "EXIT")]
        return _dot([("b0", b0), ("b1", b1), ("b2", b2), ("b3", b3)],
                    [("b0", "b1"), ("b0", "b2"), ("b1", "b3"), ("b2", "b3")])
    one = kern(("DEPBAR.LE SB0, 0x0", "NOP"))
    both = kern(("DEPBAR.LE SB0, 0x0", "DEPBAR.LE SB0, 0x0"))
    d1, k1 = _co(tmp_path, "onebranch", one, [(LDS, CP, "thread")])
    d2, k2 = _co(tmp_path, "bothbranches", both, [(LDS, CP, "thread")])
    assert _tags(sd.analyze(d1, k1, co_async=True))[(CP, LDS)]["verdict"] == "RACE"
    assert sd.analyze(d2, k2, co_async=True)["verdicts"] == []


def test_guarded_wait_does_not_count(tmp_path):
    dot, kj = _co(tmp_path, "guarded", _straight("@P1 DEPBAR.LE SB0, 0x0"), [(LDS, CP, "thread")])
    assert _tags(sd.analyze(dot, kj, co_async=True))[(CP, LDS)]["verdict"] == "RACE"


def test_copy_as_the_later_access_and_cross_thread_edges_are_unchanged(tmp_path):
    """Only an edge whose EARLIER access is the copy and that has a same-thread instance is a
    candidate: a read before the copy (program order orders it) and a cross-thread-only edge
    keep today's verdicts."""
    dot, kj = _co(tmp_path, "later", _straight(None),
                  [(CP, LDS, "thread"), (LDS, CP, "block")])
    off, on = sd.analyze(dot, kj), sd.analyze(dot, kj, co_async=True)
    strip = [{k: v for k, v in x.items() if k != "async"} for x in on["verdicts"]]
    assert _canon(strip) == _canon(off["verdicts"]) and on["skipped_edges"] == off["skipped_edges"]
    assert all(x["async"] is False for x in on["verdicts"])


def test_mixed_edge_loses_its_barrier_credit(tmp_path):
    """An edge with a same-thread and a cross-warp instance, a barrier but no wait in between:
    today ORDERED by the barrier (R1); the agent's instance is ordered by no barrier (T1a)."""
    ins = [(0x00, "S2R R0, SR_TID.X"), (CP, COPY), (0x20, "LDGDEPBAR"),
           (0x40, "BAR.SYNC.DEFER_BLOCKING 0x0"), (0x50, "NOP"), (LDS, "LDS R4, [R5]"),
           (0x70, "EXIT")]
    dot, kj = _co(tmp_path, "mixed", _dot([("b0", ins)]), [(LDS, CP, ("thread", "block"))])
    off = _tags(sd.analyze(dot, kj))[(CP, LDS)]
    assert off["verdict"] == "ORDERED" and off["observed_distance"] == "block"
    v = _tags(sd.analyze(dot, kj, co_async=True))[(CP, LDS)]
    assert v["verdict"] == "RACE" and v["async"] is True and v["observed_distance"] == "block"
    assert v["strength"] == "none" and v["ordering_syncs"] == []
    # with the wait before the barrier, the barrier's credit stands
    ins2 = ins[:3] + [(0x30, "DEPBAR.LE SB0, 0x0")] + ins[3:]
    d2, k2 = _co(tmp_path, "mixed2", _dot([("b0", ins2)]), [(LDS, CP, ("thread", "block"))])
    assert _tags(sd.analyze(d2, k2, co_async=True))[(CP, LDS)]["verdict"] == "ORDERED"


def test_mbarrier_kernel_keeps_the_pre_t1a_reading(tmp_path):
    dot, kj = _co(tmp_path, "mbar", _straight(None, [(0x28, "ARRIVES.LDGSTSBAR.64 [URZ+0x100]")]),
                  [(LDS, CP, "thread")])
    on = sd.analyze(dot, kj, co_async=True)
    assert on["verdicts"] == [] and on["diagnostics"]["co_rules"]["async_pcs"] == 0


def test_switches_do_nothing_on_a_clock_mode_dump(tmp_path):
    """A kernel JSON with an hb_* key is not collector-only: co_async and co_r3 are ignored."""
    dot, kj = _co(tmp_path, "clock", _straight(None), [(LDS, CP, "thread")],
                  extra={"hb_events": []})
    base = _canon(sd.analyze(dot, kj))
    for kw in ({"co_async": True}, {"co_r3": "off"}, {"co_r3": "strict"},
               {"co_async": True, "co_r3": "off"}):
        assert _canon(sd.analyze(dot, kj, **kw)) == base, kw


def test_bad_r3_mode_is_an_error(tmp_path):
    dot, kj = _co(tmp_path, "bad", _straight(None), [(LDS, CP, "thread")])
    with pytest.raises(ValueError):
        sd.analyze(dot, kj, co_r3="loose")
    assert rc.co_r3_mode() == "cfg"
    with pytest.raises(ValueError):
        rc.co_r3_mode("loose")


# ---------------------------------------------------------------- recorded fixtures (C1 store)
_MEMR, _MEMF = "P6-memcpy-shared_readwrite_race-racy", "P6-memcpy-shared_readwrite_race-fixed"
_RTRAW, _MM = "P5-race_interblock_none-lock_rtraw", "P4-matrix-multiplication-norace-small"


def _fx(pid):
    d = _CO / pid
    for dot in sorted((d / "dots").glob("*.dot")):
        kj = str(d / "collector-only" / "kernel_0.json")
        try:
            sd.analyze(str(dot), kj)
        except sd.AlignmentError:
            continue
        return str(dot), kj
    raise AssertionError(f"no dot aligns with {pid}")


def test_cuhadron_memcpy_racy_is_raw_fixed_is_clean():
    """F4: LDGSTS @0x70 -> LDS @0x90 with the wait (DEPBAR.LE SB0, 0x0) only after the read
    (@0xa0) in the racy build; the fixed build waits (@0x90) before its read (@0xa0)."""
    dot, kj = _fx(_MEMR)
    assert sd.analyze(dot, kj)["verdicts"] == []                 # C1: the miss
    for cc in (False, True):
        rep = sd.analyze(dot, kj, chain_closure=cc, co_async=True)
        races = [v for v in rep["verdicts"] if v["verdict"] == "RACE"]
        assert [(v["ancient_pc"], v["current_pc"], v["race_type"], v["space"], v["async"])
                for v in races] == [(0x70, 0x90, "RAW", "shared", True)]
    dot, kj = _fx(_MEMF)
    for cc in (False, True):
        rep = sd.analyze(dot, kj, chain_closure=cc, co_async=True)
        assert [v for v in rep["verdicts"] if v["verdict"] in ("RACE", "SC")] == []


def test_rtraw_pair_under_off_and_strict():
    """ScoR race_interblock_none-lock_rtraw, C1 collector-only recording: the pair scalar-clock
    reports (the dummy stores 0x170 / 0x2f0, WAW across the blocks) is ORDERED today by the
    chain 0x1b0 (block 1's unlock) -> 0x230 (block 0's CAS). off: reported (RACE, tagged
    atomic_chain_off). strict: STILL ORDERED -- the chain lands on block 0's own CAS acquire, so
    the landing check (a non-CAS landing) does not apply, and no CAS lies between 0x170 and the
    release 0x1b0 in program order, so write-before-lock does not fire either. The rtraw pair
    proper (0x140 -> 0x340, derived with the chain closure) is SC (strong conflict) in all three
    modes: R3 already declines it under cfg (_past_release)."""
    dot, kj = _fx(_RTRAW)
    for cc in (False, True):
        t = {m: _tags(sd.analyze(dot, kj, chain_closure=cc, co_r3=m)) for m in sd.CO_R3_MODES}
        assert t["cfg"][(0x170, 0x2f0)]["verdict"] == "ORDERED"
        assert t["cfg"][(0x170, 0x2f0)]["hb_chain"] == ["0x1b0", "0x230"]
        assert t["strict"][(0x170, 0x2f0)]["verdict"] == "ORDERED"
        assert t["strict"][(0x170, 0x2f0)]["atomic_chain_off"] is False
        v = t["off"][(0x170, 0x2f0)]
        assert v["verdict"] == "RACE" and v["race_type"] == "WAW" and v["atomic_chain_off"] is True
        assert v["hb_chain"] is None and v["observed_distance"] == "grid"
        if cc:
            for m in sd.CO_R3_MODES:
                assert t[m][(0x140, 0x340)]["verdict"] == "SC"
            assert t["off"][(0x140, 0x340)]["atomic_chain_off"] is False


def test_matrix_multiplication_norace_lock_ordered_under_strict():
    """matrix-multiplication-norace's locks (CAS 0x540 / EXCH 0x5c0 and CAS 0x910 / EXCH 0x9a0,
    fenced sections): the in-section pairs stay ORDERED under strict; under off they become
    strong conflicts (SC: both accesses .STRONG.SYS), tagged atomic_chain_off."""
    dot, kj = _fx(_MM)
    for cc in (False, True):
        cfg = _tags(sd.analyze(dot, kj, chain_closure=cc))
        strict = sd.analyze(dot, kj, chain_closure=cc, co_r3="strict")
        off = sd.analyze(dot, kj, chain_closure=cc, co_r3="off")
        locked = [k for k, v in cfg.items() if v["hb_chain"]]
        assert {(0x5a0, 0x590), (0x980, 0x960)} <= set(locked)
        assert len(locked) == (4 if cc else 2)
        st, of = _tags(strict), _tags(off)
        for k in locked:
            assert st[k]["verdict"] == "ORDERED" and st[k]["hb_chain"] == cfg[k]["hb_chain"]
            assert of[k]["verdict"] == "SC" and of[k]["atomic_chain_off"] is True
        assert strict["summary"]["races"] == strict["summary"]["sc"] == 0
        assert off["summary"]["races"] == 0 and off["summary"]["sc"] == len(locked)
        assert off["diagnostics"]["co_rules"]["r3_withheld"] == len(locked)


def test_r3_closure_rtraw_has_no_certificate_to_withhold(tmp_path):
    """testdata/r3_closure (rtraw, A2-inverted schedule; hb_* keys stripped): no certificate
    under cfg already (no 0x1b0 -> 0x230 hop), so strict and off withhold nothing -- the tag is
    False everywhere and the verdicts equal cfg's."""
    t = json.loads(_R3C_JSON.read_text())
    t = {k: v for k, v in t.items() if not k.startswith("hb_") and k != "coherence_profile"}
    kj = tmp_path / "kernel_0.json"
    kj.write_text(json.dumps(t))
    base = sd.analyze(str(_R3C_DOT), str(kj), chain_closure=True)
    for m in ("strict", "off"):
        rep = sd.analyze(str(_R3C_DOT), str(kj), chain_closure=True, co_r3=m)
        assert all(v["atomic_chain_off"] is False for v in rep["verdicts"])
        strip = [{k: x for k, x in v.items() if k != "atomic_chain_off"} for v in rep["verdicts"]]
        assert _canon(strip) == _canon(base["verdicts"])


def test_strict_landing_check_decided_on_the_cfg(tmp_path):
    """One thread's code: CAS 0x10, fence, store 0x30, fence, EXCH 0x50 (unlock), store 0x60 after
    the unlock. The only sync hop is 0x50 -> 0x50 (one thread's unlock to another's), a landing on
    a non-CAS RMW with cur = 0x60 after it. cfg: the trace never joins 0x50 to the CAS 0x10 (no
    edge), so the landing check stays silent and the chain certifies (0x30, 0x60); strict takes
    the location condition as true: the landing check fires, no certificate, a report tagged
    atomic_chain_off."""
    ins = [(0x00, "S2R R0, SR_TID.X"), (0x10, "ATOMG.E.CAS.STRONG.GPU PT, R0, [R2], R4, R5"),
           (0x20, "MEMBAR.SC.GPU"), (0x30, "STG.E [R6.64], R7"), (0x40, "MEMBAR.SC.GPU"),
           (0x50, "ATOMG.E.EXCH.STRONG.GPU PT, RZ, [R2.64], RZ"), (0x60, "STG.E [R8.64], R7"),
           (0x70, "EXIT")]
    flags = {0x10: "READWRITE GLOBAL", 0x30: "WRITE GLOBAL", 0x50: "READWRITE GLOBAL",
             0x60: "WRITE GLOBAL"}
    edges = [(0x60, 0x30, "grid"), (0x50, 0x50, "grid")]
    dot, kj = _write(tmp_path, "lock", _dot([("b0", ins)]), _kj(flags, edges))
    cfg = _tags(sd.analyze(dot, kj))[(0x30, 0x60)]
    assert cfg["verdict"] == "ORDERED" and cfg["hb_chain"]
    st = _tags(sd.analyze(dot, kj, co_r3="strict"))[(0x30, 0x60)]
    assert st["verdict"] == "RACE" and st["atomic_chain_off"] is True and st["hb_chain"] is None


# ---------------------------------------------------------------- harness
def _store(tmp_path, pid, extra_mode=None):
    s = tmp_path / "store" / pid
    shutil.copytree(_CO / pid, s)
    if extra_mode:      # the same collector-only dump filed under another mode's name
        shutil.copytree(s / "collector-only", s / extra_mode)
        meta = json.loads((s / "meta.json").read_text())
        meta["modes"][extra_mode] = meta["modes"]["collector-only"]
        (s / "meta.json").write_text(json.dumps(meta))
    return s


_TIMER = re.compile(r";analysis_s=[0-9.]+")


def _rows(idir, tmp_path, tag, **kw):
    cdir = tmp_path / f"confirm-{tag}"
    cdir.mkdir()
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=parallel.blib.COLUMNS)
    w.writeheader()
    parallel.analyze_one(str(idir), w, str(cdir), analysis_workers=1, **kw)
    rows = list(csv.DictReader(io.StringIO(buf.getvalue())))
    conf = {p.name.split("__")[-1][:-5]: json.loads(p.read_text()) for p in cdir.glob("*.json")}
    return rows, conf


def test_analyze_one_notes_raw_tags_and_mode_scope(tmp_path, monkeypatch):
    CO, VC = parallel.CO, parallel.VC
    monkeypatch.setattr(parallel, "MODES", (VC, CO))
    idir = _store(tmp_path, _MEMR, extra_mode=VC)
    off, conf_off = _rows(idir, tmp_path, "off")
    assert {r["mode"]: r["verdict"] for r in off} == {VC: "CLEAN", CO: "CLEAN"}
    assert not any("co_" in r["notes"] for r in off)
    assert '"async"' not in json.dumps(conf_off) and "atomic_chain_off" not in json.dumps(conf_off)
    for tag, kw, env in (("kw", {"co_async": True, "co_r3": "off"}, {}),
                         ("env", {}, {"CUVEIN_CO_ASYNC": "1", "CUVEIN_CO_R3": "off"})):
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        on, conf = _rows(idir, tmp_path, tag, **kw)
        by = {}
        for r in on:
            by.setdefault(r["mode"], []).append(r)
        # the vector-clock-named dir gets the defaults: unchanged, no tokens
        assert [_TIMER.sub("", r["notes"]) for r in by[VC]] == \
            [_TIMER.sub("", r["notes"]) for r in off if r["mode"] == VC]
        assert all(r["verdict"] == "CLEAN" for r in by[VC])
        for r in by[CO]:
            assert r["verdict"] == "RACE" and r["report_ids"] == "shared:0x70-0x90:RAW"
            assert r["notes"].endswith(";co_async=1;co_r3=off"), r["notes"]
        raw = conf[CO]["raw"]
        assert [(x["a_pc"], x["b_pc"], x["async"], x["atomic_chain_off"]) for x in raw] == \
            [(0x70, 0x90, True, False)]
        assert '"async"' not in json.dumps(conf[VC])
        for k in env:
            monkeypatch.delenv(k)


def test_analyze_reports_off_is_byte_identical_and_r3_tag():
    for pid in (_MEMR, _MEMF, _RTRAW, _MM):
        d, dots = str(_CO / pid / "collector-only"), str(_CO / pid / "dots")
        base = _canon(rc._analyze_reports(d, dots, workers=1))
        assert _canon(rc._analyze_reports(d, dots, workers=1, co_async=False, co_r3="cfg")) == base
        assert '"async"' not in base and "atomic_chain_off" not in base
    d, dots = str(_CO / _RTRAW / "collector-only"), str(_CO / _RTRAW / "dots")
    ids, _, raw = rc._analyze_reports(d, dots, workers=1, co_r3="off")
    assert ids == ["global:0x170-0x2f0:WAW"]
    assert [(r["a_pc"], r["b_pc"], r["atomic_chain_off"]) for r in raw] == [(0x170, 0x2f0, True)]
    assert all("async" not in r for r in raw)
    assert _canon(rc._analyze_reports(d, dots, workers=4, co_r3="off", co_async=True,
                                      chain_closure=True)) == \
        _canon(rc._analyze_reports(d, dots, workers=1, co_r3="off", co_async=True,
                                   chain_closure=True))


def test_env_resolution_and_cli_flags(monkeypatch):
    assert rc.co_async_enabled() is False and rc.co_async_enabled(True) is True
    monkeypatch.setenv("CUVEIN_CO_ASYNC", "1")
    assert rc.co_async_enabled() is True and rc.co_async_enabled(False) is False
    monkeypatch.setenv("CUVEIN_CO_R3", "strict")
    assert rc.co_r3_mode() == "strict" and rc.co_r3_mode("cfg") == "cfg"
    assert rc.co_note(False, "cfg") == "" and rc.co_note(True, "strict") == ";co_async=1;co_r3=strict"
    monkeypatch.setattr(sys, "argv", ["parallel.py", "analyze", "--co-async", "--co-r3", "off",
                                      "--id", "x"])
    seen = {}
    monkeypatch.setattr(parallel, "cmd_analyze", lambda a: seen.update(vars(a)))
    parallel.main()
    assert seen["co_async"] is True and seen["co_r3"] == "off"

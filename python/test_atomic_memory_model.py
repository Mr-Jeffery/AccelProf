"""Phase 2 memory-model discriminator (relaxed vs release/acquire atomics).

The HB certificate requires that every HB edge the model creates is honored by the
hardware. For an atomic release/acquire that means a RELAXED / unfenced atomic must NOT
synchronize surrounding non-atomic accesses -- otherwise the model hides a real race
(a false negative = unsound).

testdata/atomic_mm_handoff.cu is one kernel in two versions that differ in exactly one
thing, the flag atomics' memory order:
  handoff_strong  : release/acquire + __threadfence()  -> the data read IS PTX-ordered
                    after the data write        -> NORACE (sound control; must hold).
  handoff_relaxed : memory_order_relaxed, no fence     -> the data read is NOT PTX-ordered
                    -> a genuine race           -> the model MUST report a race.

FINDING (RTX 4060 Ti, sm_89, CUDA 13.2): on this toolchain BOTH the relaxed and the
release/acquire device-scope atomics disassemble to the identical opcode
`ATOM.E.{EXCH,ADD}.STRONG.GPU`; the ONLY SASS difference is that handoff_strong carries
`MEMBAR.SC.GPU` + `MEMBAR.ALL.GPU` fences that handoff_relaxed lacks. `.STRONG` is a
coherence-SCOPE marker, not a release/acquire-ordering marker. sync_dominance.atomic_scope
keys the synchronizing scope on `.STRONG.<scope>` alone, so it gives the RELAXED flag the
same GRID scope as the strong one, and the runtime HB model (oracle + engine) orders the
non-atomic data access in BOTH -> handoff_relaxed is reported NORACE = a false negative.

=> The model is currently UNSOUND on unfenced/relaxed atomics that publish non-atomic
   state. The relaxed-should-race assertion is therefore marked xfail(strict) so it (a)
   documents the known unsoundness and (b) turns into a FAILURE the moment a fix makes the
   race visible, prompting this xfail to be removed. See the Phase 2 report.

The sound control (handoff_strong -> norace) is a plain assertion and must always hold.
Uses the Python oracle (self-contained: no atomic-scope sidecar / YOSEMITE env needed);
builds on demand and skips if no GPU / nvcc, mirroring test_intersubwarp_readwrite.

T10 (D9, the last section): a load/store's strength and scope come from its SASS token
(.STRONG.<scope>), in the sidecar's strength column, the engine, the oracle and R2 alike.
testdata/strong_ldst_scopes.cu has one strong-store/strong-load litmus per scope (cta, gpu,
sys) at two distances; the DR/SC class is asserted in both modes, engine == oracle, the
sidecar's lines, and the pre-T10 `generic` policy (a sidecar without the column) end to end.
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import atomic_scope_sidecar
import hb_oracle as ho
import sync_dominance as sd

_ROOT = Path(__file__).resolve().parents[1]
_SRC = Path(__file__).resolve().parent / "testdata" / "atomic_mm_handoff.cu"


def _artifacts():
    """(dots, {kernel_substr: trace}) built on demand; None if no source/GPU/build."""
    if not _SRC.is_file():
        return None
    work = _ROOT / "cuHadron" / "_mm_handoff"      # a gitignored scratch area
    work.mkdir(parents=True, exist_ok=True)
    binary = work / "mm.out"
    ext = work / "mm_extracted_cubins"

    def _collect():
        dots = sorted(ext.glob("*.dot"))
        deps = sorted(work.glob("dependency_mm*"))
        traces = sorted(deps[-1].glob("kernel_*.json")) if deps else []
        by_name = {}
        for t in traces:
            nm = json.loads(t.read_text())["kernel"]["kernel_name"]
            if "strong" in nm:
                by_name["strong"] = t
            elif "relaxed" in nm:
                by_name["relaxed"] = t
        return dots, by_name

    dots, by_name = _collect()
    if dots and {"strong", "relaxed"} <= by_name.keys():
        return dots, by_name

    build = subprocess.run(
        ["nvcc", "-arch=native", "-lineinfo", "--cudart", "shared",
         str(_SRC), "-o", str(binary)], cwd=work, capture_output=True)
    if build.returncode != 0 or not binary.exists():
        return None
    subprocess.run(["bash", str(_ROOT / "getall.sh"), str(binary.resolve())],
                   cwd=_ROOT, capture_output=True, timeout=600)
    dots, by_name = _collect()
    return (dots, by_name) if dots and {"strong", "relaxed"} <= by_name.keys() else None


def _oracle(dots, trace):
    for dot in dots:
        try:
            return ho.analyze(dot, trace)
        except sd.AlignmentError:
            continue
    raise AssertionError(f"no CFG aligns with {trace}")


def _data_races(report):
    # races on the contested non-atomic global g_data (RAW/WAR/WAW), not the flag atomics
    return [r for r in report["races"] if r["kind"] in ("RAW", "WAR", "WAW")]


def test_strong_handoff_is_norace():
    """SOUND control: a proper release/acquire + fence handoff must order the data read
    after the data write -> zero races. Must always hold."""
    art = _artifacts()
    if art is None:
        pytest.skip("no GPU / nvcc / source to build atomic_mm_handoff")
    dots, by = art
    report = _oracle(dots, by["strong"])
    assert report["summary"]["races"] == 0, \
        f"release/acquire handoff must be race-free, got {report['races']}"


@pytest.mark.xfail(strict=True, reason="KNOWN UNSOUND (Phase 2): .STRONG is a coherence-"
                   "scope marker present on relaxed atomics too; atomic_scope treats the "
                   "unfenced relaxed flag as synchronizing, hiding this real race. Remove "
                   "this xfail when the fence-aware scope fix lands.")
def test_relaxed_handoff_should_race():
    """A relaxed/unfenced atomic must NOT order the surrounding non-atomic access, so the
    data read genuinely races the data write. Currently the model reports norace (unsound)
    -> xfail. Flips to a failure (prompting xfail removal) once the model is fixed."""
    art = _artifacts()
    if art is None:
        pytest.skip("no GPU / nvcc / source to build atomic_mm_handoff")
    dots, by = art
    report = _oracle(dots, by["relaxed"])
    assert len(_data_races(report)) >= 1, \
        "relaxed handoff: data read is not PTX-ordered after the write and must race"


# --- T10 (D9): strength and scope from the SASS token ----------------------------------------

_SCOPES_SRC = Path(__file__).resolve().parent / "testdata" / "strong_ldst_scopes.cu"
_LITMUS = ("cta_interwarp", "gpu_interwarp", "sys_interwarp",
           "cta_interblock", "gpu_interblock", "sys_interblock", "plain_interblock")
# The class under the default policy (token): DR only where a scope does not cover the other
# thread (cta across blocks) or an access is weak (the plain control).
_TOKEN_CLASS = {"cta_interwarp": "SC", "gpu_interwarp": "SC", "sys_interwarp": "SC",
                "cta_interblock": "DR", "gpu_interblock": "SC", "sys_interblock": "SC",
                "plain_interblock": "DR"}
_SASS_SCOPE = {"cta": ("SM", sd.BLOCK), "gpu": ("GPU", sd.GRID), "sys": ("SYS", sd.GRID)}


def _getall(tmp_path_factory, policy=None):
    """(dots, {kernel: trace}, sidecar text) of one getall.sh run of strong_ldst_scopes.cu,
    with CUVEIN_STRONG_LDST=policy if given (the sidecar, hence the engine, follows it)."""
    if not _SCOPES_SRC.is_file() or shutil.which("nvcc") is None:
        pytest.skip("no nvcc / source (run on a GPU node)")
    d = tmp_path_factory.mktemp(f"strong_ldst_{policy or 'default'}")
    binary = d / "strong_ldst_scopes"
    b = subprocess.run(["nvcc", "-arch=native", "-lineinfo", "--cudart", "shared",
                        str(_SCOPES_SRC), "-o", str(binary)], capture_output=True)
    if b.returncode != 0:
        pytest.skip(f"build failed: {b.stderr.decode()[-300:]}")
    env = dict(os.environ)
    env.pop("CUVEIN_STRONG_LDST", None)
    if policy:
        env["CUVEIN_STRONG_LDST"] = policy
    subprocess.run(["bash", str(_ROOT / "getall.sh"), str(binary)], cwd=_ROOT, env=env,
                   capture_output=True, timeout=600)
    ext = d / "strong_ldst_scopes_extracted_cubins"
    dots = sorted(ext.glob("*.dot"))
    by = {}
    for t in sorted(d.glob("dependency_strong_ldst_scopes*/kernel_*.json")):
        nm = json.loads(t.read_text())["kernel"]["kernel_name"]
        for k in _LITMUS:
            if nm.startswith(k + "("):
                by[k] = t
    if not dots or set(_LITMUS) - by.keys():
        pytest.skip("no trace produced (GPU / collector unavailable)")
    side = ext / "atomic_scope.txt"
    return dots, by, side.read_text() if side.exists() else ""


@pytest.fixture(scope="module")
def scopes_run(tmp_path_factory):
    return _getall(tmp_path_factory)


@pytest.fixture(scope="module")
def scopes_generic(tmp_path_factory):
    return _getall(tmp_path_factory, "generic")


def _pair(trace):
    """(dump, store record, load record) of a litmus kernel's one conflict."""
    t = json.loads(Path(trace).read_text())
    mem = [e for e in sorted(t["hb_events"], key=lambda e: e["seq"]) if "lanes" in e]
    ld = next(e for e in mem if e["type"] == "read")
    st = next(e for e in mem if e["type"] == "write"
              and e["lanes"][0]["addr"] == ld["lanes"][0]["addr"])
    return t, st, ld


def _ops(dots, t, *pcs):
    """(the aligning dot, the opcodes of pcs) for a dump."""
    for dot in dots:
        try:
            kernels = sd.parse_dot(dot)
            g = sd.HBGraph(*kernels[sd.select_kernel(kernels, t["kernel"]["kernel_name"])])
            return dot, [g.pc_opcode[pc] for pc in pcs]
        except sd.AlignmentError:
            continue
    raise AssertionError("no CFG aligns with the trace")


def _tid(e):
    return (e["block"] << 10) | (e["warp"] << 5) | e["lanes"][0]["lane"]


def _expected(kernel, dots, t, st, ld):
    """The pair's class by the definition, from the active policy's strength table."""
    _, (sop, lop) = _ops(dots, t, st["pc"], ld["pc"])
    ms = sd.morally_strong(sd.coherent_scope(sop), _tid(st), sd.coherent_scope(lop), _tid(ld))
    cls = "SC" if ms else "DR"
    if sd.strong_ldst_policy() == "token":
        assert cls == _TOKEN_CLASS[kernel], (kernel, sop, lop)
    return cls


def _pair_verdict(dot, trace, a, b):
    rep = sd.analyze(dot, trace)
    vs = [v for v in rep["verdicts"] if {v["current_pc"], v["ancient_pc"]} == {a, b}]
    assert len(vs) == 1, vs
    return vs[0]


@pytest.mark.parametrize("op,policy,want", [
    ("LDG.E.STRONG.SYS", "token", sd.GRID),          # volatile / ld.relaxed.sys.global
    ("STG.E.STRONG.GPU", "token", sd.GRID),
    ("LDG.E.STRONG.SM", "token", sd.BLOCK),          # ld.relaxed.cta.global
    ("ST.E.STRONG.CTA", "token", sd.BLOCK),
    ("LD.E.64.STRONG.SYS", "token", sd.GRID),        # cuda::atomic load, generic form
    ("LDG.E", "token", None),                        # plain
    ("LDS", "token", None),                          # shared: no token in SASS -> weak
    ("LDG.E.STRONG.XYZ", "token", None),             # unknown scope -> weak (errs narrow)
    ("LDG.E.STRONG", "token", None),                 # no scope -> weak
    ("LDGSTS.E.BYPASS.LTC128B.128", "token", None),  # a copy is never strong
    ("ATOMG.E.CAS.STRONG.GPU", "token", sd.GRID),    # the RMW column is unchanged
    ("ATOMS.ADD", "token", sd.BLOCK),
    ("ATOMG.E.ADD", "token", sd.NONE),               # an RMW naming no scope: empty scope
    ("RED.E.ADD.STRONG.SM", "token", sd.BLOCK),
    ("LDG.E.STRONG.SYS", "generic", None),           # the pre-T10 policies are unchanged
    ("LD.E.STRONG.SYS", "generic", sd.GRID),
    ("LDG.E.STRONG.SYS", "all", sd.GRID),
    ("LDG.E.STRONG.XYZ", "all", sd.NONE),
    ("LD.E.STRONG.SYS", "none", None),
])
def test_strength_token_rule(op, policy, want):
    assert sd.coherent_scope(op, policy) == want


def test_default_policy_is_token(monkeypatch):
    monkeypatch.delenv("CUVEIN_STRONG_LDST", raising=False)
    assert sd.strong_ldst_policy() == "token"
    monkeypatch.setenv("CUVEIN_STRONG_LDST", "generic")
    assert sd.strong_ldst_policy() == "generic"


def test_sidecar_strength_lines_only_under_token(tmp_path):
    """The strength column is written under `token` for every memory pc and not at all
    under a pre-T10 policy, whose file is the pre-T10 sidecar."""
    dot = Path(__file__).resolve().parent / "testdata" / "norace_interwarp_barrier_raw.sm_86.dot"
    out = {}
    for pol in ("token", "generic"):
        p = tmp_path / f"{pol}.txt"
        atomic_scope_sidecar.main([str(dot), "-o", str(p), "--strong-ldst", pol])
        out[pol] = p.read_text().splitlines()
    strength = [ln for ln in out["token"] if ln.startswith("# strength ")]
    mem = {pc for blocks, _, _ in sd.parse_dot(dot).values() for ins in blocks.values()
           for pc, op in ins if sd.classify(op) == "mem"}
    assert {int(ln.split()[2]) for ln in strength} == mem and len(strength) == len(mem)
    assert all(ln.split()[3:5] == ["weak", "-"] for ln in strength)   # LDS, STS, STG.E
    assert [ln for ln in out["token"] if not ln.startswith("# strength ")] == out["generic"]
    assert not [ln for ln in out["generic"] if ln.startswith("# strength ")]


def test_sidecar_strength_column(scopes_run):
    """Step 1: the strength column names every litmus access -- the strong ones with their
    scope, the plain control weak -- and the old `ldst` lines list the same strong pcs (an
    engine older than T10 reads those and computes the same races)."""
    dots, by, side = scopes_run
    lines = side.splitlines()
    for k, trace in by.items():
        t, st, ld = _pair(trace)
        key = re.sub(r"\s+", "", t["kernel"]["kernel_name"])
        _, (sop, lop) = _ops(dots, t, st["pc"], ld["pc"])
        for pc, op in ((st["pc"], sop), (ld["pc"], lop)):
            if k == "plain_interblock":
                assert op.split(".")[0] in ("STG", "LDG") and "STRONG" not in op.split("."), op
                assert f"# strength {pc} weak - {key}" in lines
                assert not [ln for ln in lines if ln.startswith(f"{pc} ") and ln.endswith(key)]
            else:
                tok, scope = _SASS_SCOPE[k.split("_")[0]]
                # the address-spaced form the pre-T10 generic policy called weak
                assert op.split(".")[0] in ("STG", "LDG") and op.endswith(f".STRONG.{tok}"), op
                assert f"# strength {pc} strong {scope} {key}" in lines
                assert f"{pc} {scope} ldst {key}" in lines


@pytest.mark.parametrize("kernel", _LITMUS)
def test_strong_ldst_class(scopes_run, kernel, tmp_path):
    """Step 3: the pair's DR/SC class, in the engine's hb_races and in both modes' verdicts."""
    dots, by, _ = scopes_run
    t, st, ld = _pair(by[kernel])
    cls = _expected(kernel, dots, t, st, ld)
    recs = [r for r in t.get("hb_races", []) if {r["a_pc"], r["b_pc"]} == {st["pc"], ld["pc"]}]
    assert recs and {r["class"] for r in recs} == {cls}, recs
    dot, _ = _ops(dots, t, st["pc"])
    v = _pair_verdict(dot, by[kernel], st["pc"], ld["pc"])
    assert (v["verdict"], v["hb_class"], v["conflict_class"]) == \
        (("SC", "sc", "SC") if cls == "SC" else ("RACE", "structural", "DR")), v
    stripped = dict(t)
    for key in ("hb_races", "hb_races_sync_only", "coherence_profile"):
        stripped.pop(key, None)
    sp = tmp_path / "scalar_clock.json"
    sp.write_text(json.dumps(stripped))
    v = _pair_verdict(dot, sp, st["pc"], ld["pc"])
    assert (v["verdict"], v["conflict_class"]) == \
        (("SC", "SC") if cls == "SC" else ("RACE", "DR")), v


def _race_key(r):
    return (r.get("a_pc"), r["b_pc"], r["kind"], r.get("class"), r["space"], r.get("dist"),
            r.get("async"), r.get("count"))


@pytest.mark.parametrize("kernel", _LITMUS)
def test_strong_ldst_engine_matches_oracle(scopes_run, kernel):
    dots, by, _ = scopes_run
    t = json.loads(by[kernel].read_text())
    dot, _ = _ops(dots, t)
    rep = ho.analyze(dot, by[kernel])
    assert sorted({_race_key(r) for r in t.get("hb_races", [])}) == \
        sorted({_race_key(r) for r in rep["races"]}), kernel
    assert t.get("hb_races_sync_only") == rep["races_sync_only"], kernel


def test_generic_sidecar_keeps_pre_t10_behaviour(scopes_generic):
    """Old sidecars keep today's behaviour: under CUVEIN_STRONG_LDST=generic the sidecar has
    no strength column, the engine takes the pre-T10 path, equals the oracle under generic,
    and every pair of the litmus is a DR (the address-spaced strong forms are weak there)."""
    dots, by, side = scopes_generic
    assert side and not [ln for ln in side.splitlines() if ln.startswith("# strength ")]
    for k, trace in by.items():
        t, st, ld = _pair(trace)
        dot, _ = _ops(dots, t)
        rep = ho.analyze(dot, trace, strong_ldst="generic")
        assert sorted({_race_key(r) for r in t.get("hb_races", [])}) == \
            sorted({_race_key(r) for r in rep["races"]}), k
        recs = [r for r in t["hb_races"] if {r["a_pc"], r["b_pc"]} == {st["pc"], ld["pc"]}]
        assert recs and {r["class"] for r in recs} == {"DR"}, (k, recs)

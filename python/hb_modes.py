"""The two cuVein analysis modes, and the names they had before task T8 (2026-09-23).

scalar-clock   was "trace-only" / "no-engine". The collector only dumps hb_events
               (YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=scalar-clock); the verdicts come
               from the static leg (R1/R2/R3) and sync_dominance.barrier_only_pairs(),
               which needs only a per-thread scalar epoch.
vector-clock   was "engine". The in-process HbEngine (full scoped vector clocks,
               per-address release/acquire) runs over the same event stream
               (YOSEMITE_HB_MODE=vector-clock, the default under YOSEMITE_HB_TRACE=1)
               and its hb_races / hb_races_sync_only are crossed into the verdicts;
               python/hb_oracle.py is its exact offline oracle.

Not mode names (unchanged by T8): the HbEngine class, hb_engine_* functions, the
kernel_N.json keys (hb_events, hb_races, hb_races_sync_only, coherence_profile,
tv_violation), the E*.csv timing columns t_trace / t_engine, the oracle state
"engine-only" (engine result not cross-checked against the oracle).

Persisted artifacts were rewritten by eval/baselines/migrate_mode_names.py. For one
release every reader still accepts the old names through canon() / resolve_dir() /
resolve_confirm(), which print one deprecation line per source; with
CUVEIN_NO_LEGACY_NAMES=1 they raise instead (the T8 acceptance check runs that way).
"""
import os
import sys

VECTOR_CLOCK = "vector-clock"
SCALAR_CLOCK = "scalar-clock"
MODES = (VECTOR_CLOCK, SCALAR_CLOCK)          # collection order used by the harness
LEGACY = {"engine": VECTOR_CLOCK, "trace-only": SCALAR_CLOCK, "no-engine": SCALAR_CLOCK}
LEGACY_OF = {VECTOR_CLOCK: "engine", SCALAR_CLOCK: "trace-only"}
LABEL = {VECTOR_CLOCK: "cuVein (vector-clock)", SCALAR_CLOCK: "cuVein (scalar-clock)"}
SHORT = {VECTOR_CLOCK: "cuVein-VC", SCALAR_CLOCK: "cuVein-SC"}
ENV = "YOSEMITE_HB_MODE"                      # read by the collector
LEGACY_ENV = "YOSEMITE_HB_NO_ENGINE"          # pre-T8; the collector still honours it (warns)


class LegacyNameError(ValueError):
    """A pre-T8 mode name was met while CUVEIN_NO_LEGACY_NAMES is set."""


_warned = set()


def _legacy(source, what):
    if os.environ.get("CUVEIN_NO_LEGACY_NAMES"):
        raise LegacyNameError(f"{source or '<input>'}: pre-T8 {what}")
    key = source or "<input>"
    if key not in _warned:
        _warned.add(key)
        print(f"DEPRECATED (pre-T8 mode names): {key}: {what}; migrate with "
              f"eval/baselines/migrate_mode_names.py", file=sys.stderr, flush=True)


def canon(mode, source=""):
    """A mode name as read from a CSV row / meta.json / confirm file -> the T8 name.
    '' (non-cuVein rows) and the new names pass through unchanged."""
    if mode in LEGACY:
        _legacy(source, f"mode {mode!r} (now {LEGACY[mode]!r})")
        return LEGACY[mode]
    return mode


def check(mode):
    """Validate a mode given on a command line / in $BASELINE_MODES (legacy accepted)."""
    m = canon(mode, "command line / $BASELINE_MODES")
    if m not in MODES:
        raise ValueError(f"unknown cuVein mode {mode!r}: expected one of {MODES}")
    return m


def parse_modes(spec):
    """'vector-clock,scalar-clock' -> tuple of checked mode names."""
    return tuple(check(m.strip()) for m in spec.split(",") if m.strip())


def collector_env(mode):
    """The collector's environment for one mode (YOSEMITE_HB_TRACE is set by the caller)."""
    return {ENV: check(mode)}


_supported = {}


def engine_library(accel_prof_home):
    """Path of the libsanalyzer.so the collector of <accel_prof_home> loads: the first
    RPATH/RUNPATH entry of lib/libcompute_sanitizer.so that holds one (readelf), else
    the documented install location build/sanalyzer/lib."""
    import subprocess
    coll = os.path.join(accel_prof_home, "lib", "libcompute_sanitizer.so")
    try:
        out = subprocess.run(["readelf", "-d", coll], capture_output=True, text=True,
                             timeout=60).stdout
        for line in out.splitlines():
            if "RPATH" in line or "RUNPATH" in line:
                for d in line.split("[", 1)[1].rsplit("]", 1)[0].split(":"):
                    cand = os.path.join(d, "libsanalyzer.so")
                    if os.path.exists(cand):
                        return cand
    except (OSError, IndexError, subprocess.SubprocessError):
        pass
    return os.path.join(accel_prof_home, "build", "sanalyzer", "lib", "libsanalyzer.so")


def require_collector_support(accel_prof_home):
    """Refuse to collect with an engine library that predates T8: it ignores
    YOSEMITE_HB_MODE, so a scalar-clock run would silently run the engine and dump
    hb_races -- a vector-clock trace filed as scalar-clock. Checked once per library."""
    lib = engine_library(accel_prof_home)
    if lib not in _supported:
        try:
            with open(lib, "rb") as fh:
                _supported[lib] = ENV.encode() in fh.read()
        except OSError:
            _supported[lib] = False
    if not _supported[lib]:
        raise RuntimeError(
            f"{lib} does not read {ENV} (a pre-T8 engine library, or none): rebuild and "
            f"install sanalyzer (bin/build, or `make install` in sanalyzer/ with "
            f"INSTALL_DIR=<checkout>/build/sanalyzer) before collecting HB traces")
    return lib


def resolve_dir(parent, mode, suffix=""):
    """<parent>/<mode><suffix>; a store the converter did not reach still has
    <parent>/<legacy><suffix> -- returned with a deprecation line. Returns the new
    path when neither exists (callers test existence themselves)."""
    new = os.path.join(parent, mode + suffix)
    if os.path.exists(new):
        return new
    old = os.path.join(parent, LEGACY_OF.get(mode, mode) + suffix)
    if old != new and os.path.exists(old):
        _legacy(parent, f"directory {os.path.basename(old)!r}")
        return old
    return new


def resolve_confirm(confirm_dir, _id, mode):
    """<confirm_dir>/<id>__cuvein__<mode>.json; the legacy file name is accepted."""
    return _resolve_file(confirm_dir, f"{_id}__cuvein__{mode}.json",
                         f"{_id}__cuvein__{LEGACY_OF.get(mode, mode)}.json")


def _resolve_file(parent, new_name, old_name):
    new = os.path.join(parent, new_name)
    if os.path.exists(new):
        return new
    old = os.path.join(parent, old_name)
    if old != new and os.path.exists(old):
        _legacy(parent, f"file name {old_name!r}")
        return old
    return new


def canon_meta(meta, source=""):
    """A kept-trace meta.json dict with pre-T8 'modes' keys / partial_dump values ->
    T8 names, in place (returns it)."""
    modes = meta.get("modes")
    if isinstance(modes, dict) and any(k in LEGACY for k in modes):
        meta["modes"] = {canon(k, source): v for k, v in modes.items()}
    for v in (meta.get("modes") or {}).values():
        pd = v.get("partial_dump") if isinstance(v, dict) else None
        if not pd:
            continue
        for mode, legacy in LEGACY_OF.items():
            if pd.startswith(legacy + "-partial-rep"):
                _legacy(source, f"partial_dump {pd!r}")
                v["partial_dump"] = mode + pd[len(legacy):]
                break
    return meta

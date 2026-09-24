#!/usr/bin/env python3
"""Shared library for the head-to-head baseline harness (eval/baselines/).

Centralizes: runtime environment resolution (CUDA_HOME / ACCEL_PROF_HOME /
LD_LIBRARY_PATH), the single unified per-run result schema every tool runner
writes, a timed-subprocess runner with a native baseline + peak-RSS poll, cubin
extraction, and a pc->source-line mapper built from `nvdisasm --print-line-info`.

Nothing here modifies the detector, the sidecar, the oracle, or any existing
eval/*.py script -- it only *calls* them. It deliberately does NOT reuse the
hardcoded CUDA_HOME in eval/driver.py / eval/racecheck.py (a stale spack path
that does not exist on this cluster); CUDA_HOME is resolved at runtime on the GPU
node instead. The timing helper mirrors eval/driver.py:run_timed but takes the
env explicitly so the resolved CUDA_HOME is used.

Cluster reality (see project memory 'accelprof-build-env'): the login node has no
usable CUDA/GPU; full CUDA + compute-sanitizer live on SLURM GPU nodes. Every
function that needs nvcc/nvdisasm/compute-sanitizer/a GPU must run on a GPU node
(srun). resolve_cuda_home() raises with a clear message when CUDA is absent so a
login-node invocation fails loudly instead of silently mis-measuring.
"""
import csv
import glob
import os
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path

# --- paths -----------------------------------------------------------------
APH = os.environ.get("ACCEL_PROF_HOME") or os.environ.get(
    "CUVEIN_HOME", "/home/fzheng4/AccelProf")
APH = str(Path(APH).resolve())
PYDIR = f"{APH}/python"
# the cuVein mode vocabulary (vector-clock / scalar-clock) lives next to the detector;
# import it from THIS checkout's python/ (the harness code, not the runtime one)
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python"))
import hb_modes  # noqa: E402
SIDECAR = f"{PYDIR}/atomic_scope_sidecar.py"
RESULTS_DIR = f"{APH}/eval/results"
BASELINES_DIR = f"{APH}/eval/baselines"

# The single unified per-run schema. Every tool runner appends rows with exactly
# these columns to eval/results/baselines-<tool>.csv, so make_tables.py can join
# them. verdict in {RACE, CLEAN, ERROR, TIMEOUT}. mode is '' except cuVein
# {vector-clock, scalar-clock} (hb_modes.MODES). report_ids is a space-joined, deduped list of the tool's
# native identifiers (source lines for HiRace/racecheck; pcs for iGUARD/cuVein);
# report_lines carries the nvdisasm-mapped source lines for pc-based tools.
COLUMNS = [
    "id", "pset", "program", "build", "input", "tool", "mode", "rep",
    "verdict", "reports_dedup", "report_ids", "report_lines",
    "wall_s", "native_wall_s", "peak_mb", "rc", "notes",
]

VERDICTS = ("RACE", "CLEAN", "ERROR", "TIMEOUT")


def resolve_cuda_home():
    """Best-effort CUDA_HOME that actually contains nvcc/nvdisasm. Raises if none
    is usable (e.g. on the login node) so callers fail loudly."""
    cands = []
    for v in ("CUDA_HOME", "CUDA_PATH"):
        if os.environ.get(v):
            cands.append(os.environ[v])
    cands += [
        "/usr/local/cuda",
        *sorted(glob.glob("/usr/local/cuda-*"), reverse=True),
        *sorted(glob.glob("/home/fzheng4/spack/opt/spack/*/cuda-*"), reverse=True),
    ]
    for c in cands:
        if c and os.path.exists(os.path.join(c, "bin", "nvdisasm")):
            return c
    raise RuntimeError(
        "no usable CUDA_HOME found (need bin/nvdisasm). Tried: "
        + ", ".join(dict.fromkeys(cands))
        + ". This step needs a GPU node -- run under srun on a GPU partition.")


def cuda_home_or_none():
    try:
        return resolve_cuda_home()
    except RuntimeError:
        return None


def base_env(cuda_home=None, hb_trace=False, hb_mode=None, scope_file=None):
    """Env dict for a tool run. Mirrors eval/driver.py:base_env but resolves a
    real CUDA_HOME and lets the HB knobs be set explicitly. hb_mode: 'vector-clock' /
    'scalar-clock' (hb_modes.MODES) -> YOSEMITE_HB_MODE; only with hb_trace."""
    ch = cuda_home or resolve_cuda_home()
    e = os.environ.copy()
    e["ACCEL_PROF_HOME"] = APH
    e["CUVEIN_HOME"] = APH
    e["CUDA_HOME"] = ch
    e["CUDA_PATH"] = ch
    e["PATH"] = f"{APH}/bin:{ch}/bin:" + e.get("PATH", "")
    e["LD_LIBRARY_PATH"] = (f"{ch}/compute-sanitizer:{ch}/lib64:"
                            + e.get("LD_LIBRARY_PATH", ""))
    # drop every HB knob inherited from the shell, the pre-T8 mode switch included
    # (the collector would still honour it and silently flip the mode)
    for k in ("YOSEMITE_HB_TRACE", hb_modes.ENV, hb_modes.LEGACY_ENV, "YOSEMITE_ATOMIC_SCOPE_FILE"):
        e.pop(k, None)
    if hb_trace:
        hb_modes.require_collector_support(APH)   # a pre-T8 library ignores YOSEMITE_HB_MODE
        e["YOSEMITE_HB_TRACE"] = "1"
        e.update(hb_modes.collector_env(hb_mode or hb_modes.VECTOR_CLOCK))
    if scope_file:
        e["YOSEMITE_ATOMIC_SCOPE_FILE"] = scope_file
    return e


# --- timed subprocess (mirrors driver.run_timed; env passed in) -------------
def _descendants(root):
    kids = {}
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            with open(f"/proc/{d}/stat") as f:
                ppid = int(f.read().split(") ", 1)[1].split()[1])
            kids.setdefault(ppid, []).append(int(d))
        except (OSError, IndexError, ValueError):
            pass
    out, stack = [], [root]
    while stack:
        p = stack.pop()
        out.append(p)
        stack.extend(kids.get(p, []))
    return out


def _rss_kb(pids):
    tot = 0
    for p in pids:
        try:
            with open(f"/proc/{p}/status") as f:
                for ln in f:
                    if ln.startswith("VmRSS:"):
                        tot += int(ln.split()[1])
                        break
        except OSError:
            pass
    return tot


def _prefer_oom_victim():
    """In the child, before exec: make the traced app (inherited by everything it
    spawns) the kernel OOM killer's first choice. An engine run can fill the node
    (100+ GB); without this the killer may pick the harness instead and the whole
    shard dies with no rows (evcand shard 0, P6 asyncmemcpy)."""
    try:
        with open("/proc/self/oom_score_adj", "w") as f:
            f.write("1000")
    except OSError:
        pass


def run_timed(cmd, env, cwd, timeout, poll_mem=False, stdin_path=None,
              stderr_path=None):
    """-> (wall_s, peak_rss_kb, rc, timed_out). One invocation; kills the whole
    process group on timeout (accelprof is a bash wrapper whose sanitizer child
    would otherwise orphan and leak multi-GB RSS). stderr_path (optional) captures
    the child's stdout+stderr to a file so failures can be root-caused."""
    stop = threading.Event()
    local_peak = [0]
    fin = open(stdin_path, "rb") if stdin_path else subprocess.DEVNULL
    ferr = open(stderr_path, "wb") if stderr_path else subprocess.DEVNULL
    t0 = time.perf_counter()
    try:
        p = subprocess.Popen(cmd, env=env, cwd=cwd, stdin=fin,
                             stdout=ferr, stderr=subprocess.STDOUT if stderr_path else subprocess.DEVNULL,
                             start_new_session=True, preexec_fn=_prefer_oom_victim)
    except OSError as e:
        if stdin_path:
            fin.close()
        if stderr_path:
            ferr.close()
            try:   # leave the reason where the caller's stderr tail will find it
                with open(stderr_path, "w") as f:
                    f.write(f"launch OSError: {e}\n")
            except OSError:
                pass
        return "NA", 0, 127, False
    if poll_mem:
        def poll():
            while not stop.is_set():
                local_peak[0] = max(local_peak[0], _rss_kb(_descendants(p.pid)))
                time.sleep(0.1)
        threading.Thread(target=poll, daemon=True).start()

    def _killtree():
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            p.kill()

    timed_out = False
    try:
        rc = p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        _killtree(); p.wait(); rc = 124; timed_out = True
    _killtree()
    stop.set()
    if stdin_path:
        fin.close()
    if stderr_path:
        ferr.close()
    return round(time.perf_counter() - t0, 3), local_peak[0], rc, timed_out


def tail_text(path, n=40, maxch=2000):
    """Last n lines of a (possibly binary/huge) log file, comma-free for CSV notes."""
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            sz = f.tell()
            f.seek(max(0, sz - 65536))
            txt = f.read().decode("utf-8", "replace")
    except OSError:
        return ""
    lines = [ln for ln in txt.splitlines() if ln.strip()][-n:]
    return "\n".join(lines)[-maxch:]


def extract(exe_abs, cubindir, env):
    """cubin -> CFG .dot per cubin -> atomic-scope sidecar. Returns (scope_or_'',
    list_of_cubins). Uses .env/bin/python for the sidecar (no nested conda run,
    unlike getall.sh)."""
    shutil.rmtree(cubindir, ignore_errors=True)
    os.makedirs(cubindir)
    subprocess.run(["cuobjdump", "-xelf", "all", exe_abs], cwd=cubindir, env=env,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cubs = glob.glob(f"{cubindir}/*.cubin") or glob.glob(f"{cubindir}/*.elf")
    for c in cubs:
        dot = os.path.splitext(c)[0] + ".dot"
        with open(dot, "w") as f:
            subprocess.run(["nvdisasm", "-bbcfg", "-poff", c], stdout=f,
                           stderr=subprocess.DEVNULL, env=env)
    scope = f"{cubindir}/atomic_scope.txt"
    dots = glob.glob(f"{cubindir}/*.dot")
    py = f"{APH}/.env/bin/python"
    if dots:
        r = subprocess.run([py, SIDECAR, *dots, "-o", scope],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if r.returncode == 0 and os.path.exists(scope):
            return scope, cubs
    return "", cubs


# --- pc -> source line ------------------------------------------------------
def pc_line_map(cubin, env):
    """{pc_offset(int): 'file:line'} from `nvdisasm --print-line-info`. Offsets
    are per-function; nvdisasm prints '//## File "x", line N' comments preceding
    the instruction block plus '/*OFFSET*/' on each instruction line. Returns a
    map keyed by instruction offset. Requires the cubin to be built with
    -lineinfo; returns {} otherwise (recorded, not fatal)."""
    try:
        out = subprocess.run(["nvdisasm", "--print-line-info", cubin], env=env,
                             capture_output=True, text=True, timeout=120).stdout
    except (OSError, subprocess.TimeoutExpired):
        return {}
    import re
    cur = None
    m = {}
    file_re = re.compile(r'line (\d+)[^\n]*"([^"]+)"')
    alt_re = re.compile(r'//## File "([^"]+)", line (\d+)')
    off_re = re.compile(r'/\*([0-9a-fA-F]+)\*/')
    for ln in out.splitlines():
        a = alt_re.search(ln)
        if a:
            cur = f"{os.path.basename(a.group(1))}:{a.group(2)}"
            continue
        b = file_re.search(ln)
        if b and "File" in ln:
            cur = f"{os.path.basename(b.group(2))}:{b.group(1)}"
            continue
        o = off_re.search(ln)
        if o and cur:
            m[int(o.group(1), 16)] = cur
    return m


# --- result CSV -------------------------------------------------------------
def open_results(tool):
    """Return (writer, filehandle) for eval/results/baselines-<tool>.csv, header
    written if new. Caller closes the handle."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = f"{RESULTS_DIR}/baselines-{tool}.csv"
    new = not os.path.exists(path)
    fh = open(path, "a", newline="")
    w = csv.DictWriter(fh, fieldnames=COLUMNS)
    if new:
        w.writeheader()
    return w, fh, path


def row(**kw):
    """Build a schema-complete row dict; unspecified columns default to ''."""
    r = {c: "" for c in COLUMNS}
    r.update({k: v for k, v in kw.items() if k in COLUMNS})
    return r


def read_manifest(path=None):
    """Yield dict rows from the shared manifest.csv."""
    path = path or f"{BASELINES_DIR}/manifest.csv"
    with open(path, newline="") as f:
        yield from csv.DictReader(f)

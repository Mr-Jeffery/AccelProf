#!/usr/bin/env python3
"""Two-phase, shardable cuVein runner for multi-node parallelism.

The serial run_cuvein.py does GPU trace collection AND Python sync_dominance
analysis in one process on one GPU node. This splits them so the cluster can be
used in parallel (feasibility verified: trace collection runs on any GPU node,
not just sm_86; the Python analysis + even nvcc builds run on CPU-only nodes):

  collect  (GPU, sharded)  -- for each program: native timing, cubin/CFG/scope
           extraction, then accelprof engine + no-engine runs; SAVE the trace
           dumps + dots + a meta.json (timing, node/arch, pc->line map) under the
           trace store. No analysis. Distributed over many GPU nodes via --shard.
  analyze  (CPU, sharded)  -- read the saved traces + dots, run sync_dominance
           over them, and emit the unified per-run rows into a per-shard CSV. No
           GPU. Distributed over CPU nodes via --shard.

Then merge_csv concatenates the shard CSVs into eval/results/baselines-cuvein.csv.
Every trace store lives on BeeGFS (/mnt/beegfs/$USER/cuvein_traces/<tag>; compute
nodes only, not backed up, no caps) -- see eval/STORAGE.md; _store_root() refuses
anything else.
Verdicts are arch-independent (a racy litmus reports on sm_86 and sm_89 alike);
node+arch are recorded per program so overhead stays interpretable.

  # on a GPU node, one shard of the trace phase:
  $PY parallel.py collect --pset P4,P5,P6 --shard 0/8
  # on a CPU node, one shard of the analysis phase:
  $PY parallel.py analyze --pset P4,P5,P6 --shard 0/8
  # after all shards:
  $PY parallel.py merge
"""
import argparse
import glob
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blib
sys.path.insert(0, blib.PYDIR)
sys.path.insert(0, f"{blib.APH}/eval")
import sync_dominance as sd   # noqa: E402
import aggregate as agg       # noqa: E402
import run_cuvein as rc       # reuse _analyze_reports  # noqa: E402

# $BASELINE_MODES=trace-only restricts a run to one mode (e.g. a static-leg revision).
MODES = tuple(m for m in os.environ.get("BASELINE_MODES", "engine,trace-only").split(",") if m)


BEEGFS_ROOT = f"/mnt/beegfs/{os.environ.get('USER', 'nobody')}"


def _store_root():
    """Where trace dumps go: BeeGFS, and nothing else (T0 policy, eval/STORAGE.md).

    $BASELINE_TRACE_DIR must name a directory under /mnt/beegfs/$USER (the sbatch
    scripts use /mnt/beegfs/$USER/cuvein_traces/<tag>); unset, the default is
    /mnt/beegfs/$USER/cuvein_traces. Anything else -- /mnt/local, /tmp, home -- is
    refused with a message instead of being used silently: the earlier policy (sbatch
    scripts pointing at node-local /mnt/local or /tmp; unset -> silent fall-through
    beegfs -> /mnt/local -> home) is what filled the 230 GB node-local disk on c37
    (memcpy_htod_kernel_race-fixed row lost), overflowed the 40 GB home quota (11 GB
    for 117 programs) and deleted every timed-out rep's partial dump. BeeGFS is
    mounted on compute nodes only (not the login node), so
    this resolves at run time on the node. BASELINE_TRACE_ALLOW_NONBEEGFS=1 is the
    explicit escape hatch for a throw-away local test (it prints a warning)."""
    env = os.environ.get("BASELINE_TRACE_DIR")
    d = env or f"{BEEGFS_ROOT}/cuvein_traces"
    real = os.path.realpath(d)
    on_beegfs = real.startswith(os.path.realpath(BEEGFS_ROOT) + "/") or real == os.path.realpath(BEEGFS_ROOT)
    if not on_beegfs and not os.environ.get("BASELINE_TRACE_ALLOW_NONBEEGFS"):
        raise SystemExit(
            f"trace store {d!r} is not under {BEEGFS_ROOT}: every trace store lives on BeeGFS "
            f"(export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/<tag>; see eval/STORAGE.md). "
            f"Set BASELINE_TRACE_ALLOW_NONBEEGFS=1 only for a throw-away local test.")
    if not on_beegfs:
        print(f"WARNING: trace store {d} is not on BeeGFS (BASELINE_TRACE_ALLOW_NONBEEGFS set)",
              file=sys.stderr, flush=True)
    elif not os.path.isdir("/mnt/beegfs"):
        raise SystemExit(
            f"/mnt/beegfs is not mounted on {socket.gethostname()}: trace collection and "
            f"analysis run on compute nodes (srun/sbatch), never on the login node.")
    else:
        os.makedirs(BEEGFS_ROOT, exist_ok=True)
        try:
            os.chmod(BEEGFS_ROOT, 0o700)
        except OSError:
            pass
    os.makedirs(d, exist_ok=True)
    return d


STORE = f"{blib.RESULTS_DIR}/traces"   # rebound to _store_root() at command start


def _rows(manifest, psets, ids):
    for m in blib.read_manifest(manifest):
        if psets and m["pset"] not in psets:
            continue
        if ids and m["id"] not in ids:
            continue
        yield m


def _shard(items, shard):
    if not shard:
        return items
    k, n = (int(x) for x in shard.split("/"))
    return [it for i, it in enumerate(items) if i % n == k]


def _arch():
    """compute_cap of the GPU the run will use. nvidia-smi ignores CUDA_VISIBLE_DEVICES,
    so on a dual-GPU node (c20-22/c25/c34: an sm_89 4060 Ti next to a 2060/2080 Super)
    the first line would be the wrong GPU; with a single pinned device (setup/pin8g.sh
    sets its UUID) ask for that one."""
    cmd = ["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"]
    vis = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    if vis and "," not in vis:
        cmd[1:1] = ["-i", vis]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=30).stdout.strip().splitlines()
        return out[0].strip() if out else "?"
    except Exception:
        return "?"


# ---------- collect (GPU) ----------
def collect_one(mrow, cuda, reps, floor=120):
    """Collect traces for one program with ALL heavy IO on scratch. accelprof
    writes its dependency_* dump to the CWD, and a single dump can be multi-GB, so
    we run it in a scratch work dir under STORE (node-local/beegfs), never in the
    home bin/ dir. The exe is symlinked into the work dir so accelprof's ./<base>
    resolves there. Only the (small) kernel JSONs, dots, meta and the captured
    stderr of failing runs are kept. `floor` is the minimum tool timeout (s)."""
    exe = mrow["exe"]
    idir = f"{STORE}/{mrow['id']}"
    shutil.rmtree(idir, ignore_errors=True)
    work = f"{idir}/work"
    logs = f"{idir}/logs"
    os.makedirs(work, exist_ok=True)
    os.makedirs(logs, exist_ok=True)
    meta = {k: mrow[k] for k in ("id", "pset", "program", "build", "input")}
    meta.update(node=socket.gethostname(), arch=_arch(), modes={},
                store=STORE, status="collecting",
                started=time.strftime("%Y-%m-%d %H:%M:%S"),
                slurm_job=os.environ.get("SLURM_JOB_ID", ""))

    def _write_meta():
        # written at the start and after every mode so that a shard killed by SLURM
        # (time limit, node failure, OOM) leaves a readable marker: status stays
        # "collecting" and `analyze` turns it into an ERROR collection-interrupted row
        # instead of silently producing no row at all.
        tmp = f"{idir}/meta.json.tmp"
        Path(tmp).write_text(json.dumps(meta))
        os.replace(tmp, f"{idir}/meta.json")

    _write_meta()
    if not (os.path.exists(exe) and os.access(exe, os.X_OK)):
        meta["error"] = "missing-exe"
        meta["status"] = "done"
        _write_meta()
        return
    base = os.path.basename(exe)
    link = f"{work}/{base}"
    try:
        os.symlink(os.path.realpath(exe), link)
        meta["exe_link"] = "symlink"
    except OSError as e:
        shutil.copy(os.path.realpath(exe), link)
        meta["exe_link"] = f"copy({e.__class__.__name__})"
    args = [a for a in mrow["args"].split() if a] if mrow["args"] else []
    stdin = mrow["stdin"] or None
    man_timeout = int(mrow["timeout"] or 600)
    nenv = blib.base_env(cuda)
    # HeCBench apps open their inputs relative to the CWD (e.g. srad
    # `../data/srad/image.pgm`, bezier `input/control.txt`), so mirror the app's
    # source dir layout next to the scratch work dir: <idir>/data -> HeCBench/src/data
    # and <work>/input -> <app src>/input. Harness-only; the corpus is untouched.
    if mrow["pset"] in ("P7", "P9"):
        hec = f"{HERE}/corpora/HeCBench/src"
        app_src = f"{hec}/{mrow['program']}"
        for lnk, target in ((f"{idir}/data", f"{hec}/data"),
                            (f"{work}/input", f"{app_src}/input"),
                            (f"{work}/data", f"{app_src}/data")):
            # NB: loop variable must not shadow `link` (the exe symlink) -- an
            # earlier version did, making the native timing run exec a directory
            # (rc 127) for every P7 app while accelprof (./<base>) still worked.
            if os.path.isdir(target) and not os.path.lexists(lnk):
                try:
                    os.symlink(target, lnk)
                except OSError:
                    pass
        # args like ../dxtc2-sycl/data/lena_std.ppm: mirror that sibling source dir
        for a_ in args:
            if a_.startswith("../"):
                sib = a_.split("/")[1]
                if os.path.isdir(f"{hec}/{sib}") and not os.path.lexists(f"{idir}/{sib}"):
                    try:
                        os.symlink(f"{hec}/{sib}", f"{idir}/{sib}")
                    except OSError:
                        pass

    # native timing in the work dir (any app output files stay on scratch); the
    # native rc + stderr are recorded so an app that fails on its own is never
    # blamed on the collector.
    native, native_rc = None, None
    for r_ in range(reps):
        w, _, rcode, to = blib.run_timed([link, *args], nenv, work, man_timeout,
                                         stdin_path=stdin,
                                         stderr_path=f"{logs}/native_rep{r_ + 1}.txt")
        native_rc = rcode if native_rc is None else max(native_rc, rcode)
        if not to and isinstance(w, (int, float)):
            native = w if native is None else min(native, w)
    # "10x native or 20 min" read as up to 20 min: floor 120s by default (the engine
    # runs 3-218x native, REPORT.md F3), hard cap 1200s. --timeout-floor raises the
    # floor (P7 overhead-only set uses the full 20 min).
    tool_timeout = min(max(int(10 * native), floor), 1200) if native else max(man_timeout, floor)
    meta["native_wall"] = native
    meta["native_rc"] = native_rc
    meta["native_err"] = blib.tail_text(f"{logs}/native_rep1.txt", 12, 600)
    meta["tool_timeout"] = tool_timeout

    cubindir = f"{work}/cubins"
    scope, cubs = blib.extract(os.path.realpath(exe), cubindir, nenv)
    pcmap = {}
    for c in cubs:
        pcmap.update(blib.pc_line_map(c, nenv))
    meta["pc_lines"] = {str(k): v for k, v in pcmap.items()}
    meta["scope_present"] = bool(scope)
    os.makedirs(f"{idir}/dots", exist_ok=True)
    for dot in glob.glob(f"{cubindir}/*.dot"):
        shutil.copy(dot, f"{idir}/dots/")

    accel = ["accelprof", "-t", "pc_dependency_analysis", "-n", "1",
             f"./{base}", *args]

    def _clean_deps():
        for d in glob.glob(f"{work}/dependency_{base}_*"):
            shutil.rmtree(d, ignore_errors=True)

    def _save(kjs, md):
        # work/ and <idir>/<mode>/ are on the same filesystem (both under STORE), so
        # this is a rename, not a copy: a saved program never needs 2x its dump.
        shutil.rmtree(md, ignore_errors=True)
        os.makedirs(md, exist_ok=True)
        for kj in kjs:
            shutil.move(kj, f"{md}/{os.path.basename(kj)}")

    def _keep_partial(depdir, mode, rep, rm):
        """A timed-out rep is killed mid-write: its kernel JSONs are a prefix of the
        run and the last one may be truncated. Keep them under <id>/<mode>-partial-rep<k>/
        with a PARTIAL marker (analysis never reads that directory; it is evidence for
        the memory-footprint / trace-size studies), one such directory per mode: the
        rep that got furthest (largest raw dump) wins."""
        cur = glob.glob(f"{idir}/{mode}-partial-rep*")
        if cur:
            try:
                prev = json.loads(Path(f"{cur[0]}/PARTIAL").read_text()).get("dump_mb", 0)
            except (OSError, ValueError):
                prev = 0
            if rm.get("dump_mb", 0) <= prev:
                return None
            for c in cur:
                shutil.rmtree(c, ignore_errors=True)
        pd = f"{idir}/{mode}-partial-rep{rep}"
        os.makedirs(pd, exist_ok=True)
        for kj in glob.glob(f"{depdir}/kernel_*.json"):
            shutil.move(kj, f"{pd}/{os.path.basename(kj)}")
        Path(f"{pd}/PARTIAL").write_text(json.dumps(dict(
            rm, mode=mode, rep=rep,
            note="timed-out rep: prefix of the run, last kernel JSON may be truncated; "
                 "never a verdict")))
        return os.path.basename(pd)

    for mode in MODES:
        env = blib.base_env(cuda, hb_trace=True, no_engine=(mode == "trace-only"),
                            scope_file=scope or None)
        reps_meta = []
        saved = partial = False
        partial_dump = None
        for rep in range(1, reps + 1):
            _clean_deps()
            errp = f"{logs}/{mode}_rep{rep}.txt"
            wall, peak, rcode, to = blib.run_timed(accel, env, work, tool_timeout,
                                                   poll_mem=True, stdin_path=stdin,
                                                   stderr_path=errp)
            deps = sorted(glob.glob(f"{work}/dependency_{base}_*"),
                          key=os.path.getmtime)
            depdir = deps[-1] if deps else ""
            kjs = glob.glob(f"{depdir}/kernel_*.json") if depdir else []
            # size of the raw dump at exit (timeouts: how far the trace got)
            dump_mb = 0.0
            if depdir:
                for f_ in glob.glob(f"{depdir}/*"):
                    try:
                        dump_mb += os.path.getsize(f_) / 1e6
                    except OSError:
                        pass
            # complete = the app ran to its own exit status under the tool. accelprof
            # returns 1 when the app dies (OOM-killed engine run: "Killed ... Fail to run
            # the application"), yet the kernels finished BEFORE the kill are already on
            # disk -- such a dump covers a prefix of the run only and must never be read
            # as a CLEAN verdict (P1-CC_..Push..Block-slower_atomic-1296n: 1 of 5 kernels).
            complete = (not to) and rcode == (native_rc or 0)
            rm = dict(wall=wall, peak_mb=round(peak / 1024.0, 1) if peak else "",
                      rc=rcode, timed_out=to, nkernels=len(kjs), dump_mb=round(dump_mb, 1),
                      complete=complete)
            if to or not kjs or not complete:
                rm["err"] = blib.tail_text(errp, 10, 500)
            reps_meta.append(rm)
            # a timed-out rep is killed mid-write: its kernel JSONs are truncated
            # (JSONDecodeError downstream), so only a non-timed-out rep's dump is saved:
            # the first COMPLETE one, else the first partial one (flagged; a race it
            # already shows is still a race, but it can never certify CLEAN).
            if kjs and not to and (not saved or (partial and complete)):
                _save(kjs, f"{idir}/{mode}")
                saved, partial = True, not complete
            elif kjs and to:
                kept = _keep_partial(depdir, mode, rep, rm)
                if kept:
                    partial_dump = kept
            _clean_deps()               # free the (possibly multi-GB) dump at once
        ev, uncounted = _count_events(f"{idir}/{mode}") if saved else (0, [])
        meta["modes"][mode] = dict(reps=reps_meta, saved=saved, partial=partial,
                                   events=ev, events_uncounted=uncounted,
                                   partial_dump=partial_dump)
        _write_meta()                   # per-mode checkpoint
    # trace size (for the P7 "largest-trace" selection): total hb_events in the
    # saved engine dump. Rows report their OWN mode's count (meta.modes.<mode>.events).
    meta["events"] = meta["modes"].get("engine", {}).get("events", 0)
    shutil.rmtree(work, ignore_errors=True)   # keep only kernel JSONs + dots + meta + logs
    meta["status"] = "done"
    meta["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _write_meta()


# json.loads needs ~6-10x the text size in RAM: P7-bezier-surface's complete 138 GB
# trace-only dump took the HARNESS (not the collector, not the analysis) to 183 GB RSS
# while counting its events and the kernel OOM killer took the whole shard.
COUNT_EVENTS_MAX_GB = float(os.environ.get("BASELINE_COUNT_EVENTS_MAX_GB", "12"))


def _count_events(mode_dir):
    """-> (total hb_events over the mode's saved kernel dumps that were parsed,
    [kernel JSONs above COUNT_EVENTS_MAX_GB that were NOT parsed]). The count is
    informational (notes, P7 largest-trace selection); an unparsed file is named in
    meta.modes.<mode>.events_uncounted rather than risking the shard."""
    events, uncounted = 0, []
    for kj in sorted(glob.glob(f"{mode_dir}/kernel_*.json")):
        try:
            if os.path.getsize(kj) > COUNT_EVENTS_MAX_GB * 1e9:
                uncounted.append(os.path.basename(kj))
                continue
            events += len(json.loads(Path(kj).read_text()).get("hb_events", []))
        except (OSError, ValueError):
            pass
    return events, uncounted


def _csvsafe(s):
    return (s or "").replace(",", ";").replace("\n", " | ").strip()


def cmd_collect(a):
    global STORE; STORE = _store_root()
    cuda = blib.resolve_cuda_home()
    psets = set(a.pset.split(",")) if a.pset else None
    ids = set(a.id.split(",")) if a.id else None
    if getattr(a,"id_file","") :
        _f=set(l.strip() for l in open(a.id_file) if l.strip()); ids=(ids or set())|_f
    rows = _shard(list(_rows(a.manifest, psets, ids)), a.shard)
    os.makedirs(STORE, exist_ok=True)
    for i, m in enumerate(rows, 1):
        print(f"[collect {i}/{len(rows)}] {m['id']}", flush=True)
        try:
            collect_one(m, cuda, a.reps)
        except Exception as e:
            Path(f"{STORE}/{m['id']}.error").write_text(f"{type(e).__name__}: {e}")
            print(f"  ERROR {type(e).__name__}: {e}", flush=True)
    print(f"collect: {len(rows)} programs -> {STORE}")


# ---------- analyze (CPU) ----------
def _analysis_mem_cap_gb(mem_gb):
    """-1 = auto (80 % of MemTotal), 0 = no cap, else GB."""
    if mem_gb is None or mem_gb < 0:
        try:
            for line in open("/proc/meminfo"):
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) * 1024 * 0.8 / 1e9
        except OSError:
            pass
        return 0
    return mem_gb or 0


def _analyze_capped(mode_dir, dots_dir, cap_s, mem_gb=-1):
    """rc._analyze_reports in a forked child with a wall-clock cap (cap_s, 0 = run
    inline, uncapped) and an address-space cap (mem_gb: -1 = 80 % of the node's RAM,
    0 = none). -> (result, reason): reason '' = analyzed; 'analysis-timeout' (child
    killed past cap_s; P9-mr: 113 GB trace, >4.5 h of sync_dominance); 'analysis-oom'
    (MemoryError under the cap -- without the cap the kernel OOM killer took the whole
    shard, P7-bezier-surface at 183 GB RSS on a 188 GB node, and the shard left NO row);
    'analysis-died(rc=N)' (the child vanished without a result). A ValueError in the
    child (truncated kernel JSON of a partial dump) is re-raised here so analyze_one's
    handling of it is unchanged; any other exception becomes a RuntimeError -> ERROR row."""
    if not cap_s:
        return rc._analyze_reports(mode_dir, dots_dir), ""
    import multiprocessing, queue
    mem_gb = _analysis_mem_cap_gb(mem_gb)
    ctx = multiprocessing.get_context("fork")
    q = ctx.Queue()

    def _child():
        try:
            if mem_gb:
                import resource
                lim = int(mem_gb * 1e9)
                resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
            q.put(("OK", rc._analyze_reports(mode_dir, dots_dir)))
        except MemoryError:
            os._exit(3)     # nothing can be allocated any more (not even the queue's
                            # feeder thread): exit code 3 is the OOM marker for the parent
        except Exception as e:  # noqa: BLE001 -- reported, not swallowed
            q.put(("EXC", (type(e).__name__, str(e)[:300])))

    proc = ctx.Process(target=_child)
    proc.start()
    deadline = time.time() + cap_s
    tag = payload = None
    while tag is None:
        try:
            tag, payload = q.get(timeout=5)
            break
        except queue.Empty:
            pass
        if not proc.is_alive():
            try:                       # the result may have landed just before exit
                tag, payload = q.get(timeout=5)
                break
            except queue.Empty:
                proc.join()
                if proc.exitcode == 3:
                    return ([], set(), []), f"analysis-oom(cap={mem_gb:.0f}GB)"
                return ([], set(), []), f"analysis-died(rc={proc.exitcode})"
        if time.time() > deadline:
            proc.kill()
            proc.join()
            return ([], set(), []), "analysis-timeout"
    proc.join()
    if tag == "OK":
        return payload, ""
    name, msg = payload
    if name == "ValueError":
        raise ValueError(msg)
    raise RuntimeError(f"{name}:{msg}")


def analyze_one(idir, writer, confirm_dir, analysis_cap=0, analysis_mem=-1):
    meta = json.loads(Path(f"{idir}/meta.json").read_text())
    common = dict(id=meta["id"], pset=meta["pset"], program=meta["program"],
                  build=meta["build"], input=meta["input"], tool="cuvein")
    pcmap = {int(k): v for k, v in meta.get("pc_lines", {}).items()}

    def lines_for(pcs):
        return ";".join(sorted({pcmap[p] for p in pcs if p in pcmap}))

    verdicts = {}
    if meta.get("error"):
        writer.writerow(blib.row(**common, verdict="ERROR", notes=meta["error"]))
        return {m: "ERROR" for m in MODES}
    dots_dir = f"{idir}/dots"
    native = meta.get("native_wall")
    native_rc = meta.get("native_rc")
    nat_note = ""
    if native_rc not in (None, 0):
        nat_note = f";native_rc={native_rc};native_err={_csvsafe(meta.get('native_err', ''))[-200:]}"
    for mode in MODES:
        mm = meta["modes"].get(mode, {})
        reps_meta = mm.get("reps", [])
        if not reps_meta:
            # No rep of this mode reached a checkpoint. With a T0 meta (status key)
            # that is still "collecting", the shard was killed (SLURM time limit,
            # NODE_FAIL, OOM) -- say so instead of writing no row at all. A finished
            # meta without the mode was collected with a restricted $BASELINE_MODES
            # (pre-T0 metas have no status key): no row, as before.
            if meta.get("status") == "collecting":
                writer.writerow(blib.row(**common, mode=mode, rep=1, verdict="ERROR",
                                         notes=f"collection-interrupted(node={meta.get('node')};"
                                               f"job={meta.get('slurm_job', '')};"
                                               f"started={meta.get('started', '')})"))
                verdicts[mode] = "ERROR"
            continue
        # analyze the saved trace once (deterministic verdict), reuse across reps
        ids_, pcs, raw = [], set(), []
        analyzed, reason = False, ""
        partial = bool(mm.get("partial"))
        if mm.get("saved") and os.path.isdir(f"{idir}/{mode}"):
            try:
                (ids_, pcs, raw), reason = _analyze_capped(f"{idir}/{mode}", dots_dir,
                                                           analysis_cap, analysis_mem)
                analyzed = not reason
            except ValueError:
                if not partial:     # a killed run's last kernel JSON may be truncated
                    raise
        mode_events = mm.get("events", meta.get("events", 0) if mode == "engine" else "")
        if mm.get("events_uncounted"):
            mode_events = f"{mode_events}(+{len(mm['events_uncounted'])} dumps >{COUNT_EVENTS_MAX_GB:.0f}GB uncounted)"
        for rep, rm in enumerate(reps_meta, 1):
            # metas written before the `complete` flag existed: derive it
            complete = rm.get("complete", not rm.get("timed_out")
                              and rm.get("rc") == (native_rc or 0))
            if rm.get("timed_out"):
                verdict = "TIMEOUT"
                notes = (f"timeout={meta.get('tool_timeout')}s;dump_mb={rm.get('dump_mb', '')}"
                         f"{nat_note};err={_csvsafe(rm.get('err', ''))[-200:]}")
                ri, rl, nd = "", "", 0
            elif reason and rm.get("nkernels", 0):
                verdict = "ERROR"     # trace collected; offline analysis timed out / OOM / died
                tagn = f"analysis-timeout={analysis_cap}s" if reason == "analysis-timeout" else reason
                notes = (f"{tagn};dump_mb={rm.get('dump_mb', '')};"
                         f"nkernels={rm.get('nkernels')};node={meta.get('node')}{nat_note}")
                ri, rl, nd = "", "", 0
            elif rm.get("nkernels", 0) == 0 or (not analyzed and complete):
                verdict = "ERROR"
                notes = (f"no-kernel-json(rc={rm.get('rc')}){nat_note};"
                         f"err={_csvsafe(rm.get('err', ''))[-300:]}")
                ri, rl, nd = "", "", 0
            elif not complete and not (partial and ids_):
                # the app died under the tool (rc != native rc) after dumping only a
                # prefix of its kernels: no verdict -- in particular never CLEAN.
                verdict = "ERROR"
                notes = (f"incomplete-trace(rc={rm.get('rc')};nkernels={rm.get('nkernels')};"
                         f"peak_mb={rm.get('peak_mb', '')}){nat_note};"
                         f"err={_csvsafe(rm.get('err', ''))[-200:]}")
                ri, rl, nd = "", "", 0
            else:
                # a race already visible in a partial dump is still a race
                verdict = "RACE" if ids_ else "CLEAN"
                notes = (f"node={meta.get('node')};arch={meta.get('arch')};"
                         f"events={mode_events};nkernels={rm.get('nkernels')}"
                         + ("" if complete else f";partial(rc={rm.get('rc')})"))
                ri, rl, nd = " ".join(ids_), lines_for(pcs), len(ids_)
            verdicts[mode] = verdict if mode not in verdicts or verdict == "RACE" else verdicts[mode]
            writer.writerow(blib.row(
                **common, mode=mode, rep=rep, verdict=verdict, reports_dedup=nd,
                report_ids=ri, report_lines=rl, wall_s=rm.get("wall"),
                native_wall_s=native if native is not None else "",
                peak_mb=rm.get("peak_mb", ""), rc=rm.get("rc"), notes=notes))
        if confirm_dir and analyzed and (ids_ or not partial):
            Path(f"{confirm_dir}/{meta['id']}__cuvein__{mode}.json").write_text(
                json.dumps({"id": meta["id"], "tool": "cuvein", "mode": mode,
                            "verdict": "RACE" if ids_ else "CLEAN", "report_ids": ids_,
                            "pcs": sorted(pcs), "lines": lines_for(pcs), "raw": raw,
                            "scope_file": "", "pc_lines": {str(k): pcmap[k]
                                                           for k in pcs if k in pcmap}},
                           indent=2))
    return verdicts


def _keep_decision(verdicts, label):
    """Retention policy: a trace is worth keeping only when it is evidence of a
    disagreement with the suite label (FP/FN) or of a failure (ERROR/TIMEOUT).
    TP/TN traces are deleted. -> reason string or ''."""
    reasons = []
    for mode, v in verdicts.items():
        if v in ("ERROR", "TIMEOUT"):
            reasons.append(f"{mode}:{v}")
        elif label in ("RACE", "CLEAN") and v != label:
            reasons.append(f"{mode}:{'FP' if label == 'CLEAN' else 'FN'}")
    return ",".join(reasons)


def _keep_trace(idir, keep_dir, reason, cap_mb):
    """Copy kernel JSONs + dots + meta + logs of a kept program into keep_dir/<id>
    (home). Above cap_mb the kernel JSONs are dropped (meta+logs+dots kept) and the
    reason is suffixed with 'trace-too-large'; cap_mb 0 = no cap. The full trace
    stays in the BeeGFS store in any case (--keep-all is the default)."""
    _id = os.path.basename(idir)
    dst = f"{keep_dir}/{_id}"
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst, exist_ok=True)
    size = 0
    for root, _, files in os.walk(idir):
        for f in files:
            try:
                size += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    too_large = bool(cap_mb) and size > cap_mb * 1e6
    for sub in ("dots", "logs", *MODES):
        s = f"{idir}/{sub}"
        if os.path.isdir(s) and not (too_large and sub in MODES):
            shutil.copytree(s, f"{dst}/{sub}", dirs_exist_ok=True)
    try:
        meta = json.loads(Path(f"{idir}/meta.json").read_text())
    except (OSError, ValueError):
        meta = {}
    meta["keep_reason"] = reason + (",trace-too-large" if too_large else "")
    meta["trace_bytes"] = size
    Path(f"{dst}/meta.json").write_text(json.dumps(meta))
    return meta["keep_reason"]


def _write_store_info(store, a):
    """STORE_INFO.json: which collector build produced the dumps kept in this store.
    The dumps depend only on the collector (libsanalyzer.so), so a later Python-side
    detector revision can be re-scored from them with `analyze` (no GPU)."""
    import hashlib, subprocess, time
    info = f"{store}/STORE_INFO.json"
    if os.path.exists(info):
        return
    def sh(*cmd):
        try:
            return subprocess.run(cmd, cwd=blib.APH, capture_output=True, text=True,
                                  timeout=60).stdout
        except (OSError, subprocess.SubprocessError):
            return ""
    lib = f"{blib.APH}/build/sanalyzer/lib/libsanalyzer.so"
    try:
        lib_md5 = hashlib.md5(Path(lib).read_bytes()).hexdigest()
    except OSError:
        lib_md5 = ""
    try:
        Path(info).write_text(json.dumps({
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            "git_head": sh("git", "rev-parse", "HEAD").strip(),
            "git_diff_sha1": hashlib.sha1(sh("git", "diff", "HEAD").encode()).hexdigest(),
            "libsanalyzer_md5": lib_md5, "modes": list(MODES), "reps": a.reps,
            "pset": a.pset, "layout": "<id>/{meta.json,dots/,logs/,<mode>/kernel_*.json}",
            "note": "BeeGFS is not RAID-protected and not backed up"}, indent=2))
    except OSError:
        pass


def _cap_kept(idir, cap_gb):
    """--keep-all-cap-gb N (default 0 = no cap): a program whose saved dumps exceed
    N GB keeps meta/dots/logs only and meta.trace_dropped says so. The first BeeGFS
    sweep (evcand, 2026-09-20) ran with a 20 GB cap; it never fired there (no P1-P6
    trace is that large), but on the P7/P9 apps it would silently discard exactly the
    traces worth keeping -- do not set one unless the store really has to fit
    somewhere (eval/STORAGE.md)."""
    size = sum(os.path.getsize(f) for m in MODES
               for f in glob.glob(f"{idir}/{m}/kernel_*.json"))
    if cap_gb and size > cap_gb * 1e9:
        for m in MODES:
            shutil.rmtree(f"{idir}/{m}", ignore_errors=True)
        try:
            meta = json.loads(Path(f"{idir}/meta.json").read_text())
            meta["trace_dropped"] = f"{size / 1e9:.1f}GB > {cap_gb}GB"
            Path(f"{idir}/meta.json").write_text(json.dumps(meta))
        except (OSError, ValueError):
            pass
        return 0
    return size


def cmd_analyze(a):
    global STORE; STORE = _store_root()
    psets = set(a.pset.split(",")) if a.pset else None
    ids = set(a.id.split(",")) if a.id else None
    if getattr(a,"id_file","") :
        _f=set(l.strip() for l in open(a.id_file) if l.strip()); ids=(ids or set())|_f
    # shard over the same ordered program list so collect/analyze shards align
    rows = _shard(list(_rows(a.manifest, psets, ids)), a.shard)
    confirm_dir = (getattr(a, "confirm_dir", "") or f"{HERE}/confirm") if a.confirm else ""
    if confirm_dir:
        os.makedirs(confirm_dir, exist_ok=True)
    tag = a.shard.replace("/", "_") if a.shard else "all"
    tag = f"{getattr(a, 'tag', '') or ''}{tag}"
    results_dir = getattr(a, "results_dir", "") or blib.RESULTS_DIR
    os.makedirs(results_dir, exist_ok=True)
    path = f"{results_dir}/baselines-cuvein-shard{tag}.csv"
    import csv
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=blib.COLUMNS)
        w.writeheader()
        n = 0
        for m in rows:
            idir = f"{STORE}/{m['id']}"
            if not os.path.exists(f"{idir}/meta.json"):
                w.writerow(blib.row(id=m["id"], pset=m["pset"], program=m["program"],
                                    build=m["build"], input=m["input"], tool="cuvein",
                                    verdict="ERROR", notes="no-trace-collected"))
                continue
            n += 1
            print(f"[analyze {n}] {m['id']}", flush=True)
            try:
                analyze_one(idir, w, confirm_dir, getattr(a, "analysis_timeout", 0),
                            getattr(a, "analysis_mem", -1))
            except Exception as e:
                w.writerow(blib.row(id=m["id"], pset=m["pset"], program=m["program"],
                                    build=m["build"], input=m["input"], tool="cuvein",
                                    verdict="ERROR", notes=f"{type(e).__name__}:{e}"))
    print(f"analyze: {n} programs -> {path}")


def cmd_run(a):
    """Combined mode: for each program in the shard, collect its trace on this GPU
    node, analyze it inline, and KEEP the trace in the store (BeeGFS,
    $BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/<tag>; compute nodes only, not
    backed up) so a later detector revision is re-scored with `analyze` on identical
    traces without a GPU. --delete-traces restores the older lean behaviour (delete
    each program's trace right after its analysis; peak disk = one program) -- it was
    the default while traces landed on node-local disk or in the 40 GB home quota."""
    global STORE
    STORE = _store_root()
    import csv
    cuda = blib.resolve_cuda_home()
    psets = set(a.pset.split(",")) if a.pset else None
    ids = set(a.id.split(",")) if a.id else None
    if getattr(a,"id_file","") :
        _f=set(l.strip() for l in open(a.id_file) if l.strip()); ids=(ids or set())|_f
    rows = _shard(list(_rows(a.manifest, psets, ids)), a.shard)
    confirm_dir = (getattr(a, "confirm_dir", "") or f"{HERE}/confirm") if a.confirm else ""
    if confirm_dir:
        os.makedirs(confirm_dir, exist_ok=True)
    os.makedirs(STORE, exist_ok=True)
    keep_all = not getattr(a, "delete_traces", False)
    if keep_all:
        _write_store_info(STORE, a)
    kept_bytes = 0
    keep_dir = getattr(a, "keep_mismatch", "")
    if keep_dir:
        os.makedirs(keep_dir, exist_ok=True)
    tag = a.shard.replace("/", "_") if a.shard else "all"
    tag = f"{getattr(a, 'tag', '') or ''}{tag}"
    results_dir = getattr(a, "results_dir", "") or blib.RESULTS_DIR
    os.makedirs(results_dir, exist_ok=True)
    path = f"{results_dir}/baselines-cuvein-shard{tag}.csv"
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=blib.COLUMNS)
        w.writeheader()
        for i, m in enumerate(rows, 1):
            print(f"[run {i}/{len(rows)}] {m['id']}", flush=True)
            idir = f"{STORE}/{m['id']}"
            try:
                collect_one(m, cuda, a.reps, floor=getattr(a, "timeout_floor", 120))
                verdicts = analyze_one(idir, w, confirm_dir, getattr(a, "analysis_timeout", 0),
                            getattr(a, "analysis_mem", -1)) or {}
                if keep_dir:
                    reason = _keep_decision(verdicts, m.get("label", ""))
                    if reason:
                        kept = _keep_trace(idir, keep_dir, reason, getattr(a, "keep_cap_mb", 300))
                        print(f"  kept trace ({kept})", flush=True)
            except Exception as e:
                w.writerow(blib.row(id=m["id"], pset=m["pset"], program=m["program"],
                                    build=m["build"], input=m["input"], tool="cuvein",
                                    verdict="ERROR", notes=f"{type(e).__name__}:{e}"))
            finally:
                if keep_all:
                    kept_bytes += _cap_kept(idir, getattr(a, "keep_all_cap_gb", 0))
                else:
                    shutil.rmtree(idir, ignore_errors=True)   # TP/TN (and everything raw) deleted
            fh.flush()
    print(f"run: {len(rows)} programs -> {path}")
    if keep_all:
        print(f"kept traces: {kept_bytes / 1e9:.2f} GB in {STORE}")


def cmd_merge(a):
    """Concatenate eval/results/baselines-<tool>-shard*.csv -> baselines-<tool>.csv
    for each tool family given (default: cuvein). Shard files are never deleted."""
    import csv
    tools = [t for t in (getattr(a, "tool", "") or "cuvein").split(",") if t]
    for tool in tools:
        shards = sorted(glob.glob(f"{blib.RESULTS_DIR}/baselines-{tool}-shard*.csv"))
        if not shards:
            print(f"merge: no shards for {tool}")
            continue
        out = f"{blib.RESULTS_DIR}/baselines-{tool}.csv"
        seen = 0
        with open(out, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=blib.COLUMNS)
            w.writeheader()
            for sh in shards:
                for r in csv.DictReader(open(sh, newline="")):
                    w.writerow({c: r.get(c, "") for c in blib.COLUMNS})
                    seen += 1
        print(f"merge: {tool}: {len(shards)} shards, {seen} rows -> {out}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("collect", "analyze", "run"):
        p = sub.add_parser(name)
        p.add_argument("--manifest", default=f"{HERE}/manifest.csv")
        p.add_argument("--pset", default="")
        p.add_argument("--id", default="")
        p.add_argument("--id-file", dest="id_file", default="")
        p.add_argument("--shard", default="", help="k/N")
        p.add_argument("--reps", type=int, default=3)
        p.add_argument("--confirm", action="store_true")
        p.add_argument("--timeout-floor", dest="timeout_floor", type=int, default=120,
                       help="minimum tool timeout in s (P7 overhead set: 1200)")
        p.add_argument("--keep-mismatch", dest="keep_mismatch", default="",
                       help="dir (home) where FP/FN/ERROR/TIMEOUT traces are kept; "
                            "TP/TN traces are always deleted")
        p.add_argument("--keep-cap-mb", dest="keep_cap_mb", type=int, default=300,
                       help="size cap (MB) of one program's --keep-mismatch home copy; 0 = none")
        p.add_argument("--keep-all", dest="keep_all", action="store_true",
                       help="(default since T0; kept for old scripts) run: keep EVERY "
                            "program's trace in the BeeGFS store for later `analyze` re-scoring")
        p.add_argument("--delete-traces", dest="delete_traces", action="store_true",
                       help="run: delete each program's trace right after its analysis "
                            "(the pre-T0 lean mode; nothing is left to re-score)")
        p.add_argument("--keep-all-cap-gb", dest="keep_all_cap_gb", type=float, default=0,
                       help="drop a program's kernel JSONs above this size (0 = no cap, the "
                            "default: BeeGFS has room; a cap silently loses the largest traces)")
        p.add_argument("--tag", default="", help="prefix for the shard csv name")
        p.add_argument("--analysis-timeout", dest="analysis_timeout", type=int, default=0,
                       help="cap (s) on the offline per-mode trace analysis; past it the "
                            "rows are ERROR analysis-timeout (0 = unbounded)")
        p.add_argument("--analysis-mem-gb", dest="analysis_mem", type=float, default=-1,
                       help="with --analysis-timeout: address-space cap (GB) of the forked "
                            "analysis; -1 = 80%% of the node's RAM (default), 0 = none. A "
                            "MemoryError becomes an ERROR analysis-oom row instead of the "
                            "kernel OOM killer taking the whole shard (no row at all)")
        p.add_argument("--results-dir", dest="results_dir", default="",
                       help="write the shard csv here instead of eval/results (a detector "
                            "revision's re-run, kept apart from the merged baseline)")
        p.add_argument("--confirm-dir", dest="confirm_dir", default="",
                       help="with --confirm: detail JSON dir (default eval/baselines/confirm)")
    pm = sub.add_parser("merge")
    pm.add_argument("--tool", default="cuvein", help="comma list of tool families")
    a = ap.parse_args()
    {"collect": cmd_collect, "analyze": cmd_analyze, "run": cmd_run,
     "merge": cmd_merge}[a.cmd](a)


if __name__ == "__main__":
    main()

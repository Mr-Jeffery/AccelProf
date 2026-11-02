#!/usr/bin/env python3
"""X5 helpers shared by barrier_ordered_bins.py and pcdg_variance.py (analysis only: nothing
here changes the detector, the oracle or a verdict).

`rc._analyze_reports` is the harness's own verdict path (eval/baselines/run_cuvein.py, what
parallel.py analyze runs over a kept store). It reduces every kernel's `sync_dominance.analyze`
report to the RACE / SC reports and drops the ORDERED pairs, so the confirm files carry none of
them. `Capture` wraps `sync_dominance.analyze` for the duration of one such call and lets the
caller keep what it needs from each report (the pair classes, the edges) without running the
analysis twice; the harness result is returned unchanged next to it.

Runs on a compute node (the stores are on BeeGFS). CUVEIN_HOME defaults to this checkout.
"""
import json
import multiprocessing
import os
import queue
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = HERE.parents[2]                       # eval/baselines/setup -> checkout root
os.environ.setdefault("CUVEIN_HOME", str(WT))
sys.path.insert(0, str(WT / "eval" / "baselines"))
import blib                                # noqa: E402  (reads CUVEIN_HOME)
sys.path.insert(0, blib.PYDIR)
sys.path.insert(0, f"{blib.APH}/eval")
import sync_dominance as sd                # noqa: E402
import run_cuvein as rc                    # noqa: E402

MODES = ("vector-clock", "scalar-clock")
SCOPE_IDX = {s: i for i, s in enumerate(sd.SCOPES)}


def suite_of(pid):
    return pid.split("-", 1)[0]


class Capture:
    """Wrap sync_dominance.analyze: `fn(dot, kernel_json, report)` runs on every successful call
    (rc._analyze_reports tries each dot until one fits the kernel) and the report is handed back
    unchanged."""

    def __init__(self, fn):
        self.fn = fn

    def __enter__(self):
        self._orig = sd.analyze
        orig, fn = self._orig, self.fn

        def wrapped(dot, kj, *a, **k):
            rep = orig(dot, kj, *a, **k)
            fn(dot, kj, rep)
            return rep
        sd.analyze = wrapped
        return self

    def __exit__(self, *exc):
        sd.analyze = self._orig
        return False


def static_resolved(v):
    """R1 (a barrier/warpsync dominance of the observed distance) or R3 (a PC-level chain)
    ordered the pair, read off the verdict record the way analyze() computed it:
    r1_ordered = strength >= observed, chain_ordered = a chain exists."""
    return SCOPE_IDX[v["strength"]] >= SCOPE_IDX[v["observed_distance"]] \
        or v["hb_chain"] is not None


class PairLog:
    """Per recording: one entry per directed pair (kernel, ancient pc, current pc, space class)
    over all launches of the recording, plus (want_edges) the PCDG edges of the kernel JSONs.

      cls        the set of hb_class values the pair took over the launches (None = the
                 scalar-clock static verdict of an ordered pair carries no class)
      unresolved True if in some launch neither R1 nor R3 ordered it
      n          launches in which it was judged
    The kernel id is "<dot basename>::<mangled name>"; kdot maps it back to the dot path."""

    def __init__(self, want_edges=False):
        self.pairs = {}
        self.kdot = {}
        self.launches = {}
        self.edges = set()
        self.want_edges = want_edges
        self.nlaunch = 0

    def __call__(self, dot, kj, rep):
        kid = f"{os.path.basename(dot)}::{rep['kernel']['mangled']}"
        self.kdot[kid] = str(dot)
        self.launches[kid] = self.launches.get(kid, 0) + 1
        self.nlaunch += 1
        for v in rep["verdicts"]:
            key = (kid, v["ancient_pc"], v["current_pc"], v["space"].split("/")[0])
            e = self.pairs.get(key)
            if e is None:
                e = self.pairs[key] = {"cls": set(), "unresolved": False, "n": 0,
                                       "race_type": set(), "verdict": set()}
            e["cls"].add(v["hb_class"])
            e["race_type"].add(v["race_type"])
            e["verdict"].add(v["verdict"])
            e["n"] += 1
            if not static_resolved(v):
                e["unresolved"] = True
        if self.want_edges:
            tr = json.loads(Path(kj).read_text())
            for ed in tr.get("edges", []):
                if ed.get("ancient_pc") is not None and not ed.get("cold_miss"):
                    self.edges.add((kid, ed["ancient_pc"], ed["current_pc"]))


def run_capped(fn, cap_s, mem_gb):
    """fn() in a forked child with a wall cap (cap_s, 0 = none) and an address-space cap
    (mem_gb, 0 = none) -> (payload, reason). reason '' = ran; 'analysis-timeout';
    'analysis-oom(...)'; 'analysis-died(rc=N)'; 'exception:<Type>:<msg>'."""
    ctx = multiprocessing.get_context("fork")
    q = ctx.Queue()

    def child():
        try:
            if mem_gb:
                import resource
                lim = int(mem_gb * 1e9)
                resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
            q.put(("OK", fn()))
        except MemoryError:
            os._exit(3)
        except Exception as e:                      # noqa: BLE001 -- reported, never swallowed
            q.put(("EXC", f"{type(e).__name__}:{str(e)[:300]}"))

    proc = ctx.Process(target=child)
    proc.start()
    deadline = time.time() + cap_s if cap_s else None
    tag = payload = None
    while tag is None:
        try:
            tag, payload = q.get(timeout=5)
            break
        except queue.Empty:
            pass
        if not proc.is_alive():
            try:
                tag, payload = q.get(timeout=5)
                break
            except queue.Empty:
                proc.join()
                if proc.exitcode == 3:
                    return None, f"analysis-oom(cap={mem_gb}GB)"
                return None, f"analysis-died(rc={proc.exitcode})"
        if deadline and time.time() > deadline:
            proc.kill()
            proc.join()
            return None, "analysis-timeout"
    proc.join()
    if tag == "OK":
        return payload, ""
    return None, f"exception:{payload}"


def lpt_shards(items, weight, n):
    """Longest-processing-time assignment of items to n shards -> list of n lists."""
    loads, out = [0] * n, [[] for _ in range(n)]
    for it in sorted(items, key=weight, reverse=True):
        i = loads.index(min(loads))
        out[i].append(it)
        loads[i] += max(weight(it), 1)
    return out


def done_keys(path, keyf):
    """Keys already present in a jsonl output (resume after a time limit)."""
    got = set()
    if os.path.exists(path):
        for ln in open(path):
            try:
                got.add(keyf(json.loads(ln)))
            except Exception:                      # a truncated last line
                pass
    return got


def append_jsonl(path, rec):
    with open(path, "a") as f:
        f.write(json.dumps(rec, separators=(",", ":")) + "\n")
        f.flush()
        os.fsync(f.fileno())

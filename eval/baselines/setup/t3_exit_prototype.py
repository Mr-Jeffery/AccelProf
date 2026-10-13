#!/usr/bin/env python3
"""T3 (eval/CRS_CUDA_TRIAGE.md §6): an OFFLINE check of the proposed fix on crs-cuda's own
dumps -- not the fix. Every thread that exits in crs-cuda does so before its first access
(kernels.cu:71-77), so there "the threads of a block that ever appear in the event stream" is
exactly the block's non-exited set. Each plain __syncthreads() event (thread_count 0) is given
that count -- the participant count an exit-aware assembly reaches -- and the dump re-scored:
  scalar-clock  sync_dominance.analyze of the rewritten dump (the offline barrier pass reads
                the counts; the static leg is unchanged)
  vector-clock  hb_oracle.analyze of the rewritten vector-clock dump, strict (TV checks on),
                gives the race records the engine would emit; they replace the dump's
                hb_races / hb_races_sync_only and sync_dominance.analyze gives the verdicts
Prints, per dump, the RACE reports before (the dump as recorded) and after, as
(ancient line, current line, type) counts. CPU only (the store is on BeeGFS).
  t3_exit_prototype.py [kernel_N ...]    -> setup/t3_crs/exit_prototype.json"""
import collections
import glob
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, f"{APH}/python")
import hb_oracle as ho          # noqa: E402
import sync_dominance as sd     # noqa: E402

STORE = "/mnt/beegfs/fzheng4/cuvein_traces/full-2026-09-22/P9-crs-cuda"
DEFAULT = ["kernel_4", "kernel_6", "kernel_8", "kernel_10", "kernel_12", "kernel_16",
           "kernel_20", "kernel_21"]


def lines_of():
    """pc -> kernels.cu:<line> of each kernel (setup/t3_crs/lineinfo.txt.gz), by mangled name."""
    import gzip, re
    out, cur, line = collections.defaultdict(dict), None, None
    for ln in gzip.open(f"{HERE}/t3_crs/lineinfo.txt.gz", "rt"):
        m = re.match(r"\s*\.section\s+\.text\.(\S+),", ln)
        if m:
            cur = m.group(1)
            continue
        m = re.search(r'//## File "[^"]*/([^"/]+)", line (\d+)', ln)
        if m:
            line = f"{m.group(1)}:{m.group(2)}"
            continue
        m = re.match(r"\s*/\*([0-9a-f]{4,})\*/", ln)
        if m and cur and line:
            out[cur][int(m.group(1), 16)] = line
    return out


def exit_aware(trace):
    """Give each plain barrier event its block's seen-thread count (in place)."""
    seen = collections.defaultdict(set)
    for e in trace["hb_events"]:
        b, w = e.get("block"), e.get("warp")
        if "lanes" in e:
            seen[b].update((w << 5) | l["lane"] for l in e["lanes"])
        elif "active_mask" in e:
            seen[b].update((w << 5) | k for k in range(32) if (e["active_mask"] >> k) & 1)
    short = 0
    for e in trace["hb_events"]:
        if e["type"] == "barrier" and not e.get("thread_count"):
            e["thread_count"] = len(seen[e["block"]])
            short += e["thread_count"] < trace["kernel"]["block_thread_count"]
    return short


def score(dots, path_or_trace, tmp):
    if not isinstance(path_or_trace, str):
        with open(tmp, "w") as f:
            json.dump(path_or_trace, f)
        path_or_trace = tmp
    for dot in dots:
        try:
            return sd.analyze(dot, path_or_trace)
        except sd.AlignmentError:
            continue
    raise RuntimeError("no dot aligns")


def summarize(rep, lines):
    by = lines.get(rep["kernel"]["mangled"], {})
    c = collections.Counter((by.get(v["ancient_pc"], hex(v["ancient_pc"])),
                             by.get(v["current_pc"], hex(v["current_pc"])), v["race_type"],
                             v.get("hb_class")) for v in rep["verdicts"] if v["verdict"] == "RACE")
    return {" ".join(map(str, k)): n for k, n in sorted(c.items())}


def one(kname):
    dots = sorted(glob.glob(f"{STORE}/dots/*.dot"))
    lines = lines_of()
    tmp = f"/dev/shm/t3_exit_{os.getpid()}_{kname}.json"
    res = {"kernel": kname}
    try:
        for mode in ("scalar-clock", "vector-clock"):
            path = f"{STORE}/{mode}/{kname}.json"
            before = score(dots, path, tmp)
            t = json.load(open(path))
            res.setdefault("name", t["kernel"]["kernel_name"])
            short = exit_aware(t)
            tv = None
            if mode == "vector-clock":
                t.pop("tv_violation", None)
                with open(tmp, "w") as f:
                    json.dump(t, f)
                dot = before["inputs"]["cfg_dot"]
                try:
                    orc = ho.analyze(dot, tmp)          # strict unless $YOSEMITE_HB_STRICT=0
                except sd.AlignmentError as e:
                    tv = str(e)[:200]
                    orc = None
                if orc is not None:
                    t["hb_races"], t["hb_races_sync_only"] = orc["races"], orc["races_sync_only"]
            after = score(dots, t, tmp) if (mode == "scalar-clock" or tv is None) else None
            res[mode] = {"barrier_events_short": short, "oracle_tv": tv,
                         "before": summarize(before, lines),
                         "after": None if after is None else summarize(after, lines)}
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return res


def main():
    names = sys.argv[1:] or DEFAULT
    with ProcessPoolExecutor(max_workers=int(os.environ.get("NPROC", "4"))) as ex:
        out = list(ex.map(one, names))
    for r in out:
        for mode in ("scalar-clock", "vector-clock"):
            m = r[mode]
            nb, na = sum(m["before"].values()), (sum(m["after"].values()) if m["after"] is not None else None)
            print(f"{r['kernel']:10s} {r['name'][:22]:22s} {mode:12s} barrier events given a "
                  f"short count {m['barrier_events_short']:6d}  RACE before {nb:3d} -> after "
                  f"{na}  {'TV: ' + m['oracle_tv'] if m['oracle_tv'] else ''}")
            if m["after"]:
                print("      remaining:", m["after"])
    with open(f"{HERE}/t3_crs/exit_prototype.json", "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()

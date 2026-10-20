#!/usr/bin/env python3
"""WARPSYNC join gap, phase 2: diverged-warp syncwarp census and the merged replay (read only).

  wjg_census.py run --scan <scan.jsonl> --out <jsonl> [--min-mb a] [--max-mb b] [--slots k]
                    [--mem-gb g] [--timeout s] [--select partial|validate]
  wjg_census.py census --real <kernel json> --out <json> [--tmpdir d]      (one child)
  wjg_census.py replay --dot <dot> --trace <json> --out <json>              (one child)

For every kernel JSON the byte scan (wjg_scan.py) found with a partial syncwarp record (active
mask not covering the sync mask: a diverged warp's group), one `census` child per file:

  * loads the dump and sorts hb_events by seq (as hb_oracle.analyze does);
  * checks the scan's counts against the parsed records (records, full/partial syncwarps);
  * runs X5_BYTE_PAIRS' merge procedure, `partial_instances` below, copied verbatim from
    eval/baselines/setup/x5b_partial.py (eval/x5-byte-pairs b5e10b4): per (block, warp, pc),
    consecutive syncwarp records whose active masks reach the sync mask form one instance; a
    completed instance is merged into one record at its completion (active mask = the union,
    the earlier records dropped); its `pending_mem` counter is X5's count of memory records
    of not-yet-arrived lanes (per open instance);
  * adds counters X5 did not keep (`extras`): the same memory records counted once each and
    only for lanes inside the sync mask; instances by number of records; instances left open
    at the end of the launch; syncwarp records at another pc that arrive while an instance of
    the same warp is open (a completion across call sites, which a per-pc key cannot see);
  * if an instance completed, writes the merged dump to --tmpdir for the replay.

Then two `replay` children run hb_oracle.analyze -- the specification HbClock matches bit for bit
(CLAUDE.md A4) -- on the dump as recorded and on the merged dump, with the dump's own gate and
policy (CUVEIN_GATE*, CUVEIN_STRONG_LDST unset). Race pairs compared at three levels:
  L1  races `space:a_pc-b_pc:kind:class` and races_sync_only `a_pc-b_pc` (X5's keys)
  L2  races with thread distance and async side (hb_oracle's aggregate key)
  L3  L2 with count and a2_uncertain; races_sync_only with count
Each child runs under RLIMIT_AS = --mem-gb; a child killed by the limit or the timeout is
recorded as such (the file is then missing at that budget). The stores are only read; the
merged dump is deleted after its replay.
"""
import argparse
import collections
import glob
import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = HERE.parents[2]                       # eval/baselines/setup -> checkout root
os.environ.setdefault("CUVEIN_HOME", str(WT))
MEM = ("read", "write", "atomic")


def _imports():
    sys.path.insert(0, str(WT / "eval" / "baselines"))
    import blib                            # noqa: F401  (reads CUVEIN_HOME)
    sys.path.insert(0, blib.PYDIR)
    import sync_dominance as sd
    import hb_oracle as ho
    return sd, ho


# ---- X5_BYTE_PAIRS' merge procedure: x5b_partial.partial_instances (b5e10b4), verbatim ----
def partial_instances(ev):
    """-> (census Counter, merged event list, open-instance memory-record count)."""
    c = collections.Counter()
    opened = {}                                    # (block, warp, pc) -> [first_seq, union, records]
    drop = set()                                   # seqs of partial records merged away
    widen = {}                                     # seq of a completing record -> union mask
    pending_mem = 0
    for e in ev:
        ty = e.get("type")
        if ty == "syncwarp":
            k = (e["block"], e["warp"], e["pc"])
            sm, am = e["sync_mask"], e["active_mask"]
            if k not in opened:
                if am & sm == sm:
                    c[f"full {e['pc']:#x}"] += 1
                    continue
                opened[k] = [e["seq"], am, [e["seq"]]]
                c[f"partial {e['pc']:#x}"] += 1
                continue
            st = opened[k]
            st[1] |= am
            st[2].append(e["seq"])
            c[f"partial {e['pc']:#x}"] += 1
            if st[1] & sm == sm:
                c["partial instances completed"] += 1
                c[f"partial instance of {len(st[2])} records"] += 1
                drop.update(st[2][:-1])
                widen[st[2][-1]] = st[1]
                del opened[k]
        elif ty in MEM:
            for (b, w, _), st in opened.items():
                if b == e["block"] and w == e["warp"]:
                    lanes = {ln["lane"] for ln in e["lanes"]}
                    if any(not (st[1] >> l) & 1 for l in lanes):
                        pending_mem += 1
    c["partial instances never completed"] += len(opened)
    merged = []
    for e in ev:
        if e["seq"] in drop:
            continue
        if e["seq"] in widen:
            e = dict(e, active_mask=widen[e["seq"]])
        merged.append(e)
    return c, merged, pending_mem
# ---- end of the verbatim copy ----


def extras(ev):
    """Counters beside X5's (same instance rule: per (block, warp, pc), union reaches sync_mask)."""
    x = collections.Counter()
    opened = {}                                    # (block, warp, pc) -> [union, sync_mask, n]
    open_by_warp = collections.defaultdict(set)    # (block, warp) -> {pc}
    late_lanes = 0
    for e in ev:
        ty = e.get("type")
        if ty == "syncwarp":
            bw = (e["block"], e["warp"])
            k = (*bw, e["pc"])
            sm, am = e["sync_mask"], e["active_mask"]
            if k not in opened and open_by_warp[bw]:
                # a syncwarp record at another pc while an instance of this warp is open
                x["syncwarp records at another pc inside an open instance"] += 1
                if any(am & ~opened[(*bw, p)][0] & opened[(*bw, p)][1] for p in open_by_warp[bw]):
                    x["... with lanes the open instance still waits for"] += 1
            if k not in opened:
                if am & sm == sm:
                    continue
                opened[k] = [am, sm, 1]
                open_by_warp[bw].add(e["pc"])
                x["sync_mask full"] += sm == 0xffffffff
                x["sync_mask partial"] += sm != 0xffffffff
                continue
            st = opened[k]
            st[0] |= am
            st[2] += 1
            if st[0] & sm == sm:
                x[f"instances of {st[2]} records"] += 1
                del opened[k]
                open_by_warp[bw].discard(e["pc"])
        elif ty in MEM:
            bw = (e["block"], e["warp"])
            pcs = open_by_warp.get(bw)
            if not pcs:
                continue
            m = e.get("active_mask")
            if m is None:
                m = 0
                for ln in e["lanes"]:
                    m |= 1 << ln["lane"]
            waiting = 0
            for p in pcs:
                u, sm, _ = opened[(*bw, p)]
                waiting |= sm & ~u
            if m & waiting:
                x["memory records of not-yet-arrived lanes (once, sync-mask lanes)"] += 1
                late_lanes += bin(m & waiting).count("1")
                x[f"... by space {e.get('space')}"] += 1
    x["lane accesses of not-yet-arrived lanes"] = late_lanes
    x["instances open at the end"] = len(opened)
    return x


def race_sets(rep):
    r1, r2, r3 = set(), set(), {}
    for r in rep["races"]:
        if r.get("a_pc") is None:
            continue
        k1 = f"{r['space']}:{r['a_pc']:#x}-{r['b_pc']:#x}:{r['kind']}:{r['class']}"
        k2 = f"{k1}:{r.get('dist')}:{r.get('async', '')}"
        r1.add(k1)
        r2.add(k2)
        r3[k2] = [r["count"], r.get("a2_uncertain")]
    so = {f"{a:#x}-{b:#x}": n for a, b, n in rep["races_sync_only"]}
    return {"races_L1": sorted(r1), "races_L2": sorted(r2), "races_L3": r3,
            "sync_only_L1": sorted(so), "sync_only_L3": so,
            "summary": {k: v for k, v in rep.get("summary", {}).items() if k in ("races", "events", "sc")},
            "gate": rep.get("gate"), "gate_policy": rep.get("gate_policy")}


def pick_dot(sd, real, kname):
    dots = sorted(glob.glob(os.path.join(os.path.dirname(os.path.dirname(real)), "dots", "*.dot")))
    for d in dots:
        try:
            sd.select_kernel(sd.parse_dot(d), kname)
            return d, len(dots)
        except Exception:                      # AlignmentError or a dot that does not parse
            continue
    return None, len(dots)


def cmd_census(a):
    import orjson
    sd, _ = _imports()
    t0 = time.time()
    t = orjson.loads(Path(a.data or a.real).read_bytes())
    ev = sorted(t.get("hb_events") or [], key=lambda e: e["seq"])
    out = {"real": a.real, "kname": t["kernel"]["kernel_name"], "records": len(ev),
           "sw_full": 0, "sw_partial": 0, "seq_sorted_in_file": True}
    last = -1
    for e in t.get("hb_events") or []:
        if e["seq"] < last:
            out["seq_sorted_in_file"] = False
        last = e["seq"]
    for e in ev:
        if e.get("type") == "syncwarp":
            if e["active_mask"] & e["sync_mask"] == e["sync_mask"]:
                out["sw_full"] += 1
            else:
                out["sw_partial"] += 1
    out["hb_exits"] = bool(t.get("hb_exits"))
    out["hb_async"] = t.get("hb_async")
    c, merged, pend = partial_instances(ev)
    out["x5_census"] = dict(c)
    out["x5_pending_mem"] = pend
    out["extras"] = dict(extras(ev))
    out["completed"] = c.get("partial instances completed", 0)
    out["dropped_records"] = len(ev) - len(merged)
    dot, ndots = pick_dot(sd, a.real, out["kname"])
    out["dot"], out["ndots"] = dot, ndots
    if dot:                                  # the SASS at every pc with partial syncwarp records
        pcs = {int(k.split()[1], 16) for k in c if k.startswith("partial 0x")}
        ops = {hex(p): [] for p in sorted(pcs)}
        for mangled, (blocks, _, _) in sd.parse_dot(dot).items():
            for instrs in blocks.values():
                for ins in instrs:
                    if ins[0] in pcs:
                        ops[hex(ins[0])].append([mangled[:80], ins[1]])
        out["partial_pc_opcodes"] = ops
    if out["completed"] and dot:
        fd = os.open(a.merged, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(orjson.dumps(dict(t, hb_events=merged)))
        out["merged"] = a.merged
    out["secs"] = round(time.time() - t0, 1)
    Path(a.out).write_text(json.dumps(out))


def cmd_replay(a):
    sd, ho = _imports()
    t0 = time.time()
    try:
        rep = ho.analyze(a.dot, a.trace)
        out = race_sets(rep)
    except sd.AlignmentError as e:
        out = {"error": f"AlignmentError: {str(e)[:300]}"}
    out["secs"] = round(time.time() - t0, 1)
    Path(a.out).write_text(json.dumps(out))


def cmd_bpass(a):
    """sync_dominance.barrier_only_pairs -- the scalar-clock mode's offline pass, the same
    clock as hb_oracle's races_sync_only (test_offline_barrier_pass_matches_oracle) at O(threads)
    per barrier -- with the rmw / coherent / async pcs exactly as analyze() derives them and no
    lane cutoff."""
    import orjson
    sd, _ = _imports()
    t0 = time.time()
    tj = orjson.loads(Path(a.trace).read_bytes())
    kernels = sd.parse_dot(a.dot)
    eng = sd.HBGraph(*kernels[sd.select_kernel(kernels, tj["kernel"]["kernel_name"])])
    policy = sd.strong_ldst_policy(None)
    rmw = {pc: s for pc, op in eng.pc_opcode.items() if (s := sd.atomic_scope(op)) is not None}
    coh = {pc: s for pc, op in eng.pc_opcode.items() if (s := sd.coherent_scope(op, policy)) is not None}
    dist, tv = {}, []
    try:
        pairs = sd.barrier_only_pairs(tj, rmw, coh, None, dist, None, sd.dump_async_pcs(eng, tj), tv)
        so = {f"{x:#x}-{y:#x}": n for (x, y), n in sorted((pairs or {}).items())}
        out = {"sync_only_L1": sorted(so), "sync_only_L3": so,
               "dist": {f"{x:#x}-{y:#x}": str(d) for (x, y), d in dist.items()}, "tv": tv[:5]}
    except sd.AlignmentError as e:
        out = {"error": f"AlignmentError: {str(e)[:300]}"}
    out["secs"] = round(time.time() - t0, 1)
    Path(a.out).write_text(json.dumps(out))


def run_child(args, mem_gb, timeout):
    """-> (returncode or signal name, seconds, max RSS in MB, stderr tail)."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("CUVEIN_GATE", "CUVEIN_STRONG_LDST", "YOSEMITE_HB_STRICT"))}
    env["CUVEIN_HOME"] = str(WT)
    lim = int(mem_gb * (1 << 30))

    def pre():
        resource.setrlimit(resource.RLIMIT_AS, (lim, lim))
        os.setsid()
    t0 = time.time()
    p = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), *args], env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, preexec_fn=pre)
    killed = []

    def kill():
        killed.append(1)
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    tm = threading.Timer(timeout, kill)
    tm.start()
    err = p.stderr.read().decode(errors="replace")
    _, status, ru = os.wait4(p.pid, 0)
    tm.cancel()
    p.returncode = os.waitstatus_to_exitcode(status)
    rc = "timeout" if killed else ("MemoryError" if "MemoryError" in err else p.returncode)
    return rc, round(time.time() - t0, 1), ru.ru_maxrss // 1024, err[-600:]


def one_file(real, a, idx):
    work = Path(a.tmpdir) / f"wjg_{os.getpid()}_{idx}"
    work.mkdir(parents=True, exist_ok=True)
    rec = {"real": real, "budget_gb": a.mem_gb}
    try:
        cen = work / "census.json"
        mrg = work / "merged.json"
        data = real
        if os.path.getsize(real) >= a.copy_mb * (1 << 20):
            # BeeGFS reads at ~100 MB/s per node here: read a large dump once, onto local disk
            t0 = time.time()
            data = str(work / "orig.json")
            shutil.copyfile(real, data)
            rec["local_copy_secs"] = round(time.time() - t0, 1)
        rc, secs, rss, err = run_child(["census", "--real", real, "--data", data, "--out", str(cen),
                                        "--merged", str(mrg)], a.mem_gb, a.timeout)
        rec["census_child"] = {"rc": rc, "secs": secs, "maxrss_mb": rss}
        if rc != 0 or not cen.exists():
            rec["census_child"]["stderr"] = err
            return rec
        rec["census"] = json.loads(cen.read_text())
        if not rec["census"].get("merged"):
            return rec
        for kind in ("bpass", "replay"):          # the cheap pass first: it survives an oracle OOM
            for name, trace in (("as_recorded", data), ("merged", str(mrg))):
                o = work / f"{kind}_{name}.json"
                rc, secs, rss, err = run_child([kind, "--dot", rec["census"]["dot"], "--trace", trace,
                                                "--out", str(o)], a.mem_gb, a.timeout)
                rec[f"{kind}_{name}_child"] = {"rc": rc, "secs": secs, "maxrss_mb": rss}
                if rc != 0 or not o.exists():
                    rec[f"{kind}_{name}_child"]["stderr"] = err
                    continue
                rec[f"{kind}_{name}"] = json.loads(o.read_text())
        return rec
    finally:
        for p in work.glob("*"):
            p.unlink()
        work.rmdir()


def cmd_run(a):
    seen, todo = set(), []
    for ln in open(a.scan):
        s = json.loads(ln)
        if s["real"] in seen:
            continue
        seen.add(s["real"])
        mb = s["bytes"] / (1 << 20)
        if not (a.min_mb <= mb < a.max_mb):
            continue
        if a.select == "partial" and s["sw_partial"] > 0:
            todo.append((s["bytes"], s["real"]))
        elif a.select == "validate" and s["sw_partial"] == 0 and s["sw_full"] > 0:
            todo.append((s["bytes"], s["real"]))
    todo.sort()
    done = set()
    if os.path.exists(a.out):
        for ln in open(a.out):
            r = json.loads(ln)
            if r.get("census_child", {}).get("rc") in (0, "0") or r.get("budget_gb", 0) >= a.mem_gb:
                done.add(r["real"])
    todo = [p for _, p in todo if p not in done]
    print(f"{len(todo)} files ({a.select}, {a.min_mb}-{a.max_mb} MB), {a.slots} slots x {a.mem_gb} GB",
          flush=True)
    lock = threading.Lock()
    t0 = time.time()
    with open(a.out, "a") as out, ThreadPoolExecutor(a.slots) as pool:
        futs = [pool.submit(one_file, p, a, i) for i, p in enumerate(todo)]
        for k, f in enumerate(futs, 1):
            r = f.result()
            with lock:
                out.write(json.dumps(r) + "\n")
                out.flush()
            c = r.get("census", {})
            diff = ""
            if "replay_as_recorded" in r and "replay_merged" in r:
                b, m = r["replay_as_recorded"], r["replay_merged"]
                diff = " ".join(f"{lv}:{len(set(m.get(lv, [])) - set(b.get(lv, [])))}+/"
                                f"{len(set(b.get(lv, [])) - set(m.get(lv, [])))}-"
                                for lv in ("races_L1", "sync_only_L1", "races_L2"))
            print(f"{k}/{len(todo)} {time.time() - t0:.0f}s {r['census_child']} "
                  f"completed={c.get('completed')} pend={c.get('x5_pending_mem')} {diff} "
                  f"{r['real'][-100:]}", flush=True)
    print(f"done {time.time() - t0:.0f}s", flush=True)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--scan", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--min-mb", type=float, default=0)
    p.add_argument("--max-mb", type=float, default=1e12)
    p.add_argument("--slots", type=int, default=8)
    p.add_argument("--mem-gb", type=float, default=20)
    p.add_argument("--timeout", type=float, default=6 * 3600)
    p.add_argument("--select", choices=("partial", "validate"), default="partial")
    p.add_argument("--tmpdir", default=os.environ.get("TMPDIR", "/tmp"))
    p.add_argument("--copy-mb", type=float, default=500,
                   help="copy dumps at least this large to --tmpdir before reading them")
    p = sub.add_parser("census")
    p.add_argument("--real", required=True)
    p.add_argument("--data", default="", help="a local copy of --real to read instead")
    p.add_argument("--out", required=True)
    p.add_argument("--merged", required=True)
    for name in ("replay", "bpass"):
        p = sub.add_parser(name)
        p.add_argument("--dot", required=True)
        p.add_argument("--trace", required=True)
        p.add_argument("--out", required=True)
    a = ap.parse_args()
    {"run": cmd_run, "census": cmd_census, "replay": cmd_replay, "bpass": cmd_bpass}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())

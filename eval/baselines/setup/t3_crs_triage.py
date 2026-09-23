#!/usr/bin/env python3
"""T3 (crs-cuda triage): re-score one kept-store program kernel by kernel with the
current detector and tabulate every report with its source lines, verdict-matrix class
and (vector-clock) the racing thread ids; plus barrier-instance diagnostics from the
event stream: arrivals per dynamic instance vs the expected participant count, warps
that issue a post-barrier access while the model still holds their instance open (the
hardware released it), and threads that never appear in the stream.

  t3_crs_triage.py --store /mnt/beegfs/$USER/cuvein_traces/full-2026-09-22 --id P9-crs-cuda \
      --lineinfo <nvdisasm --print-line-info output> --out eval/baselines/setup/t3_crs

Writes <out>/triage.json (everything), <out>/triage.md (tables) and
<out>/detail_<mode>.json ({"dedup_reports": [...]}, the shape eval/triage.py reads).
Read-only on the store; runs on a CPU node (BeeGFS)."""
import argparse
import collections
import glob
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "python"))
import sync_dominance as sd  # noqa: E402

MODES = ("vector-clock", "scalar-clock")


def parse_lineinfo(path):
    """nvdisasm --print-line-info text -> {mangled function: {pc: 'file:line'}}."""
    out, func, loc = {}, None, None
    rx_sec = re.compile(r'^\s*\.section\s+\.text\.([^,\s]+)')
    rx_file = re.compile(r'//## File "([^"]+)", line (\d+)')
    rx_pc = re.compile(r'/\*([0-9a-f]{4,})\*/')
    for line in open(path, errors="replace"):
        m = rx_sec.match(line)
        if m:
            func, loc = m.group(1), None
            out.setdefault(func, {})
            continue
        m = rx_file.search(line)
        if m:
            loc = f"{os.path.basename(m.group(1))}:{m.group(2)}"
            continue
        m = rx_pc.search(line)
        if m and func is not None and loc is not None:
            out[func][int(m.group(1), 16)] = loc
    return out


def tid_parts(t):
    return {"block": t >> 10, "warp": (t >> 5) & 0x1f, "lane": t & 0x1f}


def barrier_diag(trace):
    """Replay only the barrier-instance assembly of hb_oracle/HbEngine over hb_events."""
    ev = sorted(trace.get("hb_events") or (), key=lambda e: e["seq"])
    btc = trace["kernel"].get("block_thread_count")
    tid = lambda b, w, l: (b << 10) | (w << 5) | l
    pending, expected_of, waiting = {}, {}, {}
    fired = collections.Counter()          # arrivals at fire time -> instances
    ran_past = collections.Counter()       # (arrived, expected) -> instances released short
    seen = collections.defaultdict(set)    # block -> tids seen in any event
    n_mem = n_bar = 0
    for e in ev:
        b, w = e["block"], e["warp"]
        typ = e["type"]
        if typ == "barrier":
            n_bar += 1
            key, m = (b, e["bar_index"]), e["active_mask"]
            arr = pending.setdefault(key, set())
            lanes = [k for k in range(32) if (m >> k) & 1]
            arr.update(tid(b, w, k) for k in lanes)
            seen[b].update(tid(b, w, k) for k in lanes)
            exp = e.get("thread_count") or btc
            expected_of[key] = exp
            if not exp or len(arr) >= exp:
                fired[len(arr)] += 1
                for t in arr:
                    waiting.pop((b, (t >> 5) & 0x1f), None)
                del pending[key]
            else:
                waiting[(b, w)] = key
            continue
        if typ == "syncwarp":
            m = e["sync_mask"]
            seen[b].update(tid(b, w, k) for k in range(32) if (m >> k) & 1)
            continue
        n_mem += 1
        seen[b].update(tid(b, w, l["lane"]) for l in e.get("lanes", ()))
        key = waiting.get((b, w))
        if key is not None and key in pending:
            arr = pending.pop(key)
            ran_past[(len(arr), expected_of.get(key))] += 1
            for t in arr:
                waiting.pop((b, (t >> 5) & 0x1f), None)
    missing = collections.Counter((btc or 0) - len(s) for s in seen.values())
    left_open = collections.Counter((len(a), expected_of.get(k)) for k, a in pending.items())
    return {
        "block_thread_count": btc, "blocks_seen": len(seen), "mem_events": n_mem,
        "barrier_records": n_bar,
        "instances_fired": sum(fired.values()),
        "fired_by_arrivals": {str(k): v for k, v in sorted(fired.items())},
        "instances_released_short": sum(ran_past.values()),
        "released_short_by_arrived_expected": {f"{a}/{x}": v for (a, x), v in sorted(ran_past.items())},
        "instances_left_open": sum(left_open.values()),
        "left_open_by_arrived_expected": {f"{a}/{x}": v for (a, x), v in sorted(left_open.items())},
        "threads_never_seen_per_block": {str(k): v for k, v in sorted(missing.items())},
    }


def race_stats(trace):
    """hb_races grouped by unordered pc pair -> counts, thread relations, samples."""
    by = collections.defaultdict(list)
    for r in trace.get("hb_races") or ():
        if r.get("a_pc") is None:
            continue
        by[(min(r["a_pc"], r["b_pc"]), max(r["a_pc"], r["b_pc"]))].append(r)
    out = {}
    for k, recs in by.items():
        rel = collections.Counter(sd.SCOPES[sd.thread_distance(r["a_tid"], r["b_tid"])]
                                  for r in recs)
        same_addr_writer_lane = sum(1 for r in recs if r["a_tid"] == r["b_tid"])
        out[k] = {
            "records": len(recs),
            "relation": dict(rel),
            "kinds": dict(collections.Counter(r["kind"] for r in recs)),
            "distinct_blocks": len({r["b_tid"] >> 10 for r in recs}),
            "self_pairs": same_addr_writer_lane,
            "samples": [{"a": tid_parts(r["a_tid"]), "a_pc": hex(r["a_pc"]),
                         "b": tid_parts(r["b_tid"]), "b_pc": hex(r["b_pc"]),
                         "kind": r["kind"], "space": r.get("space"), "addr": hex(r["addr"])}
                        for r in recs[:3]],
        }
    return out


def short(name):
    m = re.search(r"(gcrs_m_\d+_w_\d+)", name)
    return m.group(1) if m else name[:40]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--lineinfo", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--modes", default=",".join(MODES))
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    idir = os.path.join(a.store, a.id)
    li = parse_lineinfo(a.lineinfo) if a.lineinfo else {}
    # largest dot first: sd.analyze parses the whole kernel JSON before it can tell that a
    # dot lacks the kernel, and 4 of this binary's 6 dots are empty (14 bytes)
    dots = sorted(glob.glob(f"{idir}/dots/*.dot"), key=lambda p: -os.path.getsize(p))
    result = {"store": a.store, "id": a.id, "modes": {}}
    for mode in a.modes.split(","):
        kjs = sorted(glob.glob(f"{idir}/{mode}/kernel_*.json"),
                     key=lambda p: int(re.search(r"kernel_(\d+)", p).group(1)))
        kernels, dedup = [], {}
        t0 = time.time()
        for kj in kjs:
            trace = json.loads(open(kj).read())
            kname = trace["kernel"]["kernel_name"]
            info = {"file": os.path.basename(kj), "bytes": os.path.getsize(kj),
                    "kernel": kname, "short": short(kname),
                    "grid_dim": trace["kernel"].get("grid_dim"),
                    "block_dim": trace["kernel"].get("block_dim"),
                    "hb_events": len(trace.get("hb_events") or ()),
                    "hb_races": None if trace.get("hb_races") is None else len(trace["hb_races"]),
                    "tv_violation": trace.get("tv_violation"),
                    "barrier": barrier_diag(trace)}
            rs = race_stats(trace) if trace.get("hb_races") is not None else {}
            del trace
            rep = None
            for dot in dots:
                try:
                    rep = sd.analyze(dot, kj)
                    break
                except sd.AlignmentError:
                    continue
            if rep is None:
                info["aligned"] = False
                kernels.append(info)
                continue
            info["aligned"] = True
            info["mangled"] = rep["kernel"]["mangled"]
            lmap = li.get(rep["kernel"]["mangled"], {})
            info["summary"] = rep["summary"]
            info["event_candidates"] = rep["diagnostics"].get("event_candidates")
            info["syncs"] = [(s["pc_hex"], s["opcode"], s["qualifying"]) for s in rep["syncs"]]
            reports = []
            for v in rep["verdicts"]:
                if v["verdict"] != "RACE":
                    continue
                k = (min(v["current_pc"], v["ancient_pc"]), max(v["current_pc"], v["ancient_pc"]))
                r = {x: v[x] for x in ("ancient_pc_hex", "current_pc_hex", "opcodes", "space",
                                       "race_type", "observed_distance", "strength",
                                       "hb_class", "hb_chain", "event_candidate",
                                       "edge_rescued", "benign", "contested_weight")}
                r["ancient_line"] = lmap.get(v["ancient_pc"])
                r["current_line"] = lmap.get(v["current_pc"])
                r["engine_records"] = rs.get(k)
                reports.append(r)
                dedup.setdefault(sd_key(v), dict(v, kernel=short(kname)))
            info["reports"] = reports
            kernels.append(info)
            print(f"[{mode}] {info['file']} {info['short']} {info['bytes']/1e6:.0f} MB "
                  f"races={len(reports)} tv={bool(info['tv_violation'])} "
                  f"short={info['barrier']['instances_released_short']} "
                  f"({time.time()-t0:.0f}s)", flush=True)
        result["modes"][mode] = {"kernels": kernels, "dedup_reports": len(dedup)}
        with open(os.path.join(a.out, f"detail_{mode}.json"), "w") as f:
            json.dump({"dedup_reports": [dedup[k] for k in sorted(dedup)]}, f, indent=1)
    with open(os.path.join(a.out, "triage.json"), "w") as f:
        json.dump(result, f, indent=1, default=str)
    write_md(result, os.path.join(a.out, "triage.md"))
    return 0


def sd_key(v):
    """The harness's dedup key (run_cuvein._analyze_reports via aggregate._dedup_key)."""
    a, b = sorted((v["ancient_pc"], v["current_pc"]))
    return (a, b, v["space"].split("/")[0])


def write_md(res, path):
    L = [f"# {res['id']} triage (store {res['store']})", ""]
    for mode, d in res["modes"].items():
        ks = d["kernels"]
        L += [f"## {mode}: {len(ks)} kernel dumps, {d['dedup_reports']} deduped reports "
              "(harness dedup key: pc pair + space)", "",
              "| dump | kernel | grid×block | MB | events | reports | tv_violation | barrier instances fired / released short / left open | threads never seen per block |",
              "|---|---|---|---|---|---|---|---|---|"]
        for k in ks:
            bd = k["barrier"]
            L.append(f"| {k['file']} | {k['short']} | {k['grid_dim']}×{k['block_dim']} | "
                     f"{k['bytes']/1e6:.0f} | {k['hb_events']} | {len(k.get('reports', []))} | "
                     f"{(k['tv_violation'] or '')[:60]} | {bd['instances_fired']} / "
                     f"{bd['instances_released_short']} {bd['released_short_by_arrived_expected']} / "
                     f"{bd['instances_left_open']} | {bd['threads_never_seen_per_block']} |")
        L += ["", "| kernel | anc pc (line) | cur pc (line) | space | type | dist | strength | hb_class | event_cand | chain | engine records (relation) |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for k in ks:
            for r in k.get("reports", []):
                er = r["engine_records"]
                ers = f"{er['records']} {er['relation']}" if er else ""
                L.append(f"| {k['short']} | {r['ancient_pc_hex']} ({r['ancient_line']}) | "
                         f"{r['current_pc_hex']} ({r['current_line']}) | {r['space']} | "
                         f"{r['race_type']} | {r['observed_distance']} | {r['strength']} | "
                         f"{r['hb_class']} | {r['event_candidate']} | "
                         f"{'yes' if r['hb_chain'] else ''} | {ers} |")
        L.append("")
    open(path, "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    sys.exit(main())

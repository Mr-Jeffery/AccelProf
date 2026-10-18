#!/usr/bin/env python3
"""X5 byte pairs: the report's tables (read only; prints markdown).

  x5b_tables.py <byte_pairs.jsonl> <partial.jsonl>

  A  per program and pair, both modes side by side
  B  per kernel (dot): the NOPs, the CALL sites with the instruction they return to, the body of
     the $__internal_0_$__cuda_sm70_warpsync helper, and the syncwarp records by pc (full /
     partial) summed over the program's recordings in the events store
  C  diverged-warp syncwarp instances (x5b_partial.py) per program and mode
"""
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import x5_common as xc                       # noqa: E402,F401
from x5_common import sd                     # noqa: E402
import pydot                                 # noqa: E402

ROOT = "/mnt/beegfs/fzheng4/cuvein_traces"


def short(pid):
    s = pid.replace("CC_CUDA_V_Data_", "").replace("_IntType", "")
    s = re.sub(r"_No[A-Za-z]+Bug", "", s)
    return s.replace("_ReadWrite", "").replace("_NonDup", "").replace("_Warp", "")


def dot_listing(dot):
    (graph,) = pydot.graph_from_dot_file(dot)
    out = {}
    for sub in graph.get_subgraphs():
        name = sub.get_name().strip('"')
        lines = []
        for node in sub.get_nodes():
            label = node.get_attributes().get("label")
            if label is not None:
                lines += [ln.strip() for ln in sd._label_lines(label.strip('"')) if sd._INSTR.match(ln)]
        lines.sort(key=lambda ln: int(ln.split(":")[0], 16))
        out[name] = lines
    return out


def main():
    rows = [json.loads(ln) for ln in open(sys.argv[1])]
    part = [json.loads(ln) for ln in open(sys.argv[2])]

    print("### A. Per program and pair (vector-clock / scalar-clock)\n")
    head = ["suite", "program", "u -> v", "type", "opcodes", "NOP on every path (syncwarp pc)",
            "X1 launches with edge u->v", "X1 lists the pair", "syncwarp records at that pc",
            "instances: syncwarp between (both lanes active) / not", "oracle as recorded lists it",
            "that pc's records removed: lists it (launches)", "R1 / with NOP as WARPSYNC"]
    print("| " + " | ".join(head) + " |\n|" + "---|" * len(head))
    grp = collections.OrderedDict()
    for r in sorted(rows, key=lambda r: (r["suite"], r["id"], int(r["u"], 16))):
        grp.setdefault((r["suite"], r["id"], r["u"], r["v"]), {})[r["mode"]] = r
    pmap = {(p["id"], p["mode"]): p for p in part}

    def both(f):
        return " / ".join(f(m) for m in ("vector-clock", "scalar-clock"))
    for (suite, pid, u, v), by in grp.items():
        r0 = next(iter(by.values()))
        st = r0["static"]

        def x1e(m):
            r = by.get(m)
            return f"{r['x1']['counts'].get('edge_launches', 0)}/{r['x1']['counts'].get('launches', 0)}" if r else "—"

        def x1l(m):
            r = by.get(m)
            if not r:
                return "—"
            c = r["x1"]["counts"]
            return str(sum(c.get(f"{n}:True", 0) for n in ("hb_races", "hb_races_sync_only", "hb_sync_pass")))

        def ev(m, f):
            r = by.get(m)
            return f(r["events"]) if r and r.get("events") else "no store"

        def inst(m):
            p = pmap.get((pid, m))
            k = f"{u}->{v}"
            if suite == "P6":
                return ev(m, lambda e: f"cross-warp {e['instances'].get('cross_warp', 0)}")
            if not p or k not in p["pairs"]:
                return "no store"
            c = p["pairs"][k]
            return f"{c.get('both_active', 0)} / {c.get('sync_mask_only', 0) + c.get('uncovered', 0) + c.get('cross_warp', 0)}"
        cut = ", ".join(st["cut_nops"] + st["cut_syncs"])
        cells = [suite, short(pid), f"{u} -> {v}", r0["race_type"], f"{st['op_u']} / {st['op_v']}", cut,
                 both(x1e), both(x1l),
                 both(lambda m: ev(m, lambda e: "; ".join(f"{k.split()[1]} {n}" for k, n in e["sync_records_at_cut_pcs"].items()))),
                 both(inst),
                 both(lambda m: ev(m, lambda e: f"{e['counts'].get('oracle_sync_only:True', 0)}/{e['counts']['launches']}")),
                 both(lambda m: ev(m, lambda e: "; ".join(f"{var}: {d.get('sync_only:True', 0)}" for var, d in e["oracle_with_sync_records_removed"].items()))),
                 f"{st['r1_strength']} / {st.get('r1_strength_nop_as_warpsync', '—')}"]
        print("| " + " | ".join(cells) + " |")

    print("\n### B. Per kernel: syncwarp instructions and records\n")
    dots = collections.OrderedDict()
    for r in rows:
        if r["suite"] == "P6":
            continue
        dotbase = r["kernel"].split("::")[0]
        dots.setdefault(dotbase, (f"{ROOT}/{r['store']}/{r['id']}/dots/{dotbase}", r["kernel"].split("::")[1], set()))[2].add(r["id"])
    for dotbase, (dot, mangled, pids) in dots.items():
        lst = dot_listing(dot)
        kl = lst.get("cluster_" + mangled, [])
        nops = [ln.split(":")[0] for ln in kl if sd._INSTR.match(ln).group(3).startswith("NOP")]
        calls = []
        for i, ln in enumerate(kl):
            if sd._INSTR.match(ln).group(3).startswith("CALL"):
                calls.append(f"{ln.split(':')[0]} -> returns to {kl[i + 1].split(':')[0]} ({sd._INSTR.match(kl[i + 1]).group(3)})" if i + 1 < len(kl) else ln)
        helper = [ln for n, l in lst.items() if "warpsync" in n for ln in l]
        rec = collections.Counter()
        for p in part:
            if p["id"] in pids and p["kernel"].split("::")[0] == dotbase:
                for k, n in p["census"].items():
                    if k.startswith(("full ", "partial 0x")):
                        rec[k] += n
        print(f"- `{dotbase.replace('.sm_89.dot', '')}` ({len(pids)} programs): NOPs {', '.join(nops)}; "
              f"CALL {', '.join(calls) or 'none'}; helper `{' | '.join(h.split(':', 1)[1].strip() for h in helper) or 'none'}`"
              f"; syncwarp records (all its recordings in the events store, both modes): "
              + ", ".join(f"{k} {n}" for k, n in sorted(rec.items(), key=lambda kv: int(kv[0].split()[-1], 16))))

    print("\n### C. Diverged-warp syncwarp instances (partial records) and the merged replay\n")
    print("| program | mode | launches | partial records (pc) | partial instances (2 / 3 records) | never completed | "
          "memory records of not-yet-arrived lanes | race pairs only after merge / only before | replay |")
    print("|---|---|---|---|---|---|---|---|---|")
    tot = collections.Counter()
    for p in sorted(part, key=lambda p: (p["id"], p["mode"])):
        c = p["census"]
        pr = {k: n for k, n in c.items() if k.startswith("partial 0x")}
        tot["groups"] += 1
        tot["groups with partial"] += bool(pr)
        tot["pending"] += p["pending_lane_mem_records"]
        tot["after"] += len(p["only_after_merge"])
        tot["before"] += len(p["only_before_merge"])
        tot["errors"] += len(p["errors"])
        if not pr:
            continue
        print(f"| {short(p['id'])} | {p['mode']} | {p['launches']} | {', '.join(f'{k.split()[1]} {n}' for k, n in pr.items())} | "
              f"{c.get('partial instance of 2 records', 0)} / {c.get('partial instance of 3 records', 0)} | "
              f"{c.get('partial instances never completed', 0)} | {p['pending_lane_mem_records']} | "
              f"{len(p['only_after_merge'])} / {len(p['only_before_merge'])} | "
              f"{'shared-only' if p['shared_only'] else 'full'} |")
    print(f"\ntotals: {dict(tot)}")


if __name__ == "__main__":
    main()

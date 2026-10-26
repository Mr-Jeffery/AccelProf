"""Classify the lock hand-off of every X1b-harness re-recording of P5-race_interblock_none-lock_rtraw.
usage: rerec_classify.py <node> [<node> ...]   (compute node: reads the BeeGFS store)
For each run and mode: the lock word's recorded RMW order (kernel JSON coherence_profile, tid 1024 = block 1,
tid 0 = block 0), which block acquired first, whether the second acquirer's winning CAS (its second-to-last
RMW on the lock) is recorded before the first owner's unlock (its last RMW): "inverted" = A2 inversion,
FINAL_RTRAW.md's schedule C. Plus events, the lock-word dependency edges, hb_races and the row's verdict.
Writes eval/results/final-b/rtraw-rerec/x1b-harness/<node>/classify.csv."""
import csv, glob, json, os, sys
ID = "P5-race_interblock_none-lock_rtraw"
BASE = "/mnt/beegfs/fzheng4/cuvein_traces/x1b-rtraw-rerec/x1b-harness"
OUT = "/home/fzheng4/wt-x1b/eval/results/final-b/rtraw-rerec/x1b-harness"
LOCK = {0xb0, 0x1b0, 0x230, 0x330}
for node in sys.argv[1:]:
    rows = {}
    for f in glob.glob(f"{OUT}/{node}/baselines-cuvein-shard*.csv"):
        for r in csv.DictReader(open(f)):
            tag = os.path.basename(f).split("shardrerec-")[1].split("0_1")[0] if "shardrerec-" in f else f
            rows[(tag, r["mode"])] = r
    out = []
    for rd in sorted(glob.glob(f"{BASE}/{node}/run*"), key=lambda p: int(p.rsplit("run", 1)[1])):
        k = int(rd.rsplit("run", 1)[1])
        for mode in ("vector-clock", "scalar-clock"):
            kj = f"{rd}/{ID}/{mode}/kernel_0.json"
            rec = dict(node=node, run=k, mode=mode)
            if not os.path.exists(kj):
                rec["note"] = "no kernel JSON"; out.append(rec); continue
            t = json.load(open(kj))
            prof = [v["seq"] for v in (t.get("coherence_profile") or {}).values()
                    if {s[0] for s in v["seq"]} == {0, 1024}]
            rec["events"] = t.get("hb_events_count")
            edges = sorted((hex(e["current_pc"]), hex(e["ancient_pc"])) for e in t.get("edges", [])
                           if e.get("ancient_pc") is not None and e["current_pc"] in LOCK and e["ancient_pc"] in LOCK
                           and e["current_pc"] != e["ancient_pc"])
            rec["lock_edges"] = " ".join(f"{a}<-{b}" for a, b in edges)
            E = set(edges)
            if ("0x230", "0x1b0") in E: rec["handoff"] = "b1->b0 normal"
            elif ("0x330", "0x1b0") in E: rec["handoff"] = "b1->b0 inverted"
            elif ("0xb0", "0x330") in E: rec["handoff"] = "b0->b1 normal"
            elif ("0x1b0", "0x330") in E: rec["handoff"] = "b0->b1 inverted"
            else: rec["handoff"] = "?"
            if prof:
                seq = prof[0]
                first = seq[0][0]; second = 1024 - first
                pos_f = [i for i, s in enumerate(seq) if s[0] == first]
                pos_s = [i for i, s in enumerate(seq) if s[0] == second]
                rec["first"] = "block1" if first == 1024 else "block0"
                rec["lock_rmws"] = f"{len(pos_f)}+{len(pos_s)}"
                rec["inverted"] = int(len(pos_s) >= 2 and pos_s[-2] < pos_f[-1])
                rec["order"] = " ".join(("b1" if s[0] == 1024 else "b0") for s in seq)
            races = t.get("hb_races") or []
            rec["hb_races"] = " ".join(f"{hex(x['a_pc'])}/{hex(x['b_pc'])}:{x['kind']}:{x['class']}:a2={x['a2_uncertain']}" for x in races)
            for (tag, m), r in rows.items():
                if m == mode and tag.endswith(f"-{k}"):
                    rec["verdict"] = r["verdict"]; rec["reports"] = r["reports_dedup"]; rec["report_ids"] = r["report_ids"]
            out.append(rec)
    keys = ["node", "run", "mode", "handoff", "first", "lock_rmws", "inverted", "events", "order", "lock_edges", "hb_races", "verdict", "reports", "report_ids", "note"]
    with open(f"{OUT}/{node}/classify.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); [w.writerow({k: r.get(k, "") for k in keys}) for r in out]
    for mode in ("vector-clock", "scalar-clock"):
        R = [r for r in out if r["mode"] == mode]
        ho = {}
        for r in R: ho[r.get("handoff", "?")] = ho.get(r.get("handoff", "?"), 0) + 1
        verd = {}
        for r in R: verd[r.get("verdict", "?")] = verd.get(r.get("verdict", "?"), 0) + 1
        ev = sorted({r.get("events") for r in R}, key=str)
        print(f"{node} {mode}: runs {len(R)}, hand-off {ho}, events {ev}, verdicts {verd}")

import json
B = "/mnt/beegfs/fzheng4/cuvein_traces"
i = "P5-race_interblock_none-lock_rtraw"
for st in ("final-2026-10", "final-2026-11"):
    t = json.load(open(f"{B}/{st}/{i}/vector-clock/kernel_0.json"))
    print("=====", st, "edges", len(t["edges"]), "nodes", len(t.get("nodes", [])))
    print(" first edge raw:", json.dumps(t["edges"][0])[:400])
    print(" first node raw:", json.dumps(t["nodes"][0])[:300] if t.get("nodes") else None)
    for e in t["edges"]:
        s = {k: (hex(v) if isinstance(v, int) and v > 15 else v) for k, v in e.items()}
        print("  ", json.dumps(s)[:300])
    print(" hb_gate:", t.get("hb_gate"), "hb_gate_policy:", t.get("hb_gate_policy"))
    print(" coherence_profile:", json.dumps(t.get("coherence_profile"))[:600])

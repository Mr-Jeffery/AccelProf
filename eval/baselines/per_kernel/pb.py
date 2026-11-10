import csv,collections
D="/home/fzheng4/wt-x13/eval/results/per-kernel"
for r in csv.DictReader(open(f"{D}/baselines.csv")):
    if r["run"].startswith("P9:"): print(r["tool"],r["run"],r["kernel"][:45],"|",r["reported_locations"][:70],"|",r["method_detail"][:90])
print("RERUN")
c=collections.Counter()
for r in csv.DictReader(open(f"{D}/sc_rerun_p9.csv")): c[(r["id"],r["verdict"],r["notes"][:40])]+=1
for k,v in c.items(): print(v,k)
print("amb/unm notes:", sum(1 for r in csv.DictReader(open(f"{D}/baselines_notes.csv")) if "ambiguous" in r["note"] or "unmapped" in r["note"]))
for r in csv.DictReader(open(f"{D}/baselines_notes.csv")):
    if "ambiguous" in r["note"] or "unmapped" in r["note"] or "without" in r["note"]: print(r)

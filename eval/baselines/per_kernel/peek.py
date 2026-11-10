import csv,collections
D="/home/fzheng4/wt-x13/eval/results"
c=0
seen=set()
for f in ("baselines-iguard.csv",):
    for r in csv.DictReader(open(f"{D}/{f}")):
        if r["verdict"]=="RACE" and r["pset"] in ("PI","P1","P6") and r["pset"] not in seen:
            seen.add(r["pset"]); print(r["id"][:50], repr(r["report_ids"][:400]))
n=collections.Counter()
for r in csv.DictReader(open(f"{D}/per-kernel/baselines_notes.csv")):
    if r["tool"] in ("racecheck","supercollider") : n[(r["tool"],r["note"][:100])]+=1
for k,v in n.most_common(14): print(v,k)
for r in list(csv.DictReader(open(f"{D}/per-kernel/baselines_notes.csv")))[:0]: pass

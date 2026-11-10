import csv,collections
D="/home/fzheng4/wt-x13/eval/results/per-kernel/ck11"
for f in ("vc","sc","co_c6"):
    c=collections.Counter()
    for r in csv.DictReader(open(f"{D}/{f}.csv")):
        c[(r["id"],r["store"].split("/")[-1],r["status"][:40],r["n_races"]!="0")]+=1
    print("==",f)
    for k,v in sorted(c.items()): print(v,k)

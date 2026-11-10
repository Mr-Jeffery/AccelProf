import csv,glob,collections
D="/home/fzheng4/wt-x13/eval/results/per-kernel"
allids=open(f"{D}/ids_table.txt").read().split()
extra=set(open(f"{D}/missing_sc_extra.txt").read().split())
for m,pats in (("sc",["ck/sc-*.csv","ck2/sc*.csv"]),("co",["ck/co-*.csv","ck2/co-*.csv"]),("vc",["ck/vc-*.csv"])):
    done=collections.Counter(); st=collections.Counter()
    for p in pats:
        for f in glob.glob(f"{D}/{p}"):
            for r in csv.DictReader(open(f)):
                if m=="sc" and r["id"] in extra and "ck/sc-" in f: continue
                done[r["id"]]+=1; st[r["status"].split(":")[0]]+=1
    miss=[i for i in allids if i not in done]
    print(m,"missing",len(miss),miss[:3],dict(st))
    open(f"{D}/missing2_{m}.txt","w").write("\n".join(miss)+"\n")

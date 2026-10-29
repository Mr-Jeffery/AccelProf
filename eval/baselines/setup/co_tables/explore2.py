import sys,collections
sys.argv=[sys.argv[0],"--collector-only"]
sys.path.insert(0,"eval/baselines")
import make_tables as mt
R="eval/results"
runs,meta=mt.load_runs([f"{R}/final-b/merged/baselines-cuvein.csv",f"{R}/collector-only/merged/baselines-cuvein.csv"])
man=mt.load_manifest()
print(len(runs),len(meta),len(man))
# P6 categories
c=collections.Counter()
for i,m in meta.items():
    if m[0]=="P6":
        lab=man[i]["label"]; cat=m[1].split("/")[0]
        v=runs.get((i,"cuvein",mt.VC),{}).get("verdict")
        c[(cat,lab,v)]+=1
for k,v in sorted(c.items(),key=str): print(k,v)
for ps in ("P1","PI","P3","P4","P5","P6","P9"):
    for mode in mt.MODES3:
        cc,_=mt.confusion(runs,meta,man,(ps,),"cuvein",mode)
        print(ps,mode,mt._mcell(cc))


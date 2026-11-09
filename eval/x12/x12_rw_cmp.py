import csv, collections, sys
D=(sys.argv[1] if len(sys.argv)>1 else "res").rstrip("/")+"/"
def rd(f): return list(csv.DictReader(open(D+f,newline="")))
def key(r): return (r["target"],r["variant"],r.get("component") or "-")
def outc(rows):
    d={}
    for r in rows:
        if r["mode"]!="collector-only": continue
        d[key(r)]=r["outcome"]
    return d
def cnt(d, ids=None):
    c=collections.Counter()
    for k,v in d.items():
        if ids is not None and k[0] in ids: continue
        c[(k[1],v)]+=1
    return c
for s in ("b","c"):
    std=outc(rd(f"{s}-std.csv")); ch=outc(rd(f"{s}-chain.csv")); c2=outc(rd(f"c2-{s}.csv"))
    c6=rd(f"c6-{s}.csv"); c6d={ (r["target"],r["variant"],r["component"]): r["co_chain"] for r in c6}
    print("=== set",s)
    keys=sorted(set(std)|set(ch))
    print("rows std",len(std),"chain",len(ch),"c2",len(c2),"c6",len(c6d))
    # moves
    for name,a,b in (("X12 std vs C2",std,c2),("X12 chain vs C6",ch,c6d)):
        mv=[(k,a.get(k),b.get(k)) for k in keys if a.get(k)!=b.get(k)]
        print(name,"differences:",len(mv))
        for m in mv: print("   ",m)

print("\n##### normalized")
N={"CLEAN":"CLEAN-FOR-PAIR","RESIDUAL":"RESIDUAL-AS-EXPECTED","STILL":"STILL-REPORTED","DET-as-DR":"DETECTED-AS-DR"}
nz=lambda v: N.get(v,v)
def nrace(rows):
    return {key(r):(r["n_race"],r["n_sc"]) for r in rows if r["mode"]=="collector-only"}
for s in ("b","c"):
    std=outc(rd(f"{s}-std.csv")); ch=outc(rd(f"{s}-chain.csv")); c2=outc(rd(f"c2-{s}.csv"))
    c6={ (r["target"],r["variant"],r["component"]): nz(r["co_chain"]) for r in rd(f"c6-{s}.csv")}
    mv=[(k,ch[k],c6.get(k)) for k in ch if ch[k]!=c6.get(k)]
    print(s,"chain vs C6 after label normalisation:",mv)
    mv=[(k,std[k],c2.get(k)) for k in std if std[k]!=c2.get(k)]
    print(s,"std vs C2:",mv)
    print(s,"std counts",sorted(collections.Counter((k[1],v) for k,v in std.items()).items()))
    print(s,"chain counts",sorted(collections.Counter((k[1],v) for k,v in ch.items()).items()))
    c2f={k:v for k,v in c2.items() if k in std}
    print(s,"C2 counts (same ids)",sorted(collections.Counter((k[1],v) for k,v in c2f.items()).items()))
    # report counts
    a=nrace(rd(f"{s}-std.csv")); b=nrace(rd(f"c2-{s}.csv")); c=nrace(rd(f"{s}-chain.csv"))
    chg=[(k,a[k],b[k]) for k in a if k in b and a[k]!=b[k]]
    print(s,"ids where (n_race,n_sc) std != C2:",len(chg),"of",len(a)); 
    for x in chg: print("    ",x)
    c6n={(r["target"],r["variant"],r["component"]):(r["co_chain_n_race"],r["co_chain_n_sc"]) for r in rd(f"c6-{s}.csv")} if s=="b" else {}
    if c6n:
        chg=[(k,c[k],c6n[k]) for k in c if k in c6n and c[k]!=c6n[k]]
        print(s,"ids where chain (n_race,n_sc) != C6:",len(chg),"of",len(c))
        for x in chg: print("    ",x)

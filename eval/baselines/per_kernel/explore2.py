import json, glob, os, sys
T="/mnt/beegfs/fzheng4/cuvein_traces"
def show(d):
    print("==", d)
    print(sorted(os.listdir(d))[:20])
    for m in ("vector-clock","scalar-clock","collector-only"):
        fs=sorted(glob.glob(f"{d}/{m}/kernel_*.json"))
        if fs:
            j=json.load(open(fs[0]))
            def sk(x,dep=0):
                if isinstance(x,dict): return {k:(sk(v,dep+1) if dep<1 else type(v).__name__) for k,v in list(x.items())[:40]}
                return type(x).__name__
            print(m, len(fs), os.path.basename(fs[0]), json.dumps(sk(j))[:1800])
            for k in ("kernel_name","name","kernel","demangled","kernel_id","func"):
                if k in j: print(k, str(j[k])[:200])
    print(sorted(os.listdir(d+"/dots"))[:5] if os.path.isdir(d+"/dots") else "no dots")
show(f"{T}/final-2026-11/P4-1dconv-racy-small")
show(f"{T}/final-2026-11-co/P4-1dconv-racy-small")
x=[p for p in os.listdir(T) if p.startswith("x11b-scalar-clock-expdist")]
print(x)
for p in x[:1]:
    show(f"{T}/{p}")
    for r,ds,fs in os.walk(f"{T}/{p}"):
        print(r, len(fs)); break
m=json.load(open(f"{T}/final-2026-11/P4-1dconv-racy-small/meta.json"))
print([k for k in m]); print(str(m.get("pc_lines"))[:300])

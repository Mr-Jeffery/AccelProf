import re,sys,difflib
D="eval/results/collector-only-tables/mt"
A=open(f"{D}/BASELINES_A.md").read().split("\n")
B=open(f"{D}/BASELINES_B.md").read().split("\n")
def cells(l): return [c.strip() for c in l.strip().strip("|").split(" | ")]
out=[];drop=set();intab=False
for l in B:
    if l.startswith("|") and l.count(" | ")>=1:
        if not intab:   # header row
            h=l; hc=cells(l); drop={i for i,c in enumerate(hc) if "cuVein-CO" in c or "collector-only" in c.lower() and "cuVein (collector-only)" in c or c=="cuVein (collector-only)"}
            intab=True
            keep=[c for i,c in enumerate(hc) if i not in drop]
            out.append("| "+" | ".join(keep)+" |" if drop else l); continue
        if set(l.replace("|","").strip())<=set("-") :
            out.append("|"+"---|"*(len(cells(l))-len(drop)) if drop else l); continue
        cs=cells(l)
        if any(c in ("cuVein-CO","collector-only") for c in cs[:3]): continue
        if drop:
            cs=[re.sub(r"<br>\*\*cuVein-CO\*\*.*$","",c) for i,c in enumerate(cs) if i not in drop]
            out.append("| "+" | ".join(cs)+" |")
        else:
            out.append(re.sub(r"<br>\*\*cuVein-CO\*\*[^|]*","",l))
    else:
        intab=False; drop=set(); out.append(l)
# normalise A the same way for the dash-row width
A2=[ "|"+"---|"*(len(cells(l))) if (l.startswith("|") and set(l.replace("|","").strip())<=set("-") and l.strip()!="|") else l for l in A]
out2=[ "|"+"---|"*(len(cells(l))) if (l.startswith("|") and set(l.replace("|","").strip())<=set("-") and l.strip()!="|") else l for l in out]
d=[x for x in difflib.unified_diff(A2,out2,lineterm="",n=0) if not x.startswith(("---","+++"))]
print("A lines",len(A),"B lines",len(B),"stripped B",len(out),"diff lines",len(d))
for x in d[:60]: print(x[:300])


import csv,collections,re
R="eval/results"
man=list(csv.DictReader(open(f"eval/baselines/manifest.csv")))
print("manifest", len(man), list(man[0].keys()))
rows=list(csv.DictReader(open(f"{R}/collector-only/merged/baselines-cuvein.csv")))
c=collections.Counter()
for r in rows:
    m=re.search(r"classes=([^;]+)",r["notes"])
    c[m.group(1) if m else "-"]+=1
print(c.most_common(12))
print(collections.Counter(r["verdict"] for r in rows))
x=list(csv.DictReader(open(f"{R}/final-b/merged/baselines-cuvein.csv")))
c=collections.Counter()
for r in x:
    m=re.search(r"classes=([^;]+)",r["notes"]); c[re.sub(r"\d+","N",m.group(1)) if m else "-"]+=1
print(c.most_common(14))
print(collections.Counter(r["label"] for r in man), collections.Counter(r["pset"] for r in man))
p6=[r for r in man if r["pset"]=="P6"][:3]; print(p6)


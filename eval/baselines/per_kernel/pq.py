import csv
D="/home/fzheng4/wt-x13/eval/results/per-kernel"
for r in csv.DictReader(open(f"{D}/curace.csv")):
    if r["binary"] in ("hecbench:tridiagonal","hecbench:expdist","hecbench:atomicCAS","hecbench:knn","hecbench:dxtc2"):
        print(r["binary"][9:],r["mode"][:5],r["kernel"][:38],r["verdict"],r["report_pairs"],r["runs"],r["runs_launched"])
print("iguard P4 racy:")
for r in csv.DictReader(open(f"{D}/kernel_verdicts_baselines.csv")):
    if r["tool"]=="iguard" and ("graph-coloring_racy" in r["binary"] or "graph-connectivity_racy" in r["binary"]): print(r["binary"].split("/")[-1],r["kernel"][:25],r["verdict"])

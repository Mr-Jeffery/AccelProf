import csv,os
D="/home/fzheng4/wt-x13/eval/results/per-kernel"
for r in csv.DictReader(open(f"{D}/fp_kernels.csv")):
    if r["suite"] in ("P4","P6","P9"): print(r["suite"],r["tool"],r["mode"],os.path.basename(r["binary"])[:30],r["kernel"][:50],"|",list(r.values())[-1][:140])
print("MISSED")
for r in csv.DictReader(open(f"{D}/missed_kernels.csv")): print(r)

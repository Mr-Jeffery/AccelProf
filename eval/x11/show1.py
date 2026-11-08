import json,glob,os
d=json.load(open("/mnt/beegfs/fzheng4/x11_work/step0b/step0.json"))
for r in d["recs"]:
    if r.get("same") is False: print(r["id"],r["first_diff_detail"],r["diff_kernels"][:4])
print(sorted(os.listdir("/home/fzheng4/AccelProf/eval/baselines/bin/P6")))

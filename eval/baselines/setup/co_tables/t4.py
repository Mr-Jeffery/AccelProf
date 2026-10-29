import csv, io, subprocess
def show(ref, path):
    return list(csv.DictReader(io.StringIO(subprocess.run(["git","show",f"{ref}:{path}"],capture_output=True,text=True,check=True).stdout)))
for ref,p in (("origin/eval/collector-only-realworld","eval/results/realworld_co_t21c/recall.csv"),("origin/study/realworld-candidates","eval/results/realworld_t21c/recall.csv")):
    for r in show(ref,p):
        if "llmc-new-3" in r["target"]: print(ref[-12:], {k:r[k] for k in ("target","variant","mode","flavor","component","wave","route","pattern","expected_class","outcome","n_race","matched")})


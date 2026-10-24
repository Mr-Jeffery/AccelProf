#!/bin/bash
#SBATCH -p normal
#SBATCH --exclude=c2,c21,c23,c37,c43,c46,c54,c77
#SBATCH -t 00:30:00
#SBATCH -o /home/fzheng4/x1b/rtt23-%j.log
# X1b: P5-race_interblock_none-lock_rtraw, X1's and X1b's recordings, analyzed with R3's location
# closure off (CUVEIN_R3_LOC_CLOSURE=0, the pre-T23 rule) and on (default), by t23_closure.py
W=/home/fzheng4/wt-x1b; PY=/home/fzheng4/AccelProf/.env/bin/python
O=$W/eval/results/final-b/rtraw-t23; mkdir -p $O
cd $W || exit 1
hostname; date -Is; git rev-parse --short=12 HEAD
echo P5-race_interblock_none-lock_rtraw > $O/ids.txt
for st in final-2026-10 final-2026-11; do
  $PY eval/baselines/setup/t23_closure.py scan --store /mnt/beegfs/fzheng4/cuvein_traces/$st --ids $O/ids.txt --out $O/scan-$st.jsonl
  $PY eval/baselines/setup/t23_closure.py diff $O/scan-$st.jsonl --all --out $O/diff-$st.jsonl
  $PY eval/baselines/setup/t23_closure.py summary $O/diff-$st.jsonl
done
$PY - $O <<'PY'
import json, os, sys, glob
sys.path.insert(0, "/home/fzheng4/wt-x1b/python")
import sync_dominance as sd
O = sys.argv[1]
for f in sorted(glob.glob(f"{O}/scan-*.jsonl")):
    for ln in open(f):
        r = json.loads(ln)
        if r.get("status") != "scanned":
            print(f, r.get("mode"), r.get("status")); continue
        for clo in ("0", "1"):
            os.environ["CUVEIN_R3_LOC_CLOSURE"] = clo
            res = sd.analyze(r["dot"], r["path"])
            vs = [(v.get("current_pc_hex"), v.get("ancient_pc_hex"), v.get("race_type"), v.get("verdict"),
                   v.get("hb_class"), v.get("a2_uncertain"), bool(v.get("r3_loc_closure"))) for v in res["verdicts"]]
            print(os.path.basename(f), r["mode"], os.path.basename(r["path"]), "closure=" + clo,
                  "growth_cas=" + str(r.get("growth_cas")), "summary=", json.dumps(res.get("summary"))[:300])
            for v in vs:
                print("    ", v)
PY
date -Is

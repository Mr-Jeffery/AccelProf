#!/usr/bin/env bash
#SBATCH --job-name=cuvein-fix
#SBATCH --partition=rtx3060ti
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=03:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/fix-%j.log
# Corrective pass, run strictly after the present-corpora re-run (281542):
#  - rebuild P4 ScoR apps WITH --cudart shared (previous build lacked it -> all P4
#    exited rc=1 under accelprof / no kernel JSON)
#  - compile P3 (Indigo3 race-free graph codes)
#  - drop the stale P4 rows from the cuvein + racecheck CSVs, keep good P5/P6
#  - re-run cuVein (both modes) + racecheck on P4 and P3 only (append)
#  - regenerate manifest (adds P3), classify, tables
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
echo "### rebuild P4 (--cudart shared) + compile P3 ###"
$PY eval/baselines/build_corpora.py --pset P4 2>&1 | tail -4
$PY eval/baselines/build_indigo.py --stage compile --pset P3 2>&1 | tail -4
echo "### drop stale P4 rows from result CSVs ###"
$PY - <<'PY'
import csv
for tool in ("cuvein","racecheck"):
    p=f"eval/results/baselines-{tool}.csv"
    try: rows=list(csv.DictReader(open(p)))
    except FileNotFoundError: continue
    keep=[r for r in rows if r["pset"]!="P4"]
    w=csv.DictWriter(open(p,"w",newline=""),fieldnames=rows[0].keys())
    w.writeheader(); w.writerows(keep)
    print(f"{tool}: kept {len(keep)} (dropped {len(rows)-len(keep)} P4)")
PY
echo "### regenerate manifest (adds P3) ###"
$PY eval/baselines/mk_manifest.py
echo "### re-run cuVein + racecheck on P4 + P3 ###"
$PY eval/baselines/run_cuvein.py --pset P4,P3 --confirm
$PY eval/baselines/run_racecheck.py --pset P4
echo "### classify + tables ###"
$PY eval/baselines/classify_endpoints.py
$PY eval/baselines/make_tables.py
echo "fix done"

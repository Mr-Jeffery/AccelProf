#!/usr/bin/env bash
#SBATCH --job-name=cuvein-p3
#SBATCH --partition=rtx3060ti
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=02:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/p3-%j.log
# Adds P3 (Indigo3 race-free CC/MIS/MST graph codes) to the comparison: compile,
# regenerate the manifest (now incl. P3), run cuVein both modes (appends to the
# cuvein CSV), then re-classify + rebuild tables. Submitted with a dependency on
# the present-corpora re-run so it runs strictly after it (shared c48 / cuvein CSV).
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
echo "### compile P3 (Indigo3) ###"
$PY eval/baselines/build_indigo.py --stage compile --pset P3 2>&1 | tail -8
echo "### regenerate manifest (now includes P3) ###"
$PY eval/baselines/mk_manifest.py
echo "### run cuVein on P3 (both modes) ###"
$PY eval/baselines/run_cuvein.py --pset P3 --confirm
echo "### classify + tables ###"
$PY eval/baselines/classify_endpoints.py
$PY eval/baselines/make_tables.py
echo "p3 done"

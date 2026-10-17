#!/bin/bash
# X5 step 1: the two plans (BeeGFS is not mounted on the login node), the barrier-ordered pairs
# the X1 confirm files contain, and the BAR/WARPSYNC operand forms of the X1 dots.
#   sbatch eval/baselines/setup/p_x5_plan.sh
#SBATCH -p normal
#SBATCH -J x5-plan
#SBATCH -t 04:00:00
#SBATCH -c 1
#SBATCH -o /home/fzheng4/wt-x5/eval/x_logs/x5-plan-%j.log
W=${W:-/home/fzheng4/wt-x5}
RT=${RT:-/home/fzheng4/AccelProf}
PY=$RT/.env/bin/python
cd "$W" || exit 1
export CUVEIN_HOME=$W
echo "node $(hostname) job ${SLURM_JOB_ID} $(date -Is)"; git rev-parse HEAD; $PY --version
$PY -c "import networkx; print('networkx', networkx.__version__)"
mkdir -p eval/results/x5
S=eval/baselines/setup
set -x
$PY $S/barrier_ordered_bins.py confirm-scan $RT/eval/baselines/confirm_final $RT/eval/baselines/confirm_final-long \
    $RT/eval/baselines/confirm_final-long-sc $RT/eval/baselines/confirm_final-24h-vc \
    $RT/eval/baselines/confirm_final-24h-sc | tee eval/results/x5/confirm_scan.txt
$PY $S/barrier_ordered_bins.py plan --out eval/results/x5/bo_plan.json | tee eval/results/x5/bo_plan.txt
$PY $S/pcdg_variance.py plan --out eval/results/x5/var_plan.json | tee eval/results/x5/var_plan.txt
python3 $S/x5_bar_forms.py | tee eval/results/x5/bar_forms.txt

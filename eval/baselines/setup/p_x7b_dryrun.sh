#!/usr/bin/env bash
#SBATCH --job-name=x7b-dryrun
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c0,c1,c22,c23,c34,c46
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=00:30:00
#SBATCH --output=/home/fzheng4/wt-x7b/eval/x_logs/x7b-dryrun-%j.log
# X7 B2: default path of run_sanitizer.py / run_iguard.py unchanged by the --timeout option.
# OLD = the harness at eval/collector-only-tables (copied to _old_run_*.py, uncommitted), NEW = this checkout.
cd /home/fzheng4/wt-x7b || exit 1
source eval/baselines/gpu_env.sh
export IGUARD_SO=/home/fzheng4/AccelProf/eval/baselines/setup/iguard/iguard.so
hostname; echo CUDA_HOME=$CUDA_HOME; readlink -f /usr/local/cuda
ID=P4-1dconv-norace-small
O=eval/results/x7b-dryrun
for v in old new; do
  if [ $v = old ]; then S=_old_run_sanitizer.py; G=_old_run_iguard.py; else S=run_sanitizer.py; G=run_iguard.py; fi
  $PY eval/baselines/$S --tools racecheck --id $ID --out $O/san-$v.csv
  $PY eval/baselines/$G --id $ID --reps 1 --out $O/ig-$v.csv
done
# the new --timeout path, for the record
$PY eval/baselines/run_sanitizer.py --tools racecheck --id $ID --timeout 600 --out $O/san-newto.csv
$PY eval/baselines/run_iguard.py --id $ID --reps 1 --timeout 600 --out $O/ig-newto.csv

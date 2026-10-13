#!/usr/bin/env bash
#SBATCH --job-name=x0-kdiff
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=08:00:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/x0-kdiff-%j.log
W=/home/fzheng4/AccelProf/.claude/worktrees/wt-x0
cd $W || exit 1
echo "host=$(hostname) HEAD=$(git rev-parse --short HEAD) $(date -Is)"
/usr/bin/time -v .env/bin/python eval/baselines/setup/x0_kernel_diff.py --store /mnt/beegfs/$USER/cuvein_traces/t20-parity2 \
   --over eval/baselines/setup/x0_over_cutoff.txt --out eval/baselines/setup/x0_kernel_diff.json 2>&1 | grep -v "^\s*\(Page\|Socket\|File\|Signals\|Swaps\|Voluntary\|Involuntary\|Average\|Minor\|Major\|Exit\|Percent\|System\|User\)"
echo "== done $(date -Is)"

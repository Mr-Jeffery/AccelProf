#!/usr/bin/env bash
#SBATCH --job-name=t24-py
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=01:00:00
# T24: run one short CPU command of this worktree's python (tables, summaries) on a compute node.
#   sbatch -p normal -x c2,c21,c23,c37,c46,c54 -o <log> t24_py.sh <script> <args>...
W=${W:-/home/fzheng4/wt-t24}
for d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do
  timeout 10 ls $d > /dev/null 2>&1 || { echo "ABORT on $(hostname): $d not readable"; exit 3; }
done
cd $W || exit 1
echo "host=$(hostname) HEAD=$(git rev-parse --short HEAD) $(date -Is): $*"
$W/.env/bin/python "$@"

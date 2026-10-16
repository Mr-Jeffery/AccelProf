#!/usr/bin/env bash
#SBATCH --job-name=t22-inspect
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=02:00:00
# T22: the BeeGFS inspections of t22_inspect.py (compute node; no GPU work).
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t22}
S=/mnt/beegfs/$USER/cuvein_traces
P=$W/.env/bin/python
I=$W/eval/baselines/setup/t22_inspect.py
echo "host=$(hostname) $(date -Is)"
$P $I shards $S/t22-parity-b 8
$P $I unreadable $S/t22-diag3-P7-heartwall-cuda-n32
$P $I unreadable $S/t22-diag3-P7-heartwall-cuda-n16
$P $I mem $S/t22-diag-P9-knn-cuda-n1 $S/t22-diag-P9-knn-cuda-n8 $S/t22-diag3-P9-knn-cuda-n16 \
    $S/t22-diag-P7-heartwall-cuda-n1 $S/t22-diag3-P7-heartwall-cuda-n8 $S/t22-diag3-P7-heartwall-cuda-n16
echo "== done $(date -Is)"

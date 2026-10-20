#!/usr/bin/env bash
#SBATCH --job-name=t22-slots
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:00:00
# T22 §2.2: the private SLOTCOUNT build's counters of the bfs and nbody runs (t22_inspect.py slots).
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t22}
S=/mnt/beegfs/$USER/cuvein_traces
echo "host=$(hostname) $(date -Is)"
$W/.env/bin/python $W/eval/baselines/setup/t22_inspect.py slots $S/t22-slot-P7-bfs-cuda-n1 $S/t22-slot-P7-nbody-cuda-n1
echo "== done $(date -Is)"

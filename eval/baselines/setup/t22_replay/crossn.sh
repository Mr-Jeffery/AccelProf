#!/usr/bin/env bash
#SBATCH --job-name=t22-crossn
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
# T22 verification B, cross-N: pick.py's kernels of a recorded store (non-empty hb_sync_pass, the
# largest, one per program) replayed at each N of NS by replay_run.sh -- every drain threaded
# (INLINE0=1) -- and compared with the recording's own aggregates.
#   STORE=<store dir> NPICK=3 NS="1 2 8 32" sbatch -p <partition> -o <log> eval/baselines/setup/t22_replay/crossn.sh
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t22}
export KERNELS=$($W/.env/bin/python $W/eval/baselines/setup/t22_replay/pick.py $STORE --n ${NPICK:-3})
echo "picked: $KERNELS"
export INLINE0=${INLINE0-1}
bash $W/eval/baselines/setup/t22_replay/replay_run.sh

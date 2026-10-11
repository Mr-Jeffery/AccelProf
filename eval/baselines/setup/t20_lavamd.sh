#!/usr/bin/env bash
#SBATCH --job-name=t20-lavamd
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54,c2
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=23:00:00
# T20 step 4: P7-lavaMD (full input, one kernel of 398.8 M records) in one MODE, the runtimes of
# RTS one after the other on ONE node through t19_long.sh (no-dump, HB_STATS at kernel end):
#   t20 = this worktree, t19 = the installed runtime (3c7eefd), d67 = the d67ed41 mirror (T4's bar;
#   t20_rt_d67.sh). Results: /mnt/beegfs/$USER/t20-lavamd-<rt>/P7-lavaMD-cuda/<mode>.
#   MODE=scalar-clock|vector-clock [RTS="t20 t19 d67"] [CAP=9000] sbatch -o <log> eval/baselines/setup/t20_lavamd.sh
set -u
export W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t20}; A=/home/fzheng4/AccelProf
cd $W || exit 1
echo "host=$(hostname) $(lscpu | /usr/bin/grep 'Model name' | sed 's/  */ /g') mem=$(free -g | awk '/Mem:/{print $2}')G HEAD=$(git -C $W rev-parse --short HEAD) mode=$MODE $(date -Is)"
echo P7-lavaMD-cuda > $W/build_logs/lavamd.ids
for rt in ${RTS:-t20 t19 d67}; do
  case $rt in t20) R=$W;; t19) R=$A;; d67) R=$W/rt-d67;; esac
  RT=$R OUTDIR=t20-lavamd-$rt IDS=$W/build_logs/lavamd.ids MODES=$MODE CAP=${CAP:-9000} EVERY=0 \
     bash eval/baselines/setup/t19_long.sh 2>&1 | sed "s/^/[$rt] /"
done
echo "== done $(date -Is)"

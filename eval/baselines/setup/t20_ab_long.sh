#!/usr/bin/env bash
#SBATCH --job-name=t20-ab-long
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54,c2,c37
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=23:00:00
# T20 step 4 (t20_lavamd.sh for any program): program ID in MODE, the runtimes of RTS one after the
# other on ONE node through t19_long.sh (no-dump, HB_STATS at kernel end), CAP seconds each; for
# programs that do not finish, the kernels completed within CAP is the same-node comparison.
#   ID=<manifest id> MODE=scalar-clock|vector-clock [RTS="t20 t19"] [CAP=1800] sbatch -o <log> t20_ab_long.sh
#   (results: /mnt/beegfs/$USER/t20-ab-long-<rt>/<id>/<mode>)
set -u
export W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t20}; A=/home/fzheng4/AccelProf
cd $W || exit 1
echo "host=$(hostname) $(lscpu | /usr/bin/grep 'Model name' | sed 's/  */ /g') mem=$(free -g | awk '/Mem:/{print $2}')G HEAD=$(git -C $W rev-parse --short HEAD) id=$ID mode=$MODE cap=${CAP:-1800} $(date -Is)"
ids=$W/build_logs/ab-long-$SLURM_JOB_ID.ids; echo $ID > $ids
for rt in ${RTS:-t20 t19}; do
  case $rt in t20) R=$W;; t19) R=$A;; d67) R=$W/rt-d67;; esac
  RT=$R OUTDIR=t20-ab-long-$rt IDS=$ids MODES=$MODE CAP=${CAP:-1800} EVERY=0 \
     bash eval/baselines/setup/t19_long.sh 2>&1 | sed "s/^/[$rt] /"
done
echo "== done $(date -Is)"

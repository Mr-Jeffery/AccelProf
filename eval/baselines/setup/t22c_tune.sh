#!/usr/bin/env bash
#SBATCH --job-name=t22c-tune
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=08:00:00
# T22 cont., Fix 1's thresholds by measurement: PROGS (default nbody) in scalar-clock mode at N=1
# (the serial pass), the harness (t22_perf.sh: no dump, HB_STATS), one after the other on one node,
# per VARIANT:
#   old      the b6a615e runtime (mirror $M/rt-old: neither fix)
#   <c>:<m>  the HB_TAIL_TUNE runtime (mirror $M/rt-tune: both fixes) with YOSEMITE_HB_TAIL_C=c,
#            YOSEMITE_HB_TAIL_MAX=m -- the tail of a P-slot prefix is the largest power of two
#            t <= m with t*t <= c*P, at least 8; <c>:8 = the fixed 8-slot tail (Fix 2 alone)
# Then per run the kernel JSONs' write times (the store's mtimes, s) and each kernel's
# hb_stats.hb_clock.buckets (t22c_kstats.py).
#   VARIANTS="old 4:8 4:256 ..." CAP=1200 sbatch -p <gpu partition> -o <log> eval/baselines/setup/t22c_tune.sh
set -u
W0=${W0:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t22}
M=${M:-/mnt/beegfs/$USER/t22c}
echo "host=$(hostname) nproc=$(nproc) $(lscpu | grep 'Model name' | sed 's/  */ /g') $(date -Is)"
for prog in ${PROGS:-P7-nbody-cuda}; do
  for v in $VARIANTS; do
    if [ "$v" = old ]; then
      W=$M/rt-old; tag=t22c-tune-old; unset YOSEMITE_HB_TAIL_C YOSEMITE_HB_TAIL_MAX
    else
      W=$M/rt-tune; tag=t22c-tune-c${v%:*}m${v#*:}
      export YOSEMITE_HB_TAIL_C=${v%:*} YOSEMITE_HB_TAIL_MAX=${v#*:}
    fi
    echo "######## $prog variant $v (W=$W) start $(date +%s.%N)"
    W=$W RUNS="$prog:1" CAP=${CAP:-1200} TAG=$tag bash $W0/eval/baselines/setup/t22_perf.sh
    $W0/.env/bin/python $W0/eval/baselines/setup/t22c_kstats.py /mnt/beegfs/$USER/cuvein_traces/$tag-$prog-n1
  done
done
echo "== done $(date -Is)"

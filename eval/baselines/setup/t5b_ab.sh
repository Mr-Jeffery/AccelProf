#!/usr/bin/env bash
#SBATCH --job-name=t5b-ab
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=03:00:00
# T5b: same-node A/B wall time of one program in vector-clock mode under several runtimes
# (setup/t5b_profile.py, perf at 29 Hz, no call graph).
#   ID=<manifest id> RTS="<checkout> <checkout>" CAP=<s> sbatch -p rtx4060ti16g -x c54,c2 \
#       -o <W>/build_logs/t5b-ab-%j.log eval/baselines/setup/t5b_ab.sh
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/t5b-shared-base-clock}
cd $W || exit 1
for R in ${RTS:?}; do
  export ACCEL_PROF_HOME=$R
  source eval/baselines/gpu_env.sh
  export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$LD_LIBRARY_PATH
  echo "== host=$(hostname) runtime $R libsanalyzer $(sha256sum $(ldd $R/lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}') | cut -c1-16)"
  S=$(date +%s.%N)
  $PY eval/baselines/setup/t5b_profile.py --id ${ID:?} --cap ${CAP:-1200} --freq 29 \
      --work /mnt/beegfs/$USER/t5b_ab/$(basename $R) 2>&1 | head -${LINES_OUT:-12}
  echo "wall incl. extraction: $(echo "$(date +%s.%N) - $S" | bc) s"
done

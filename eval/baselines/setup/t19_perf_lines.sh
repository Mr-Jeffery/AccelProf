#!/usr/bin/env bash
#SBATCH --job-name=t19-perf-lines
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=02:00:00
# T19 step 5: the perf data of t19_profile.sh re-reported by source line (self time, no call
# graph), so the time inlined into HbClock::process splits into bucket lookup, clock joins,
# window bookkeeping, record decoding; t19_perf_attr.py groups the lines.
#   sbatch -p rtx4060ti16g -x c54,c2 -o <log> eval/baselines/setup/t19_perf_lines.sh
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t19}
P=/mnt/beegfs/$USER/t19_profile
for d in ${DIRS:-P7-hotspot-cuda-vector-clock P9-fpc-cuda-scalar-clock}; do
  echo "== $d"
  perf report -i $P/$d/work/perf.data --no-children --stdio -g none --sort dso,sym,srcline \
      --percent-limit 0.2 2>/dev/null | /usr/bin/grep -v "^#" | /usr/bin/grep -v "^$" > $P/$d/lines.txt
  head -80 $P/$d/lines.txt | cut -c1-220
  cp $P/$d/lines.txt $W/eval/baselines/setup/t19_perf/$d.lines.txt
done
echo "== done $(date -Is)"

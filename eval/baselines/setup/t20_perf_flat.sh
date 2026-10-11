#!/usr/bin/env bash
#SBATCH --job-name=t20-perf-flat
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:00:00
# T20: flat self time by symbol and by source line for the perf.data files of t20_profile.sh
# (hotspot vector-clock, fpc scalar-clock) -> eval/baselines/setup/t20_perf/<id>-<mode>.{sym,lines}.txt
#   W=<worktree> sbatch -o <log> eval/baselines/setup/t20_perf_flat.sh
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t20}
for d in /mnt/beegfs/$USER/t20_profile/*/; do
  n=$(basename $d); p=$d/work/perf.data
  [ -f $p ] || continue
  perf report -i $p --no-children --stdio -g none --sort sym --percent-limit 0.3 2>/dev/null \
      | /usr/bin/grep -v "^#" | /usr/bin/grep -v "^$" > $W/eval/baselines/setup/t20_perf/$n.sym.txt
  perf report -i $p --no-children --stdio -g none --sort sym,srcline --percent-limit 0.3 2>/dev/null \
      | /usr/bin/grep -v "^#" | /usr/bin/grep -v "^$" > $W/eval/baselines/setup/t20_perf/$n.lines.txt
  echo "$n: $(wc -l < $W/eval/baselines/setup/t20_perf/$n.sym.txt) symbols"
done
echo "== done $(date -Is)"

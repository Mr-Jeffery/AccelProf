#!/usr/bin/env bash
#SBATCH --job-name=t20-perf-alloc
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:00:00
# T20: for the perf.data of t20_profile.sh, (1) self time per thread (the teardown thread vs the
# analysis thread) and (2) the callers of the allocator symbols -> t20_perf/<id>-<mode>.{tid,alloc}.txt
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t20}
for d in /mnt/beegfs/$USER/t20_profile/*/; do
  n=$(basename $d); p=$d/work/perf.data
  [ -f $p ] || continue
  perf report -i $p --no-children --stdio -g none --sort pid --percent-limit 0.5 2>/dev/null \
      | /usr/bin/grep -v "^#" | /usr/bin/grep -v "^$" > $W/eval/baselines/setup/t20_perf/$n.tid.txt
  perf report -i $p --no-children --stdio -G --sort pid,sym --percent-limit 1 \
      --symbols _int_malloc,_int_free,malloc_consolidate,unlink_chunk.isra.2,malloc 2>/dev/null \
      | /usr/bin/grep -v "^$" | head -400 > $W/eval/baselines/setup/t20_perf/$n.alloc.txt
done
echo "== done $(date -Is)"

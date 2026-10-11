#!/usr/bin/env bash
#SBATCH --job-name=t19-perf-alloc
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=02:00:00
# T19 step 5: who calls the allocator -- the malloc/free samples of t19_profile.sh's perf data
# with their callers (DWARF call graph), so the allocator share is attributed.
#   sbatch -p rtx4060ti16g -x c54,c2 -o <log> eval/baselines/setup/t19_perf_alloc.sh
P=/mnt/beegfs/$USER/t19_profile
OUT=/home/fzheng4/AccelProf/.claude/worktrees/wt-t19/eval/baselines/setup/t19_perf
for d in P7-hotspot-cuda-vector-clock P9-fpc-cuda-scalar-clock; do
  echo "== $d"
  perf report -i $P/$d/work/perf.data --no-children --stdio --sort sym \
      --symbols=cfree@GLIBC_2.2.5,unlink_chunk.isra.2,malloc_consolidate,_int_free,malloc,_int_malloc,_int_realloc \
      -g caller,2,callee,function,percent --max-stack 12 2>/dev/null | /usr/bin/grep -v "^#" | /usr/bin/grep -v "^$" > $OUT/$d.alloc.txt
  /usr/bin/grep -E "HbClock::|PcDependency::|^ +[0-9.]+%" $OUT/$d.alloc.txt | head -60 | cut -c1-160
done
echo "== done $(date -Is)"

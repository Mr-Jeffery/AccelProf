#!/usr/bin/env bash
#SBATCH --job-name=t19-ab-small
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
# T19: same-node A/B of the bucket layouts on a reduced P7-lavaMD (-boxes1d $BOXES; the manifest
# row uses 30): every runtime in RTS (name=checkout pairs), REPS runs each, interleaved, no-dump,
# HB_STATS at kernel end only, in MODE. With PERF=1 the last rep of each runtime runs under
# `perf record` (DWARF call graphs) and is reported by source line.
#   W=<worktree> RTS="before=/home/fzheng4/AccelProf v1=<wt>/rt1 v3=<wt>/rt3" sbatch -w <node> -o <log> \
#       eval/baselines/setup/t19_ab_small.sh
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t19}; A=/home/fzheng4/AccelProf
BOXES=${BOXES:-12}; REPS=${REPS:-2}; MODE=${MODE:-scalar-clock}
cd $W || exit 1
export ACCEL_PROF_HOME=$A
source eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$LD_LIBRARY_PATH
exe=$A/eval/baselines/bin/P7/lavaMD-cuda
R=/mnt/beegfs/$USER/t19-ab-small; rm -rf $R; mkdir -p $R/cubins
echo "host=$(hostname) $(lscpu | /usr/bin/grep 'Model name' | sed 's/  */ /g') boxes=$BOXES reps=$REPS mode=$MODE"
( cd $R/cubins && cuobjdump -xelf all $exe > /dev/null 2>&1; for c in *.cubin *.elf; do [ -f "$c" ] && nvdisasm -bbcfg -poff "$c" > "${c%.*}.dot" 2>/dev/null; done; \
  $PY $W/python/atomic_scope_sidecar.py *.dot -o atomic_scope.txt > /dev/null 2>&1 )
for rep in $(seq 1 $REPS); do
  for spec in ${RTS:-before=$A v1=$W/rt1 v2=$W/rt2 v3=$W/rt3}; do
    name=${spec%%=*}; home=${spec#*=}
    D=$R/$name-$rep; mkdir -p $D; ln -sf $exe $D/lavaMD-cuda
    lib=$(ldd $home/lib/libcompute_sanitizer.so | awk '/sanalyzer.so/{print $3}')
    P=(); [ "${PERF:-0}" = 1 ] && [ $rep = $REPS ] && P=(perf record -F 199 --call-graph dwarf,16384 -o $D/perf.data --)
    t0=$(date +%s.%N)
    ( cd $D && env ACCEL_PROF_HOME=$home PATH=$home/bin:$PATH YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=$MODE \
        YOSEMITE_HB_DUMP=0 YOSEMITE_HB_STATS=1 YOSEMITE_ATOMIC_SCOPE_FILE=$R/cubins/atomic_scope.txt \
        "${P[@]}" accelprof -v -t pc_dependency_analysis -n 1 ./lavaMD-cuda -boxes1d $BOXES < /dev/null > stdout.txt 2>&1; echo "rc=$?" > rc.txt )
    t1=$(date +%s.%N)
    st=$(/usr/bin/grep -h "HB_STATS\] kernel_" $D/*.accelprof.log | tail -1 | /usr/bin/grep -o '"buckets": {[^}]*}')
    printf "%-7s rep %d  libsanalyzer %s  wall %7.1f s  %s  %s\n" $name $rep $(sha256sum $lib | cut -c1-8) \
        $(echo "$t1 - $t0" | bc) "$(cat $D/rc.txt)" "$st"
    if [ ${#P[@]} -gt 0 ]; then
      perf report -i $D/perf.data --no-children --stdio -g none --sort dso,sym,srcline --percent-limit 0.2 2>/dev/null \
          | /usr/bin/grep -v "^#" | /usr/bin/grep -v "^$" > $W/eval/baselines/setup/t19_perf/lavaMD-small-$name.lines.txt
    fi
  done
done
echo "== done $(date -Is)"

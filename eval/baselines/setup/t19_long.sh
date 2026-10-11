#!/usr/bin/env bash
#SBATCH --job-name=t19-long
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54,c2
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=05:00:00
# T4 step 4, the programs the 1,200 s harness cap cuts off under no-dump mode: do they finish
# at all, and how does HbClock's state grow? One program per array task (IDS line k), each
# mode in turn with a CAP-second limit, YOSEMITE_HB_DUMP=0 and YOSEMITE_HB_STATS_EVERY=<n> (a
# stats line after n, 2n, 4n, ... records -> the growth curve even when the kernel never ends).
# Runs accelprof directly (the harness's cap is a hard 1,200 s); the dump dir, the tool's log
# (accelprof -v) and rc/wall go to /mnt/beegfs/$USER/t4-long/<id>/<mode>/.
#   W=/home/fzheng4/wt-T4 IDS=eval/baselines/setup/t4_long_ids.txt CAP=7200 \
#     sbatch --array=0-<n-1> -o /home/fzheng4/wt-T4/build_logs/t4-long-%A_%a.log eval/baselines/setup/t4_long.sh
set -u
W=${W:-/home/fzheng4/wt-T4}; CAP=${CAP:-7200}; EVERY=${EVERY:-2000000}
IDS=${IDS:-eval/baselines/setup/t4_long_ids.txt}
cd $W || exit 1
# T19: RT=<checkout> runs another runtime (the before side: RT=/home/fzheng4/AccelProf, the
# installed one) with this worktree's scripts; MODES restricts the modes; OUTDIR the BeeGFS dir
export ACCEL_PROF_HOME=${RT:-$W}
source eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$LD_LIBRARY_PATH
id=$(sed -n "$((${SLURM_ARRAY_TASK_ID:-0} + 1))p" $IDS)
row=$(awk -F, -v id="$id" '$1==id' eval/baselines/manifest.csv)
exe=$(echo "$row" | cut -d, -f6); args=$(echo "$row" | cut -d, -f7); pset=$(echo "$row" | cut -d, -f2); prog=$(echo "$row" | cut -d, -f3)
base=$(basename $exe)
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader) mem=$(free -g | awk '/Mem:/{print $2}')G HEAD=$(git -C $W rev-parse --short HEAD) libsanalyzer $(sha256sum $(ldd $ACCEL_PROF_HOME/lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}') | cut -c1-16) id=$id exe=$exe args=[$args] cap=${CAP}s every=$EVERY"
# the CFG + sidecar once (as parallel.py / getall.sh do)
R=/mnt/beegfs/$USER/${OUTDIR:-t19-long}/$id; mkdir -p $R
cub=$R/cubins; mkdir -p $cub
( cd $cub && cuobjdump -xelf all $exe > /dev/null 2>&1; for c in *.cubin *.elf; do [ -f "$c" ] && nvdisasm -bbcfg -poff "$c" > "${c%.*}.dot" 2>/dev/null; done; \
  $PY $W/python/atomic_scope_sidecar.py *.dot -o atomic_scope.txt > /dev/null 2>&1 )
scope=$cub/atomic_scope.txt
hec=$W/eval/baselines/corpora/HeCBench/src
for mode in ${MODES:-scalar-clock vector-clock}; do
  D=$R/$mode; rm -rf $D; mkdir -p $D; ln -sf $(readlink -f $exe) $D/$base
  # HeCBench inputs relative to the cwd, as parallel.py mirrors them
  if [ "$pset" = P7 ] || [ "$pset" = P9 ]; then
    [ -d $hec/data ] && ln -sfn $hec/data $R/data
    [ -d $hec/$prog/input ] && ln -sfn $hec/$prog/input $D/input
    [ -d $hec/$prog/data ] && ln -sfn $hec/$prog/data $D/data
    for a_ in $args; do case $a_ in ../*) sib=$(echo $a_ | cut -d/ -f2); [ -d $hec/$sib ] && ln -sfn $hec/$sib $R/$sib;; esac; done
  fi
  echo "== $mode start $(date -Is)"
  t0=$(date +%s)
  # GNU time is not on every node image (c0, c1 gave rc 127): without it the RSS comes from
  # the HB_STATS lines (rss_kb) and the wall from the timestamps
  TIME=(); [ -x /usr/bin/time ] && TIME=(/usr/bin/time -f "maxrss_kb=%M wall_s=%e" -o $D/time.txt)
  ( cd $D && env YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=$mode YOSEMITE_HB_DUMP=0 YOSEMITE_HB_STATS=1 \
      YOSEMITE_HB_STATS_EVERY=$EVERY YOSEMITE_ATOMIC_SCOPE_FILE=$scope \
      "${TIME[@]}" timeout -s KILL ${CAP}s accelprof -v -t pc_dependency_analysis -n 1 ./$base $args < /dev/null > $D/stdout.txt 2>&1; echo "rc=$?" > $D/rc.txt )
  echo "== $mode end $(date -Is) elapsed=$(( $(date +%s) - t0 ))s $(cat $D/rc.txt) $(cat $D/time.txt 2>/dev/null | tr '\n' ' ')"
  ls $D/dependency_*/kernel_*.json 2>/dev/null | wc -l | sed 's/^/kernel JSONs: /'
  /usr/bin/grep -h "HB_STATS" $D/*.accelprof.log $D/stdout.txt 2>/dev/null | tail -3 | cut -c1-400
done
echo "== done $(date -Is)"

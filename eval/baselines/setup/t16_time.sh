#!/usr/bin/env bash
#SBATCH --job-name=t16-time
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54,c2,c37
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --output=/home/fzheng4/wt-t16/build_logs/t16-time-%j.log
# T16 step 5: the cost of a second, certain-policy run. The programs of IDS (P7/P9 ones that
# finish in both modes under no-dump mode, eval/NO_DUMP.md) run with the worktree runtime,
# YOSEMITE_HB_DUMP=0, vector-clock mode under YOSEMITE_HB_GATE_POLICY=recorded and =certain
# (REPS reps each, interleaved, one node) and scalar-clock mode once (the policy does not touch
# it); wall and peak RSS per run, the kernels' hb_chain counters, and the verdicts of
# sync_dominance.analyze on the no-dump dumps under both policies (the sound column on the
# realistic suites). Modelled on t19_long.sh (HeCBench inputs as parallel.py mirrors them).
#   W=/home/fzheng4/wt-t16 IDS=eval/baselines/setup/t16_time_ids.txt sbatch eval/baselines/setup/t16_time.sh
set -u
W=${W:-/home/fzheng4/wt-t16}; REPS=${REPS:-2}; CAP=${CAP:-3600}
IDS=${IDS:-eval/baselines/setup/t16_time_ids.txt}
cd $W || exit 1
export ACCEL_PROF_HOME=$W CUDA_HOME=${CUDA_HOME:-/usr/local/cuda-13.3}
source eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$LD_LIBRARY_PATH
unset YOSEMITE_HB_GATE_POLICY CUVEIN_GATE_POLICY
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader) mem=$(free -g | awk '/Mem:/{print $2}')G $(lscpu | /usr/bin/grep 'Model name' | sed 's/  */ /g') HEAD=$(git -C $W rev-parse --short HEAD) libsanalyzer $(sha256sum $(ldd $W/lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}') | cut -c1-16) cuda=$(readlink -f $CUDA_HOME) $(date -Is)"
R=/mnt/beegfs/$USER/t16-time; mkdir -p $R
hec=$W/eval/baselines/corpora/HeCBench/src
while read -r id; do
  [ -z "$id" ] && continue
  row=$(awk -F, -v id="$id" '$1==id' eval/baselines/manifest.csv)
  exe=$(echo "$row" | cut -d, -f6); args=$(echo "$row" | cut -d, -f7); pset=$(echo "$row" | cut -d, -f2); prog=$(echo "$row" | cut -d, -f3)
  base=$(basename $exe)
  P=$R/$id; mkdir -p $P/cubins
  ( cd $P/cubins && cuobjdump -xelf all $exe > /dev/null 2>&1; for c in *.cubin *.elf; do [ -f "$c" ] && nvdisasm -bbcfg -poff "$c" > "${c%.*}.dot" 2>/dev/null; done; \
    $PY $W/python/atomic_scope_sidecar.py *.dot -o atomic_scope.txt > /dev/null 2>&1 )
  scope=$P/cubins/atomic_scope.txt
  echo "== $id exe=$exe args=[$args]"
  for rep in $(seq 1 $REPS); do
    for cfg in vector-clock:recorded vector-clock:certain $([ $rep = 1 ] && echo scalar-clock:recorded); do
      mode=${cfg%%:*}; pol=${cfg##*:}
      D=$P/$mode-$pol-$rep; rm -rf $D; mkdir -p $D; ln -sf $(readlink -f $exe) $D/$base
      if [ "$pset" = P7 ] || [ "$pset" = P9 ]; then
        [ -d $hec/data ] && ln -sfn $hec/data $P/data
        [ -d $hec/$prog/input ] && ln -sfn $hec/$prog/input $D/input
        [ -d $hec/$prog/data ] && ln -sfn $hec/$prog/data $D/data
        for a_ in $args; do case $a_ in ../*) sib=$(echo $a_ | cut -d/ -f2); [ -d $hec/$sib ] && ln -sfn $hec/$sib $P/$sib;; esac; done
      fi
      TIME=(); [ -x /usr/bin/time ] && TIME=(/usr/bin/time -f "maxrss_kb=%M wall_s=%e" -o $D/time.txt)
      t0=$(date +%s.%N)
      ( cd $D && env YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=$mode YOSEMITE_HB_DUMP=0 YOSEMITE_HB_STATS=1 \
          YOSEMITE_HB_GATE_POLICY=$pol YOSEMITE_ATOMIC_SCOPE_FILE=$scope \
          "${TIME[@]}" timeout -s KILL ${CAP}s accelprof -v -t pc_dependency_analysis -n 1 ./$base $args < /dev/null > $D/stdout.txt 2>&1; echo "rc=$?" > $D/rc.txt )
      t1=$(date +%s.%N)
      nk=$(ls $D/dependency_*/kernel_*.json 2>/dev/null | wc -l)
      chain=$($PY - $D <<'PYEOF'
import glob, json, sys
c = {}
for f in glob.glob(f"{sys.argv[1]}/dependency_*/kernel_*.json"):
    j = json.load(open(f))
    for k, v in (j.get("hb_chain") or {}).items():
        c[k] = c.get(k, 0) + v
print(json.dumps(c) if c else "-")
PYEOF
)
      printf "%-22s %-13s %-9s rep %d  wall %8.1f s  %s  %s  kernels %s  hb_chain %s\n" "$id" $mode $pol $rep $(echo "$t1 - $t0" | bc) "$(cat $D/rc.txt)" "$(cat $D/time.txt 2>/dev/null | tr '\n' ' ')" "$nk" "$chain"
    done
  done
  # verdicts from the no-dump dumps under both policies (rep 1), scalar-clock for reference
  for cfg in vector-clock-recorded vector-clock-certain scalar-clock-recorded; do
    D=$P/$cfg-1; dep=$(ls -d $D/dependency_* 2>/dev/null | head -1)
    [ -n "$dep" ] || continue
    $PY - "$dep" "$P/cubins" $cfg <<'PYEOF'
import glob, sys
sys.path.insert(0, "eval/baselines"); sys.path.insert(0, "python")
import run_cuvein
ids, pcs, raw = run_cuvein._analyze_reports(sys.argv[1], sys.argv[2])
race, sc = run_cuvein.split_raw(raw)
print(f"   verdict {sys.argv[3]}: {'RACE' if ids else 'CLEAN'} reports={len(ids)} {run_cuvein.classes_note(raw)} ids={' '.join(ids[:6])}{' ...' if len(ids) > 6 else ''}")
PYEOF
  done
done < $IDS
echo "== done $(date -Is)"

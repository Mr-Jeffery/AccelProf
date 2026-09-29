#!/usr/bin/env bash
#SBATCH --job-name=t10-measure
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=02:00:00
# T10: the engine's memory and time with the strength column, on the programs of T5a/T9's
# measurement set whose SASS has address-spaced .STRONG accesses (the only ones whose bucket
# keys change): P4 reduction-norace-large (T5a/T9's "reduction, large input") and
# rule-110-norace-small. BEFORE = the installed runtime (libsanalyzer 75f46012) with the main
# checkout's sidecar (policy generic); AFTER = the T10 runtime with the T10 sidecar (token);
# same node, same helper (setup/t5a_stats.py, YOSEMITE_HB_STATS=1), vector-clock mode.
#   W=<worktree> sbatch -p rtx4060ti16g -x c54,c2 -o <W>/build_logs/t10-measure-%j.log \
#       <W>/eval/baselines/setup/t10_measure.sh
set -u
W=${W:?W=<the T10 worktree>}; A=/home/fzheng4/AccelProf
cd $W || exit 1
EV=$W/eval/baselines/setup/t10_stats; mkdir -p $EV
unset CUVEIN_STRONG_LDST
for side in before after; do
  R=$A; [ $side = after ] && R=$W
  (
    export ACCEL_PROF_HOME=$R
    source $W/eval/baselines/gpu_env.sh
    export CUDA_HOME=/usr/local/cuda-13.3 CUDA_PATH=/usr/local/cuda-13.3
    export PATH=$R/bin:/usr/local/cuda-13.3/bin:$PATH
    export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:/usr/local/cuda-13.3/compute-sanitizer:${LD_LIBRARY_PATH:-}
    echo "== $side: host=$(hostname) runtime=$R collector $(sha256sum $R/lib/libcompute_sanitizer.so | cut -c1-16) -> $(ldd $R/lib/libcompute_sanitizer.so | grep sanalyzer | awk '{print $3}')"
    S="$W/.env/bin/python $W/eval/baselines/setup/t5a_stats.py --out $EV"
    $S --mode vector-clock --label t10-$side-reduction-norace-large \
       --exe $A/eval/baselines/bin/P4/reduction_norace --stdin $A/eval/baselines/inputs/reduction.large.in --cap 900
    $S --mode vector-clock --label t10-$side-rule-110-norace-small \
       --exe $A/eval/baselines/bin/P4/rule-110_norace --stdin $A/eval/baselines/inputs/rule-110.small.in --cap 900
  )
done
$W/.env/bin/python - $EV <<'EOF'
import json, sys, glob
for p in sorted(glob.glob(f"{sys.argv[1]}/t10-*.json")):
    d = json.load(open(p))
    for k in d.get("kernels", []):
        e = (k.get("hb_stats") or {}).get("engine", {})
        b = e.get("buckets", {})
        print(f"{d['label']:42s} {k['file']:14s} wall {d['wall_s']:7.2f}s peak {d['peak_rss_mb']:8.1f} MB "
              f"buckets loc={b.get('locations')} groups={b.get('groups')} entries={b.get('entries')} "
              f"bytes={b.get('bytes_est')} races={e.get('races', {}).get('records')} lib={d.get('engine_lib_sha16')}")
EOF
echo "== done $(date -Is)"

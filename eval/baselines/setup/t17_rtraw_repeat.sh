#!/usr/bin/env bash
#SBATCH --job-name=t17-rtraw-rep
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=01:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t17-rtraw-repeat-%j.log
# T17 merge check follow-up: race_interblock_none-lock_rtraw differed between the previous
# runtime (e527875d / T1a collector objects / fatbin a2d7368b) and the installed one (T15+T17)
# in all three configurations. Is that the lock's schedule? Five runs per runtime and
# configuration; print each run's normalised signature (t5a_compare.norm) and hb_events
# count, and whether the two runtimes' outcome sets overlap.
#   sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t17_rtraw_repeat.sh
set -u
A=/home/fzheng4/AccelProf; P=/home/fzheng4/rt-prev-e527875d
cd $A || exit 1
source eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,driver_version --format=csv,noheader)"
OUT=/mnt/beegfs/$USER/t17-rtraw-repeat; rm -rf $OUT; mkdir -p $OUT
exe=ScoR/microbenchmarks/bin/race_interblock_none-lock_rtraw; base=$(basename $exe)
for conf in default hb-vc; do for rt in prev new; do for k in 1 2 3 4 5; do
  R=$A; [ $rt = prev ] && R=$P
  D=$OUT/$conf/$rt/$k; mkdir -p $D; ln -s $A/$exe $D/$base
  envs=(env -u YOSEMITE_HB_TRACE -u YOSEMITE_HB_MODE -u YOSEMITE_HB_NO_ENGINE -u YOSEMITE_ATOMIC_SCOPE_FILE -u YOSEMITE_HB_STATS -u YOSEMITE_HB_LATE_SEQ)
  [ $conf != default ] && envs+=(YOSEMITE_HB_TRACE=1)
  ( cd $D && "${envs[@]}" ACCEL_PROF_HOME=$R PATH=$R/bin:$PATH accelprof -t pc_dependency_analysis -n 1 ./$base < /dev/null > /dev/null 2>&1 )
  d=$(ls -d $D/dependency_${base}_* 2>/dev/null | head -1); [ -n "$d" ] && mv "$d" $D/dump
done; done; done
$PY - $OUT <<'PYEOF'
import hashlib, json, os, sys
sys.path.insert(0, "eval/baselines/setup")
from t5a_compare import norm
root = sys.argv[1]
for conf in ("default", "hb-vc"):
    sigs = {}
    for rt in ("prev", "new"):
        for k in sorted(os.listdir(f"{root}/{conf}/{rt}")):
            p = f"{root}/{conf}/{rt}/{k}/dump/kernel_0.json"
            n = norm(p)
            s = hashlib.sha256(json.dumps(n, sort_keys=True).encode()).hexdigest()[:10]
            sigs.setdefault(rt, []).append(s)
            print(f"{conf} {rt} run{k}: sig {s} edges {len(n.get('edges', []))} hb_events {len(n.get('hb_events', [])) if 'hb_events' in n else '-'}")
    a, b = set(sigs["prev"]), set(sigs["new"])
    print(f"{conf}: prev outcomes {len(a)}, new outcomes {len(b)}, shared {len(a & b)}")
PYEOF

#!/usr/bin/env bash
#SBATCH --job-name=t4-check
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=04:00:00
#SBATCH --output=/home/fzheng4/wt-T4/build_logs/t4-check-%j.log
# T4 (no-dump mode): (1) the default tool path (no YOSEMITE_HB_TRACE) is unchanged -- the live
# runtime vs the worktree's on two ScoR programs, compared up to device addresses and dist
# histograms (setup/t5a_compare.norm); (2) the green set (CLAUDE.md A4 + test_instance_gate.py)
# plus python/test_no_dump.py, every trace re-recorded with the worktree runtime (getall.sh sets
# ACCEL_PROF_HOME to the worktree: private lib/, ScoR/ and cuHadron/).
#   W=/home/fzheng4/wt-T4 sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t4_check.sh
set -u
W=${W:-/home/fzheng4/wt-T4}; A=/home/fzheng4/AccelProf
cd "$W" || exit 1
export ACCEL_PROF_HOME=$W
export CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap,driver_version --format=csv,noheader) HEAD=$(git -C "$W" rev-parse --short HEAD) dirty=$(git -C "$W" status --porcelain -uno | wc -l) $(date -Is)"
for rt in $A $W; do
  echo "runtime $rt collector $(sha256sum $rt/lib/libcompute_sanitizer.so | cut -c1-16) -> $(ldd $rt/lib/libcompute_sanitizer.so | grep sanalyzer | awk '{print $3}')"
done
echo "t4 libsanalyzer $(sha256sum $W/sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16)"

if [ -z "${SKIP_DEFAULT:-}" ]; then
echo "== (1) default path, live vs t4"
OUT=/mnt/beegfs/$USER/t4-check; rm -rf $OUT; mkdir -p $OUT
for exe in ScoR/microbenchmarks/bin/race_interblock_none-lock_rtraw ScoR/microbenchmarks/bin/norace_interblock_atom; do
  base=$(basename $exe)
  for rt in live t4; do
    R=$A; [ $rt = t4 ] && R=$W
    D=$OUT/$base/default/$rt; mkdir -p $D; ln -s $A/$exe $D/$base
    ( cd $D && env -u YOSEMITE_HB_TRACE -u YOSEMITE_HB_MODE -u YOSEMITE_HB_NO_ENGINE -u YOSEMITE_HB_DUMP \
        -u YOSEMITE_ATOMIC_SCOPE_FILE -u YOSEMITE_HB_STATS ACCEL_PROF_HOME=$R PATH=$R/bin:$PATH \
        accelprof -v -t pc_dependency_analysis -n 1 ./$base < /dev/null > stdout.txt 2>&1; echo "rc=$?" > rc.txt )
    d=$(ls -d $D/dependency_${base}_* 2>/dev/null | head -1); [ -n "$d" ] && mv "$d" $D/dump
  done
done
.env/bin/python - $OUT <<'EOF'
import os, sys
sys.path.insert(0, "eval/baselines/setup")
from t5a_compare import norm
root, bad = sys.argv[1], 0
for prog in sorted(os.listdir(root)):
    da, db = f"{root}/{prog}/default/live/dump", f"{root}/{prog}/default/t4/dump"
    fa, fb = sorted(os.listdir(da)), sorted(os.listdir(db))
    same = fa == fb and all(norm(f"{da}/{f}") == norm(f"{db}/{f}") for f in fa)
    bad += not same
    print(f"{prog} default: live vs t4: {'IDENTICAL' if same else 'DIFFERENT'} up to device addresses and dist ({len(fa)} files)")
print("ALL IDENTICAL" if not bad else f"{bad} DIFFERENT")
EOF
fi

echo "== (2) green set + test_no_dump (worktree runtime)"
rm -rf ScoR/microbenchmarks/artifacts/* cuHadron/_coherent_ldst cuHadron/_mm_handoff cuHadron/_gate_held cuHadron/_t12_*
.env/bin/python -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py \
    python/test_barrier_exit.py python/test_hb_substitutions.py python/test_cp_async.py \
    python/test_instance_gate.py python/test_no_dump.py \
    -rfExXs --tb=short -p no:cacheprovider 2>&1 | grep -v "Warning\|setParseAction\|^$\|capture-warnings" | tail -80
echo "== done $(date -Is)"

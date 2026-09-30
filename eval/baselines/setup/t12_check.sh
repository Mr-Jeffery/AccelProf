#!/usr/bin/env bash
#SBATCH --job-name=t12-check
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=02:00:00
# T12 (design/instance_gate.md): (1) the default tool path (no YOSEMITE_HB_TRACE) is unchanged --
# main runtime vs the T14 worktree runtime on two ScoR programs, compared up to device
# addresses and dist histograms (setup/t5a_compare.norm); (2) the green set (CLAUDE.md A4),
# every trace re-recorded with the worktree runtime (getall.sh sets ACCEL_PROF_HOME to the
# worktree: private lib/, ScoR/ and cuHadron/). The engine==oracle keys of the green set
# include a2_uncertain since T14.
#   W=<worktree> sbatch -p rtx4060ti16g -x c54,c2 -o <W>/build_logs/t12-check-%j.log \
#       eval/baselines/setup/t12_check.sh
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/feat-instance-gate}; A=/home/fzheng4/AccelProf
cd "$W" || exit 1
export ACCEL_PROF_HOME=$W
export CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$LD_LIBRARY_PATH
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader) HEAD=$(git -C "$W" rev-parse --short HEAD) dirty=$(git -C "$W" status --porcelain -uno | wc -l)"
for rt in $A $W; do
  echo "runtime $rt collector $(sha256sum $rt/lib/libcompute_sanitizer.so | cut -c1-16) -> $(ldd $rt/lib/libcompute_sanitizer.so | grep sanalyzer | awk '{print $3}')"
done
echo "t12 libsanalyzer $(sha256sum $W/sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16)"

if [ -z "${SKIP_DEFAULT:-}" ]; then
echo "== (1) default path, main vs t12"
OUT=/mnt/beegfs/$USER/t12-check; rm -rf $OUT; mkdir -p $OUT
for exe in ScoR/microbenchmarks/bin/race_interblock_none-lock_rtraw ScoR/microbenchmarks/bin/norace_interblock_atom; do
  base=$(basename $exe)
  for rt in main t12; do
    R=$A; [ $rt = t12 ] && R=$W
    D=$OUT/$base/default/$rt; mkdir -p $D; ln -s $A/$exe $D/$base
    ( cd $D && env -u YOSEMITE_HB_TRACE -u YOSEMITE_HB_MODE -u YOSEMITE_HB_NO_ENGINE \
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
    da, db = f"{root}/{prog}/default/main/dump", f"{root}/{prog}/default/t12/dump"
    fa, fb = sorted(os.listdir(da)), sorted(os.listdir(db))
    same = fa == fb and all(norm(f"{da}/{f}") == norm(f"{db}/{f}") for f in fa)
    bad += not same
    print(f"{prog} default: main vs t12: {'IDENTICAL' if same else 'DIFFERENT'} up to device addresses and dist ({len(fa)} files)")
print("ALL IDENTICAL" if not bad else f"{bad} DIFFERENT")
EOF
fi

echo "== (2) green set (worktree runtime)"
rm -rf ScoR/microbenchmarks/artifacts/* cuHadron/_coherent_ldst cuHadron/_mm_handoff cuHadron/_gate_held cuHadron/_t12_*
.env/bin/python -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py \
    python/test_barrier_exit.py python/test_hb_substitutions.py python/test_cp_async.py python/test_instance_gate.py \
    -rfExXs --tb=line -p no:cacheprovider 2>&1 | grep -v "Warning\|setParseAction\|^$\|capture-warnings" | tail -60
echo "== done $(date -Is)"
echo "== (3) Detect reference, both gates"
.env/bin/python design/algorithms_check.py --gate=instance | tail -3
.env/bin/python design/algorithms_check.py --gate=trusting | tail -1
echo "== done $(date -Is)"

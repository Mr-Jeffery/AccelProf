#!/usr/bin/env bash
#SBATCH --job-name=t9-check
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=02:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t9-check-%j.log
# T9: (1) the default tool path (no YOSEMITE_HB_TRACE) is unchanged -- main runtime vs the
# T9 worktree runtime on two run-to-run deterministic ScoR programs, compared up to device
# addresses and dist histograms (setup/t5a_compare.norm); (2) the green set (CLAUDE.md A4)
# plus python/test_hb_substitutions.py, every trace re-recorded with the worktree runtime
# (getall.sh sets ACCEL_PROF_HOME to the worktree: private lib/, ScoR/ and cuHadron/);
# (3) design/algorithms_check.py over the regenerated ScoR traces.
#   sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t9_check.sh
set -u
W=${W:-/home/fzheng4/wt-T9}; A=/home/fzheng4/AccelProf
cd $W || exit 1
source eval/baselines/gpu_env.sh
[ -n "${PIN8G:-}" ] && source eval/baselines/setup/pin8g.sh
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap,driver_version --format=csv,noheader) HEAD=$(git -C $W rev-parse --short HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l)"
for rt in $A $W; do
  echo "runtime $rt collector $(sha256sum $rt/lib/libcompute_sanitizer.so | cut -c1-16) -> $(ldd $rt/lib/libcompute_sanitizer.so | grep sanalyzer | awk '{print $3}')"
done
echo "t9 libsanalyzer $(sha256sum $W/sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16)"

echo "== (1) default path, main vs t9"
OUT=/mnt/beegfs/$USER/t9_check; rm -rf $OUT; mkdir -p $OUT
for exe in ScoR/microbenchmarks/bin/race_interblock_none-lock_rtraw ScoR/microbenchmarks/bin/norace_interblock_atom; do
  base=$(basename $exe)
  for rt in main t9; do
    R=$A; [ $rt = t9 ] && R=$W
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
    da, db = f"{root}/{prog}/default/main/dump", f"{root}/{prog}/default/t9/dump"
    fa, fb = sorted(os.listdir(da)), sorted(os.listdir(db))
    same = fa == fb and all(norm(f"{da}/{f}") == norm(f"{db}/{f}") for f in fa)
    bad += not same
    print(f"{prog} default: main vs t9: {'IDENTICAL' if same else 'DIFFERENT'} up to device addresses and dist ({len(fa)} files)")
print("ALL IDENTICAL" if not bad else f"{bad} DIFFERENT")
EOF

echo "== (2) green set + test_hb_substitutions.py (worktree runtime)"
rm -rf ScoR/microbenchmarks/artifacts/* cuHadron/_coherent_ldst cuHadron/_mm_handoff
.env/bin/python -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py \
    python/test_hb_substitutions.py -rxXs -p no:cacheprovider 2>&1 | tail -25

echo "== (3) algorithms_check over the regenerated ScoR traces"
.env/bin/python design/algorithms_check.py 2>&1 | tail -40
echo "== done $(date -Is)"

#!/usr/bin/env bash
#SBATCH --job-name=t10-check
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=03:00:00
# T10 (CLAUDE.md section C): checks of the sidecar strength column on one GPU node, with the
# worktree's private runtime (t9_build.sh with W=<worktree>: collector in <W>/lib, RPATH ->
# <W>/sanalyzer/wt_install). Nothing in the main checkout is written; its runtime is only run.
#  (1) the default tool path (no YOSEMITE_HB_TRACE): main vs T10 runtime on two ScoR programs,
#      compared up to device addresses and dist histograms (setup/t5a_compare.norm);
#  (2) compatibility: strong_ldst_scopes.cu traced with a T10 sidecar by the INSTALLED engine
#      (main runtime, libsanalyzer 75f46012, which reads only the `ldst` lines) and by the T10
#      engine (strength column): hb_races and hb_races_sync_only must agree kernel by kernel,
#      and both equal the T10 oracle;
#  (3) the green set (CLAUDE.md A4), every trace re-recorded with the T10 runtime, then
#      test_host_hb.py (outside the green set);
#  (4) design/algorithms_check.py over the regenerated ScoR traces (oracle == Detect).
#   W=<worktree> sbatch -p rtx4060ti16g -x c54,c2 -o <W>/build_logs/t10-check-%j.log \
#       <W>/eval/baselines/setup/t10_check.sh
set -u
W=${W:?W=<the T10 worktree>}; A=/home/fzheng4/AccelProf
cd $W || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
export CUDA_HOME=/usr/local/cuda-13.3 CUDA_PATH=/usr/local/cuda-13.3
export PATH=/usr/local/cuda-13.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:/usr/local/cuda-13.3/compute-sanitizer:${LD_LIBRARY_PATH:-}
unset CUVEIN_STRONG_LDST
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader | head -1) HEAD=$(git -C $W rev-parse --short HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l)"
for rt in $A $W; do
  echo "runtime $rt collector $(sha256sum $rt/lib/libcompute_sanitizer.so | cut -c1-16) -> $(ldd $rt/lib/libcompute_sanitizer.so | grep sanalyzer | awk '{print $3}')"
done
echo "installed libsanalyzer $(sha256sum $A/build/sanalyzer/lib/libsanalyzer.so | cut -c1-16)  T10 libsanalyzer $(sha256sum $W/sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16)"
OUT=/mnt/beegfs/$USER/t10_check; rm -rf $OUT; mkdir -p $OUT

echo "== (1) default path, main vs t10"
for exe in ScoR/microbenchmarks/bin/race_interblock_none-lock_rtraw ScoR/microbenchmarks/bin/norace_interblock_atom; do
  base=$(basename $exe)
  for rt in main t10; do
    R=$A; [ $rt = t10 ] && R=$W
    D=$OUT/$base/default/$rt; mkdir -p $D; ln -s $A/$exe $D/$base
    ( cd $D && env -u YOSEMITE_HB_TRACE -u YOSEMITE_HB_MODE -u YOSEMITE_HB_NO_ENGINE \
        -u YOSEMITE_ATOMIC_SCOPE_FILE -u YOSEMITE_HB_STATS ACCEL_PROF_HOME=$R PATH=$R/bin:$PATH \
        accelprof -v -t pc_dependency_analysis -n 1 ./$base < /dev/null > stdout.txt 2>&1; echo "rc=$?" > rc.txt )
    d=$(ls -d $D/dependency_${base}_* 2>/dev/null | head -1); [ -n "$d" ] && mv "$d" $D/dump
  done
done
$PY - $OUT <<'EOF'
import os, sys
sys.path.insert(0, "eval/baselines/setup")
from t5a_compare import norm
root, bad = sys.argv[1], 0
for prog in sorted(p for p in os.listdir(root) if os.path.isdir(f"{root}/{p}/default")):
    da, db = f"{root}/{prog}/default/main/dump", f"{root}/{prog}/default/t10/dump"
    fa, fb = sorted(os.listdir(da)), sorted(os.listdir(db))
    same = fa == fb and all(norm(f"{da}/{f}") == norm(f"{db}/{f}") for f in fa)
    bad += not same
    print(f"{prog} default: main vs t10: {'IDENTICAL' if same else 'DIFFERENT'} up to device addresses and dist ({len(fa)} files)")
print("ALL IDENTICAL" if not bad else f"{bad} DIFFERENT")
EOF

echo "== (2) one T10 sidecar, installed engine vs T10 engine (strong_ldst_scopes)"
C=$OUT/compat; mkdir -p $C/ext
nvcc -arch=native -lineinfo --cudart shared python/testdata/strong_ldst_scopes.cu -o $C/strong_ldst_scopes
( cd $C/ext && cuobjdump -xelf all ../strong_ldst_scopes > /dev/null && \
  for cb in *.cubin; do nvdisasm -bbcfg -poff $cb > ${cb%.cubin}.dot; done && \
  $PY $W/python/atomic_scope_sidecar.py *.dot -o atomic_scope.txt )
grep -c "^# strength " $C/ext/atomic_scope.txt | sed 's/^/strength lines: /'
for rt in main t10; do
  R=$A; [ $rt = t10 ] && R=$W
  D=$C/$rt; mkdir -p $D; ln -s $C/strong_ldst_scopes $D/strong_ldst_scopes
  ( cd $D && YOSEMITE_HB_TRACE=1 YOSEMITE_ATOMIC_SCOPE_FILE=$C/ext/atomic_scope.txt \
      ACCEL_PROF_HOME=$R PATH=$R/bin:$PATH \
      accelprof -v -t pc_dependency_analysis -n 1 ./strong_ldst_scopes < /dev/null > stdout.txt 2>&1; echo "rc=$?" > rc.txt )
  d=$(ls -d $D/dependency_strong_ldst_scopes_* 2>/dev/null | head -1); [ -n "$d" ] && mv "$d" $D/dump
done
$PY - $C <<'EOF'
import glob, json, os, sys
sys.path.insert(0, "python")
import hb_oracle as ho, sync_dominance as sd
C = sys.argv[1]
key = lambda r: (r.get("a_pc"), r["b_pc"], r["kind"], r.get("class"), r["space"], r.get("dist"),
                 r.get("async"), r.get("count"))
dots = sorted(glob.glob(f"{C}/ext/*.dot"))
bad = 0
for f in sorted(os.listdir(f"{C}/t10/dump")):
    if not f.startswith("kernel_"):
        continue
    m, t = (json.load(open(f"{C}/{rt}/dump/{f}")) for rt in ("main", "t10"))
    rep = None
    for dot in dots:
        try:
            rep = ho.analyze(dot, f"{C}/t10/dump/{f}")
            break
        except sd.AlignmentError:
            continue
    km, kt, ko = ({key(r) for r in x} for x in (m.get("hb_races", []), t.get("hb_races", []), rep["races"]))
    ok = km == kt == ko and m.get("hb_races_sync_only") == t.get("hb_races_sync_only") == rep["races_sync_only"]
    bad += not ok
    cls = sorted({r["class"] for r in t.get("hb_races", [])})
    print(f"{t['kernel']['kernel_name']:48s} installed==t10==oracle: {ok}  classes {cls}")
print("ALL AGREE" if not bad else f"{bad} DISAGREE")
EOF

echo "== (3) green set (CLAUDE.md A4), T10 runtime"
rm -rf ScoR/microbenchmarks/artifacts/* cuHadron/_coherent_ldst cuHadron/_mm_handoff
$PY -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py \
    python/test_barrier_exit.py python/test_hb_substitutions.py python/test_cp_async.py \
    -rxXs -p no:cacheprovider -W ignore 2>&1 | tail -30
echo "== (3b) test_host_hb.py (outside the green set)"
$PY -m pytest python/test_host_hb.py -rxXs -p no:cacheprovider -W ignore 2>&1 | tail -5

echo "== (4) algorithms_check over the regenerated ScoR traces"
$PY design/algorithms_check.py 2>&1 | tail -40
echo "== done $(date -Is)"

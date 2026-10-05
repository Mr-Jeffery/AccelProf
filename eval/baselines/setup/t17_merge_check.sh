#!/usr/bin/env bash
#SBATCH --job-name=t17-merge-check
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=06:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t17-merge-check-%j.log
# T17 merge (cuVein b6c9055) on the INSTALLED runtime (setup/t17_install.sh):
#  (1) default tool path (no YOSEMITE_HB_TRACE): installed vs the previous runtime (mirror
#      /home/fzheng4/rt-prev-e527875d: libsanalyzer e527875d, the T1a collector objects,
#      fatbin a2d7368b) on two ScoR programs, up to device addresses and dist (t5a_compare.norm);
#  (2) HB dumps with YOSEMITE_HB_LATE_SEQ unset, vector-clock and scalar-clock: installed vs
#      previous (pre-T15), with T15's per-event key fields (bpos, lkey) dropped first;
#  (3) the green set (CLAUDE.md A4) + test_instance_gate.py, every trace re-recorded, then
#      test_instance_gate.py again on the fresh artifacts;
#  (4) P9-crs-cuda recorded afresh, both modes, analyzed by this checkout.
#   sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t17_merge_check.sh
set -u
A=/home/fzheng4/AccelProf; P=/home/fzheng4/rt-prev-e527875d
cd $A || exit 1
export CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
h() { sha256sum "$1" | cut -c1-16; }
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap,driver_version --format=csv,noheader) HEAD=$(git rev-parse --short HEAD) date=$(date -Is)"
for R in $A $P; do
  echo "runtime $R: collector $(h $R/lib/libcompute_sanitizer.so) -> $(ldd $R/lib/libcompute_sanitizer.so | grep sanalyzer | awk '{print $3}') $(h $(ldd $R/lib/libcompute_sanitizer.so | grep sanalyzer | awk '{print $3}')) fatbin $(h $R/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin)"
done

OUT=/mnt/beegfs/$USER/t17-merge-check; rm -rf $OUT; mkdir -p $OUT
for exe in ScoR/microbenchmarks/bin/race_interblock_none-lock_rtraw ScoR/microbenchmarks/bin/norace_interblock_atom; do
  base=$(basename $exe)
  for conf in default hb-vc hb-sc; do
    for rt in prev new; do
      R=$A; [ $rt = prev ] && R=$P
      D=$OUT/$base/$conf/$rt; mkdir -p $D; ln -s $A/$exe $D/$base
      envs=(env -u YOSEMITE_HB_TRACE -u YOSEMITE_HB_MODE -u YOSEMITE_HB_NO_ENGINE -u YOSEMITE_ATOMIC_SCOPE_FILE -u YOSEMITE_HB_STATS -u YOSEMITE_HB_LATE_SEQ)
      [ $conf != default ] && envs+=(YOSEMITE_HB_TRACE=1)
      [ $conf = hb-sc ] && envs+=(YOSEMITE_HB_MODE=scalar-clock)
      ( cd $D && "${envs[@]}" ACCEL_PROF_HOME=$R PATH=$R/bin:$PATH \
          accelprof -v -t pc_dependency_analysis -n 1 ./$base < /dev/null > stdout.txt 2>&1; echo "rc=$?" > rc.txt )
      d=$(ls -d $D/dependency_${base}_* 2>/dev/null | head -1); [ -n "$d" ] && mv "$d" $D/dump
    done
  done
done
$PY - $OUT <<'PYEOF'
import json, os, sys
sys.path.insert(0, "eval/baselines/setup")
from t5a_compare import norm
root, bad = sys.argv[1], 0
T15 = ("bpos", "lkey")
def strip(p, tmp):
    d = json.load(open(p))
    keys = set()
    for e in d.get("hb_events", []):
        for k in T15:
            if k in e:
                keys.add(k); e.pop(k)
    json.dump(d, open(tmp, "w"))
    return keys
for prog in sorted(os.listdir(root)):
    for conf in ("default", "hb-vc", "hb-sc"):
        da, db = f"{root}/{prog}/{conf}/prev/dump", f"{root}/{prog}/{conf}/new/dump"
        if not (os.path.isdir(da) and os.path.isdir(db)):
            print(f"{prog} {conf}: MISSING dump"); bad += 1; continue
        fa, fb = sorted(os.listdir(da)), sorted(os.listdir(db))
        same, dropped, raw = fa == fb, set(), True
        for f in fa if same else []:
            raw &= open(f"{da}/{f}", "rb").read() == open(f"{db}/{f}", "rb").read()
            ta, tb = f"{root}/.a.json", f"{root}/.b.json"
            if f.endswith(".json"):
                dropped |= strip(f"{da}/{f}", ta) | strip(f"{db}/{f}", tb)
                same &= norm(ta) == norm(tb)
            else:
                same &= norm(f"{da}/{f}") == norm(f"{db}/{f}")
        bad += not same
        print(f"{prog} {conf}: prev vs new: {'IDENTICAL' if same else 'DIFFERENT'} up to device addresses and dist"
              f"{' (and ' + ','.join(sorted(dropped)) + ')' if dropped else ''}; raw bytes {'equal' if raw else 'differ'} ({len(fa)} files)")
print("ALL IDENTICAL" if not bad else f"{bad} DIFFERENT")
PYEOF

echo "== (3) green set (installed runtime)"
export ACCEL_PROF_HOME=$A
rm -rf ScoR/microbenchmarks/artifacts/* cuHadron/_coherent_ldst cuHadron/_mm_handoff cuHadron/_gate_held cuHadron/_t12_*
$PY -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py \
    python/test_barrier_exit.py python/test_hb_substitutions.py python/test_cp_async.py python/test_instance_gate.py \
    -rfExXs --tb=line -p no:cacheprovider 2>&1 | grep -v "Warning\|setParseAction\|^$\|capture-warnings" | tail -12
echo "== (3b) test_instance_gate.py on the fresh artifacts"
$PY -m pytest python/test_instance_gate.py -q -p no:cacheprovider 2>&1 | tail -2

echo "== (4) P9-crs-cuda fresh, both modes"
TAG=t17-merge-crs; STORE=/mnt/beegfs/$USER/cuvein_traces/$TAG-2026-10-01
rm -rf $STORE $OUT/crs; mkdir -p $OUT/crs
T=$(date +%s)
BASELINE_TRACE_DIR=$STORE $PY eval/baselines/parallel.py run \
    --manifest eval/baselines/manifest.csv --id P9-crs-cuda --reps 1 --confirm \
    --timeout-floor 1200 --tag $TAG --results-dir $OUT/crs \
    --confirm-dir $OUT/crs/confirm 2>&1 | tail -3
echo "run+analyze: $(( $(date +%s) - T )) s"
cut -d, -f1,7,8,9,10,16,17 $OUT/crs/*.csv
echo "== done $(date -Is)"

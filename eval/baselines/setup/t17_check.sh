#!/usr/bin/env bash
#SBATCH --job-name=t17-check
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=02:00:00
#SBATCH --output=/home/fzheng4/wt-T17/build_logs/t17-check-%j.log
# T17 (rename, no value changes): (1) default tool path (no YOSEMITE_HB_TRACE), main runtime
# (live libsanalyzer e527875d = 7849a70) vs the T17 runtime, two ScoR programs, compared up
# to device addresses and dist histograms (t5a_compare.norm); (2) vector-clock dumps, same
# two programs, main vs T17, whole kernel JSON up to addresses, plus one YOSEMITE_HB_STATS run
# each (main writes hb_stats.engine, T17 hb_stats.hb_clock: same object otherwise);
# (3) the green set (CLAUDE.md A4 + test_instance_gate.py) with the worktree runtime.
#   sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t17_check.sh
set -u
W=${W:-/home/fzheng4/wt-T17}; A=/home/fzheng4/AccelProf
cd "$W" || exit 1
export CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$LD_LIBRARY_PATH
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader) HEAD=$(git -C "$W" rev-parse --short HEAD) dirty=$(git -C "$W" status --porcelain -uno | wc -l)"
for rt in $A $W; do
  echo "runtime $rt collector $(sha256sum $rt/lib/libcompute_sanitizer.so | cut -c1-16) -> $(ldd $rt/lib/libcompute_sanitizer.so | grep sanalyzer | awk '{print $3}') $(sha256sum $(ldd $rt/lib/libcompute_sanitizer.so | grep sanalyzer | awk '{print $3}') | cut -c1-16)"
done

OUT=/mnt/beegfs/$USER/t17-check; rm -rf $OUT; mkdir -p $OUT
for exe in ScoR/microbenchmarks/bin/race_interblock_none-lock_rtraw ScoR/microbenchmarks/bin/norace_interblock_atom; do
  base=$(basename $exe)
  side=$OUT/$base/sidecar.txt; mkdir -p $OUT/$base
  for conf in default hb-vc hb-stats; do
    for rt in main t17; do
      R=$A; [ $rt = t17 ] && R=$W
      D=$OUT/$base/$conf/$rt; mkdir -p $D; ln -s $A/$exe $D/$base
      envs=(env -u YOSEMITE_HB_TRACE -u YOSEMITE_HB_MODE -u YOSEMITE_HB_NO_ENGINE -u YOSEMITE_ATOMIC_SCOPE_FILE -u YOSEMITE_HB_STATS)
      [ $conf != default ] && envs+=(YOSEMITE_HB_TRACE=1)
      [ $conf = hb-stats ] && envs+=(YOSEMITE_HB_STATS=1)
      ( cd $D && "${envs[@]}" ACCEL_PROF_HOME=$R PATH=$R/bin:$PATH \
          accelprof -v -t pc_dependency_analysis -n 1 ./$base < /dev/null > stdout.txt 2>&1; echo "rc=$?" > rc.txt )
      d=$(ls -d $D/dependency_${base}_* 2>/dev/null | head -1); [ -n "$d" ] && mv "$d" $D/dump
    done
  done
done
.env/bin/python - $OUT <<'PYEOF'
import json, os, sys
sys.path.insert(0, "eval/baselines/setup")
from t5a_compare import norm
root, bad = sys.argv[1], 0
for prog in sorted(os.listdir(root)):
    for conf in ("default", "hb-vc", "hb-stats"):
        da, db = f"{root}/{prog}/{conf}/main/dump", f"{root}/{prog}/{conf}/t17/dump"
        fa, fb = sorted(os.listdir(da)), sorted(os.listdir(db))
        if conf == "hb-stats":      # rename the one key, then compare everything but RSS
            def ld(p):
                d = json.load(open(p))
                s = d.get("hb_stats")
                if s is not None:
                    s["hb_clock"] = s.pop("hb_clock", s.pop("engine", None))
                    for k in ("rss_kb", "hwm_kb"):
                        s.pop(k, None)
                    keys = sorted(s)
                    d["hb_stats"] = s
                return d, (keys if s is not None else None)
            same = fa == fb
            for f in fa if same else []:
                if not f.startswith("kernel_"):
                    same &= norm(f"{da}/{f}") == norm(f"{db}/{f}"); continue
                (x, kx), (y, ky) = ld(f"{da}/{f}"), ld(f"{db}/{f}")
                raw_a = json.load(open(f"{da}/{f}")).get("hb_stats", {})
                raw_b = json.load(open(f"{db}/{f}")).get("hb_stats", {})
                print(f"  {prog} {f}: main hb_stats keys {sorted(raw_a)} | t17 {sorted(raw_b)}")
                tmp_a, tmp_b = f"{root}/.a.json", f"{root}/.b.json"
                json.dump(x, open(tmp_a, "w")); json.dump(y, open(tmp_b, "w"))
                same &= norm(tmp_a) == norm(tmp_b)
        else:
            same = fa == fb and all(norm(f"{da}/{f}") == norm(f"{db}/{f}") for f in fa)
        bad += not same
        print(f"{prog} {conf}: main vs t17: {'IDENTICAL' if same else 'DIFFERENT'} up to device addresses and dist ({len(fa)} files)")
print("ALL IDENTICAL" if not bad else f"{bad} DIFFERENT")
PYEOF
for rt in main t17; do
  echo "stderr labels ($rt): $(cat $OUT/*/hb-stats/$rt/*.accelprof.log 2>/dev/null | grep -o '^\[HB_[A-Z]*\]' | sort | uniq -c | tr '\n' ' ')"
done

echo "== (3) green set (worktree runtime)"
export ACCEL_PROF_HOME=$W
rm -rf ScoR/microbenchmarks/artifacts/* cuHadron/_coherent_ldst cuHadron/_mm_handoff cuHadron/_gate_held cuHadron/_t12_*
.env/bin/python -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py \
    python/test_barrier_exit.py python/test_hb_substitutions.py python/test_cp_async.py python/test_instance_gate.py \
    -rfExXs --tb=line -p no:cacheprovider 2>&1 | grep -v "Warning\|setParseAction\|^$\|capture-warnings" | tail -60

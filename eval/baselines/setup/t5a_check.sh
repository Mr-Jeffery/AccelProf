#!/usr/bin/env bash
#SBATCH --job-name=t5a-check
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:30:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t5a-check-%j.log
# T5a (eval/MEMORY_FOOTPRINT.md): (1) the YOSEMITE_HB_STATS hook changes nothing when
# unset -- the default tool path and the vector-clock dump of two run-to-run deterministic
# ScoR programs (eval/MODE_RENAME.md section 3.2), installed library (main runtime) vs the
# T5a worktree runtime, byte for byte; with YOSEMITE_HB_STATS=1 the dump differs from the
# unset run only by the added "hb_stats" field. (2) the green set (Claude.md A4) from the
# worktree runtime (getall.sh records every trace with ACCEL_PROF_HOME = the worktree).
# Comparison: setup/t5a_compare.py (up to device addresses and per-edge dist histograms).
#   PIN8G=1 sbatch -p rtx4060ti8g -w c20 eval/baselines/setup/t5a_check.sh
set -u
W=/home/fzheng4/wt-T5a; A=/home/fzheng4/AccelProf
cd $W || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
[ -n "${PIN8G:-}" ] && source eval/baselines/setup/pin8g.sh
lib() { .env/bin/python -c "import sys; sys.path.insert(0,'$W/python'); import hb_modes; print(hb_modes.engine_library('$1'))"; }
echo "host=$(hostname) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap --format=csv,noheader)"
for rt in $A $W; do L=$(lib $rt); echo "runtime $rt engine-lib $L $(sha256sum $L | cut -c1-16)"; done
OUT=/mnt/beegfs/$USER/t5a_check; rm -rf $OUT; mkdir -p $OUT
for exe in ScoR/microbenchmarks/bin/race_interblock_none-lock_rtraw ScoR/microbenchmarks/bin/norace_interblock_atom; do
  base=$(basename $exe)
  for conf in default hb-vc hb-vc-stats; do
    for rt in main t5a; do
      [ $conf = hb-vc-stats ] && [ $rt = main ] && continue
      R=$A; [ $rt = t5a ] && R=$W
      D=$OUT/$base/$conf/$rt; mkdir -p $D; ln -s $A/$exe $D/$base
      E=(env -u YOSEMITE_HB_TRACE -u YOSEMITE_HB_MODE -u YOSEMITE_HB_NO_ENGINE -u YOSEMITE_ATOMIC_SCOPE_FILE -u YOSEMITE_HB_STATS ACCEL_PROF_HOME=$R PATH=$R/bin:$PATH)
      case $conf in hb-vc) E+=(YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=vector-clock);;
                    hb-vc-stats) E+=(YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=vector-clock YOSEMITE_HB_STATS=1);; esac
      ( cd $D && "${E[@]}" accelprof -v -t pc_dependency_analysis -n 1 ./$base < /dev/null > stdout.txt 2>&1; echo "rc=$?" > rc.txt )
      d=$(ls -d $D/dependency_${base}_* 2>/dev/null | head -1); [ -n "$d" ] && mv "$d" $D/dump
    done
  done
done
# device allocation addresses move run to run (two runs of ONE library differ the same way)
.env/bin/python eval/baselines/setup/t5a_compare.py $OUT
echo "== green set (worktree runtime)"
rm -rf ScoR/microbenchmarks/artifacts/*
.env/bin/python -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py -rxXs 2>&1 | tail -6
echo "== done $(date -Is)"

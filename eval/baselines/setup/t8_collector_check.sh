#!/usr/bin/env bash
#SBATCH --job-name=t8-coll
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:00:00
#SBATCH --output=/home/fzheng4/wt-T8/eval/baselines/setup/t8_check/coll-%x-%j.log
# T8 collector check. Records the collector's output for three programs, twice each,
# under whatever libsanalyzer.so is installed now (PHASE=before: the pre-T8 library;
# PHASE=after: the T8 library), in five configurations:
#   default         no YOSEMITE_HB_TRACE              -> must be byte-identical before/after
#   hb-vc           YOSEMITE_HB_TRACE=1 (+ HB_MODE=vector-clock after)
#   hb-sc           YOSEMITE_HB_TRACE=1 + NO_ENGINE=1 before / HB_MODE=scalar-clock after
#   hb-legacy       YOSEMITE_HB_TRACE=1 YOSEMITE_HB_NO_ENGINE=1 (after only: deprecation path)
#   hb-bogus        YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=bogus   (after only: warning path)
#   PHASE=before|after PIN8G=1 [RT=<runtime checkout>] sbatch -p rtx4060ti8g -w c20 t8_collector_check.sh
# RT (default the main checkout) is the ACCEL_PROF_HOME whose bin/accelprof and
# lib/libcompute_sanitizer.so run: the T8 worktree, whose lib/ holds a private collector
# relinked against the T8 libsanalyzer.so (sanalyzer/t8_relink.sh), tests the new library
# without touching the shared build/sanalyzer/lib.
set -u
PHASE=${PHASE:?before|after}
A=${RT:-/home/fzheng4/AccelProf}
cd $A || exit 1
export ACCEL_PROF_HOME=$A
source eval/baselines/gpu_env.sh
[ -n "${PIN8G:-}" ] && source eval/baselines/setup/pin8g.sh
OUT=/mnt/beegfs/$USER/t8_check/$PHASE; rm -rf "$OUT"; mkdir -p "$OUT"
LIB=$($A/.env/bin/python -c "import sys; sys.path.insert(0, '$A/python'); import hb_modes; print(hb_modes.engine_library('$A'))")
echo "host=$(hostname) phase=$PHASE runtime=$A engine-lib=$LIB sha256=$(sha256sum $LIB | cut -c1-16) $(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap --format=csv,noheader)"
PROGS="ScoR/microbenchmarks/bin/race_interblock_none-lock_rtraw eval/baselines/bin/P4/1dconv_norace ScoR/microbenchmarks/bin/norace_interblock_atom"
for exe in $PROGS; do
  base=$(basename $exe)
  stdin=/dev/null; [ "$base" = 1dconv_norace ] && stdin=$A/eval/baselines/inputs/1dconv.small.in
  confs="default hb-vc hb-sc"; [ "$PHASE" = after ] && confs="$confs hb-legacy hb-bogus"
  for conf in $confs; do
    for rep in 1 2; do
      W=$OUT/$base/$conf/rep$rep; mkdir -p $W; ln -s $A/$exe $W/$base
      E=(env -u YOSEMITE_HB_TRACE -u YOSEMITE_HB_MODE -u YOSEMITE_HB_NO_ENGINE -u YOSEMITE_ATOMIC_SCOPE_FILE)
      case $conf in
        default)   ;;
        hb-vc)     E+=(YOSEMITE_HB_TRACE=1); [ "$PHASE" = after ] && E+=(YOSEMITE_HB_MODE=vector-clock) ;;
        hb-sc)     E+=(YOSEMITE_HB_TRACE=1); if [ "$PHASE" = after ]; then E+=(YOSEMITE_HB_MODE=scalar-clock); else E+=(YOSEMITE_HB_NO_ENGINE=1); fi ;;
        hb-legacy) E+=(YOSEMITE_HB_TRACE=1 YOSEMITE_HB_NO_ENGINE=1) ;;
        hb-bogus)  E+=(YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=bogus) ;;
      esac
      ( cd $W && "${E[@]}" accelprof -v -t pc_dependency_analysis -n 1 ./$base < $stdin > $W/stdout.txt 2> $W/stderr.txt; echo "rc=$?" > $W/rc.txt )
      d=$(ls -d $W/dependency_${base}_* 2>/dev/null | head -1)
      [ -n "$d" ] && mv "$d" $W/dump
      echo "$base $conf rep$rep $(cat $W/rc.txt) files=$(ls $W/dump 2>/dev/null | wc -l) $(grep -h '\[cuVein\]' $W/stderr.txt $W/stdout.txt $W/*.log 2>/dev/null | head -2 | tr '\n' ' ')"
    done
  done
done
echo "== done $(date -Is)"

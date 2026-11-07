#!/usr/bin/env bash
#SBATCH --job-name=t26-fix
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c2,c21,c23,c37,c46,c54
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
# T26 step 4, fixtures: every python/testdata/*.cu (+ scale/) built for sm_89 and recorded in
# collector-only mode on this node five ways (I0 installed -n 1; Ic installed -n 1 through the capture
# shim; A new -n 1; B new -n 16; Bc new -n 16 through the shim); then both captured streams replayed
# through the installed library (-n 1) and the new one (N=1, N=16, N=16 with every drain threaded).
# Comparisons (co_json_diff.py): same stream -- rI(Ic) == Ic live (replay fidelity), r1/r16/r16t(s) ==
# rI(s) for s in Ic, Bc, and Bc live == rI(Bc); live -- A and B against I0 (the brief's comparison: two
# executions, equal where the program's record stream is schedule-independent).
#   [FIX="a.cu b.cu"] sbatch -o <W>/eval/x_logs/t26-fix-%j.log <W>/eval/baselines/setup/t26_parity/fixtures.sh
set -u
W=${W:-/home/fzheng4/wt/sharded-pcdep}
source $W/eval/baselines/setup/t26_parity/common.sh
gpu=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader 2>&1 | head -1)
echo "host=$(hostname) gpu=[$gpu] cpu=[$(lscpu | sed -n 's/^Model name: *//p')] nproc=$(nproc) job=${SLURM_JOB_ID:-} $(date -Is)"
mkcaph
runtime_line
ROOT=/mnt/local/$USER/t26-fix-${SLURM_JOB_ID:-x}
mkdir -p $ROOT 2>/dev/null && touch $ROOT/.w 2>/dev/null || ROOT=/tmp/$USER-t26-fix-${SLURM_JOB_ID:-x}
mkdir -p $ROOT; echo "work=$ROOT ($(df -h $ROOT | tail -1 | awk '{print $4}') free)"
KEEP=${KEEP:-/mnt/beegfs/$USER/t26/fix-${SLURM_JOB_ID:-x}}
mkdir -p $KEEP
srcs=${FIX:-$(ls $W/python/testdata/*.cu $W/python/testdata/scale/*.cu)}
TO=${TO:-900}
live() {   # live <name> <cfg> <home> <N> [cap real lib]
  local name=$1 cfg=$2 home=$3 n=$4 real=${5:-}
  local d=$ROOT/$name/$cfg; mkdir -p $d; ln -sf $ROOT/$name/bin/$name $d/$name
  local t0=$(date +%s.%N)
  ( cd $d && env ACCEL_PROF_HOME=$home PATH=$home/bin:$PATH ${real:+CAP_REAL_LIB=$real CAP_DIR=$d} \
      timeout $TO accelprof -t pc_dependency_analysis -n $n ./$name > run.out 2> run.err; echo "rc=$?" >> run.err )
  printf "  live %-3s %s %.1fs\n" $cfg "$(tail -1 $d/run.err)" $(echo "$(date +%s.%N) - $t0" | bc)
}
for src in $srcs; do
  name=$(basename $src .cu)
  mkdir -p $ROOT/$name/bin
  if ! nvcc -arch=sm_89 -lineinfo --cudart shared -o $ROOT/$name/bin/$name $src > $ROOT/$name/nvcc.log 2>&1; then
    echo "== $name: nvcc failed: $(tail -2 $ROOT/$name/nvcc.log | tr '\n' ' ')"; continue
  fi
  echo "== $name"
  live $name I0 $INST 1
  live $name Ic $CAPH 1 $LIB_INST
  live $name A $NEWH 1
  live $name B $NEWH 16
  live $name Bc $CAPH 16 $LIB_NEW
  for s in Ic Bc; do
    cap=$(ls $ROOT/$name/$s/cap.*.bin 2>/dev/null | head -1)
    [ -n "$cap" ] || { echo "  $s: no capture"; continue; }
    echo "  $s capture $(stat -c %s $cap) bytes"
    replay $cap $ROOT/$name/r-$s-inst inst 1
    replay $cap $ROOT/$name/r-$s-n1 new 1
    replay $cap $ROOT/$name/r-$s-n16 new 16
    replay $cap $ROOT/$name/r-$s-n16t new 16 0
    for r in inst n1 n16 n16t; do grep -h "t26_replay\]\|rc=" $ROOT/$name/r-$s-$r/replay.err | tr '\n' ' ' | sed "s|^|  replay $s $r: |"; echo; done
  done
  cmpk() { $PY $DIFF "$(depdir $ROOT/$name/$1)" "$(depdir $ROOT/$name/$2)" --label "$name $3" --quiet; }
  cmpk r-Ic-inst Ic "same-stream fidelity: replay(Ic, installed) vs Ic live"
  cmpk r-Bc-n16 Bc "same-stream fidelity: replay(Bc, new N=16) vs Bc live"
  for s in Ic Bc; do
    for r in n1 n16 n16t; do cmpk r-$s-inst r-$s-$r "same-stream parity: stream $s installed -n1 vs new $r"; done
  done
  cmpk r-Bc-inst Bc "same-stream parity: Bc live (new N=16) vs installed -n1 on its records"
  cmpk I0 A "live: installed -n1 (I0) vs new N=1 (A)"
  cmpk I0 B "live: installed -n1 (I0) vs new N=16 (B)"
  cmpk I0 Ic "live control: installed -n1 (I0) vs installed -n1 again (Ic)"
  mkdir -p $KEEP/$name
  for c in I0 Ic A B Bc r-Ic-inst r-Ic-n1 r-Ic-n16 r-Ic-n16t r-Bc-inst r-Bc-n1 r-Bc-n16 r-Bc-n16t; do
    dp=$(depdir $ROOT/$name/$c); [ -n "$dp" ] && { mkdir -p $KEEP/$name/$c; cp $dp/kernel_*.json $KEEP/$name/$c/ 2>/dev/null; }
  done
done
rm -rf $ROOT
echo "== done $(date -Is)"

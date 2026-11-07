#!/usr/bin/env bash
#SBATCH --job-name=t26-synth
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --time=02:00:00
# T26 parity, synthetic streams (synth.py): each replayed through the installed library at -n 1 and the
# new one at N = 1, 2, 3, 7, 16, 64 and at 16 with every drain threaded, under a 32-object shared pool
# with 4,096-byte objects (pool misses, object reuse, offsets past the object) and under the default
# pool; every output compared with the installed library's (co_json_diff.py). CPU only.
#   [SEEDS="1 2 3"] sbatch -o <W>/eval/x_logs/t26-synth-%j.log <W>/eval/baselines/setup/t26_parity/synth.sh
set -u
W=${W:-/home/fzheng4/wt/sharded-pcdep}
source $W/eval/baselines/setup/t26_parity/common.sh
echo "host=$(hostname) cpu=[$(lscpu | sed -n 's/^Model name: *//p')] nproc=$(nproc) job=${SLURM_JOB_ID:-} $(date -Is)"
mkcaph; runtime_line
ROOT=/tmp/$USER-t26-synth-${SLURM_JOB_ID:-x}; mkdir -p $ROOT
fail=0; total=0
for seed in ${SEEDS:-1 2 3 4 5 6}; do
  $PY $W/eval/baselines/setup/t26_parity/synth.py $ROOT/s$seed.bin --seed $seed --kernels ${KERNELS:-5} --records ${RECORDS:-150000}
  echo "== seed $seed: $(stat -c %s $ROOT/s$seed.bin) bytes"
  for pool in small default; do
    if [ $pool = small ]; then
      export REPLAY_ENV="YOSEMITE_GPU_SM_COUNT=1 YOSEMITE_GPU_MAX_ACTIVE_BLOCKS_PER_SM=1 YOSEMITE_GPU_MAX_SHARED_MEMORY_PER_BLOCK=4096"
    else
      export REPLAY_ENV=""
    fi
    D=$ROOT/s$seed-$pool
    replay $ROOT/s$seed.bin $D/inst inst 1
    grep -h "t26_replay\]\|rc=" $D/inst/replay.err | tr '\n' ' ' | sed "s|^|  $pool inst n=1: |"; echo
    for cfg in 1 2 3 7 16 64 16t; do
      n=${cfg%t}; im=""; [ "$cfg" != "$n" ] && im=0
      replay $ROOT/s$seed.bin $D/n$cfg new $n $im
      total=$((total + 1))
      $PY $DIFF "$(depdir $D/inst)" "$(depdir $D/n$cfg)" --label "seed $seed pool $pool: installed -n1 vs new N=$cfg" --quiet || fail=$((fail + 1))
    done
    /usr/bin/grep -c "unknown memory type" $D/inst/replay.out | sed "s|^|  unknown-type lines (installed): |"
    /usr/bin/grep -c "unknown memory type" $D/n16/replay.out | sed "s|^|  unknown-type lines (new N=16): |"
  done
done
echo "== synth: $total comparisons, $fail differ"
rm -rf $ROOT
echo "== done $(date -Is)"

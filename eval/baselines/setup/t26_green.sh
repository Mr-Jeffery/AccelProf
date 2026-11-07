#!/usr/bin/env bash
#SBATCH --job-name=t26-green
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c2,c21,c23,c37,c46,c54
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
# T26 step 4: the green set on the worktree runtime (ACCEL_PROF_HOME=W: lib -> stage-t26/rt-lib) --
# CLAUDE.md A4's seven files + test_collector_only.py (one pytest run, ScoR artifacts wiped first, as A4
# says), then test_no_dump.py, then test_co_chain.py from origin/eval/co-chain-b (C6b's verdict-layer
# test, CPU only: it reads recorded fixtures, not the runtime; run from a read-only checkout of that
# branch, ~/wt/co-chain-b-ro). The tests call `accelprof -n 1`; WORKERS=<N> re-runs the GPU files
# with every accelprof call at N workers (a wrapper bin/ first on PATH rewrites -n).
#   [WORKERS=16] sbatch -o <W>/eval/x_logs/t26-green-%j.log <W>/eval/baselines/setup/t26_green.sh
set -u
W=${W:-/home/fzheng4/wt/sharded-pcdep}; CC=${CC:-/home/fzheng4/wt/co-chain-b-ro}
source $W/eval/baselines/setup/t26_parity/common.sh
gpu=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader 2>&1 | head -1)
echo "host=$(hostname) gpu=[$gpu] cpu=[$(lscpu | sed -n 's/^Model name: *//p')] nproc=$(nproc) job=${SLURM_JOB_ID:-} $(date -Is)"
mkcaph; runtime_line
cd $W
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
export PATH=$W/bin:$PATH
if [ -n "${WORKERS:-}" ]; then
  WB=/tmp/$USER-t26-green-bin-${SLURM_JOB_ID:-x}; mkdir -p $WB
  cat > $WB/accelprof <<EOF
#!/bin/bash
# T26 green set at N workers: rewrite "-n <k>" to "-n $WORKERS"
args=(); while [ \$# -gt 0 ]; do if [ "\$1" = "-n" ]; then args+=(-n $WORKERS); shift 2; else args+=("\$1"); shift; fi; done
exec $W/bin/accelprof "\${args[@]}"
EOF
  chmod +x $WB/accelprof; export PATH=$WB:$PATH
  echo "accelprof -n rewritten to -n $WORKERS ($(which accelprof))"
fi
rm -rf ScoR/microbenchmarks/artifacts/*
echo "== A4 seven + test_collector_only.py $(date -Is)"
$PY -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py \
    python/test_barrier_exit.py python/test_hb_substitutions.py python/test_cp_async.py \
    python/test_collector_only.py -q -p no:cacheprovider 2>&1 | tail -15
echo "== test_no_dump.py $(date -Is)"
$PY -m pytest python/test_no_dump.py -q -p no:cacheprovider 2>&1 | tail -6
if [ -z "${WORKERS:-}" ]; then
  echo "== test_co_chain.py from $(git -C $CC log --oneline -1) $(date -Is)"
  ( cd $CC && CUVEIN_HOME=$CC ACCEL_PROF_HOME=$CC $PY -m pytest python/test_co_chain.py -q -p no:cacheprovider 2>&1 | tail -6 )
fi
echo "== done $(date -Is)"

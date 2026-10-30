#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH -c 16
#SBATCH -t 03:00:00
#SBATCH -x c0,c1,c22,c23,c34,c46
#SBATCH -J x7a-green
#SBATCH -o /home/fzheng4/wt-x7a/eval/x_logs/x7a-green-%j.log
# X7 green set on a no-GPU `normal` node, in the worktree itself (not edited while this runs).
# As T23's p_t23_test.sh: the worktree's private copy of ScoR keeps its stored artifacts (they
# are not wiped: nothing can regenerate them without a GPU) and nvcc is a stub that fails as on
# a node without a GPU, so every on-demand GPU build skips alike on every node.
W=/home/fzheng4/wt-x7a
cd $W || exit 1
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
STUB=$(mktemp -d /tmp/x7a-stub-XXXXXX); trap 'rm -rf "$STUB"' EXIT
printf '#!/bin/sh\necho "nvcc fatal : X7 stub: no GPU on a normal node" >&2\nexit 1\n' > $STUB/nvcc
chmod +x $STUB/nvcc; export PATH="$STUB:$PATH"
echo "host=$(hostname) nproc=$(nproc) date=$(date -Is)"
echo "rev=$(git rev-parse --short=12 HEAD) dirty=$(git status --porcelain -uno | wc -l) ($(git log -1 --format=%s))"
echo "gpu: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>&1 | head -2 | tr '\n' ' ')"
echo "libsanalyzer sha256: $(sha256sum build/sanalyzer/lib/libsanalyzer.so | cut -c1-16)"
echo "scor artifacts: $(ls ScoR/microbenchmarks/artifacts | wc -l)"
PYT=".env/bin/python -m pytest -q -p no:cacheprovider -rfEs"
run() { echo; echo "=== $1"; shift; $PYT "$@" 2>&1 | grep -v "Warning\|setParseAction\|^  \|^$\|warnings summary\|Docs: https" | tail -60; echo "rc=${PIPESTATUS[0]}"; }
run "A4 green set" python/test_sync_dominance.py python/test_barrier_soundness.py python/test_coherent_ldst.py \
    python/test_atomic_memory_model.py python/test_barrier_exit.py python/test_hb_substitutions.py python/test_cp_async.py
run "gate (ScoR-parametrised)" python/test_instance_gate.py
run "test_no_dump.py" python/test_no_dump.py
run "test_collector_only.py" python/test_collector_only.py
run "test_verdict_parallel.py (X7)" python/test_verdict_parallel.py
echo "end $(date -Is)"

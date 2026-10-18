#!/usr/bin/env bash
#SBATCH --job-name=t23-test
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=02:00:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/wt-t23/eval/x_logs/t23-test-%j.log
# T23: pytest in the task worktree on a no-GPU `normal` node. The tests read the CFG/trace
# files committed under python/testdata and the worktree's private copy of ScoR (the stored
# artifacts, never regenerated here: the GPU halves skip). Nothing is recorded.
#   TESTS="python/test_x.py::name ..."   (default: the A4 green set + test_instance_gate.py)
#   LABEL=<free text echoed into the log>
W=${W:-/home/fzheng4/wt-t23}
cd "$W" || exit 1
echo "host=$(hostname) date=$(date -Is) label=${LABEL:-}"
echo "HEAD=$(git rev-parse HEAD) branch=$(git branch --show-current)"
git status --short | grep -v -E '^\?\? (build|lib|nv-compute/lib|ScoR)$' | head -20
echo "python: $(.env/bin/python --version 2>&1)"
env | grep -E '^(CUVEIN_|YOSEMITE_)' | sort
DEFAULT="python/test_sync_dominance.py python/test_barrier_soundness.py python/test_coherent_ldst.py \
python/test_atomic_memory_model.py python/test_barrier_exit.py python/test_hb_substitutions.py \
python/test_cp_async.py python/test_instance_gate.py"
# shellcheck disable=SC2086
.env/bin/python -m pytest ${TESTS:-$DEFAULT} -q -p no:cacheprovider -rfEs ${PYTEST_EXTRA:-}
echo "pytest rc=$?"

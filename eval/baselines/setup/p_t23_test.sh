#!/usr/bin/env bash
#SBATCH --job-name=t23-test
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=02:00:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/wt-t23/eval/x_logs/t23-test-%j.log
# T23: pytest on an exported revision of the task worktree, on a no-GPU `normal` node. The
# revision's python/, design/ and getall.sh are exported with `git archive` into a node-local
# directory (so a running job never sees later edits of the worktree), next to a private copy
# of the worktree's ScoR (the stored artifacts: never regenerated here). nvcc is replaced by a
# stub that fails the way a node without a GPU does, so every on-demand GPU build skips on every
# node alike (some `normal` nodes have no nvcc at all, which the tests turn into an error
# instead of a skip). Nothing is recorded.
#   REV=<git rev>                         default HEAD
#   TESTS="python/test_x.py::name ..."    default: the A4 green set + test_instance_gate.py
#   LABEL=<free text echoed into the log>
W=${W:-/home/fzheng4/wt-t23}
REV=${REV:-HEAD}
cd "$W" || exit 1
echo "host=$(hostname) date=$(date -Is) label=${LABEL:-}"
echo "rev=$(git rev-parse "$REV") ($(git log -1 --format=%s "$REV"))"
T=$(mktemp -d /tmp/t23-run-XXXXXX)
trap 'rm -rf "$T"' EXIT
git archive "$REV" python design getall.sh | tar -x -C "$T"
cp -r "$W/ScoR" "$T/ScoR"
ln -s "$W/.env" "$T/.env"
mkdir "$T/stub"
printf '#!/bin/sh\necho "nvcc fatal : T23 stub: no GPU on a normal node" >&2\nexit 1\n' > "$T/stub/nvcc"
chmod +x "$T/stub/nvcc"
export PATH="$T/stub:$PATH"
cd "$T" || exit 1
echo "python: $(.env/bin/python --version 2>&1)"
env | grep -E '^(CUVEIN_|YOSEMITE_)' | sort
DEFAULT="python/test_sync_dominance.py python/test_barrier_soundness.py python/test_coherent_ldst.py \
python/test_atomic_memory_model.py python/test_barrier_exit.py python/test_hb_substitutions.py \
python/test_cp_async.py python/test_instance_gate.py"
# shellcheck disable=SC2086
.env/bin/python -m pytest ${TESTS:-$DEFAULT} -q -p no:cacheprovider -rfEs ${PYTEST_EXTRA:-}
echo "pytest rc=$?"

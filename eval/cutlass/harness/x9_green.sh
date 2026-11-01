#!/bin/bash
#SBATCH --job-name=x9-green
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1 --exclusive
#SBATCH --time=03:00:00
#SBATCH --exclude=c0,c1,c2,c21,c22,c23,c34,c37,c46,c54
#SBATCH --output=/home/fzheng4/wt-x9/eval/x_logs/x9-green-%j.log
# X9 step 0b: python/test_co_offline.py + test_collector_only.py and the green set (merge_check.sh (1a)-(1c)'s file list),
# this branch's python/ (eval/co-offline 763bc5c) against the installed runtime f551ca0. On a GPU node, not `normal`: the
# green set builds and records GPU fixtures (C4 ran it on c24, rtx4060ti16g).
source /home/fzheng4/wt-x9/eval/cutlass/harness/x9_env.sh || exit $?
IDX=$(nvidia-smi --query-gpu=index,compute_cap --format=csv,noheader | awk -F', *' '$2=="8.9"{print $1}')
export CUDA_VISIBLE_DEVICES=$IDX
echo "gpu=$(nvidia-smi -i $IDX --query-gpu=name,compute_cap,driver_version --format=csv,noheader)"
cd $W || exit 1
rm -rf ScoR/microbenchmarks/artifacts/* cuHadron/_coherent_ldst cuHadron/_mm_handoff cuHadron/_gate_held cuHadron/_t12_*
echo "== test_co_offline.py + test_collector_only.py"
$PY -m pytest python/test_co_offline.py python/test_collector_only.py -q -rfExXs -p no:cacheprovider -W ignore 2>&1 | tail -8
echo "== (1a) green set"
$PY -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py \
    python/test_coherent_ldst.py python/test_atomic_memory_model.py \
    python/test_barrier_exit.py python/test_hb_substitutions.py python/test_cp_async.py python/test_instance_gate.py \
    python/test_syncwarp.py -q -rfExXs --tb=short -p no:cacheprovider -W ignore 2>&1 | tail -15
echo "== (1b) test_instance_gate.py alone"
$PY -m pytest python/test_instance_gate.py -q -p no:cacheprovider -W ignore 2>&1 | tail -3
echo "== (1c) test_no_dump.py"
$PY -m pytest python/test_no_dump.py -q -rfExXs -p no:cacheprovider -W ignore 2>&1 | tail -5
echo "== done $(date -Is)"

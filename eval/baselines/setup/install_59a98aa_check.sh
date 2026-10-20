#!/usr/bin/env bash
# Checks for the 59a98aa install (T22 cont. + T23): merge_check.sh (green set + gate + test_no_dump,
# then the no-dump spot check) on the installed runtime, then T22 cont.s python/test_sync_shapes.py.
#   W=<checkout> sbatch -p rtx4060ti16g ... eval/baselines/setup/install_59a98aa_check.sh
set -u
W=${W:?}
for d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do [ -d $d ] || { echo "ABORT on $(hostname): $d missing"; exit 3; }; done
bash $W/eval/baselines/setup/merge_check.sh
cd $W; source eval/baselines/gpu_env.sh; export PATH=/usr/local/cuda-13.3/bin:$PATH
echo "== (3) test_sync_shapes.py"
$PY -m pytest python/test_sync_shapes.py -q -rfExXs -p no:cacheprovider 2>&1 | tail -6
echo "== check done $(date -Is)"

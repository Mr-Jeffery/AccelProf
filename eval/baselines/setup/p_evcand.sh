#!/usr/bin/env bash
#SBATCH --job-name=cv-evcand
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c54
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --array=0-31
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/evcand-%A_%a.log
# Re-run of the labelled sets P1-P6 on the detector with event-stream candidates + the R3
# past-release gate (eval/FP_DIAGNOSIS.md), BOTH modes in one job (collect_one wipes
# <store>/<id>, so split per-mode jobs would clobber each other). EVERY trace is KEPT on
# BeeGFS (/mnt/beegfs: compute nodes only, no RAID, NOT backed up) so later detector
# revisions are re-scored with `parallel.py analyze` on identical traces (p_evcand_base.sh).
# Everything that matters still lands in home: shard csvs -> eval/results/evcand/,
# confirmation details -> confirm_evcand/, FP/FN/ERROR/TIMEOUT traces -> traces_keep_evcand/.
# manifest pinned to the snapshot this re-run was sharded with (the live manifest.csv changes)
# The 2026-09-20 run of this script used `--keep-all --keep-all-cap-gb 20`: parallel.py deleted the
# kernel JSONs of every program above 20 GB (meta.trace_dropped). T0 made keep-all the default
# with no cap; the dropped programs were re-collected into cuvein_traces/full-2026-09-22 (eval/STORAGE.md).
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
mkdir -p /mnt/beegfs/$USER && chmod 700 /mnt/beegfs/$USER
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/evcand
$PY eval/baselines/parallel.py run --manifest eval/baselines/setup/manifest.evcand.csv --pset P1,P2,P3,P4,P5,P6 \
    --shard ${SLURM_ARRAY_TASK_ID}/32 --confirm --tag evcand \
    --results-dir /home/fzheng4/AccelProf/eval/results/evcand \
    --confirm-dir /home/fzheng4/AccelProf/eval/baselines/confirm_evcand \
    --keep-mismatch /home/fzheng4/AccelProf/eval/baselines/traces_keep_evcand --keep-cap-mb 100

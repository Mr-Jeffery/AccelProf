#!/bin/bash
#SBATCH --job-name=t21c-rean
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8
#SBATCH --time=1-00:00:00
#SBATCH --exclude=c0,c1,c2,c21,c23,c37,c43,c46,c54,c77
#SBATCH --output=/home/fzheng4/wt-t21c/eval/x_logs/t21c-rean-%x-%j.log
# T21c (Jeffery 2026-10-25, "do both fixes"): re-analyze one id's existing scalar-clock recording; usage: sbatch t21c_rean.sh <id>.
# First used for colmap-new-1-buggy (t21c_rean_colmap.sh, job 320685), then lightgbm-new-1/2-buggy, whose re-recording
# (job 320772, with the cubin extraction fix) ended ERROR at --analysis-timeout 3600. Original colmap notes:
# colmap-new-1-buggy's existing scalar-clock recording
# (job 320480: recording complete, 7 kernels, 326,755 events; analysis ERROR at --analysis-timeout 3600) with
# a long analysis timeout (82,800 s inside a 24 h CPU job). CPU only, no collection. Writes the tagged CSV
# rean-colmap-new-1-buggy-...; the attribution goes to the normal attrib/ file (colmap had none).
id=${1:?usage: sbatch t21c_rean.sh <id>}
source /home/fzheng4/wt-t21c/eval/realworld/harness/recall_header.sh || exit $?
export ACCEL_PROF_HOME=$A
for CH in /usr/local/cuda-13.4 /usr/local/cuda-13.3 /usr/local/cuda; do [ -x $CH/bin/nvdisasm ] && { export CUDA_HOME=$CH; break; }; done
source $W/eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
export BASELINE_TRACE_DIR=$S0 BASELINE_MODES=scalar-clock
cd $W || exit 1
RES=$W/eval/results/realworld_t21c; CONF=$W/eval/baselines/confirm_realworld_t21c; LOG=$W/eval/x_logs
M=$W/eval/realworld/manifest_t21c.csv
echo "reanalysis id=$id host=$(hostname) job=$SLURM_JOB_ID HEAD=$(git rev-parse --short HEAD) store=$S0 cuda=$CUDA_HOME"
echo "=== $(date -Is) analyze $id"
$PY $W/eval/baselines/parallel.py analyze --manifest $M --id $id --confirm --analysis-timeout 82800 \
   --tag "rean-$id-" --results-dir $RES --confirm-dir $CONF > $LOG/analyze-rean-$id.out 2>&1
echo "  analyze rc=$? ($(tail -1 $LOG/analyze-rean-$id.out | cut -c1-200))"
ls -la $RES/*rean-$id* 2>/dev/null
echo "=== $(date -Is) attribute $id"
$PY $W/eval/realworld/harness/rw_attribute.py --id $id --store $S0 --manifest $M --out $RES/attrib/$id.json > $LOG/attrib-rean-$id.out 2>&1
echo "  attribute rc=$? ($(tail -1 $LOG/attrib-rean-$id.out | cut -c1-400))"
echo "=== $(date -Is) done"

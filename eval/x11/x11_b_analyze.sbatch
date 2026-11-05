#!/usr/bin/env bash
#SBATCH --partition=normal
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
#SBATCH --output=/home/fzheng4/wt-x11/eval/x_logs/x11/stageB/%x-%j.log
# X11 stage B, analysis half of a cuRace clock-mode run. Submitted with --dependency=afterany:<recording job>.
# Usage: APP=knn TOOL=vector-clock RUN=1 sbatch --dependency=afterany:<jobid> -J x11b-an-knn-vector-clock-r1 x11_b_analyze.sbatch
W=/home/fzheng4/wt-x1b; RT=/home/fzheng4/AccelProf; PY=$RT/.env/bin/python
APP=${APP:?}; TOOL=${TOOL:?}; RUN=${RUN:?}; TAG=${TAGX:-x11b-$TOOL-$APP-r$RUN}
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$RT CUVEIN_HOME=$RT BASELINE_MODES=$TOOL BASELINE_TRACE_DIR=/mnt/beegfs/fzheng4/cuvein_traces/$TAG
export PATH=$RT/bin:$PATH
echo "host=$(hostname) mem=$(free -g | awk '/Mem:/{print $2}')G job=${SLURM_JOB_ID} app=$APP tool=$TOOL run=$RUN tag=$TAG harness=$(git -C $W rev-parse --short=12 HEAD) $(date -Is)"
$PY /home/fzheng4/wt-x11/eval/x11/x11_b_analyze.py $W /mnt/beegfs/fzheng4/x11_work/runtree-$TAG/manifest.csv X11-$APP $TOOL \
    /home/fzheng4/wt-x11/eval/x_logs/x11/stageB/$TAG $TAG 13800
echo "== done rc=$? $(date -Is)"

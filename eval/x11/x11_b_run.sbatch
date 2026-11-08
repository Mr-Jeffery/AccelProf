#!/usr/bin/env bash
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c2,c21,c23,c37,c46,c54
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=1-00:00:00
#SBATCH --output=/home/fzheng4/wt-x11/eval/x_logs/x11/stageB/%x-%j.log
# X11 stage B: ONE (application, tool, run) per job, rtx4060ti16g only, each run capped at 84,600 s.
# Usage: APP=knn TOOL=racecheck RUN=1 sbatch -J x11b-knn-racecheck-r1 x11_b_run.sbatch
set -u
for d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do timeout 10 ls $d > /dev/null 2>&1 || { echo "NODE-PROBLEM $(hostname): $d"; exit 2; }; done
gpu=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader 2>&1 | head -1)
case "$gpu" in *"4060 Ti"*", 8.9,"*) ;; *) echo "NODE-PROBLEM $(hostname): GPU [$gpu]"; exit 2;; esac
APP=${APP:?}; TOOL=${TOOL:?}; RUN=${RUN:?}
echo "host=$(hostname) gpu=[$gpu] cpu=[$(lscpu | sed -n 's/^Model name: *//p')] mem=$(free -g | awk '/Mem:/{print $2}')G job=${SLURM_JOB_ID} app=$APP tool=$TOOL run=$RUN $(date -Is)"
export APP TOOL RUN CAP=${CAP:-84600} TAG=${TAGX:-x11b-$TOOL-$APP-r$RUN}
export TREE=/mnt/beegfs/fzheng4/x11_work/runtree-$TAG LOGD=/home/fzheng4/wt-x11/eval/x_logs/x11/stageB/$TAG
case "$TOOL" in vector-clock|scalar-clock) WH=/home/fzheng4/wt-x1b;; *) WH=/home/fzheng4/wt-x7b;; esac
export X11_RT_HEAD=$(git -C /home/fzheng4/AccelProf rev-parse HEAD) X11_W_HEAD=$(git -C $WH rev-parse HEAD)
SIF=/home/fzheng4/AccelProf/eval/baselines/setup/tools/supercollider/ubuntu2204.sif
SING=/opt/ohpc/pub/libs/singularity/3.7.1/bin/singularity
env -u LD_LIBRARY_PATH -u LD_PRELOAD $SING exec --nv --bind /mnt/beegfs,/opt,/usr/local $SIF bash /home/fzheng4/wt-x11/eval/x11/x11_b_inner.sh
echo "== done rc=$? $(date -Is)"

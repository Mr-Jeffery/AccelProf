#!/usr/bin/env bash
#SBATCH --job-name=x11-native
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c2,c21,c23,c37,c46,c54
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
#SBATCH --output=/home/fzheng4/wt-x11/eval/x_logs/x11/stageA-native-%j.log
# X11 stage A: native time, 3 runs, median, artifact binaries in the ubuntu22.04 image (GLIBC 2.34), as the collector jobs.
set -u
for d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do timeout 10 ls $d > /dev/null 2>&1 || { echo "NODE-PROBLEM $(hostname)"; exit 2; }; done
gpu=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader 2>&1 | head -1)
case "$gpu" in *"4060 Ti"*", 8.9,"*) ;; *) echo "NODE-PROBLEM $(hostname): GPU [$gpu]"; exit 2;; esac
echo "host=$(hostname) gpu=[$gpu] cpu=[$(lscpu | sed -n 's/^Model name: *//p')] job=${SLURM_JOB_ID} $(date -Is)"
SIF=/home/fzheng4/AccelProf/eval/baselines/setup/tools/supercollider/ubuntu2204.sif
SING=/opt/ohpc/pub/libs/singularity/3.7.1/bin/singularity
PY=/home/fzheng4/AccelProf/.env/bin/python; X=/home/fzheng4/wt-x11/eval/x11
TREE=/mnt/beegfs/fzheng4/x11_work/runtree-x11-native
env -u LD_LIBRARY_PATH -u LD_PRELOAD $SING exec --nv --bind /mnt/beegfs,/opt,/usr/local $SIF bash -c "$PY $X/x11_mktree.py $TREE && $PY $X/x11_a_native.py $TREE /home/fzheng4/wt-x11/eval/x_logs/x11/stageA-native.csv"
echo "== done rc=$? $(date -Is)"

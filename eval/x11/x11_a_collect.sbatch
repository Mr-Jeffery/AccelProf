#!/usr/bin/env bash
#SBATCH --job-name=x11-co
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c2,c21,c23,c37,c46,c54
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=1-00:00:00
#SBATCH --output=/home/fzheng4/wt-x11/eval/x_logs/x11/stageA-co-%x-%j.log
# X11 stage A: collector-only mode (YOSEMITE_HB_TRACE unset) on the artifact's native HeCBench binaries,
# one run per job (RUN=1..3), harness = eval/collector-only 0c286343 (C1's, ~/wt-co), runtime = ~/AccelProf lib.
# The artifact binaries need GLIBC 2.34 (cluster 2.28), so the harness runs inside the ubuntu22.04 image
# (the same one run_supercollider.py uses). Usage: RUN=1 [IDS=gpp,crs] [TAG=x11-co-r1] sbatch x11_a_collect.sbatch
set -u
for d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do timeout 10 ls $d > /dev/null 2>&1 || { echo "NODE-PROBLEM $(hostname): $d"; exit 2; }; done
RUN=${RUN:?}; TAG=${TAG:-x11-co-r$RUN}
gpu=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader 2>&1 | head -1)
case "$gpu" in *"4060 Ti"*", 8.9,"*) ;; *) echo "NODE-PROBLEM $(hostname): GPU [$gpu]"; exit 2;; esac
echo "host=$(hostname) gpu=[$gpu] cpu=[$(lscpu | sed -n 's/^Model name: *//p')] job=${SLURM_JOB_ID} run=$RUN tag=$TAG $(date -Is)"
X=/home/fzheng4/wt-x11/eval/x11
TREE=/mnt/beegfs/fzheng4/x11_work/runtree-$TAG
SIF=/home/fzheng4/AccelProf/eval/baselines/setup/tools/supercollider/ubuntu2204.sif
SING=/opt/ohpc/pub/libs/singularity/3.7.1/bin/singularity
export TAG TREE RUN IDS=${IDS:-}
export X11_RT_HEAD=$(git -C /home/fzheng4/AccelProf rev-parse HEAD) X11_RT_STATUS=$(git -C /home/fzheng4/AccelProf status --porcelain | head -1) X11_W_HEAD=$(git -C /home/fzheng4/wt-co rev-parse HEAD)
env -u LD_LIBRARY_PATH -u LD_PRELOAD $SING exec --nv --bind /mnt/beegfs,/opt,/usr/local $SIF bash $X/x11_a_inner.sh
echo "== done rc=$? $(date -Is)"

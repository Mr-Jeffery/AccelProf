#!/usr/bin/env bash
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c2,c21,c23,c37,c46,c54
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=1-00:00:00
# X12: collector-only recording of ONE of SuperCollider's 10 HeCBench binaries (the X11 native binaries), at BASELINE_WORKERS shards.
# Same harness policy as X11 stage A / C1: --reps 3 (native in the same job), --confirm, --keep-all, cap 84,600 s, accelprof -v.
# Differences from X11: N shards (BASELINE_WORKERS), reps 3 in ONE job, BASELINE_KEEP_REPS=1 (every rep's kernel JSONs kept apart, so the
# gate covers all 3), harness = T26's branch + C1's parallel.py hunks, runtime = T26's.
#   APP=crs [N=16] [W=<harness worktree>] [RT=<runtime>] [STORE=final-2026-11-co-sh] [RES=co-sharded] sbatch -J x12-co-crs -o <W>/eval/x_logs/x12-co-crs-%j.log x12_record.sbatch
#   control: N=1 RT=/home/fzheng4/AccelProf STORE=final-2026-11-co-sh-ctl RES=co-sharded-control REPS=1  (the installed runtime, -n 1, same harness)
set -u
for d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do timeout 10 ls $d > /dev/null 2>&1 || { echo "NODE-PROBLEM $(hostname): $d"; exit 2; }; done
APP=${APP:?}
gpu=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader 2>&1 | head -1)
case "$gpu" in *"4060 Ti"*", 8.9,"*) ;; *) echo "NODE-PROBLEM $(hostname): GPU [$gpu]"; exit 2;; esac
export APP N=${N:-16} REPS=${REPS:-3}
export W=${W:?harness worktree (T26 branch + C1 hunks)} RT=${RT:?runtime prefix}
export STORE=${STORE:-final-2026-11-co-sh} RES=${RES:-co-sharded}
echo "host=$(hostname) gpu=[$gpu] nproc=$(nproc) mem=$(free -g | awk '/Mem:/{print $2}')G cpu=[$(lscpu | sed -n 's/^Model name: *//p')] job=${SLURM_JOB_ID} app=$APP N=$N reps=$REPS store=$STORE $(date -Is)"
X=$W/eval/x12
export TREE=/mnt/beegfs/fzheng4/x12_work/runtree-$STORE-$APP
SIF=/home/fzheng4/AccelProf/eval/baselines/setup/tools/supercollider/ubuntu2204.sif
SING=/opt/ohpc/pub/libs/singularity/3.7.1/bin/singularity
export X11_RT_HEAD=$(git -C $RT rev-parse HEAD) X11_RT_STATUS=$(git -C $RT status --porcelain | head -1) X12_RT_HEAD=$(git -C $RT rev-parse HEAD) X12_W_HEAD=$(git -C $W rev-parse HEAD) X12_W_DIRTY=$(git -C $W status --porcelain -uno | wc -l)
env -u LD_LIBRARY_PATH -u LD_PRELOAD $SING exec --nv --bind /mnt/beegfs,/opt,/usr/local $SIF bash $X/x12_inner.sh
echo "== done rc=$? $(date -Is)"

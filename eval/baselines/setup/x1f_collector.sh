#!/usr/bin/env bash
#SBATCH --job-name=x1f-collector
#SBATCH --partition=max
#SBATCH --exclude=c[0-26],c29,c[33-37],c[39-48],c[50-59],c[73-79]
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=1-02:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/x1f-collector-%j.log
# X1-follow Part 1 (eval/X1_FOLLOW.md section 1): the collector-only cost. One program, one worker
# setting, one run: YOSEMITE_HB_TRACE unset (the collector + the PcDependency graph; no HbClock --
# YOSEMITE_HB_NO_ENGINE=1 is the deprecated alias of scalar-clock mode and runs HbClock's sync
# instance, pc_dependency_analysis.cpp:2257-2270/2599, so it is not this configuration), the
# installed runtime (d38d057), the harness's command with -v, cap CAP (24 h for heartwall/knn).
# `max` partition (8-day limit) pinned by the exclude list to c60-c72 (RTX 4060 Ti 16 GB, EPYC 8124P,
# 188 GB): a 24 h cap plus native runs does not fit rtx4060ti16g's 1-day limit.
#   ID=P7-heartwall-cuda WORKERS=1|default CAP=86400 sbatch eval/baselines/setup/x1f_collector.sh
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-x1}
RT=/home/fzheng4/AccelProf
source $W/eval/baselines/setup/home_quota_guard.sh
cd $RT || exit 1
ID=${ID:?}; WORKERS=${WORKERS:?}; CAP=${CAP:-86400}
for v in $(env | /usr/bin/grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_HB_DUMP
export ACCEL_PROF_HOME=$RT CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
h() { sha256sum "$1" | cut -c1-16; }
gpu=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader 2>&1 | head -1)
case "$gpu" in *"4060 Ti"*", 8.9,"*) ;; *) echo "NODE-PROBLEM $(hostname): GPU [$gpu]"; exit 2;; esac
[ -d /mnt/beegfs/$USER ] || { echo "NODE-PROBLEM $(hostname): BeeGFS not mounted"; exit 2; }
echo "host=$(hostname) gpu=[$gpu] mem=$(free -g | awk '/Mem:/{print $2}')G cpu=[$(lscpu | sed -n 's/^Model name: *//p')] nproc=$(nproc) nproc_all=$(nproc --all) job=${SLURM_JOB_ID:-} $(date -Is)"
echo "runtime $RT libsanalyzer $(h $RT/build/sanalyzer/lib/libsanalyzer.so) collector $(h $RT/lib/libcompute_sanitizer.so) fatbin $(h $RT/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin); harness $W HEAD=$(git -C $W rev-parse --short=12 HEAD)"
N=${NAME:-$ID-collector-n$WORKERS}
$PY $W/eval/baselines/setup/x1f_run.py --id $ID --config collector --workers $WORKERS --cap $CAP \
    --native-reps 3 --name $N --out $W/eval/x1_follow/collector --work /mnt/beegfs/$USER/x1_follow/runs \
    > $W/eval/x1_follow/collector/$N.driver.txt 2>&1
tail -2 $W/eval/x1_follow/collector/$N.driver.txt
echo "== done $(date -Is)"

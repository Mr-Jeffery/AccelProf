# T21b copy of job_header.sh with the T21b worktree: exit 97 (hostname on stderr) when home, BeeGFS or the worktree is unreadable.
for _d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4 /home/fzheng4/wt-t21b/eval/realworld; do
  timeout 10 ls "$_d" >/dev/null 2>&1 || { echo "T21b job_header: host=$(hostname) missing or unreadable $_d" >&2; exit 97; }
done
unset _d
export WT=/home/fzheng4/wt-t21b
export RW=/mnt/beegfs/fzheng4/realworld
export INCOMING=/home/fzheng4/incoming/realworld
export HARNESS=$WT/eval/realworld/harness
export CUDA_HOME=${CUDA_HOME:-/usr/local/cuda}
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$CUDA_HOME/compute-sanitizer:${LD_LIBRARY_PATH:-}
source "$WT/eval/baselines/setup/home_quota_guard.sh"
echo "T21b build job: host=$(hostname) job=${SLURM_JOB_ID:-none} date=$(date +%FT%T) cpus=${SLURM_CPUS_PER_TASK:-?}"
echo "T21b build job: $(nvcc --version 2>&1 | tail -1)"

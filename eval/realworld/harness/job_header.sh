# eval/realworld/harness/job_header.sh -- `source` this at the top of every T21 SLURM job script.
# T21c: set T21_WT=/home/fzheng4/wt-t21c to run this harness from the T21c worktree (default: T21a's).
# Hard-fails (exit 97, hostname on stderr) when the node cannot see home or BeeGFS: c23 and c46
# were found without /home/fzheng4 on 2026-10-20. Resubmit with that node in --exclude and
# record it in eval/REALWORLD.md section 1 ("Excluded nodes").
for _d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4 ${T21_WT:-/home/fzheng4/wt-t21a}/eval/realworld; do
  [ -d "$_d" ] || { echo "T21 job_header: host=$(hostname) missing $_d" >&2; exit 97; }
done
unset _d
export WT=${T21_WT:-/home/fzheng4/wt-t21a}                 # the T21a worktree: the only checkout T21a touches
export RW=/mnt/beegfs/fzheng4/realworld         # {src,build,runs}/<id>/{buggy,fixed}
export INCOMING=/home/fzheng4/incoming/realworld # partial clones + exports (login node writes, jobs read)
export HARNESS=$WT/eval/realworld/harness
export CUDA_HOME=${CUDA_HOME:-/usr/local/cuda}
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$CUDA_HOME/compute-sanitizer:${LD_LIBRARY_PATH:-}
source "$WT/eval/baselines/setup/home_quota_guard.sh"
echo "T21 job: host=$(hostname) job=${SLURM_JOB_ID:-none} date=$(date +%FT%T) cpus=${SLURM_CPUS_PER_TASK:-?}"
echo "T21 job: $(nvcc --version 2>&1 | tail -1)"

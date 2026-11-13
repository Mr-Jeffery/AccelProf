#!/usr/bin/env bash
#SBATCH --job-name=x13-gpu
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c0,c1,c2,c11,c12,c13,c14,c15,c18,c21,c22,c23,c34,c35,c36,c37,c46,c54
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=10:00:00
# X13: one whole rtx4060ti16g node held for the task; the phases (green set, parity, runs) are srun --overlap steps of
# this job (x13_*.sh). Releases when /home/fzheng4/x13_STOP exists.
echo "host=$(hostname) job=$SLURM_JOB_ID $(date -Is)"; nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader
rm -f /home/fzheng4/x13_STOP
while [ ! -e /home/fzheng4/x13_STOP ]; do sleep 20; done
echo "== released $(date -Is)"

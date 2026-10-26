#!/bin/bash
#SBATCH --job-name=m3-jit-path-b130c
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --exclude=c0,c1,c2,c37,c54,c79
#SBATCH --output=/home/fzheng4/m3work/m3c-%j.log
# M3 (Jeffery 2026-10-26): PTX-only vs SASS builds under the profiler; one rtx4060ti16g node.
for CH in /usr/local/cuda-13.4 /usr/local/cuda-13.3 /usr/local/cuda; do [ -x $CH/bin/nvcc ] && { export CUDA_HOME=$CH; break; }; done
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
echo "host=$(hostname) job=$SLURM_JOB_ID cuda=$CUDA_HOME date=$(date -Is)"
nvidia-smi --query-gpu=name,driver_version,compute_cap --format=csv,noheader
cd /home/fzheng4/m3work
/home/fzheng4/AccelProf/.env/bin/python m3_jit_path.py --out /home/fzheng4/m3work/out130c --reps 3 --build-cuda /usr/local/cuda-13.0
echo "done rc=$? $(date -Is)"

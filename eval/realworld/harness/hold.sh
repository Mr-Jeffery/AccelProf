#!/bin/bash
# T21a work node: one whole `normal` node held for a few hours (the cluster allocates whole nodes and the
# queue for `normal` is long); the build/run/racecheck commands are SLURM job steps inside this allocation:
#   srun --jobid=<this job> --overlap bash eval/realworld/harness/step.sh <logname> <command...>
# Stops itself when eval/x_logs/HOLD_STOP exists or at the time limit.
source /home/fzheng4/wt-t21a/eval/realworld/harness/job_header.sh
echo "--- toolchain"; which gcc g++ cmake ninja make python3 git pip conda 2>&1
gcc --version | head -1; g++ --version | head -1; cmake --version | head -1; python3 --version
nproc; free -g | head -2; df -h /mnt/local /tmp 2>&1 | tail -2
which nvdisasm cuobjdump compute-sanitizer nvcc; nvcc --version | tail -3
ls /usr/local/ | head -20; ls /usr/local/cuda/compute-sanitizer | head -5
module avail 2>&1 | head -40
nvidia-smi --query-gpu=name,compute_cap --format=csv 2>&1 | head -3
echo "--- holding"
while [ ! -e "$WT/eval/x_logs/HOLD_STOP" ]; do sleep 30; done

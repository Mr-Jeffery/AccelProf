#!/usr/bin/env bash
#SBATCH --job-name=x11-step0b
#SBATCH --partition=normal
#SBATCH --time=01:00:00
#SBATCH --output=/home/fzheng4/wt-x11/eval/x_logs/x11/step0b-%j.log
mkdir -p /mnt/beegfs/fzheng4/x11_work/step0b
python3 /home/fzheng4/wt-x11/eval/x11/x11_diff.py /mnt/beegfs/fzheng4/x11_work/step0b

#!/bin/bash
#SBATCH -p normal
#SBATCH --exclude=c0,c1,c23,c46
#SBATCH -N 1 -n 1 -c 2
#SBATCH -t 04:00:00
#SBATCH -J tv-scan
#SBATCH -o /home/fzheng4/tvscan/log-%A_%a.log
# M4 TV census: one shard per array task. Usage: sbatch --array=0-23 p_tv_scan.sh
NSH=${NSH:-24}
OUT=${OUT:-/home/fzheng4/tvscan/out}
hostname
python3 --version
python3 -I /home/fzheng4/tvscan/tv_scan.py scan --shard $SLURM_ARRAY_TASK_ID --nshards $NSH --out $OUT

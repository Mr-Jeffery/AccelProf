#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH -t 00:05:00
#SBATCH -o /home/fzheng4/wt-c6/eval/x_logs/c6-cpuinfo-%N-%j.log
echo "host=$(hostname) nproc=$(nproc)"
lscpu | grep -E "^(Model name|Socket|Core|Thread|CPU\(s\)|CPU MHz|CPU max MHz|CPU min MHz|Vendor)"
grep -m1 "cpu MHz" /proc/cpuinfo

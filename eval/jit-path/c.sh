#!/bin/bash
#SBATCH -J m3-ctl -p normal -N1 -n1 -t 00:15:00 --exclude=c0,c1,c23,c46 -o /home/fzheng4/m3work/m3ctl-%j.log
export CUDA_HOME=/usr/local/cuda-13.4
cd /home/fzheng4/m3work && /home/fzheng4/AccelProf/.env/bin/python m3_control134.py

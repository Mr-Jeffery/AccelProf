#!/bin/bash
#SBATCH -p normal
#SBATCH --exclude=c0,c1,c23,c46
#SBATCH -t 12:00:00
#SBATCH -J x6-cert-first
#SBATCH -o /home/fzheng4/wt-x6/eval/x_logs/x6-%j.log
cd /home/fzheng4/wt-x6
# merged X1b CSV from origin/eval/final-sweep-b @ 94fde73 (git show ...:eval/results/final-b/merged/baselines-cuvein.csv)
~/AccelProf/.env/bin/python eval/baselines/setup/x6_cert_first.py --csv /home/fzheng4/x6tmp/baselines-cuvein-final-b.csv --out-dir eval/results/x6 --workers 16 --resume

#!/usr/bin/env bash
#SBATCH --job-name=cuvein-baselines
#SBATCH --partition=rtx3060ti
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/present-%j.log
# Full present-corpora baseline run (P4 ScoR apps, P5 ScoR micro+canary, P6 cuHadron)
# through cuVein (vector-clock+scalar-clock) and racecheck, then rebuild tables.
cd /home/fzheng4/AccelProf || exit 1
export PSETS="P4,P5,P6"
export STAGES="build cuvein racecheck tables"
bash eval/baselines/run_all.sh

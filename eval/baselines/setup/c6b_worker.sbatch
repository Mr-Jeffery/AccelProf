#!/bin/bash
#SBATCH --job-name=c6b-step4
#SBATCH --partition=normal
#SBATCH --exclusive
#SBATCH --exclude=c0,c1,c22,c23,c34,c46
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --time=08:00:00
#SBATCH --output=/home/fzheng4/c6b-step4/worker-%j.log
# C6b step 4: ONE node, one job. Runs the command files dropped into /home/fzheng4/c6b-step4/q/ one after the other
# (as c6_worker.sbatch of C6). Exits after 40 minutes with nothing to do, or when q/STOP exists.
Q=/home/fzheng4/c6b-step4/q
echo "worker host=$(hostname) start=$(date -Is) nproc=$(nproc)"
lscpu | grep -E "Model name|Socket|Thread|Core" | head -5
idle=0
while true; do
  [ -e $Q/STOP ] && break
  did=0
  for f in $(ls $Q/*.sh 2>/dev/null | sort); do
    [ -e $f.started ] && continue
    touch $f.started; did=1; idle=0
    echo "$(date -Is) run $(basename $f)"
    bash $f > $f.out 2>&1; echo "rc=$?" >> $f.out; touch $f.done
  done
  if [ $did = 0 ]; then sleep 5; idle=$((idle+5)); [ $idle -gt 2400 ] && break; fi
done
echo "worker end=$(date -Is)"

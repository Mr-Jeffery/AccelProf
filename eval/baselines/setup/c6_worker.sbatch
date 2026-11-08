#!/bin/bash
#SBATCH --job-name=c6-step3
#SBATCH --partition=normal
#SBATCH --exclusive
#SBATCH --exclude=c0,c1,c22,c23,c34,c46
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --time=16:00:00
#SBATCH --output=/home/fzheng4/c6-step3/worker-%j.log
# C6 step 3: ONE node, one job. Runs the command files that are dropped into /home/fzheng4/c6-step3/q/ (bg_*.sh in the
# background, the others one after the other), so every analysis of step 3 (tables, detection comparison, cost, real-world
# attribution) shares this allocation. Exits after 40 minutes with nothing to do, or when q/STOP exists.
Q=/home/fzheng4/c6-step3/q
echo "worker host=$(hostname) start=$(date -Is) nproc=$(nproc) mem=$(free -g | awk '/Mem:/{print $2}')G"
lscpu | grep -E "Model name|Socket|Thread|Core" | head -5
idle=0
while true; do
  [ -e $Q/STOP ] && break
  did=0
  for f in $(ls $Q/*.sh 2>/dev/null | sort); do
    [ -e $f.started ] && continue
    touch $f.started; did=1; idle=0
    echo "$(date -Is) run $(basename $f)"
    case $(basename $f) in
      bg_*) (bash $f > $f.out 2>&1; echo "rc=$?" >> $f.out; touch $f.done) & ;;
      *)    bash $f > $f.out 2>&1; echo "rc=$?" >> $f.out; touch $f.done ;;
    esac
  done
  if [ $did = 0 ]; then
    sleep 5; idle=$((idle+5))
    run=0; for s in $Q/*.sh.started; do [ -e "$s" ] || continue; [ -e "${s%.started}.done" ] || run=$((run+1)); done
    [ $idle -gt 2400 ] && [ $run = 0 ] && break
  fi
done
wait
echo "worker end=$(date -Is)"

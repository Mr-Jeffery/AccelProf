#!/usr/bin/env bash
#SBATCH --job-name=t24-time
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --time=16:00:00
# T24 step 6: wall time before (the installed runtime, 38af04e) and after (the worktree's private
# runtime) on ONE node, one after the other, through t19_long.sh (accelprof directly, YOSEMITE_HB_DUMP=0,
# YOSEMITE_HB_STATS=1 at kernel end, a CAP-second limit): P7-heartwall-cuda in scalar-clock mode at
# YOSEMITE_HB_SHARDS=16 (T22 cont.'s step-D setting), then the ECL-CC program with the most diverged
# syncwarp instances in X5b (P1 ...Push_NonDeterm..._NonPersist_RaceBug_Warp...-default-1296n: 9,480 /
# 9,239 partial instances) in both modes. Order: heartwall before, after; CC before, after.
#   sbatch -p rtx4060ti16g -x c2,c21,c23,c37,c46,c54 -o <W>/eval/x_logs/t24-time-%j.log <W>/eval/baselines/setup/t24_time.sh
set -u
export W=${W:-/home/fzheng4/wt-t24}; A=/home/fzheng4/AccelProf
for d in $A /mnt/beegfs/fzheng4; do
  timeout 10 ls $d > /dev/null 2>&1 || { echo "ABORT on $(hostname): $d not readable"; exit 3; }
done
cd $W || exit 1
EV=$W/eval/results/t24/time; mkdir -p $EV
echo P7-heartwall-cuda > $EV/heartwall.txt
echo P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Warp_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-default-1296n > $EV/cc.txt
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader | head -1) $(lscpu | grep 'Model name' | sed 's/  */ /g') nproc=$(nproc) mem=$(free -g | awk '/Mem:/{print $2}')G HEAD=$(git rev-parse --short HEAD) $(date -Is)"
run() {   # <label> <ids> <modes> <cap> <shards or empty>
  for rt in before after; do
    R=$A; [ $rt = after ] && R=$W
    echo "==== $1 $rt: runtime $R libsanalyzer $(sha256sum $(ldd $R/lib/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}') | cut -c1-16) $(date -Is)"
    ( [ -n "$5" ] && export YOSEMITE_HB_SHARDS=$5; RT=$R OUTDIR=t24-time-$rt IDS=$2 MODES="$3" CAP=$4 EVERY=0 \
        bash eval/baselines/setup/t19_long.sh 2>&1 | sed "s/^/[$1 $rt] /" )
  done
}
run heartwall $EV/heartwall.txt scalar-clock ${HW_CAP:-9000} 16
run cc $EV/cc.txt "scalar-clock vector-clock" ${CC_CAP:-3600} ""
echo "== done $(date -Is)"

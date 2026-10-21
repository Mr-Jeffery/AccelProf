#!/usr/bin/env bash
#SBATCH --job-name=t24-parity
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=12:00:00
# T24 parity B and C (T20's protocol, eval/THREAD_INDEX.md section 5): STEP=rec records T5b's parity set
# (setup/t5b_parity_ids.txt, 65 programs) with the worktree's private runtime in both modes, dump on,
# the 120 s floor, one rep, YOSEMITE_HB_SHARDS=16 for scalar-clock (vector-clock runs the serial pass),
# kept on BeeGFS cuvein_traces/$TAG (p_t5b_timeout.sh); STEP=spec compares HbClock with the
# specification on it (p_t5b_parity_cmp.sh -> t5b_parity.py compare), STEP=agg the aggregates with
# the records (p_t4_parity_cmp.sh -> t4_parity.py compare, CAP 25000). This wrapper adds the
# filesystem check every T24 job makes and runs the existing script unchanged.
#   STEP=rec  sbatch -p rtx4060ti16g -x c2,c21,c23,c37,c46,c54 --array=0-7 -o <W>/eval/x_logs/t24-parity-rec-%A_%a.log t24_parity.sh
#   STEP=spec sbatch -p normal -x ... --array=0-7 --dependency=afterany:<rec> -o <W>/eval/x_logs/t24-parity-spec-%A_%a.log t24_parity.sh
#   STEP=agg  sbatch -p normal -x ... --array=0-7 --dependency=afterany:<rec> -o <W>/eval/x_logs/t24-parity-agg-%A_%a.log t24_parity.sh
set -u
export W=${W:-/home/fzheng4/wt-t24} TAG=${TAG:-t24-parity}
for d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do
  timeout 10 ls $d > /dev/null 2>&1 || { echo "ABORT on $(hostname): $d not readable"; exit 3; }
done
cd $W || exit 1
S=eval/baselines/setup
case ${STEP:?set STEP=rec|spec|agg} in
  rec)  export IDS=$S/t5b_parity_ids.txt BASELINE_MODES=vector-clock,scalar-clock FLOOR=120 \
               YOSEMITE_HB_SHARDS=${SHARDS:-16} YOSEMITE_HB_STATS=1
        exec bash $S/p_t5b_timeout.sh ;;
  spec) exec bash $S/p_t5b_parity_cmp.sh ;;
  agg)  export CAP=${CAP:-25000}; exec bash $S/p_t4_parity_cmp.sh ;;
esac

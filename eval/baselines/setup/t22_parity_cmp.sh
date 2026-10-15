#!/usr/bin/env bash
#SBATCH --job-name=t22-parity-cmp
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=12:00:00
# T22 verification B (as p_t4_parity_cmp.sh, the T20 method, eval/THREAD_INDEX.md section 2): on a
# store recorded in scalar-clock mode with the dump on and YOSEMITE_HB_SHARDS=N, every kernel
# JSON's sharded aggregates (hb_sync_pass, hb_rmw_points) against the replay of that run's own
# hb_events by barrier_only_pairs / trace_rmw_points with the lane cutoff lifted
# (CUVEIN_BARRIER_PASS_MAX_LANES=10**12, set by t4_parity.py), and analyze() from the aggregates
# (the X0 default) against CUVEIN_PREFER_RECORDS=1. CPU only; BeeGFS (not on the login node).
# PAR=<k> runs k comparer processes in this one job (t4_parity.py --shard i/k), then the table.
#   TAG=<store tag> PAR=32 sbatch -p <partition> -o <W>/eval/baselines/setup/build_logs/t22-parity-cmp-%j.log eval/baselines/setup/t22_parity_cmp.sh
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t22}
TAG=${TAG:?set TAG}
PAR=${PAR:-1}
cd $W || exit 1
D=eval/baselines/setup/t22_parity/$TAG
mkdir -p $D
echo "host=$(hostname) nproc=$(nproc) mem=$(free -g | awk '/Mem:/{print $2}')G HEAD=$(git -C $W rev-parse --short HEAD) par=$PAR $(date -Is)"
for k in $(seq 0 $((PAR - 1))); do
  .env/bin/python eval/baselines/setup/t4_parity.py compare --store /mnt/beegfs/$USER/cuvein_traces/$TAG \
      --out $D/shard$k.json --cap ${CAP:-3600} --shard $k/$PAR ${IDS:+--ids $IDS} > $D/shard$k.log 2>&1 &
done
wait
.env/bin/python eval/baselines/setup/t4_parity.py table $D/shard*.json
echo "== done $(date -Is)"

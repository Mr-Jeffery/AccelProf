#!/usr/bin/env bash
#SBATCH --job-name=t24-replay60
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16
#SBATCH --time=04:00:00
# T24 step 4: t24_replay60.py over X5b's 60 recordings (groups = eval/results/x5b/partial.jsonl of
# branch eval/x5-byte-pairs b5e10b4), 16 shards as parallel processes on one node (as X5b's
# p_x5b_partial.sh); the 38af04e oracle is extracted from git. Outputs eval/results/t24/replay60*.jsonl.
#   sbatch -p normal -x c2,c21,c23,c37,c46,c54 -o <W>/eval/x_logs/t24-replay60-%j.log <W>/eval/baselines/setup/t24_replay60.sh
set -u
W=${W:-/home/fzheng4/wt-t24}
for d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do
  timeout 10 ls $d > /dev/null 2>&1 || { echo "ABORT on $(hostname): $d not readable"; exit 3; }
done
cd $W || exit 1
PY=$W/.env/bin/python
T=$(mktemp -d /tmp/t24-replay60-XXXX); export TMPDIR=$T
git show b5e10b4:eval/results/x5b/partial.jsonl > $T/groups.jsonl
git show 38af04e:python/hb_oracle.py > $T/hb_oracle_38af04e.py
echo "host=$(hostname) job ${SLURM_JOB_ID} HEAD=$(git rev-parse --short HEAD) dirty=$(git status --porcelain -uno | wc -l) groups=$(wc -l < $T/groups.jsonl) $(date -Is)"
R=eval/results/t24; mkdir -p $R
for I in $(seq 0 15); do
  $PY eval/baselines/setup/t24_replay60.py --groups $T/groups.jsonl --old-oracle $T/hb_oracle_38af04e.py \
      --out $R/replay60_$I.jsonl --shard $I/16 > eval/x_logs/t24-replay60-${SLURM_JOB_ID}-$I.log 2>&1 &
done
wait
cat $R/replay60_{0..15}.jsonl > $R/replay60.jsonl && rm -f $R/replay60_{0..15}.jsonl
echo "tracebacks: $(grep -l Traceback eval/x_logs/t24-replay60-${SLURM_JOB_ID}-*.log | wc -l)"
$PY - $R/replay60.jsonl <<'EOF'
import json, sys, collections
rows = [json.loads(l) for l in open(sys.argv[1])]
tot = collections.Counter()
for r in rows:
    tot["groups"] += 1; tot["launches"] += r["launches"]
    tot["groups with partial instances"] += any(k.startswith("instances of") for k in r["census"])
    for k, v in r["census"].items(): tot[k] += v
    tot["pairs only new"] += sum(r["only_new"].values()); tot["pairs only old"] += sum(r["only_old"].values())
    tot["new != merged"] += sum(r["new_ne_merged"].values())
    tot["launches with TV (new, strict)"] += len(r["tv_new"]); tot["launches with TV (old)"] += len(r["tv_old"])
    tot["errors"] += len(r["errors"])
print(dict(tot))
for r in rows:
    if r["only_new"] or r["only_old"] or r["new_ne_merged"] or r["tv_new"] or r["errors"]:
        print(r["id"][:70], r["mode"], r["only_new"], r["only_old"], r["new_ne_merged"], r["tv_new"][:2], r["errors"][:2])
EOF
rm -rf $T
echo "== done $(date -Is)"

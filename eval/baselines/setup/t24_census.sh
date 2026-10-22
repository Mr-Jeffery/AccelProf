#!/usr/bin/env bash
#SBATCH --job-name=t24-census
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8
#SBATCH --time=04:00:00
# T24: t24_census.py over a kept store (default the T24 parity recording), 8 processes on one node;
# kernel JSONs above MAXGB are listed, not read. Output eval/results/t24/census-<tag>.jsonl.
#   TAG=t24-parity sbatch -p normal -x c2,c21,c23,c37,c46,c54 -o <W>/eval/x_logs/t24-census-%j.log <W>/eval/baselines/setup/t24_census.sh
set -u
W=${W:-/home/fzheng4/wt-t24}; TAG=${TAG:-t24-parity}
for d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do
  timeout 10 ls $d > /dev/null 2>&1 || { echo "ABORT on $(hostname): $d not readable"; exit 3; }
done
cd $W || exit 1
PY=$W/.env/bin/python; R=eval/results/t24; mkdir -p $R
echo "host=$(hostname) job ${SLURM_JOB_ID} HEAD=$(git rev-parse --short HEAD) store $TAG $(date -Is)"
for I in $(seq 0 7); do
  $PY eval/baselines/setup/t24_census.py --store /mnt/beegfs/$USER/cuvein_traces/$TAG --out $R/census-$TAG-$I.jsonl \
      --shard $I/8 --max-gb ${MAXGB:-3} > eval/x_logs/t24-census-${SLURM_JOB_ID}-$I.log 2>&1 &
done
wait
cat $R/census-$TAG-{0..7}.jsonl > $R/census-$TAG.jsonl && rm -f $R/census-$TAG-{0..7}.jsonl
echo "tracebacks: $(grep -l Traceback eval/x_logs/t24-census-${SLURM_JOB_ID}-*.log | wc -l)"
$PY - $R/census-$TAG.jsonl <<'EOF'
import json, sys, collections
rows = [json.loads(l) for l in open(sys.argv[1])]
tot, progs = collections.Counter(), collections.defaultdict(collections.Counter)
for r in rows:
    tot["kernel JSONs"] += 1
    if "skipped_bytes" in r: tot["skipped (size)"] += 1; print("skipped", r["file"], r["skipped_bytes"]); continue
    if r.get("no_events"): tot["no hb_events"] += 1; continue
    p = "/".join(r["file"].split("/")[:2])
    for k, v in r.items():
        if k != "file": tot[k] += v; progs[p][k] += v
print(dict(tot))
for p, c in sorted(progs.items()):
    if c["partial records"] or c["records naming exited or absent lanes"] or c["open at end"]:
        print(p, dict(c))
print("programs x modes with syncwarp records:", sum(1 for c in progs.values() if c["syncwarp records"]))
EOF
echo "== done $(date -Is)"

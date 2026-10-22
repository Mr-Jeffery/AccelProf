#!/usr/bin/env bash
#SBATCH --job-name=t24-replay-store
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8
#SBATCH --time=04:00:00
# T24: t24_replay_store.py over the (program, mode) dirs of a kept store that t24_census.py lists (a
# diverged WARPSYNC or a sync_mask naming exited/absent lanes), 8 processes on one node; 38af04e's
# oracle and sync_dominance extracted from git. Output eval/results/t24/replay-<tag>.jsonl.
# NPROC processes (default 8); SKIP=<previous output> leaves its dirs out; SUF names the output.
#   TAG=t24-parity sbatch -p normal -x c2,c21,c23,c37,c46,c54 -o <W>/eval/x_logs/t24-replay-store-%j.log <W>/eval/baselines/setup/t24_replay_store.sh
set -u
W=${W:-/home/fzheng4/wt-t24}; TAG=${TAG:-t24-parity}
for d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4; do
  timeout 10 ls $d > /dev/null 2>&1 || { echo "ABORT on $(hostname): $d not readable"; exit 3; }
done
cd $W || exit 1
PY=$W/.env/bin/python; R=eval/results/t24
T=$(mktemp -d /tmp/t24-rs-XXXX); export TMPDIR=$T
git show 38af04e:python/hb_oracle.py > $T/hb_oracle_38af04e.py
git show 38af04e:python/sync_dominance.py > $T/sync_dominance_38af04e.py
echo "host=$(hostname) job ${SLURM_JOB_ID} HEAD=$(git rev-parse --short HEAD) dirty=$(git status --porcelain -uno | wc -l) store $TAG $(date -Is)"
N=${NPROC:-8}; O=$R/replay-$TAG${SUF:-}
for I in $(seq 0 $((N - 1))); do
  $PY eval/baselines/setup/t24_replay_store.py --store /mnt/beegfs/$USER/cuvein_traces/$TAG \
      --census $R/census-$TAG.jsonl --old-oracle $T/hb_oracle_38af04e.py --old-sd $T/sync_dominance_38af04e.py \
      --out $O-$I.jsonl --shard $I/$N ${SKIP:+--skip-done $SKIP} > eval/x_logs/t24-replay-store-${SLURM_JOB_ID}-$I.log 2>&1 &
done
wait
cat $(seq -f "$O-%g.jsonl" 0 $((N - 1))) > $O.jsonl && rm -f $(seq -f "$O-%g.jsonl" 0 $((N - 1)))
echo "tracebacks: $(grep -l Traceback eval/x_logs/t24-replay-store-${SLURM_JOB_ID}-*.log | wc -l)"
$PY - $O.jsonl <<'EOF'
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1])]
print("dirs", len(rows), "kernels", sum(r["kernels"] for r in rows),
      "only_new", sum(sum(r["only_new"].values()) for r in rows), "only_old", sum(sum(r["only_old"].values()) for r in rows),
      "tv_new", sum(len(r["tv_new"]) for r in rows), "tv_old", sum(len(r["tv_old"]) for r in rows), "errors", sum(len(r["errors"]) for r in rows))
for r in rows:
    print(r["dir"][:90], r["kernels"], "ONLY-NEW", r["only_new"], "ONLY-OLD", r["only_old"], "TVn", r["tv_new"][:1], "TVo", r["tv_old"][:1], r["errors"][:1])
EOF
rm -rf $T
echo "== done $(date -Is)"

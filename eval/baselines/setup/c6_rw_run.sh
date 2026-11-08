#!/usr/bin/env bash
# C6 step 3, real-world: attribute (chain closure on) every id of the recall set (T21b, store realworld-2026-10-co) and the candidate set
# (T21c, store realworld-2026-10-t21c-co) that ended RACE or CLEAN in step 2, heaviest first, P at a time, each with a time limit; then score.
set -u
. /home/fzheng4/c6-step3/env.sh
RWH=/home/fzheng4/c6rw; RWR=$S3/rw; N=$W/eval/results/co-chain
P=${P:-8}; LIM=${LIM:-12h}
for CH in /usr/local/cuda-13.4 /usr/local/cuda-13.3 /usr/local/cuda; do [ -x $CH/bin/nvdisasm ] && { export CUDA_HOME=$CH; break; }; done
[ -n "${CUDA_HOME:-}" ] || { echo "no nvdisasm on $(hostname)"; exit 96; }
export PATH=$CUDA_HOME/bin:$PATH LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
export RW_MODES=collector-only
echo "host=$(hostname) cuda=$CUDA_HOME $(date -Is)"
$PY - <<PYEOF > $RWR/cmds.txt
import csv, re
out = []
for st, f in (("t21b", "$N/merged-c2-recall/baselines-cuvein.csv"), ("t21c", "$N/merged-c2-cand/baselines-cuvein.csv")):
    best = {}
    for r in csv.DictReader(open(f, newline="")):
        m = re.search(r"analysis_s=([0-9.]+)", r["notes"])
        a = float(m.group(1)) if m else 0.0
        if r["verdict"] in ("RACE", "CLEAN"):
            best[r["id"]] = max(best.get(r["id"], 0.0), a)
    out += [(a, st, i) for i, a in best.items()]
for a, st, i in sorted(out, reverse=True):
    print(st, i)
PYEOF
wc -l $RWR/cmds.txt
rw1() {
  set=$1; id=$2
  case $set in
    t21b) H=$RWH/t21b; S0=/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10-co;      M=$W/eval/realworld/manifest_t21b.csv; RES=$RWR/realworld ;;
    t21c) H=$RWH/t21c; S0=/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10-t21c-co; M=$W/eval/realworld/manifest_t21c.csv; RES=$RWR/realworld_t21c ;;
  esac
  mkdir -p /tmp/c6rw-$id; export TMPDIR=/tmp/c6rw-$id
  t0=$(date +%s)
  timeout $LIM $PY $H/eval/realworld/harness/rw_attribute.py --id $id --store $S0 --manifest $M --out $RES/attrib/$id.json > $RWR/attrib-$id.out 2>&1
  echo "$(date -Is) attribute $set $id rc=$? wall=$(( $(date +%s) - t0 ))s: $(tail -1 $RWR/attrib-$id.out | cut -c1-200)"
  rm -rf /tmp/c6rw-$id
}
export -f rw1; export RWH RWR W PY LIM
NH=${NH:-8}
head -n $NH $RWR/cmds.txt | xargs -P $NH -L 1 bash -c 'rw1 "$@"' _ &
tail -n +$((NH+1)) $RWR/cmds.txt | xargs -P $P -L 1 bash -c 'rw1 "$@"' _ &
wait
echo "== attribution done $(date -Is)"
$PY $RWH/t21b/eval/realworld/harness/rw_score.py --results $RWR/realworld --manifest $W/eval/realworld/manifest_t21b.csv --pairs $RWH/t21b/eval/realworld/recall_pairs.json --write > $RWR/score_t21b.out 2>&1; echo "score t21b rc=$?"
$PY $RWH/t21c/eval/realworld/harness/rw_score.py --results $RWR/realworld_t21c --manifest $W/eval/realworld/manifest_t21c.csv --pairs $RWH/t21c/eval/realworld/recall_pairs.json --exclude lightgbm-new-1,lightgbm-new-2,llamacpp-open-2 --write > $RWR/score_t21c.out 2>&1; echo "score t21c rc=$?"
echo "== all done $(date -Is)"

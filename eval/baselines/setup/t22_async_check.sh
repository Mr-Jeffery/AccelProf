#!/usr/bin/env bash
#SBATCH --job-name=t22-async
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=00:30:00
# T22: which programs of the parity store have cp.async copies (sidecar `# async` lines from the
# kept CFGs) and pipeline records in their dumps -- i.e. whether B1 covered the sharded pass's
# broadcast of copies.
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t22}
S=/mnt/beegfs/$USER/cuvein_traces/${TAG:-t22-parity-b}
T=$(mktemp -d)
for d in $S/*/; do
  id=$(basename $d); ls $d/dots/*.dot > /dev/null 2>&1 || continue
  $W/.env/bin/python $W/python/atomic_scope_sidecar.py $d/dots/*.dot -o $T/sc.txt > /dev/null 2>&1
  na=$(grep -c "^# async" $T/sc.txt)
  [ "$na" = 0 ] && continue
  ev=$(cat $d/scalar-clock/kernel_*.json 2>/dev/null | grep -o '"type": "pipeline_[a-z]*"' | sort | uniq -c | tr '\n' ' ')
  echo "$id: async pcs $na; pipeline records: ${ev:-none}"
done
rm -rf $T
echo "== done $(date -Is)"

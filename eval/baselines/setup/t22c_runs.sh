#!/usr/bin/env bash
#SBATCH --job-name=t22c-runs
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=1-00:00:00
# T22 cont. steps C and D: several t22_perf.sh groups one after the other on one node, each
#   "<runtime>|<cap>|<tag>|<id>:<N>[:<reps>] ..."   (groups separated by ";" in RUNGROUPS)
# runtime = final (the worktree W: both fixes) or old (the mirror $M/rt-old: b6a615e, neither fix);
# results eval/results/<tag>-<id>-n<N>, stores cuvein_traces/<same>; then t22c_kstats.py per store
# into the results dir's kstats.txt (each kernel JSON's write time: what had finished by when).
#   RUNGROUPS="final|86400|t22c-c|P7-bfs-cuda:1 P7-bfs-cuda:8; old|5400|t22c-cold|P7-bfs-cuda:1" \
#     sbatch -p rtx4060ti16g -x <hosts> -o <log> eval/baselines/setup/t22c_runs.sh
set -u
W0=${W0:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t22}
M=${M:-/mnt/beegfs/$USER/t22c}
echo "host=$(hostname) nproc=$(nproc) $(lscpu | grep 'Model name' | sed 's/  */ /g') $(date -Is)"
IFS=';' read -ra G <<< "$RUNGROUPS"
for g in "${G[@]}"; do
  IFS='|' read -r rt cap tag runs <<< "$g"
  rt=$(echo $rt); W=$W0; [ "$rt" = old ] && W=$M/rt-old
  echo "######## runtime $rt (W=$W) cap $cap tag $tag runs: $runs  $(date -Is)"
  W=$W RUNS="$runs" CAP=$cap TAG=$tag bash $W0/eval/baselines/setup/t22_perf.sh
  for r in $runs; do
    IFS=: read -r id n _ <<< "$r"
    K=$W0/eval/results/$tag-$id-n$n/kstats.txt
    $W0/.env/bin/python $W0/eval/baselines/setup/t22c_kstats.py /mnt/beegfs/$USER/cuvein_traces/$tag-$id-n$n > $K
    awk 'NR <= 12 || /not JSON/ {print} END {if (NR > 12) print "  ... (" NR - 1 " kernel JSONs: " FILENAME ")"}' $K
  done
done
echo "== done $(date -Is)"

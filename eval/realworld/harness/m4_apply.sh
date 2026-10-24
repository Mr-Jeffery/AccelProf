#!/bin/bash
# T21b: apply the m4 reanalysis of hecbench-hungarian-1 (arrays 319392_2 buggy, 319541 fixed): m4 shard CSVs and attribution become the main-flavor files; then score.
R=/home/fzheng4/wt-t21b/eval/results/realworld
cd /home/fzheng4/wt-t21b || exit 1
cp $R/baselines-cuvein-shardhecbench-hungarian-1-buggy-all.csv $R/baselines-cuvein-shardhecbench-hungarian-1-buggy-all.csv.m4-before
for v in buggy fixed; do
  cp $R/baselines-cuvein-shardm4-hecbench-hungarian-1-$v-all.csv $R/baselines-cuvein-shardhecbench-hungarian-1-$v-all.csv || exit 2
  cp /home/fzheng4/rean_m4/attr/hecbench-hungarian-1-$v.json $R/attrib/hecbench-hungarian-1-$v.json || exit 3
done
exec bash eval/realworld/harness/score_all.sh

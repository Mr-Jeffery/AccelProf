#!/usr/bin/env bash
# X11 stage A remaining collector-only runs (one job per (app, run)) and stage B (one job per (app, tool, run)).
cd /home/fzheng4/wt-x11
A=eval/x11/x11_a_collect.sbatch; B=eval/x11/x11_b_run.sbatch
: > eval/x_logs/x11/submitted_jobs.txt
# stage A: apps 2..10 (atomicCAS stays in the three running loops 327527-327529); control apps first
for app in overlap fpc gpp crs mr dxtc2 expdist knn tridiagonal; do
  for r in 1 2 3; do
    id=$(RUN=$r TAG=x11-co-r$r-$app IDS=$app sbatch --parsable -J x11co-$app-r$r $A)
    echo "A collector-only $app r$r $id" >> eval/x_logs/x11/submitted_jobs.txt
  done
done
# stage B: runs per cell = the old row's (3 if it finished in the 1,200 s / 5,400 s stage, else 1)
runs() { case "$1:$2" in
  atomicCAS:racecheck) echo 3;; atomicCAS:*) echo 1;;
  dxtc2:*) echo 3;;
  knn:*) echo 1;;
  tridiagonal:iguard) echo 3;; tridiagonal:*) echo 1;;
  expdist:racecheck|expdist:iguard) echo 3;; expdist:*) echo 1;;
  mr:*) echo 3;; esac; }
for app in mr dxtc2 expdist tridiagonal atomicCAS knn; do
  for tool in racecheck iguard vector-clock scalar-clock; do
    n=$(runs $app $tool)
    for r in $(seq 1 $n); do
      id=$(APP=$app TOOL=$tool RUN=$r sbatch --parsable -J x11b-$app-$tool-r$r $B)
      echo "B $app $tool r$r $id" >> eval/x_logs/x11/submitted_jobs.txt
    done
  done
done
wc -l eval/x_logs/x11/submitted_jobs.txt

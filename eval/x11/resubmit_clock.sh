#!/usr/bin/env bash
# X11: cuRace clock-mode runs as recording job (rtx4060ti16g, cap 84,600 s) + analysis job (normal, 4 h, afterany recording).
# Smoke test first (overlap, scalar-clock, 1 run, 1,200 s).
cd /home/fzheng4/wt-x11
R=eval/x11/x11_b_run.sbatch; A=eval/x11/x11_b_analyze.sbatch; J=eval/x_logs/x11/submitted_jobs.txt
pair() { # app tool run [extra env via TAGX/CAP]
  local app=$1 tool=$2 r=$3
  local rid=$(APP=$app TOOL=$tool RUN=$r sbatch --parsable -J x11b-$app-$tool-r$r $R)
  local aid=$(APP=$app TOOL=$tool RUN=$r sbatch --parsable --dependency=afterany:$rid -J x11b-an-$app-$tool-r$r $A)
  echo "B2 $app $tool r$r rec=$rid analysis=$aid" >> $J; echo "$rid $aid"; }
# smoke
rid=$(APP=overlap TOOL=scalar-clock RUN=1 CAP=1200 TAGX=x11smoke-scalar-clock-overlap-r1 sbatch --parsable -J x11smoke-rec --time=01:00:00 $R)
aid=$(APP=overlap TOOL=scalar-clock RUN=1 TAGX=x11smoke-scalar-clock-overlap-r1 sbatch --parsable --dependency=afterany:$rid -J x11smoke-an $A)
echo "SMOKE overlap scalar-clock rec=$rid analysis=$aid" >> $J; echo "smoke $rid $aid"
# stage B clock modes (atomicCAS dropped)
for app in mr dxtc2 expdist tridiagonal knn; do for tool in vector-clock scalar-clock; do
  case $app in mr|dxtc2) n=3;; *) n=1;; esac
  for r in $(seq 1 $n); do pair $app $tool $r > /dev/null; done
done; done
grep -c "^B2" $J

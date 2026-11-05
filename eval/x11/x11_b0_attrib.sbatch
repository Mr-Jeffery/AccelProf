#!/usr/bin/env bash
#SBATCH --job-name=x11-src2
#SBATCH --partition=normal
#SBATCH --time=00:30:00
#SBATCH --output=/home/fzheng4/wt-x11/eval/x_logs/x11/srccheck-attrib-%j.log
# X11 source check: which commits in 6a8c46c4..7d2d3c56 touch source files (not Makefile/CMakeLists.txt) of each app; dxtc2 compress() attribution.
cd /home/fzheng4/x11-work/HeCBench
for a in atomicCAS dxtc2 knn tridiagonal expdist mr; do
  echo "=== $a: commits touching src/$a-cuda/ : $(git rev-list --count 6a8c46c4..7d2d3c56 -- src/$a-cuda/); source files (not Makefile/CMake):"
  git log --format="%h %s" --name-only 6a8c46c4..7d2d3c56 -- src/$a-cuda/ | awk '/^[0-9a-f]{8} /{h=$0;next} NF&&$0!~/(Makefile|CMakeLists.txt)$/{print h " :: " $0}' | sort -u
done
echo "=== dxtc2 attribution of the removed colorSums/bestFitLine/loadColorBlock"
git log --format="%h %s" 6a8c46c4..7d2d3c56 -S"loadColorBlock" -- src/dxtc2-cuda/main.cu
git log --format="%h %s" 6a8c46c4..7d2d3c56 -S"sums[idx ^ 8]" -- src/dxtc2-cuda/main.cu

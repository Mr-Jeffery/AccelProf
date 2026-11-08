#!/usr/bin/env bash
#SBATCH --job-name=x11-src
#SBATCH --partition=normal
#SBATCH --time=01:00:00
#SBATCH --output=/home/fzheng4/wt-x11/eval/x_logs/x11/srccheck-clone-%j.log
# X11 source check: blobless clone of zjin-lcf/HeCBench (full history, blobs on demand), then the log/diff of src/<app>-cuda/ for 6a8c46c4..7d2d3c56.
set -u
D=/home/fzheng4/x11-work/HeCBench
[ -d $D/.git ] || git clone --filter=blob:none --no-checkout https://github.com/zjin-lcf/HeCBench.git $D
cd $D
git cat-file -t 6a8c46c4651dbe85e16a787d9a786cfe8f80e00d 7d2d3c567be522a2104065165de0a4a233a6ea1a
git merge-base --is-ancestor 6a8c46c4 7d2d3c56 && echo "6a8c46c4 is an ancestor of 7d2d3c56"
git log -1 --format="%h %cI %s" 6a8c46c4; git log -1 --format="%h %cI %s" 7d2d3c56
echo "commits in range: $(git rev-list --count 6a8c46c4..7d2d3c56)"
for a in atomicCAS dxtc2 knn tridiagonal expdist mr; do
  echo "=== $a"; git log --format="%h %cI %s" 6a8c46c4..7d2d3c56 -- src/$a-cuda/
done
mkdir -p /home/fzheng4/wt-x11/eval/x_logs/x11/srccheck
for a in atomicCAS dxtc2 knn tridiagonal expdist mr; do git diff 6a8c46c4 7d2d3c56 -- src/$a-cuda/ > /home/fzheng4/wt-x11/eval/x_logs/x11/srccheck/$a.diff; wc -l /home/fzheng4/wt-x11/eval/x_logs/x11/srccheck/$a.diff; done

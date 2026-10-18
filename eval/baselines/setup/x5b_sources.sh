#!/bin/bash
# X5 byte pairs: the cc_vertex_data source of every program in the `other` bin (read only).
# For each distinct dot basename: the .cu files of that name under the corpora, and inside
# cc_vertex_data the lines that touch updated[] or call __syncwarp / __syncthreads.
C=/mnt/beegfs/fzheng4/home_archive/eval_baselines/corpora
CSV=${1:-/home/fzheng4/wt-x5-byte-pairs/eval/results/x5/barrier_ordered_pairs.csv}
grep ",other," "$CSV" | grep "^P[13]," | cut -d, -f5 | sed 's/::.*//; s/\.sm_[0-9]*\.dot$//' | sort -u |
while read -r n; do
  echo "=== $n"
  find -L "$C" -name "$n.cu" 2>/dev/null | while read -r f; do
    echo "--- $f ($(md5sum "$f" | cut -c1-12))"
    awk '/__global__ void cc_vertex_data/{on=1} on{print FNR": "$0} on&&/^}/{exit}' "$f" |
      grep -E "cc_vertex_data|updated|__syncwarp|__syncthreads|for \(|while"
  done
done

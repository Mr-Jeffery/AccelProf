#!/bin/bash
# X5 byte pairs: what is at the syncwarp pcs outside the kernel cluster (0x10a0 / 0x1010)? (read only)
T=/mnt/beegfs/fzheng4/cuvein_traces/final-2026-10
C=/mnt/beegfs/fzheng4/home_archive/eval_baselines/corpora/Indigo3Suite/generatedCodes/CUDA/CC-CUDA
for P in P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_Atomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n:10a0 \
         P1-CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Warp_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug-default-100n:1010; do
  ID=${P%%:*}; PC=${P##*:}
  DOT=$(ls $T/$ID/dots/*.dot)
  echo "########## $ID  pc 0x$PC  dot $DOT"
  echo "-- clusters:"; grep -o 'subgraph "*cluster_[^" {]*' "$DOT"
  echo "-- lines mentioning $PC or WARPSYNC / CALL / RET:"
  grep -o "$PC:[^\\]*\|[0-9a-f]\{4\}: *[^\\]*\(WARPSYNC\|CALL\|RET\)[^\\]*" "$DOT" | head -20
  N=${ID#P?-}; N=${N%-*}; N=${N%-default}
  F=$C/$N.cu; [ -f "$F" ] || F=$(find -L /mnt/beegfs/fzheng4/home_archive/eval_baselines/corpora -name "$N.cu" | head -1)
  echo "-- source $F: syncwarp / any / ballot / device functions"
  grep -n "__syncwarp\|_sync(\|__device__\|__global__\|atomic" "$F" | head -40
done

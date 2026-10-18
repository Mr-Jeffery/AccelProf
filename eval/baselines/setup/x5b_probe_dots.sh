#!/bin/bash
P=CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug
T=/mnt/beegfs/fzheng4/cuvein_traces
for s in evcand t9-after t10-after t12-after t14-after t16-certain final-2026-10; do
  d=$T/$s/P1-$P-default-100n
  echo "$s dot=$(md5sum $d/dots/*.dot | cut -c1-12) size=$(stat -c %s $d/vector-clock/kernel_2.json) events=$(grep -c '"hb_events": \[' $d/vector-clock/kernel_2.json) meta=$(grep -o '"libsanalyzer[^,]*' $d/meta.json | head -1)"
done
echo ----
awk '/cc_vertex_data/,/^}/' /mnt/beegfs/fzheng4/home_archive/eval_baselines/corpora/Indigo3Suite/generatedCodes/CUDA/CC-CUDA/$P.cu | head -70

#!/bin/bash
# X9 R6: chunk the conv sm80/sm75/sm89, s32_interleaved, reduction_device and epilogue_threadblock binaries (per launch 0.68 s, budget 700 s)
PY=/home/fzheng4/AccelProf/.env/bin/python; C=/home/fzheng4/wt-x9/eval/cutlass/harness/x9_chunks.py
for x in "conv_device_tensorop_f8_sm89 conv-sm80" "conv_device_tensorop_f16_sm80 conv-sm80" "conv_device_tensorop_f32_sm75 conv-sm80" \
         "conv_device_tensorop_f32_sm80 conv-sm80" "conv_device_tensorop_f32_tf32_sm80 conv-sm80" "conv_device_tensorop_s32_interleaved conv-sm80" \
         "reduction_device reduction" "epilogue_threadblock epilogue-unit"; do
  set -- $x; $PY $C --prog $1 --family $2 --budget 700 --per-launch 0.68 || echo "FAILED $1"
done

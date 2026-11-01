# X9 recording groups (manifest ids: whole binary -all, or gtest chunks -cNN from x9_chunks.py), sourced by submissions
p() { for x in "$@"; do printf "cutlass-%s " $x; done; }
R1=$(p gemm_device_blas3-c00 gemm_device_blas3-c01 gemm_device_blas3-c02 gemm_device_broadcast-all)
R2=$(p gemm_device_simt-all gemm_device_simt_3x-c00 gemm_device_simt_3x-c01 conv_device_simt-c00 conv_device_simt-c01 gemm_device_blas3_gaussian-all epilogue_thread-all epilogue_threadblock-all epilogue_warp-all)
R3=$(p gemm_device_tensorop_f32_tf32_sm80-all gemm_device_tensorop_f64-all gemm_device_tensorop_f16_sm80-all gemm_device_tensorop_f32_sm80-c00 gemm_device_tensorop_f32_sm80-c01 gemm_device_tensorop_f32_sm80-c02 gemm_device_tensorop_f32_sm80_3x-all)
R4=$(p gemm_device_mixed_input_tensorop_sm80-all gemm_device_sparse_tensorop_sm80-all gemm_device_tensorop_s32_sm80-all gemm_device_tensorop_planar_complex-c00 gemm_device_tensorop_planar_complex-c01 gemm_device_tensorop_sm89-all gemm_device_tensorop_sm89_blockwise-all)
R5=$(p gemm_device_tensorop_sm75-c00 gemm_device_tensorop_sm75-c01 gemm_device_wmma-all gemm_device_grouped-all gemm_device_grouped_blas3-all gemm_device_grouped_rank_2k_scheduler-all gemm_device_grouped_scheduler-all gemm_device_gemm_with_fused_epilogue_tensorop-c00 gemm_device_gemm_with_fused_epilogue_tensorop-c01 gemm_device_gemm_with_fused_epilogue_tensorop-c02)
# R6: conv sm80/sm75/sm89 + s32_interleaved chunks, conv s32, reduction (device chunks, kernel, thread), epilogue_threadblock chunks
# (x9_chunks.py --budget 700 --per-launch 0.68, eval/cutlass/harness/r6_chunks.sh). conv f32_sm70 runs 0 tests on sm_89: not recorded.
R6=$(cut -d, -f1 /home/fzheng4/wt-x9/eval/cutlass/manifest_cutlass.csv | grep -E '^cutlass-(conv_device_tensorop_(f8_sm89|f16_sm80|f32_sm75|f32_sm80|f32_tf32_sm80|s32_interleaved)-c|reduction_device-c|epilogue_threadblock-c)' | tr '\n' ' ')
R6="$R6 $(p conv_device_tensorop_s32-all reduction_kernel-all reduction_thread-all)"

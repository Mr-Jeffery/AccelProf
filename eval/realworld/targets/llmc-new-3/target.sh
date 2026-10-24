# llmc-new-3: softmax_autoregressive_backward_kernel7 / _kernel8 block_acc shared-memory races (R1, T21c candidate).
# Pinned (buggy) f1e2ace651495b74ae22d45d1723443fd00ecd3a (karpathy/llm.c); no fix commit, only the buggy variant is built.  Route R1: the repo's own dev/cuda
# program attention_backward.cu with the project's own nvcc flags from dev/cuda/Makefile (CFLAGS = -O3 --use_fast_math, NVCCFLAGS = -lcublas -lcublasLt -std=c++17;
# the Makefile's `__nvcc_device_query` GPU probe is replaced by $RW_NVCC_FLAGS = -arch=sm_89, i.e. SASS sm_89 + PTX compute_89) plus -lineinfo.
# Host-side edits ONLY (sed on a copy in the node-local build tree, outside every kernel; one line replaced by one line so source line numbers are unchanged):
#   main(): `int B = 4;` -> `int B = 1;`,  `int T = 1024;` -> `int T = 64;`   (the table's "B=1, T=64"; C=768, NH=12 unchanged; correctness pass uses block_size 256)
#   main(): the benchmark sweep `for (int j = 0; j < sizeof(block_sizes) / sizeof(int); j++)` -> `j < 0` (skipped, as the record says to trim it)
# The applied edit is saved as host-edits.txt next to the artifact.  t_cmd runs kernel 7 and then kernel 8 (the record names both).
T_ROUTE=R1; T_KERNEL=softmax_autoregressive_backward_kernel; T_SPACE=shared; T_EXE=attention_backward; T_ARTIFACTS="attention_backward host-edits.txt"
t_export() {   # login node
  "$HARNESS/export_rev.sh" cand/llm.c "$2" "$3" dev/cuda llmc train_gpt2_fp32.cu
}
t_build() {    # cwd = $OUT (node-local)
  cp "$SRC"/dev/cuda/common.h "$SRC"/dev/cuda/attention_backward.cu . || return 1
  cp attention_backward.cu attention_backward.cu.orig
  sed -i -e 's/^    int B = 4;$/    int B = 1;/' -e 's/^    int T = 1024;$/    int T = 64;/' \
         -e 's/^    for (int j = 0; j < sizeof(block_sizes) \/ sizeof(int); j++) {$/    for (int j = 0; j < 0; j++) {/' attention_backward.cu
  diff -u attention_backward.cu.orig attention_backward.cu > host-edits.txt
  [ "$(grep -c '^[-+] ' host-edits.txt)" = 6 ] || { echo "host edits did not apply as expected:"; cat host-edits.txt; return 1; }
  cat host-edits.txt
  nvcc -O3 --use_fast_math $RW_NVCC_FLAGS $RW_LINEINFO -lcublas -lcublasLt -std=c++17 attention_backward.cu -o attention_backward
}
t_cmd() { echo "$ART/attention_backward 7 && $ART/attention_backward 8"; }

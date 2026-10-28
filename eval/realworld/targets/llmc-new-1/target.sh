# llmc-new-1: layernorm_backward_kernel10 cross-block hand-off through global scratch (plain store128 partials, relaxed atomicInc, plain load128 by the last block) (R1, T21c candidate).
# Pinned (buggy) f1e2ace651495b74ae22d45d1723443fd00ecd3a (karpathy/llm.c); no fix commit, only the buggy variant is built.  Route R1: the repo's own dev/cuda
# program layernorm_backward.cu with the project's own nvcc flags from dev/cuda/Makefile (CFLAGS = -O3 --use_fast_math, NVCCFLAGS = -lcublas -lcublasLt -std=c++17;
# the Makefile's `__nvcc_device_query` GPU probe is replaced by $RW_NVCC_FLAGS = -arch=sm_89, i.e. SASS sm_89 + PTX compute_89, the same as the Makefile would
# generate with GPU_COMPUTE_CAPABILITY=89) plus -lineinfo.  The file defines ENABLE_BF16 itself (floatX = nv_bfloat16).
# Host-side edits ONLY (sed on a copy in the node-local build tree, outside every kernel; line numbers of the source are unchanged, one line replaced by one line):
#   main(): `int B = 8;` -> `int B = 1;`,  `int T = 1024;` -> `int T = 64;`   (the table's "recompiled with B=1, T=64"; C stays 1600)
#   main(): the second `for (int j = 0; j < sizeof(block_sizes) / sizeof(int); j++)` (the 100-repeat timing sweep after "now time the kernel") -> `j < 0`
#   (timing loop skipped: 6 block sizes x 100 repeats would multiply the thread-level accesses ~100-fold; the correctness sweep over block sizes 32..1024 is kept).
# The applied edit is saved as host-edits.txt next to the artifact.
T_ROUTE=R1; T_KERNEL=layernorm_backward_kernel10; T_SPACE=global; T_RACECHECK=na; T_EXE=layernorm_backward; T_ARTIFACTS="layernorm_backward host-edits.txt"
t_export() {   # login node
  "$HARNESS/export_rev.sh" cand/llm.c "$2" "$3" dev/cuda llmc
}
t_build() {    # cwd = $OUT (node-local)
  cp "$SRC"/dev/cuda/common.h "$SRC"/dev/cuda/layernorm_backward.cu . || return 1
  cp layernorm_backward.cu layernorm_backward.cu.orig
  sed -i -e 's/^    int B = 8;$/    int B = 1;/' -e 's/^    int T = 1024;$/    int T = 64;/' \
         -e '/now time the kernel/{n;s/j < sizeof(block_sizes) \/ sizeof(int)/j < 0/}' layernorm_backward.cu
  diff -u layernorm_backward.cu.orig layernorm_backward.cu > host-edits.txt
  [ "$(grep -c '^[-+] ' host-edits.txt)" = 6 ] || { echo "host edits did not apply as expected:"; cat host-edits.txt; return 1; }
  cat host-edits.txt
  nvcc -O3 --use_fast_math $RW_NVCC_FLAGS $RW_LINEINFO -lcublas -lcublasLt -std=c++17 layernorm_backward.cu -o layernorm_backward
}
t_cmd() { echo "$ART/layernorm_backward 10"; }

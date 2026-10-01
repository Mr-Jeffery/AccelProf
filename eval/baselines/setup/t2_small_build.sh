#!/usr/bin/env bash
# T2 step 4: reduced-size builds of the four cuHadron host/inter-kernel programs, whose
# shipped sizes (2.6e8 / 1.3e10 accesses; 1e8-iteration single-thread loops) time out on
# trace volume alone. Each size constant becomes a compile-time define whose default is
# the shipped value (so the source keeps its meaning), and the build passes a small value:
#   asyncmemcpy/memcpy_htod_kernel_race   N = 256Mi -> T2_N = 4096 elements
#   asyncmemcpy/kernel_memcpy_dtoh_race   N = 512Mi -> 65536, KERNEL_N = 64Mi -> 8192
#   interkernel/global_readwrite_race     producer loop 5e7 -> 1000, consumer loop 1e6 -> 1000
#   interkernel/global_writewrite_race    both loops 5e7 -> 1000
# racy (default) and fixed (-DFIXED), sm_89, -lineinfo --cudart shared, into
# eval/baselines/bin/P6small/ (build output, gitignored like every eval/baselines/bin/*).
# The rows are eval/baselines/setup/manifest.t2small.csv. Needs nvcc (a compute node).
set -e
A=/home/fzheng4/AccelProf
SRC=$A/cuHadron; OUT=${OUT:-$A/eval/baselines/bin/P6small}
T=$(mktemp -d); mkdir -p $OUT
patch_src() {   # patch_src <in> <out> <sed script>: constant -> #ifndef define (default = shipped)
  { printf '%s\n' "$3" | sed -n 's/^#D //p'; sed "$(printf '%s\n' "$3" | grep -v '^#D ')" "$1"; } > "$2"
}
patch_src $SRC/asyncmemcpy/memcpy_htod_kernel_race.cu $T/htod.cu \
'#D #ifndef T2_N
#D #define T2_N (256ULL * 1024 * 1024)
#D #endif
s/const size_t N = 256ULL \* 1024 \* 1024;/const size_t N = T2_N;/'
patch_src $SRC/asyncmemcpy/kernel_memcpy_dtoh_race.cu $T/dtoh.cu \
'#D #ifndef T2_N
#D #define T2_N (512 * 1024 * 1024)
#D #endif
#D #ifndef T2_KERNEL_N
#D #define T2_KERNEL_N (64 * 1024 * 1024)
#D #endif
s/const int N = 512 \* 1024 \* 1024;/const int N = T2_N;/
s/const int KERNEL_N = 64 \* 1024 \* 1024;/const int KERNEL_N = T2_KERNEL_N;/'
patch_src $SRC/interkernel/global_readwrite_race.cu $T/ikrw.cu \
'#D #ifndef T2_ITERS
#D #define T2_ITERS 50000000
#D #endif
#D #ifndef T2_READS
#D #define T2_READS 1000000
#D #endif
s/i < 50000000;/i < T2_ITERS;/
s/i < 1000000;/i < T2_READS;/'
patch_src $SRC/interkernel/global_writewrite_race.cu $T/ikww.cu \
'#D #ifndef T2_ITERS
#D #define T2_ITERS 50000000
#D #endif
s/i < 50000000;/i < T2_ITERS;/g'
for f in htod dtoh ikrw ikww; do
  grep -c "T2_" $T/$f.cu | xargs echo "$f: T2_ occurrences"
done
N="nvcc -arch=sm_89 -lineinfo --cudart shared"
for v in racy fixed; do
  F=""; [ $v = fixed ] && F="-DFIXED"
  $N $F -DT2_N=4096ULL -o $OUT/asyncmemcpy__memcpy_htod_kernel_race__$v $T/htod.cu
  $N $F -DT2_N=65536 -DT2_KERNEL_N=8192 -o $OUT/asyncmemcpy__kernel_memcpy_dtoh_race__$v $T/dtoh.cu
  $N $F -DT2_ITERS=1000 -DT2_READS=1000 -o $OUT/interkernel__global_readwrite_race__$v $T/ikrw.cu
  $N $F -DT2_ITERS=1000 -o $OUT/interkernel__global_writewrite_race__$v $T/ikww.cu
done
ls -la $OUT; rm -rf $T

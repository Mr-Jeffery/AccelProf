#!/bin/bash
# T21c copy of T21b's script (study/realworld-recall): worktree wt-t21c, store realworld-2026-10-t21c, results eval/results/realworld_t21c, manifest_t21c.csv.
# T21b: rebuild the T21a artifacts with the CUDA runtime linked SHARED (--cudart shared), into a separate tree.
# Why: accelprof LD_PRELOADs libcompute_sanitizer.so, which calls cudart symbols (cudaDeviceGetStreamPriorityRange ...)
# that only resolve when the application itself loads libcudart.so; the T21a artifacts (all but llama.cpp) link the static
# runtime and die with "undefined symbol" before the first kernel (eval/baselines/build_corpora.py:50, HARDENING_REPORT.md:144).
# Same sources, same flags, same toolkit (13.4); only the runtime linkage differs. The SASS is then compared with T21a's artifact.
#   IDS="cccl-1 cccl-2" sbatch -p normal ... relink_job.sh
for _d in /home/fzheng4/AccelProf /mnt/beegfs/fzheng4 /home/fzheng4/wt-t21c /home/fzheng4/wt-t21c/eval/realworld; do
  timeout 10 ls "$_d" >/dev/null 2>&1 || { echo "T21b relink: host=$(hostname) missing or unreadable $_d" >&2; exit 97; }
done
W=/home/fzheng4/wt-t21c
export CUDA_HOME=${CUDA_HOME:-/usr/local/cuda-13.4}   # T21c: the candidates were built with 13.4; /usr/local/cuda is 13.3 on some nodes (c26)
export RW_ART_ROOT=/mnt/beegfs/fzheng4/realworld_t21c/build
export RW_CUDART_SHARED=1
CUDA13=/usr/local/cuda-13.4
export RW_NVCC_APPEND_EXTRA="--cudart shared -ldl -Xlinker -rpath=$CUDA13/lib64"
export NVCC_APPEND_FLAGS="$RW_NVCC_APPEND_EXTRA"
export RW_CMAKE_EXTRA="-DCMAKE_CUDA_RUNTIME_LIBRARY=Shared -DCMAKE_EXE_LINKER_FLAGS=-ldl"
export NJOBS=${NJOBS:-${SLURM_CPUS_PER_TASK:-8}}
mkdir -p /mnt/local/fzheng4/rw 2>/dev/null && [ -w /mnt/local/fzheng4/rw ] || { echo "T21b relink: host=$(hostname) /mnt/local/fzheng4 not writable" >&2; exit 95; }
cd $W/eval/realworld/harness || exit 1
echo "T21b relink: host=$(hostname) job=${SLURM_JOB_ID:-none} $(date -Is) cpus=$NJOBS cuda=$(readlink -f /usr/local/cuda) NVCC_APPEND_FLAGS=$NVCC_APPEND_FLAGS"
mkdir -p $RW_ART_ROOT $W/eval/x_logs/relink
for id in $IDS; do
  echo "=== $(date -Is) build $id"
  T21_WT=$W bash ./rw.sh $id build > $W/eval/x_logs/relink/build-$id.out 2>&1
  rc=$?
  echo "  build rc=$rc: $(grep -E '^== build .* rc=|artifacts ->' $W/eval/x_logs/relink/build-$id.out | tr '\n' ' ' | cut -c1-300)"
  [ $rc -eq 0 ] || { tail -5 $W/eval/x_logs/relink/build-$id.out; continue; }
  for v in buggy fixed; do
    [ -d /mnt/beegfs/fzheng4/realworld/build/$id/$v ] || continue   # T21c: candidates have the buggy build only
    exe=$(python3 - $id $v <<'PY'
import csv, sys
for r in csv.DictReader(open('/home/fzheng4/wt-t21c/eval/realworld/manifest.csv')):
    if r['id'] == f"{sys.argv[1]}-{sys.argv[2]}":
        print(r['exe'])
PY
)
    new=${exe/\/mnt\/beegfs\/fzheng4\/realworld\/build/$RW_ART_ROOT}
    echo "  $v: orig=$exe new=$new"
    readelf -d $new | grep -E "NEEDED.*cudart|RPATH|RUNPATH" | sed 's/^/    /'
    /usr/bin/env python3 ./rw_sass_equal.py "$exe" "$new" | tail -3 | sed 's/^/    /'
  done
done
echo "=== $(date -Is) done"

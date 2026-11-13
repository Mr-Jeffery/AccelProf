# X13 environment (sourced): the worktree is the runtime (lib -> stage-x13/rt-lib), as T26's.
W=${W:-/home/fzheng4/wt-shard-balance}; S=${S:-/home/fzheng4/stage-x13}; INST=/home/fzheng4/AccelProf
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
export CUDA_HOME=/usr/local/cuda-13.3 CUDA_PATH=/usr/local/cuda-13.3
export PATH=$W/bin:$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:$CUDA_HOME/compute-sanitizer:$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}
for v in $(env | /usr/bin/grep -o '^\(YOSEMITE\|CAP\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_WORKERS
export PY=$INST/.env/bin/python
HEC=$INST/eval/baselines/corpora/HeCBench/src
BIN=$INST/eval/baselines/bin
X=$W/eval/x13
D=/mnt/beegfs/fzheng4/x13

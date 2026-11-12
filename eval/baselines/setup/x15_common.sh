# X15 common environment (sourced). CPU only.
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\|BASELINE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=/home/fzheng4/wt-x15 CUVEIN_HOME=/home/fzheng4/wt-x15
W=/home/fzheng4/wt-x15; PY=/home/fzheng4/AccelProf/.env/bin/python
B=/mnt/beegfs/fzheng4/cuvein_traces; HX=/home/fzheng4/x15rw/t21c; SU=$W/eval/baselines/setup
ID=colmap-new-1-buggy
OUT=$W/eval/results/x15
for CH in /usr/local/cuda-13.4 /usr/local/cuda-13.3 /usr/local/cuda; do [ -x $CH/bin/nvdisasm ] && { export CUDA_HOME=$CH; break; }; done
[ -n "${CUDA_HOME:-}" ] || { echo "no nvdisasm on $(hostname)"; exit 96; }
export PATH=$CUDA_HOME/bin:$PATH LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
HD=$HX/eval/realworld/harness

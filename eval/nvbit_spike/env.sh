# Source on the compute node (inside the T13 allocation). Clean environment for
# NVBit runs: no Sanitizer collector, no YOSEMITE_* variables.
export CUDA_HOME=/usr/local/cuda-13.3
export PATH=$CUDA_HOME/bin:/usr/bin:/bin
export LD_LIBRARY_PATH=$CUDA_HOME/lib64
export CXX=/usr/bin/g++
unset LD_PRELOAD CUDA_INJECTION64_PATH
for v in $(env | sed -n 's/^\(YOSEMITE_[A-Z_]*\)=.*/\1/p'); do unset "$v"; done
export NVBIT_ROOT=$HOME/incoming/nvbit
export SPIKE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export WORK=$NVBIT_ROOT/work
mkdir -p "$WORK"

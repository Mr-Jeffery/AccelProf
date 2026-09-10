export ACCEL_PROF_HOME=$(pwd)
export PATH=${ACCEL_PROF_HOME}/bin:${PATH}
export LD_LIBRARY_PATH="$CUDA_HOME/compute-sanitizer:$LD_LIBRARY_PATH"

INPUT_PATH="$1"
INPUT_DIR=$(dirname "$INPUT_PATH")
INPUT_BASENAME=$(basename "$INPUT_PATH")
FILE_NAME=${INPUT_BASENAME%.*}

# CFG generation
OUT_DIR=${INPUT_DIR}/${FILE_NAME}_extracted_cubins
mkdir -p "$OUT_DIR"
cd "$OUT_DIR"
cuobjdump -xelf all "$INPUT_PATH"

shopt -s nullglob
cubin_files=( *.cubin )
if [ ${#cubin_files[@]} -eq 0 ]; then
    cubin_files=( *.elf )
fi

for cubin in "${cubin_files[@]}"; do
    BIN_NAME=${cubin%.*}
    nvdisasm -bbcfg -poff "$cubin" > "${BIN_NAME}.dot"
    # dot -Tpng "${BIN_NAME}.dot" -o "${BIN_NAME}.png"
done

# Atomic-scope sidecar (pc -> coherence scope) for the dynamic-HB engine. Scope is
# a static SASS property only in the CFG, so distill it here (before the trace run)
# into a file the analyzer reads via YOSEMITE_ATOMIC_SCOPE_FILE.
if [ ${#cubin_files[@]} -gt 0 ]; then
    conda run -p "$ACCEL_PROF_HOME/.env" python \
        "$ACCEL_PROF_HOME/python/atomic_scope_sidecar.py" *.dot -o atomic_scope.txt \
        && export YOSEMITE_ATOMIC_SCOPE_FILE="$(pwd)/atomic_scope.txt"
fi
shopt -u nullglob

# JSON generation
cd "$INPUT_DIR"
# -n 1: single replay worker so edge ancient/current order is temporal
# (multi-worker replay records analyzer processing order for cross-block pairs)
# YOSEMITE_HB_TRACE=1: dump the raw per-instance event stream (hb_events) for the
# Phase 2 happens-before oracle (python/hb_oracle.py). Opt-in, corpus-scale.
YOSEMITE_HB_TRACE=1 accelprof -v -t pc_dependency_analysis -n 1 "./$INPUT_BASENAME"
cd "$(dirname "$0")"
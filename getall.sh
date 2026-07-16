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
shopt -u nullglob

# JSON generation
cd "$INPUT_DIR"
accelprof -v -t pc_dependency_analysis "./$INPUT_BASENAME"
cd "$(dirname "$0")"
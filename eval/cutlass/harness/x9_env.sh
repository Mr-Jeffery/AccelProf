# eval/cutlass/harness/x9_env.sh -- `source` at the top of every X9 job (GPU or CPU).
# Sets W (worktree), A (installed runtime), CB (BeeGFS root), the CUDA/gcc paths and PY; checks the installed runtime's
# hashes against f551ca0 (libsanalyzer 5a20fd14, collector b746b4dd, fatbin a2d7368b): exit 99 on a mismatch, 97 when
# home/BeeGFS/the worktree is unreadable. Exports X9_HS/X9_HC/X9_HF/X9_HL (16-hex prefixes) for meta.json.
export W=/home/fzheng4/wt-x9 A=/home/fzheng4/AccelProf CB=/mnt/beegfs/fzheng4/cutlass
for _d in $A /mnt/beegfs/fzheng4 $W $A/lib/libcompute_sanitizer.so; do
  timeout 10 ls "$_d" >/dev/null 2>&1 || { echo "X9 env: host=$(hostname) missing or unreadable $_d" >&2; exit 97; }
done
for _k in $(env | grep -E '^(YOSEMITE_|CUVEIN_|BASELINE_)' | cut -d= -f1); do unset "$_k"; done
unset _d _k
export ACCEL_PROF_HOME=$A CUDA_HOME=/usr/local/cuda-13.3 CUDA_PATH=/usr/local/cuda-13.3
[ -x $CUDA_HOME/bin/nvdisasm ] || { echo "X9 env: host=$(hostname) $CUDA_HOME missing" >&2; exit 96; }
source $A/eval/baselines/gpu_env.sh
export ACCEL_PROF_HOME=$A CUVEIN_HOME=$W
export PATH=$CUDA_HOME/bin:/opt/ohpc/pub/compiler/gcc/12.4.0/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
export PY=$A/.env/bin/python
_h16() { sha256sum "$1" | cut -c1-16; }
_lsa=$(ldd $A/lib/libcompute_sanitizer.so | awk '/libsanalyzer.so/{print $3; exit}')
export X9_LSA=$_lsa X9_HS=$(_h16 $_lsa) X9_HC=$(_h16 $A/lib/libcompute_sanitizer.so)
export X9_HF=$(_h16 $A/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin)
export X9_HL=$(_h16 $A/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency_late.fatbin)
if [ "$X9_HS" != 5a20fd14ab6c6806 ] || [ "$X9_HC" != b746b4dd23e90f46 ] || [ "$X9_HF" != a2d7368bc1c61986 ]; then
  echo "X9 env: RUNTIME HASH MISMATCH on $(hostname): $X9_HS $X9_HC $X9_HF (want 5a20fd14ab6c6806 b746b4dd23e90f46 a2d7368bc1c61986)" >&2; exit 99
fi
echo "X9 env: host=$(hostname) job=${SLURM_JOB_ID:-none} $(date -Is) runtime=$(git -C $A rev-parse --short HEAD) branch_head=$(git -C $W rev-parse --short HEAD) libsanalyzer=$X9_HS ($_lsa) collector=$X9_HC fatbin=$X9_HF late=$X9_HL"

#!/usr/bin/env bash
#SBATCH --job-name=t10-e3
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=02:00:00
# T10 step 3, E3: the four ECL-Suite race-free egr-input codes (ECL-CC/GC/MIS/MST, the old
# E-suite's E3; eval/build_ecl.py) have no kept trace anywhere (the E-suite ran from a
# since-deleted worktree), so they are re-recorded here with the T10 private runtime, both
# modes, on the same torus-100 graph as E3 (Indigo3Suite input), into a new BeeGFS store; then
# the same traces are judged under the pre-T10 `generic` and the T10 `token` policy
# (t10_policy_compare.py: the oracle recomputes hb_races per policy, both modes' views).
# Sources: github.com/burtscher/ECL-Suite main, fetched on the login node to
# ~/incoming/ecl/ECL-Suite-main.tar.gz (sha256 be1e4139...).
#   W=<worktree> sbatch -p rtx4060ti16g -x c54,c2 -o <W>/build_logs/t10-e3-%j.log \
#       <W>/eval/baselines/setup/t10_e3.sh
set -u
W=${W:?W=<the T10 worktree>}; A=/home/fzheng4/AccelProf
cd $W || exit 1
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
source eval/baselines/gpu_env.sh
export CUDA_HOME=/usr/local/cuda-13.3 CUDA_PATH=/usr/local/cuda-13.3
export PATH=$W/bin:/usr/local/cuda-13.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:/usr/local/cuda-13.3/compute-sanitizer:${LD_LIBRARY_PATH:-}
unset CUVEIN_STRONG_LDST
echo "host=$(hostname) $(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader | head -1) HEAD=$(git -C $W rev-parse --short HEAD) collector $(sha256sum $W/lib/libcompute_sanitizer.so | cut -c1-16) libsanalyzer $(sha256sum $W/sanalyzer/wt_install/lib/libsanalyzer.so | cut -c1-16)"
E=/mnt/beegfs/$USER/t10-e3; rm -rf $E; mkdir -p $E/bin $E/src
tar -xzf /home/fzheng4/incoming/ecl/ECL-Suite-main.tar.gz -C $E/src
S=$E/src/ECL-Suite-main
# CUDA 13 dropped cudaDeviceProp::clockRate / memoryClockRate, which the codes only print in
# their banner (E3 was built with CUDA 12.9): print 0.0 instead; no kernel code changes.
sed -i 's/deviceProp\.clockRate \* 0\.001/0.0/; s/deviceProp\.memoryClockRate \* 0\.001/0.0/' \
    $S/src/racefree/egr-input/*/*.cu
for cu in $S/src/racefree/egr-input/*/*.cu; do
  n=$(basename $cu .cu)
  nvcc -arch=sm_89 -lineinfo --cudart shared -I $S/library -O3 $cu -o $E/bin/$n && echo "built $n"
done
IN=$A/eval/baselines/corpora/Indigo3Suite/inputs/undirect2dim_rand_torus_100n_400e.egr
R=$W/eval/results/t10-e3; mkdir -p $R
M=$R/manifest.e3.csv
echo "id,pset,program,build,input,exe,args,stdin,shared_mem,label,arrays_to_wrap,monitored_kernels,reps,timeout" > $M
for b in $E/bin/*; do
  [ -x "$b" ] || continue
  n=$(basename $b)
  echo "E3-$n-torus100,E3,$n,racefree,torus100,$b,$IN,,0,CLEAN,,,1,600" >> $M
done
cat $M
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/t10-e3
export BASELINE_MODES=vector-clock,scalar-clock
rm -rf $BASELINE_TRACE_DIR
$PY eval/baselines/parallel.py run --manifest $M --reps 1 --confirm --tag t10e3 \
    --results-dir $R --confirm-dir $E/confirm 2>&1 | tail -12
echo "== the same traces under generic and token"
$PY eval/baselines/t10_policy_compare.py $BASELINE_TRACE_DIR/E3-* --json $R/policy_compare.json 2>&1 | tail -80
echo "== done $(date -Is)"

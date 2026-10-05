#!/usr/bin/env bash
#SBATCH --job-name=t18-rtraw-sched
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=01:30:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t18-rtraw-sched-%j.log
# T18 (eval/A2_WINDOWS.md "Same source, two collectors"): race_interblock_none-lock_rtraw, five
# vector-clock recordings (getall.sh: CFG + sidecar + accelprof) under
#   installed : the T18 runtime (default fatbin = the pre-T15 device code, a2d7368b)
#   t15       : a private mirror of the runtime installed by 96698c1 (T15 collector f2933966, T15
#               default fatbin e9634312 -- the late-key code in the record callback), rebuilt
#               from the *.pre-t18-* backups; libsanalyzer is the installed one (T15's source
#               equals T18's there).
# then the verdicts and a2 flags of every run (t18_rtraw_verdicts.py).
set -u
A=/home/fzheng4/AccelProf; W=/home/fzheng4/wt-t18
M=/mnt/beegfs/$USER/rt-t15-mirror; OUT=/mnt/beegfs/$USER/t18-rtraw-schedules
source $A/eval/baselines/gpu_env.sh
export CUDA_HOME=/usr/local/cuda-13.3 PATH=/usr/local/cuda-13.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
rm -rf $M $OUT; mkdir -p $M/lib $M/nv-compute/lib $OUT
for x in bin .env build getall.sh; do ln -s $A/$x $M/$x; done; ln -s $W/python $M/python
cp $A/lib/libcompute_sanitizer.so.pre-t18-f2933966fb6924e9 $M/lib/libcompute_sanitizer.so
cp -r $A/nv-compute/lib/gpu_patch $M/nv-compute/lib/gpu_patch
cp $A/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin.pre-t18-e96343121c74ca0a $M/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin
h() { sha256sum "$1" | cut -c1-16; }
echo "host=$(hostname) installed: collector $(h $A/lib/libcompute_sanitizer.so) fatbin $(h $A/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin); t15 mirror: collector $(h $M/lib/libcompute_sanitizer.so) fatbin $(h $M/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin)"
exe=$A/ScoR/microbenchmarks/bin/race_interblock_none-lock_rtraw; base=$(basename $exe)
for rt in installed t15; do R=$A; [ $rt = t15 ] && R=$M
  for k in 1 2 3 4 5; do
    D=$OUT/$rt/$k; mkdir -p $D; cp $exe $D/$base
    ( cd $R && env -u YOSEMITE_HB_LATE_SEQ -u YOSEMITE_HB_MODE bash getall.sh $D/$base > $D/getall.log 2>&1 )
  done
done
$A/.env/bin/python $W/eval/baselines/t18_rtraw_verdicts.py $OUT

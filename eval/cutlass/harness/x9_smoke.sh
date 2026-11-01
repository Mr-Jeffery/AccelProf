#!/bin/bash
#SBATCH --job-name=x9-smoke
#SBATCH --partition=rtx4060ti16g,rtx4060ti8g,a5000ada
#SBATCH --nodes=1 --ntasks=1 --exclusive
#SBATCH --time=12:00:00
#SBATCH --exclude=c0,c1,c2,c21,c22,c23,c34,c37,c46,c54
#SBATCH --output=/home/fzheng4/wt-x9/eval/x_logs/x9-smoke-%j.log
# X9 step 2: per binary (BINS = paths relative to the build dir): SASS/PTX listing, gtest list, one native run (exit code,
# wall), and the kernel launch list (nsys, cuda_gpu_kern_sum) -> $CB/smoke/<name>.*
set -u
CB=/mnt/beegfs/fzheng4/cutlass; BLD=$CB/build; OUT=$CB/smoke; mkdir -p $OUT
timeout 10 ls $BLD >/dev/null || { echo "NODE-PROBLEM $(hostname)"; exit 97; }
export PATH=/usr/local/cuda-13.3/bin:$PATH LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
GPU=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader | tr '\n' ';')
IDX=$(nvidia-smi --query-gpu=index,compute_cap --format=csv,noheader | awk -F', *' '$2=="8.9"{print $1}')
IDX=$(echo "$IDX" | head -1)   # smoke only (not a recording): the first sm_89 GPU on multi-GPU nodes
[ -n "$IDX" ] || { echo "no sm_89 GPU: $GPU"; exit 98; }
export CUDA_VISIBLE_DEVICES=$IDX
NSYS=$(command -v nsys || ls /usr/local/cuda-13.3/nsight-systems*/bin/nsys /opt/nvidia/nsight-systems/*/bin/nsys 2>/dev/null | head -1)
echo "host=$(hostname) job=${SLURM_JOB_ID:-} gpu=[$GPU] nsys=[$NSYS] $(date -Is)"
for b in ${BINS:-}; do
  n=$(basename $b); exe=$BLD/$b
  case $b in */*) ;; *) exe=$(find $BLD/test/unit -name $n -type f -perm -u+x | head -1) ;; esac
  [ -x "$exe" ] || { echo "$n: MISSING"; continue; }
  echo "$n: exe=${exe#"$BLD"/}"
  cuobjdump --list-elf $exe > $OUT/$n.elf.txt 2>&1; cuobjdump --list-ptx $exe > $OUT/$n.ptx.txt 2>&1
  $exe --gtest_list_tests > $OUT/$n.tests.txt 2>&1
  ntests=$(grep -c '^  ' $OUT/$n.tests.txt)
  s=$(date +%s.%N); ( cd $(dirname $exe) && timeout 7200 $exe ${FILTER:+--gtest_filter=$FILTER} > $OUT/$n.native.txt 2>&1 ); rc=$?; e=$(date +%s.%N)
  echo "$n: elf=[$(grep -o 'sm_[0-9a-z]*' $OUT/$n.elf.txt | sort | uniq -c | tr '\n' ' ')] ptx_entries=$(grep -c -i ptx $OUT/$n.ptx.txt) tests=$ntests native_rc=$rc wall=$(echo "$e - $s" | bc)s $(grep -E '^\[  (PASSED|FAILED)|tests? from .* ran' $OUT/$n.native.txt | tr '\n' ' ')"
  if [ -n "$NSYS" ]; then
    ( cd $OUT && timeout 7200 $NSYS profile -t cuda -o $OUT/$n.nsys --force-overwrite true $exe ${FILTER:+--gtest_filter=$FILTER} > /dev/null 2>&1
      $NSYS stats -r cuda_gpu_kern_sum -f csv -o $OUT/$n $OUT/$n.nsys.nsys-rep > /dev/null 2>&1 )
    f=$(ls $OUT/$n*cuda_gpu_kern_sum*.csv 2>/dev/null | head -1)
    [ -n "$f" ] && echo "  launches: $(/home/fzheng4/AccelProf/.env/bin/python -c "import csv,sys; r=list(csv.DictReader(open(sys.argv[1]))); print(sum(int(x[\"Instances\"]) for x in r), \"over\", len(r), \"kernels\")" $f)"
  fi
done
echo "== done $(date -Is)"

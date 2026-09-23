#!/usr/bin/env bash
#SBATCH --job-name=t2-evidence
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=01:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t2-evidence-%j.log
# T2 step 1 (eval/HOST_MEMCPY_STUDY.md): what the Compute Sanitizer API gives the collector
# about host memcpys and stream/event ordering, and the order in which the callbacks fire.
# The four cuHadron asyncmemcpy programs run under the collector with NO instrumentation
# (-t code_check = GPU_NO_PATCH: every API callback, no per-access patch), so their 2.6e8 /
# 1.3e10 accesses are not traced. The T2 micro test is built in its four variants and run
# natively and under the same collector. Copies of the toolkit's Sanitizer headers go to
# build_logs/t2-headers/ (gitignored) for reading on the login node.
#   PIN8G=1 sbatch -p rtx4060ti8g eval/baselines/setup/t2_evidence.sh
set -u
W=${W:-/home/fzheng4/wt-T2}
cd "$W" || exit 1
export ACCEL_PROF_HOME=$W
source eval/baselines/gpu_env.sh
[ -n "${PIN8G:-}" ] && source eval/baselines/setup/pin8g.sh
EV=$W/eval/baselines/setup/t2_evidence; mkdir -p "$EV"
HD=$W/eval/baselines/setup/build_logs/t2-headers; mkdir -p "$HD"
echo "host=$(hostname) gpu=$(nvidia-smi -i ${CUDA_VISIBLE_DEVICES:-0} --query-gpu=name,compute_cap,driver_version --format=csv,noheader)"
nvcc --version | tail -2
compute-sanitizer --version | head -2
H=$CUDA_HOME/compute-sanitizer/include
ls -la "$H"
cp "$H"/*.h "$HD"/
R=/mnt/beegfs/$USER/t2_evidence; rm -rf "$R"; mkdir -p "$R"
run() {   # run <name> <exe> [tool]: collector log's [SANITIZER INFO] lines -> $EV/order_<name>.txt
  local name=$1 exe=$2 tool=${3:-code_check} d=$R/$1
  mkdir -p "$d"; ln -sf "$exe" "$d/$name"
  (cd "$d" && timeout 900 accelprof -v -t "$tool" "./$name" > stdout.txt 2>&1; echo "rc=$?" >> stdout.txt)
  echo "== $name ($tool): $(tail -1 "$d/stdout.txt") $(grep -m1 -i 'race\|complete\|host_memcpy_race' "$d/stdout.txt" | head -c 120)"
  grep "SANITIZER INFO" "$d/$name.accelprof.log" > "$EV/order_$name.txt"
  wc -l < "$EV/order_$name.txt"
}
for b in memcpy_htod_kernel_race kernel_memcpy_dtoh_race; do
  for v in racy fixed; do
    run "${b}__$v" "$W/eval/baselines/bin/P6/asyncmemcpy__${b}__$v.sm86.out"
  done
done
echo "== micro test"
B=$R/micro; mkdir -p "$B"
for v in racy fixed kfirst-racy kfirst-fixed; do
  F=""; case $v in fixed) F="-DFIXED";; kfirst-racy) F="-DKERNEL_FIRST";; kfirst-fixed) F="-DKERNEL_FIRST -DFIXED";; esac
  nvcc -arch=sm_89 -lineinfo --cudart shared $F -o "$B/host_memcpy_race_$v" python/testdata/host_memcpy_race.cu || echo "BUILD FAILED $v"
  echo "native $v: $("$B/host_memcpy_race_$v")"
  run "micro_$v" "$B/host_memcpy_race_$v"
done
echo "== done $(date -Is)"

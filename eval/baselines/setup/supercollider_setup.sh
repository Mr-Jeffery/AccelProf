#!/usr/bin/env bash
# B6 SuperCollider (PLDI'26) setup: fetch the Zenodo artifact, verify it, pull the
# Ubuntu 22.04 Singularity image its binaries need (GLIBC 2.34 vs EL8's 2.28), and
# run the smoke gate. There is nothing to build: the detector is a pass inside
# NVIDIA's proprietary ptxas and only pre-instrumented binaries are shipped.
#   bash eval/baselines/setup/supercollider_setup.sh          (login node: fetch+pull)
#   sbatch -p rtx4060ti16g -x c54 -t 00:20:00 --wrap 'bash .../supercollider_setup.sh gate'
set -u
REPO=/home/fzheng4/AccelProf
T=$REPO/eval/baselines/setup/tools; mkdir -p "$T/supercollider"
STATUS=$REPO/eval/baselines/setup/supercollider.status
log(){ echo "$@" | tee -a "$STATUS"; }
ZIP=$T/supercollider-artifacts-v1.zip
MD5=19759582d3e6f5274708b32326e3b7b9
export PATH=/opt/ohpc/pub/libs/singularity/3.7.1/bin:$PATH
export SINGULARITY_CACHEDIR=$T/supercollider/.sing_cache SINGULARITY_TMPDIR=$T/supercollider/.sing_tmp
mkdir -p "$SINGULARITY_CACHEDIR" "$SINGULARITY_TMPDIR"
if [ "${1:-fetch}" = fetch ]; then
  : > "$STATUS"; log "supercollider_setup $(date -Is) node=$(hostname)"
  [ -f "$ZIP" ] || wget -q -O "$ZIP" "https://zenodo.org/records/19058944/files/supercollider-artifacts-v1.zip?download=1"
  got=$(md5sum "$ZIP" | cut -d' ' -f1); log "zip md5=$got expected=$MD5"
  [ "$got" = "$MD5" ] || { log "FAIL: md5 mismatch"; exit 3; }
  [ -d "$T/supercollider/supercollider-artifacts" ] || unzip -q "$ZIP" -d "$T/supercollider"
  [ -f "$T/supercollider/ubuntu2204.sif" ] || singularity pull "$T/supercollider/ubuntu2204.sif" docker://ubuntu:22.04 >>"$STATUS" 2>&1
  A=$T/supercollider/supercollider-artifacts
  log "binaries: cuhadron=$(find $A/bin/cuhadron/instrumented -type f | wc -l) indigo=$(find $A/bin/indigo/instrumented -type f | wc -l) hecbench=$(ls $A/bin/hecbench/instrumented-balanced | wc -l)"
  log "requires: GLIBC $(objdump -T $A/bin/indigo/instrumented/conditional_edge_neighbor/conditional_edge_neighbor.out | grep -o 'GLIBC_[0-9.]*' | sort -V | tail -1) (host: $(ldd --version | head -1 | awk '{print $NF}')); driver 570+; CC>=8.0"
  log "compiler: NOT DISTRIBUTED (README: pass inside NVIDIA's proprietary ptxas) -> only shipped binaries can be measured"
  exit 0
fi
# gate (GPU node)
A=$T/supercollider/supercollider-artifacts; SIF=$T/supercollider/ubuntu2204.sif
log "gate $(date -Is) node=$(hostname) driver=$(nvidia-smi --query-gpu=driver_version,compute_cap --format=csv,noheader | head -1)"
run(){ singularity exec --nv "$SIF" env CUDA_INJECTION64_PATH=$A/lib64/librc-release.so "$@" 2>&1; }
o=$(run $A/bin/cuhadron/instrumented/intersubwarp/shared_writewrite_race.all.out)
echo "$o" | grep -q "RACECHECKER ENGAGED" && log "attach: OK" || { log "FAIL attach: $(echo "$o" | tail -3)"; exit 3; }
echo "$o" | grep -q "RACE CONDITIONS DETECTED" && log "racy cuHadron test: RACE reported" || log "racy cuHadron test: no report this attempt (probabilistic)"
o=$(run $A/bin/cuhadron/instrumented/false_positives/global_bytewise_writewrite.all.out)
echo "$o" | grep -q "RACE CONDITIONS DETECTED" && log "FP check: REPORTED (unexpected)" || log "FP check: clean"
log "GATE PASSED"

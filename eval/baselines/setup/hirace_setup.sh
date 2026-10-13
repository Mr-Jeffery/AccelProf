#!/usr/bin/env bash
# B2 HiRace setup (3-hour box). Clones + builds the pinned-LLVM pass+runtime under
# BeeGFS (LLVM is multi-GB; home is a 40 GB quota), installs clang++ to
# setup/hirace/bin/clang++. Absolute cd (sbatch $0 is the spool dir).
#   sbatch -p rtx4060ti16g -N1 -n1 -t 03:00:00 eval/baselines/setup/hirace_setup.sh
set -u
REPO=/home/fzheng4/AccelProf
cd "$REPO/eval/baselines/setup" || exit 1
source "$REPO/eval/baselines/gpu_env.sh"
DEST="$PWD/hirace"; mkdir -p "$DEST/bin" "$DEST/wrapped"
STATUS="$PWD/hirace.status"; : > "$STATUS"
log(){ echo "$@" | tee -a "$STATUS"; }
WORK="/mnt/beegfs/$USER/tools"; mkdir -p "$WORK" 2>/dev/null; chmod 700 "$WORK" 2>/dev/null
log "hirace_setup $(date -Is) node=$(hostname) CUDA=$CUDA_HOME work=$WORK"
SRC="$WORK/HiRace-Artifact-SC24"
if [ ! -d "$SRC/.git" ]; then
  log "\$ git clone --depth 1 https://github.com/JohnJacobsonIII/HiRace-Artifact-SC24 $SRC"
  git clone --depth 1 https://github.com/JohnJacobsonIII/HiRace-Artifact-SC24 "$SRC" 2>>"$STATUS" || { log "FAIL: clone"; exit 3; }
fi
cd "$SRC" || { log "FAIL: cd"; exit 3; }
built=0
for step in "./build.sh" "make" "cmake -S . -B build && cmake --build build -j"; do
  log "\$ $step"; if bash -c "$step" 2>>"$STATUS"; then built=1; break; fi; log "  (step failed, trying next)"
done
[ "$built" = 1 ] || { log "FAIL: no build entry point succeeded (pinned-LLVM box)"; exit 3; }
cxx=$(find "$SRC" -name 'clang++' -perm -u+x | head -1)
[ -n "$cxx" ] && ln -sf "$cxx" "$DEST/bin/clang++" || { log "FAIL: no clang++ produced"; exit 3; }
log "OK clang++ -> $DEST/bin/clang++"; exit 0

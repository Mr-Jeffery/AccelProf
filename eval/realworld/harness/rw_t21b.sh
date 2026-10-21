#!/bin/bash
# T21a per-target driver.   rw.sh <id> <phase> [buggy|fixed]
#
# Storage (measured 2026-10-20): creating a small file costs ~60 ms on the NFS home and ~180 ms on BeeGFS, so a source or
# build tree of thousands of files must not live on either.  Therefore: the revisions travel as ONE tarball
# (home -> BeeGFS $RW/src/<id>/<variant>.tar.gz), the build tree is unpacked and built on node-local /mnt/local, and what is
# kept on BeeGFS is the source tarball, the built artifacts ($RW/build/<id>/<variant>/), the run directories and the logs.
#
# phases        where          what
#   export      login node     t_export: revision (only the paths the build needs) -> ~/incoming/realworld/export/<id>/<variant>.tar.gz
#                              (R2 targets: r2_extract.sh instead; their files live in the worktree)
#   stage       compute node   tarball -> BeeGFS $RW/src/<id>/<variant>.tar.gz   (R2: tarball of r2/<variant> + common/)
#   build       compute node   unpack to /mnt/local/$USER/rw/<id>/<variant>/src, t_build in .../build, artifacts -> $RW/build/<id>/<variant>
#   lineinfo    compute node   once per route: SASS of $T_KERNEL built with and without -lineinfo -> targets/<id>/lineinfo.check
#   smoke       compute node   DEBUGGING ONLY: build for the node own GPU (c38: sm_75), run t_cmd once; never a result
#   native      GPU node       t_cmd <variant> three times in $RW/runs/<id>/<variant>: rc, wall, stdout md5 -> eval/realworld/native/<id>-<variant>.json
#   reach       GPU node       nsys profile of t_cmd: is $T_KERNEL launched? -> eval/realworld/native/<id>-<variant>.{kernels.csv,reach}
#   racecheck   GPU node       compute-sanitizer racecheck --racecheck-report all -> eval/realworld/racecheck/<id>-<variant>.txt
#
# A target is eval/realworld/targets/<id>/target.sh, which defines (bash):
#   T_ROUTE=R1h|R2|R1|R3  T_KERNEL=<mangled-name substring>  T_SPACE=shared|global (T_RACECHECK=na for global-memory targets)
#   T_EXE=<main binary relative to the artifact dir, default driver>  T_ARTIFACTS="<files relative to build dir to keep>" (default: driver)
#   t_export <variant> <sha> <out.tar.gz>   login node
#   t_build  <variant>                      cwd=$OUT (node-local); sources in $SRC; must honour $RW_NVCC_FLAGS and $RW_LINEINFO
#   t_cmd    <variant>                      prints the command line to run natively (cwd $RUNDIR; binaries in $ART)
# Variables: ID BUGGY FIX REPO SRC OUT ART RUNDIR TDIR WT RW INCOMING HARNESS RW_NVCC_FLAGS RW_LINEINFO NJOBS
HERE=$(cd "$(dirname "$0")" && pwd)
RWD=$(dirname "$HERE")
id=$1; phase=$2; only=${3:-}
[ -n "$id" ] && [ -n "$phase" ] || { sed -n 2,30p "$0"; exit 2; }
if [ "$phase" = export ] || [ "$phase" = info ]; then      # login node: no BeeGFS, no CUDA
  export WT=/home/fzheng4/wt-t21a RW=/mnt/beegfs/fzheng4/realworld INCOMING=/home/fzheng4/incoming/realworld HARNESS=$HERE
else
  source "$HERE/job_header_t21b.sh"
fi
PY=${PYTHON:-python3}
export TDIR=$RWD/targets/$id
eval "$($PY - "$RWD/targets.jsonl" "$id" <<'PYEOF'
import json, sys
for l in open(sys.argv[1]):
    t = json.loads(l)
    if t["id"] == sys.argv[2]:
        names = {l.rstrip("\n").split("\t")[1].lower(): l.split("\t")[0] for l in open(sys.argv[1].replace("targets.jsonl", "harness/repos.tsv")) if l.strip() and not l.startswith("#")}
        print("BUGGY=%s FIX=%s REPO=%s" % (t["buggy_commit"], t["fix_commit"], names.get(t["repo"].lower(), "")))
PYEOF
)"
[ -n "${BUGGY:-}" ] || { echo "rw.sh: no target $id" >&2; exit 2; }
T_ROUTE=; T_KERNEL=; T_SPACE=shared; T_RACECHECK=; T_EXE=driver; T_ARTIFACTS=driver; T_NATIVE_TIMEOUT=${T_NATIVE_TIMEOUT:-1200}
source "$HERE/lib_build.sh"
source "$TDIR/target.sh"
export RW_LINEINFO=${RW_LINEINFO--lineinfo}
export RW_NVCC_FLAGS=${RW_NVCC_FLAGS:--arch=sm_89}
export NJOBS=${NJOBS:-${SLURM_CPUS_PER_TASK:-16}}
variants=${only:-buggy fixed}
sha_of() { [ "$1" = buggy ] && echo "$BUGGY" || echo "$FIX"; }
NATIVE=$RWD/native; RC=$RWD/racecheck; mkdir -p "$NATIVE" "$RC"
LOCAL=/mnt/local/$USER/rw/$id

unpack() {   # $1 variant -> $LOCAL/$1/src
  rm -rf "$LOCAL/$1"; mkdir -p "$LOCAL/$1/src" "$LOCAL/$1/build"
  tar -xizf "$RW/src/$id/$1.tar.gz" -C "$LOCAL/$1/src" || return 1
  echo "unpack $id/$1: $(find "$LOCAL/$1/src" -type f | wc -l) files in $LOCAL/$1/src"
}

case $phase in
  info)       # machine-readable summary for mk_manifest.py (login node, no side effects)
    for v in $variants; do
      export ART=${RW_ART_ROOT:-$RW/build}/$id/$v RUNDIR=$RW/runs/$id/$v
      printf 'ROW\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$id" "$v" "$T_ROUTE" "$T_KERNEL" "$T_SPACE" "${T_RACECHECK:-yes}" "$ART/$T_EXE" "$(t_cmd "$v")" "$(sha_of $v)"
    done ;;
  export)
    for v in $variants; do
      d=$INCOMING/export/$id/$v.tar.gz; rm -f "$d"; mkdir -p "$(dirname "$d")"
      if [ "$T_ROUTE" = R2 ]; then echo "R2: files live in $TDIR/r2 (r2_extract.sh)"; else t_export "$v" "$(sha_of $v)" "$d"; fi
    done ;;
  stage)
    for v in $variants; do
      mkdir -p "$RW/src/$id"
      if [ "$T_ROUTE" = R2 ]; then
        tar -czf "$RW/src/$id/$v.tar.gz" -C "$TDIR/r2/$v" . $( [ -d "$TDIR/r2/common" ] && echo -C "$TDIR/r2" common )
      else
        cp "$INCOMING/export/$id/$v.tar.gz" "$RW/src/$id/$v.tar.gz"
      fi
      echo "stage $id/$v: $(du -sh "$RW/src/$id/$v.tar.gz" | cut -f1) $(sha1sum "$RW/src/$id/$v.tar.gz" | cut -c1-12)"
    done ;;
  build)
    for v in $variants; do
      unpack "$v" || exit 1
      export SRC=$LOCAL/$v/src OUT=$LOCAL/$v/build ART=${RW_ART_ROOT:-$RW/build}/$id/$v ID=$id
      cd "$OUT" || exit 1
      echo "== build $id/$v  sha $(sha_of $v)  flags: $RW_NVCC_FLAGS $RW_LINEINFO  cuda $(readlink -f /usr/local/cuda)  $(date +%T)"
      t_build "$v"; rc=$?
      echo "== build $id/$v rc=$rc $(date +%T)"; [ $rc -eq 0 ] || exit $rc
      rm -rf "$ART"; mkdir -p "$ART"
      for f in $T_ARTIFACTS *.txt *.check; do [ -e "$f" ] && { mkdir -p "$ART/$(dirname "$f")"; cp -a "$f" "$ART/$f"; }; done
      echo "artifacts -> $ART: $(ls "$ART" | tr '\n' ' ')"
    done ;;
  lineinfo)   # once per route: SASS of $T_KERNEL built with and without -lineinfo (buggy variant)
    unpack buggy || exit 1
    export SRC=$LOCAL/buggy/src OUT=$LOCAL/buggy/build ID=$id; ART=$RW/build/$id/buggy
    cd "$OUT" || exit 1
    RW_LINEINFO="" t_build buggy > "$OUT/build.log" 2>&1 || { echo "nolineinfo build failed, see $OUT/build.log"; tail -5 "$OUT/build.log"; exit 1; }
    { echo "# lineinfo check $id (route $T_ROUTE): $ART/$T_EXE (-lineinfo) vs the same build without, kernel *$T_KERNEL*, sm_89, cuda $(readlink -f /usr/local/cuda), $(date +%F)"
      "$HERE/lineinfo_check.sh" "$ART/$T_EXE" "$OUT/$T_EXE" "$T_KERNEL"; } | tee "$TDIR/lineinfo.check" ;;
  smoke)      # debugging only, NOT a deliverable: build for the node's own GPU (c38 = sm_75) and run t_cmd once, to prove the driver works
    cc=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1 | tr -d .)
    export RW_NVCC_FLAGS="-gencode arch=compute_${cc},code=sm_${cc}"
    for v in $variants; do
      unpack "$v" || exit 1
      export SRC=$LOCAL/$v/src OUT=$LOCAL/$v/build ART=$LOCAL/$v/build RUNDIR=$LOCAL/$v/run ID=$id
      mkdir -p "$RUNDIR"; cd "$OUT" || exit 1
      echo "== smoke build $id/$v for sm_${cc} on $(hostname) (NOT sm_89; debugging only)"
      t_build "$v" > build.log 2>&1 || { echo "build failed:"; tail -15 build.log; exit 1; }
      cd "$RUNDIR"; cmd=$(t_cmd "$v"); echo "== smoke run: $cmd"
      timeout 600 bash -c "$cmd" 2>&1 | tail -${SMOKE_TAIL:-15}; echo "rc=${PIPESTATUS[0]}"
    done ;;
  native|reach|racecheck)
    for v in $variants; do
      export ART=${RW_ART_ROOT:-$RW/build}/$id/$v RUNDIR=$RW/runs/$id/$v ID=$id
      mkdir -p "$RUNDIR"; cd "$RUNDIR" || exit 1
      cmd=$(t_cmd "$v")
      case $phase in
      native)
        echo "== native $id/$v on $(hostname) $(nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader | head -1): $cmd"
        $PY - "$NATIVE/$id-$v.json" "$id" "$v" "$cmd" "$T_NATIVE_TIMEOUT" <<'PYEOF'
import hashlib, json, subprocess, sys, time
out, id_, v, cmd, to = sys.argv[1:6]
runs = []
for k in range(3):
    t0 = time.time()
    try:
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, timeout=int(to))
        rc, so, se = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired as e:
        rc, so, se = 124, e.stdout or b"", e.stderr or b""
    runs.append({"rc": rc, "wall_s": round(time.time() - t0, 3), "stdout_md5": hashlib.md5(so).hexdigest(),
                 "stdout_bytes": len(so), "stdout_tail": so[-300:].decode(errors="replace"), "stderr_tail": se[-300:].decode(errors="replace")})
res = {"id": id_, "variant": v, "cmd": cmd, "runs": runs, "rcs": [r["rc"] for r in runs],
       "outputs_differ": len({r["stdout_md5"] for r in runs}) > 1}
json.dump(res, open(out, "w"), indent=1)
print(json.dumps({k: res[k] for k in ("rcs", "outputs_differ")}), [r["wall_s"] for r in runs])
print(runs[0]["stdout_tail"][-200:])
PYEOF
        ;;
      reach)
        NSYS=$(command -v nsys); [ -n "$NSYS" ] || NSYS=$(ls /opt/nvidia/nsight-systems/*/bin/nsys 2>/dev/null | tail -1)
        echo "== reach $id/$v via ${NSYS:-none}: $cmd"
        if [ -n "$NSYS" ]; then
          rm -f "$RUNDIR"/reach.nsys-rep "$RUNDIR"/reach.sqlite "$RUNDIR"/reach.qdstrm
          $NSYS profile --stats=false --force-overwrite=true -o "$RUNDIR/reach" --trace=cuda bash -c "$cmd" > "$RUNDIR/reach.stdout" 2>&1
          $NSYS stats --force-export=true --report cuda_gpu_kern_sum --format csv "$RUNDIR/reach.nsys-rep" 2>/dev/null > "$NATIVE/$id-$v.kernels.csv"
          echo "kernels listed: $(grep -c . "$NATIVE/$id-$v.kernels.csv")"
          grep -i -- "${T_KERNEL_NSYS:-$T_KERNEL}" "$NATIVE/$id-$v.kernels.csv" | cut -c1-220 | head -5 | tee "$NATIVE/$id-$v.reach"
          [ -s "$NATIVE/$id-$v.reach" ] && echo "REACHED ${T_KERNEL_NSYS:-$T_KERNEL}" || echo "NOT REACHED ${T_KERNEL_NSYS:-$T_KERNEL}"
        else echo "no nsys on this node"; fi ;;
      racecheck)
        if [ "$T_RACECHECK" = na ]; then echo "racecheck n/a: global-memory target (outside racecheck by construction)" | tee "$RC/$id-$v.txt"; continue; fi
        echo "== racecheck $id/$v: $cmd"
        { echo "# compute-sanitizer $(compute-sanitizer --version 2>&1 | tail -1) host $(hostname) cuda $(readlink -f /usr/local/cuda) $(date +%F)"
          echo "# cmd: $cmd"
          compute-sanitizer --tool racecheck --racecheck-report all --print-limit 2000 bash -c "$cmd" 2>&1; echo "# exit $?"; } > "$RC/$id-$v.txt"
        grep -E "RACECHECK SUMMARY|ERROR SUMMARY|^# exit" "$RC/$id-$v.txt" | tail -3 ;;
      esac
    done ;;
  *) echo "unknown phase $phase" >&2; exit 2 ;;
esac

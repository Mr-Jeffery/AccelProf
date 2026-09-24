#!/bin/bash
# One program-input through the cuVein race pipeline, emitting an eval CSV row.
#
#   harness.sh --suite S --program P [opts] -- <exe> [args...]
#
# Reuses getall.sh's extraction (cuobjdump/nvdisasm/atomic sidecar) then times
# three configs (native / trace-only / full engine) and runs the verdict
# aggregator. Runs against ACCEL_PROF_HOME (the built tree); writes results
# wherever --csv points. Never aborts the batch on one program's failure.
set -u
ACCEL_PROF_HOME="${ACCEL_PROF_HOME:-/home/fzheng4/AccelProf}"
source "$ACCEL_PROF_HOME/setup_env.sh"
ENV="conda run -p $ACCEL_PROF_HOME/.env python"
AGG="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/aggregate.py"

suite= program= variant= label= input= expect= racecheck= oracle= csv= detail_dir=
timeout=300 nreps=3
while [ $# -gt 0 ]; do
  case "$1" in
    --suite) suite=$2; shift 2;;
    --program) program=$2; shift 2;;
    --variant) variant=$2; shift 2;;
    --label) label=$2; shift 2;;
    --input) input=$2; shift 2;;
    --expect-pcs) expect=$2; shift 2;;
    --racecheck) racecheck=$2; shift 2;;
    --oracle) oracle=1; shift;;
    --csv) csv=$2; shift 2;;
    --detail-dir) detail_dir=$2; shift 2;;
    --timeout) timeout=$2; shift 2;;
    --reps) nreps=$2; shift 2;;
    --) shift; break;;
    *) echo "unknown arg $1" >&2; exit 2;;
  esac
done
exe="$1"; shift || true
appargs=("$@")

exe_abs="$(readlink -f "$exe")"
exe_dir="$(dirname "$exe_abs")"
exe_base="$(basename "$exe_abs")"
name="${exe_base%.*}"

if [ ! -x "$exe_abs" ]; then
  echo "MISSING exe: $exe_abs" >&2
  $ENV "$AGG" --python-dir "$ACCEL_PROF_HOME/python" --depdir /nonexistent \
       --cubindir /nonexistent --suite "$suite" --program "$program" \
       --variant "$variant" --label "$label" --input "$input" \
       ${csv:+--csv "$csv"} 2>/dev/null
  exit 0
fi

cd "$exe_dir" || exit 0
cubindir="${exe_dir}/${name}_eval_cubins"
rm -rf "$cubindir"; mkdir -p "$cubindir"

# --- extraction: cubins -> CFG dots -> atomic-scope sidecar -------------------
( cd "$cubindir" && cuobjdump -xelf all "$exe_abs" >/dev/null 2>&1 )
shopt -s nullglob
cubs=( "$cubindir"/*.cubin ); [ ${#cubs[@]} -eq 0 ] && cubs=( "$cubindir"/*.elf )
for c in "${cubs[@]}"; do nvdisasm -bbcfg -poff "$c" > "${c%.*}.dot" 2>/dev/null; done
unset YOSEMITE_ATOMIC_SCOPE_FILE
if [ ${#cubs[@]} -gt 0 ]; then
  $ENV "$ACCEL_PROF_HOME/python/atomic_scope_sidecar.py" "$cubindir"/*.dot \
       -o "$cubindir/atomic_scope.txt" >/dev/null 2>&1 \
    && export YOSEMITE_ATOMIC_SCOPE_FILE="$cubindir/atomic_scope.txt"
fi
shopt -u nullglob

# --- timing helper: min elapsed over reps; also last-run max RSS (kb) ---------
run_min() {  # reps, env-prefix... -- cmd...; echos "min_elapsed max_rss_kb rc"
  local reps=$1; shift
  local -a envp=(); while [ "$1" != "--" ]; do envp+=("$1"); shift; done; shift
  local best="" rss=0 rc=0 t m i
  for ((i=0;i<reps;i++)); do
    local out
    out=$(env "${envp[@]}" timeout "$timeout" /usr/bin/time -f '%e %M' "$@" \
          >/dev/null 2>>"$CLAUDE_JOB_DIR/tmp/_time.$$" ; echo $?)
    rc=$out
    read t m < <(tail -1 "$CLAUDE_JOB_DIR/tmp/_time.$$" 2>/dev/null)
    : > "$CLAUDE_JOB_DIR/tmp/_time.$$"
    [ -z "$t" ] && t=NA
    if [ "$best" = "" ] || awk "BEGIN{exit !($t<$best)}" 2>/dev/null; then best=$t; fi
    [ -n "$m" ] && rss=$m
  done
  echo "${best:-NA} ${rss:-0} ${rc:-0}"
}

# 1) native (no accelprof)
read tn _ rcn < <(run_min "$nreps" -- "$exe_abs" "${appargs[@]}")

# 2) trace-only (dump, engine skipped) — one rep, throwaway depdir
rm -rf "${exe_dir}/dependency_${exe_base}"_* 2>/dev/null
read tt _ rct < <(run_min 1 YOSEMITE_HB_TRACE=1 YOSEMITE_HB_NO_ENGINE=1 -- \
                  accelprof -t pc_dependency_analysis -n 1 "$exe_abs" "${appargs[@]}")
rm -rf "${exe_dir}/dependency_${exe_base}"_* 2>/dev/null

# 3) full engine — one rep, keep depdir + capture peak RSS
read te peak rce < <(run_min 1 YOSEMITE_HB_TRACE=1 -- \
                     accelprof -t pc_dependency_analysis -n 1 "$exe_abs" "${appargs[@]}")
depdir="$(ls -dt "${exe_dir}/dependency_${exe_base}"_* 2>/dev/null | head -1)"
log="${exe_dir}/${exe_base}.accelprof.log"

echo "[$program/$variant] native=${tn}s trace=${tt}s engine=${te}s peakRSS=${peak}kb rc(n/t/e)=$rcn/$rct/$rce depdir=$(basename "${depdir:-none})")"

if [ -z "$depdir" ] || [ ! -d "$depdir" ]; then
  echo "  NO engine depdir (rc=$rce) — emitting failure row" >&2
  extra_note="engine-run-failed(rc=$rce)"
  # emit a minimal row noting the failure
  $ENV "$AGG" --python-dir "$ACCEL_PROF_HOME/python" --depdir /nonexistent \
       --cubindir "$cubindir" --log "$log" --suite "$suite" --program "$program" \
       --variant "$variant" --label "$label" --input "$input" \
       --t-native "$tn" --t-trace "$tt" --t-engine "$te" \
       ${racecheck:+--racecheck "$racecheck"} ${csv:+--csv "$csv"} 2>/dev/null
  exit 0
fi

$ENV "$AGG" --python-dir "$ACCEL_PROF_HOME/python" \
     --depdir "$depdir" --cubindir "$cubindir" --log "$log" \
     --suite "$suite" --program "$program" --variant "$variant" \
     --label "$label" --input "$input" \
     --t-native "$tn" --t-trace "$tt" --t-engine "$te" --peak-kb "$peak" \
     ${expect:+--expect-pcs "$expect"} ${racecheck:+--racecheck "$racecheck"} \
     ${oracle:+--oracle} ${csv:+--csv "$csv"} \
     ${detail_dir:+--detail "$detail_dir/${program}__${variant}__${input}.json"}

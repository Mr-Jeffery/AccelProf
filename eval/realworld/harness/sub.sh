#!/bin/bash
# Submit a T21a job script from the login node.
#   sub.sh <jobname> <script> [-- sbatch options]   e.g.  sub.sh build-cccl-1 jobs/build.sh -- --cpus-per-task=16 --time=2:00:00
# Logs: eval/x_logs/<jobname>-<jobid>.log (stdout+stderr; *.log is gitignored).
# Nodes without /home or BeeGFS are excluded (c23, c46 on 2026-10-20) plus c2 c21 c37 c54 (T21 rule).
# Add nodes found bad to EXCL below and to eval/REALWORLD.md section 1.
EXCL=${T21_EXCLUDE:-c0,c1,c2,c21,c23,c37,c46,c54}   # c0, c1: no writable /mnt/local/$USER (T21c, 2026-10-24)
WT=${T21_WT:-/home/fzheng4/wt-t21a}
name=$1; script=$2; shift 2
[ "${1:-}" = "--" ] && shift
mkdir -p "$WT/eval/x_logs"
sbatch --parsable --job-name="$name" --partition="${T21_PARTITION:-normal}" --exclude="$EXCL" \
  --output="$WT/eval/x_logs/$name-%j.log" --time="${T21_TIME:-01:00:00}" --cpus-per-task="${T21_CPUS:-8}" "$@" "$script"

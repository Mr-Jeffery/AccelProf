# eval/realworld/harness/recall_header.sh -- `source` at the top of every T21b SLURM job script.
# Hard-fails (exit 97, hostname on stderr) when the node cannot read home, BeeGFS or the worktree
# (BeeGFS failed everywhere at 23:11 on 10-20; c23 and c46 have no /home/fzheng4).
export W=/home/fzheng4/wt-t21b
export A=/home/fzheng4/AccelProf
export S0=/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10
for _d in $A /mnt/beegfs/fzheng4 $W $A/lib/libcompute_sanitizer.so; do
  timeout 10 ls "$_d" >/dev/null 2>&1 || { echo "T21b job_header: host=$(hostname) missing or unreadable $_d" >&2; exit 97; }
done
timeout 10 ls /mnt/beegfs/fzheng4/realworld/build >/dev/null 2>&1 || { echo "T21b job_header: host=$(hostname) BeeGFS build dir unreadable" >&2; exit 97; }
unset _d
# no inherited detector knob: only what this script sets
for _k in $(env | grep -E '^(YOSEMITE_|CUVEIN_|BASELINE_)' | cut -d= -f1); do
  [ "$_k" = CUVEIN_HOME ] || unset "$_k"
done
unset _k

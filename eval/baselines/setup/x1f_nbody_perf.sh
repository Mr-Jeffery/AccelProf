#!/usr/bin/env bash
#SBATCH --job-name=x1f-perf
#SBATCH --partition=rtx4060ti16g
#SBATCH --exclude=c[0-3],c[23-24],c37,c[39-40],c[50-56],c[73-79]
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=12:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/x1f-perf-%j.log
# X1-follow Part 3 (eval/X1_FOLLOW.md section 3) and the short programs of Part 1.
# (1) P7-nbody-cuda, scalar-clock, the installed runtime, under perf exactly as T20's profile
#     (t20_profile.sh -> t5b_profile.py: perf record -F 49 --call-graph dwarf,16384 over the whole
#     process tree, YOSEMITE_HB_DUMP=0, YOSEMITE_HB_STATS=1, accelprof -v -n 1, `timeout 1500`), then
#     t20_perf_flat.sh / t20_perf_alloc.sh's reports (self time by symbol, by symbol+source line, by
#     thread) -> eval/x1_follow/perf/.
# (2) the HB_STATS objects of nbody's kernels from X1's 24 h stores (both modes; the complete runs)
#     -> eval/x1_follow/perf/nbody_hb_stats.json.
# (3) Part 1's two short programs, collector-only (YOSEMITE_HB_TRACE unset), -n 1 and the default
#     worker count, cap 1200 s; and, as a same-node reference, the same two in X1's configuration
#     (both modes, -n 1, YOSEMITE_HB_DUMP=0, YOSEMITE_HB_STATS=1).
# Pinned to c60-c72 (EPYC 8124P, the hosts of X1's nbody/knn rows).
#   sbatch eval/baselines/setup/x1f_nbody_perf.sh
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-x1}
RT=/home/fzheng4/AccelProf
source $W/eval/baselines/setup/home_quota_guard.sh
cd $RT || exit 1
for v in $(env | /usr/bin/grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES
export ACCEL_PROF_HOME=$RT CUDA_HOME=/usr/local/cuda-13.3
source eval/baselines/gpu_env.sh
export PATH=/usr/local/cuda-13.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
h() { sha256sum "$1" | cut -c1-16; }
gpu=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader 2>&1 | head -1)
case "$gpu" in *"4060 Ti"*", 8.9,"*) ;; *) echo "NODE-PROBLEM $(hostname): GPU [$gpu]"; exit 2;; esac
[ -d /mnt/beegfs/$USER ] || { echo "NODE-PROBLEM $(hostname): BeeGFS not mounted"; exit 2; }
P=$W/eval/x1_follow/perf; C=$W/eval/x1_follow/collector; PW=/mnt/beegfs/$USER/x1_follow/perf
mkdir -p $P $C $PW
echo "host=$(hostname) gpu=[$gpu] mem=$(free -g | awk '/Mem:/{print $2}')G cpu=[$(lscpu | sed -n 's/^Model name: *//p')] nproc=$(nproc) job=${SLURM_JOB_ID:-} $(date -Is) perf $(perf --version 2>&1)"
echo "runtime $RT libsanalyzer $(h $RT/build/sanalyzer/lib/libsanalyzer.so) collector $(h $RT/lib/libcompute_sanitizer.so) fatbin $(h $RT/nv-compute/lib/gpu_patch/gpu_patch_pc_dependency.fatbin); harness $W HEAD=$(git -C $W rev-parse --short=12 HEAD)"

echo "== (1) nbody scalar-clock under perf $(date -Is)"
BASELINE_HB_DUMP=0 $PY $W/eval/baselines/setup/t5b_profile.py --id P7-nbody-cuda --mode scalar-clock \
    --cap ${PCAP:-1500} --freq 49 --dwarf --work $PW > $P/nbody-sc.profile.txt 2>&1
tail -5 $P/nbody-sc.profile.txt
D=$PW/P7-nbody-cuda-scalar-clock/work
ls -la $D/perf.data
perf report -i $D/perf.data --no-children --stdio -g none --sort sym --percent-limit 0.3 2>/dev/null \
    | /usr/bin/grep -v "^#" | /usr/bin/grep -v "^$" > $P/nbody-sc.sym.txt
perf report -i $D/perf.data --no-children --stdio -g none --sort sym,srcline --percent-limit 0.3 2>/dev/null \
    | /usr/bin/grep -v "^#" | /usr/bin/grep -v "^$" > $P/nbody-sc.lines.txt
perf report -i $D/perf.data --no-children --stdio -g none --sort pid --percent-limit 0.5 2>/dev/null \
    | /usr/bin/grep -v "^#" | /usr/bin/grep -v "^$" > $P/nbody-sc.tid.txt
perf report -i $D/perf.data --no-children --stdio -g none --sort pid,sym --percent-limit 0.3 2>/dev/null \
    | /usr/bin/grep -v "^#" | /usr/bin/grep -v "^$" > $P/nbody-sc.tidsym.txt
perf report -i $D/perf.data --no-children --stdio -g none --sort dso --percent-limit 0.3 2>/dev/null \
    | /usr/bin/grep -v "^#" | /usr/bin/grep -v "^$" > $P/nbody-sc.dso.txt
perf report -i $D/perf.data --no-children --stdio -G --sort pid,sym --percent-limit 1 \
    --symbols _int_malloc,_int_free,malloc_consolidate,unlink_chunk.isra.2,malloc 2>/dev/null \
    | /usr/bin/grep -v "^$" | head -400 > $P/nbody-sc.alloc.txt
head -25 $P/nbody-sc.sym.txt; cat $P/nbody-sc.tid.txt
ls -la $D/dependency_* 2>/dev/null | head; cp $D/stderr.txt $P/nbody-sc.stderr.txt 2>/dev/null
$PY - $D $P/nbody-sc.profile-kernels.json <<'EOF'
import glob, json, os, re, sys
d, out = sys.argv[1:]
ks = []
for kj in sorted(glob.glob(f"{d}/dependency_*/kernel_*.json"), key=lambda p: int(re.search(r"kernel_(\d+)", p).group(1))):
    try:
        j = json.load(open(kj))
    except ValueError:
        ks.append(dict(file=os.path.basename(kj), truncated=True)); continue
    ks.append(dict(file=os.path.basename(kj), name=j.get("kernel_name") or j.get("name"), mtime=os.path.getmtime(kj),
                   hb_events_count=j.get("hb_events_count"), hb_lanes_count=j.get("hb_lanes_count"), hb_stats=j.get("hb_stats")))
json.dump(ks, open(out, "w"), indent=1)
print(f"profile run: {len(ks)} kernel JSONs")
EOF

echo "== (2) nbody HB_STATS from X1's 24 h stores $(date -Is)"
$PY - /mnt/beegfs/$USER/cuvein_traces $P/nbody_hb_stats.json <<'EOF'
import glob, json, os, re, sys
root, out = sys.argv[1:]
res = {}
for tag, mode in (("final-2026-10-24h-sc", "scalar-clock"), ("final-2026-10-24h-vc", "vector-clock")):
    ks = []
    for kj in sorted(glob.glob(f"{root}/{tag}/P7-nbody-cuda/{mode}/kernel_*.json"), key=lambda p: int(re.search(r"kernel_(\d+)", p).group(1))):
        j = json.load(open(kj))
        ks.append(dict(file=os.path.basename(kj), keys=sorted(k for k in j if k.startswith(("hb_", "kernel"))),
                       name=j.get("kernel_name") or j.get("name"), hb_events_count=j.get("hb_events_count"),
                       hb_lanes_count=j.get("hb_lanes_count"), hb_stats=j.get("hb_stats")))
    res[mode] = ks
    print(mode, len(ks), "kernel JSONs")
json.dump(res, open(out, "w"), indent=1)
EOF

echo "== (3) short programs $(date -Is)"
for id in P1-BFS_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-100n \
          P6-interkernel-global_readwrite_race-fixed; do
  sid=${id:0:40}
  for w in 1 default; do
    $PY $W/eval/baselines/setup/x1f_run.py --id $id --config collector --workers $w --cap 1200 --native-reps 3 \
        --name $sid-collector-n$w --out $C --work /mnt/beegfs/$USER/x1_follow/runs > $C/$sid-collector-n$w.driver.txt 2>&1
    tail -1 $C/$sid-collector-n$w.driver.txt
  done
  for m in scalar-clock vector-clock; do
    $PY $W/eval/baselines/setup/x1f_run.py --id $id --config $m --workers 1 --cap 1200 --no-dump --hb-stats --native-reps 3 \
        --name $sid-$m-n1 --out $C --work /mnt/beegfs/$USER/x1_follow/runs > $C/$sid-$m-n1.driver.txt 2>&1
    tail -1 $C/$sid-$m-n1.driver.txt
  done
done
echo "== done $(date -Is)"

#!/usr/bin/env bash
#SBATCH --job-name=p7-fix
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/p7fix-%j.log
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
export BASELINE_SM=89
$PY eval/baselines/build_corpora.py --arch 89 --pset P7 --hecbench-apps nbody-cuda,mandelbrot-cuda,bitonic-sort-cuda,heartwall-cuda,bezier-surface-cuda,haversine-cuda,backprop-cuda,pathfinder-cuda,srad-cuda,particlefilter-cuda,lavaMD-cuda,stencil1d-cuda 2>&1 | tail -6
# rewrite P7 manifest_rows with args for the (now --cudart shared) built apps
$PY - <<'PYEOF'
import csv,os
H="/home/fzheng4/AccelProf/eval/baselines/corpora/HeCBench"; BIN="eval/baselines/bin/P7"
ARGS={"backprop-cuda":"65536","bezier-surface-cuda":"-n 8192","bitonic-sort-cuda":"25 2",
 "heartwall-cuda":"104","haversine-cuda":f"{H}/src/geodesic-cuda/locations.txt 100",
 "nbody-cuda":"16000 10","mandelbrot-cuda":"1000","pathfinder-cuda":"100000 1000 5",
 "srad-cuda":"1000 0.5 502 458","lavaMD-cuda":"-boxes1d 30","stencil1d-cuda":"134217728 1000",
 "particlefilter-cuda":"-x 128 -y 128 -z 10 -np 400000"}
rows=[]
for app,args in ARGS.items():
    e=f"{BIN}/{app}"
    if os.path.exists(e): rows.append(dict(id=f"P7-{app}",pset="P7",program=app,build="default",
        input="default",exe=os.path.abspath(e),args=args,stdin="",shared_mem=0,label="",
        arrays_to_wrap="",monitored_kernels="",reps=3,timeout=1200))
f=["id","pset","program","build","input","exe","args","stdin","shared_mem","label","arrays_to_wrap","monitored_kernels","reps","timeout"]
w=csv.DictWriter(open(f"{BIN}/manifest_rows.csv","w",newline=""),fieldnames=f);w.writeheader()
[w.writerow(r) for r in rows]; print(f"P7 rows: {len(rows)}")
PYEOF
$PY eval/baselines/mk_manifest.py | grep P7

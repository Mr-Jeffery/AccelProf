#!/bin/bash
# D-T2 check: rw_attribute.cubin_frames on defects/attrib-global-init-frames/global_init_lineinfo.cu (must give 12 and 14, not 15)
export W=/home/fzheng4/wt-t21b; export ACCEL_PROF_HOME=/home/fzheng4/AccelProf
export CUDA_HOME=/usr/local/cuda-13.3; source $W/eval/baselines/gpu_env.sh
D=$W/eval/realworld/defects/attrib-global-init-frames
T=$(mktemp -d /tmp/dt2-XXXXXX); cd $T
nvcc -arch=sm_89 -lineinfo --cudart shared -o gil $D/global_init_lineinfo.cu && cuobjdump -xelf all gil >/dev/null
ls
$PY - <<PYEOF
import sys, glob
sys.path.insert(0, "$W/eval/realworld/harness")
import rw_attribute as ra, blib
env = blib.base_env(blib.resolve_cuda_home())
cub = glob.glob("$T/*sm_89.cubin")[0]
fr = ra.cubin_frames(cub, env, {})
print("cub", cub, "funcs", list(fr.keys()), [len(v) for v in fr.values()])


for fn, d in fr.items():
    for pc, f in sorted(d.items()):
        print(fn[:40], hex(pc), [(x["file"].split("/")[-1], x["line"]) for x in f[:1]])
PYEOF

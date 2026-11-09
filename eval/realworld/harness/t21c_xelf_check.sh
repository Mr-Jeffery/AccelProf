#!/bin/bash
#SBATCH -p normal -N1 -n1 -c4 -t 03:00:00 --exclude=c0,c1,c2,c21,c23,c37,c43,c46,c54,c77
#SBATCH -J t21c-xelf-check -o /home/fzheng4/wt-t21c/eval/x_logs/t21c-xelf-check-%j.log
# T21c: check blib.xelf_all()/extract() on lightgbm (over-long device-link ELF name) and colmap (normal path):
# every sm_89 function of the executable must come out of the extracted cubins with identical SASS.
cd /home/fzheng4/wt-t21c
export PATH=/usr/local/cuda-13.4/bin:$PATH
/home/fzheng4/AccelProf/.env/bin/python - <<'P'
import sys, os, re, subprocess, tempfile, collections
sys.path.insert(0, "eval/baselines"); import blib
env = dict(os.environ)
def fmap(paths):
    F = collections.defaultdict(list)
    for p in paths:
        o = subprocess.run(["cuobjdump", "-sass", "-arch", "sm_89", p], capture_output=True, text=True, env=env).stdout
        cur = None
        for l in o.splitlines():
            m = re.match(r"\s*Function : (\S+)", l)
            if m: cur = m.group(1); continue
            m = re.match(r"\s*/\*[0-9a-f]{4,}\*/\s+(.*?);", l)
            if m and cur: F[cur].append(" ".join(m.group(1).split()))
    return F
for exe in ["/mnt/beegfs/fzheng4/realworld_t21c/build/lightgbm-new-1/buggy/lightgbm", "/mnt/beegfs/fzheng4/realworld_t21c/build/colmap-new-1/buggy/driver"]:
    d = tempfile.mkdtemp(dir="/tmp")
    cubs = blib.xelf_all(exe, d, env)   # extraction only; extract() adds nvdisasm -bbcfg per cubin (slow on the 1,181-function dlink cubin)
    dots, scope = [], ''
    a, b = fmap([exe]), fmap([c for c in cubs if ".sm_89." in c])
    print(os.path.basename(exe), "cubins", len(cubs), "nonempty dots", len(dots), "scope", bool(scope),
          "functions exe/cubins", len(a), len(b), "SASS per function identical:", a == b, flush=True)
    print("   ", sorted(os.path.basename(c) for c in cubs)[:3], flush=True)
    dk = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    print("    differing functions:", len(dk), [(k[:70], len(a.get(k, [])), len(b.get(k, []))) for k in dk[:8]], flush=True)
P
echo done

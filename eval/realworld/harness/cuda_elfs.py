#!/usr/bin/env python3
"""Which CUDA code does a process load?  (T21a step 2, shared libraries.)
    cuda_elfs.py <exe> [--extract DIR] [--json]
Enumerates the executable and every library `ldd` resolves, runs `cuobjdump -lelf` / `-lptx` on each one that
carries device code, and reports the SASS architectures and whether any architecture is PTX-only (a PTX-only
fatbin is JIT-compiled at load and the cubin on disk is not the loaded one).  With --extract it also runs
`cuobjdump -xelf all` into DIR/<basename>/ so the CFG side can index cubins by mangled kernel name and sm_.
The loaded-module check at run time (the collector's module-load log) is T21b's; this is the static census."""
import argparse, json, os, re, subprocess, sys


def run(*a, cwd=None):
    r = subprocess.run(a, capture_output=True, text=True, cwd=cwd)
    return r.returncode, r.stdout, r.stderr


def census(path, extract=None):
    rc, o, _ = run("cuobjdump", "-lelf", path)
    elfs = re.findall(r":\s*(\S+\.(sm_\d+)\.cubin)", o) if rc == 0 else []
    rc2, o2, _ = run("cuobjdump", "-lptx", path)
    ptx = re.findall(r":\s*(\S+\.(sm_\d+)\.ptx)", o2) if rc2 == 0 else []
    if not elfs and not ptx:
        return None
    d = {"path": path, "sass_archs": sorted({a for _, a in elfs}), "n_cubins": len(elfs),
         "ptx_archs": sorted({a for _, a in ptx}), "n_ptx": len(ptx)}
    d["ptx_only_archs"] = sorted(set(d["ptx_archs"]) - set(d["sass_archs"]))
    if extract:
        dd = os.path.join(extract, os.path.basename(path))
        os.makedirs(dd, exist_ok=True)
        run("cuobjdump", "-xelf", "all", os.path.abspath(path), cwd=dd)
        d["extracted_to"] = dd
    return d


ap = argparse.ArgumentParser()
ap.add_argument("exe")
ap.add_argument("--extract")
ap.add_argument("--json", action="store_true")
x = ap.parse_args()
paths = [os.path.realpath(x.exe)]
rc, o, _ = run("ldd", x.exe)
for l in o.splitlines():
    m = re.search(r"=>\s*(/\S+)", l)
    if m and os.path.exists(m.group(1)):
        paths.append(os.path.realpath(m.group(1)))
res = [c for c in (census(p, x.extract) for p in dict.fromkeys(paths)) if c]
if x.json:
    print(json.dumps(res, indent=1))
else:
    for c in res:
        print("%s: %d cubin(s) %s; PTX %s%s" % (c["path"], c["n_cubins"], ",".join(c["sass_archs"]) or "-",
                                               ",".join(c["ptx_archs"]) or "-",
                                               ("; PTX-ONLY " + ",".join(c["ptx_only_archs"])) if c["ptx_only_archs"] else ""))
    if not res:
        print("no device code found")

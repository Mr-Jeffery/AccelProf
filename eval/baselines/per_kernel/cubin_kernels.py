#!/usr/bin/env python3
"""X13 step 1a: the __global__ functions in each binary's cubin: `cuobjdump -elf` entry kernels are the functions with
a .nv.constant0.<mangled> section (device functions have .text.<name> only). Demangled with cu++filt.
Usage: cubin_kernels.py OUT.csv MANIFEST IDS_FILE [--native DIR]"""
import csv, os, re, subprocess, sys
out, manifest, idsf = sys.argv[1:4]
CB = "/usr/local/cuda-13/bin"
ids = {l.strip() for l in open(idsf) if l.strip()}
exes = {}
for r in csv.DictReader(open(manifest)):
    if r["id"] in ids and r["exe"]:
        exes.setdefault(r["exe"], []).append(r["id"])
extra = {}
if "--native" in sys.argv:
    d = sys.argv[sys.argv.index("--native") + 1]
    for f in sorted(os.listdir(d)):
        extra[os.path.join(d, f)] = ["native:" + f]
def demangle(names):
    if not names: return {}
    import shutil
    f = shutil.which("c++filt") or f"{CB}/cu++filt"      # GNU style (int const*), the collector's kernel_name style
    p = subprocess.run([f], input="\n".join(names), capture_output=True, text=True)
    return dict(zip(names, p.stdout.split("\n")))
w = csv.writer(open(out, "w", newline=""))
w.writerow(["exe", "n_ids", "mangled", "demangled", "is_entry", "status"])
for exe, mem in list(exes.items()) + list(extra.items()):
    if not os.path.exists(exe):
        w.writerow([exe, len(mem), "", "", "", "exe-missing"]); continue
    p = subprocess.run([f"{CB}/cuobjdump", "-elf", exe], capture_output=True, text=True)
    txt = p.stdout
    ent = set(re.findall(r"^\.nv\.constant0\.(\S+)", txt, re.M))
    fun = set(re.findall(r"^\.text\.(\S+)", txt, re.M))
    names = sorted(ent | fun)
    if not names:
        w.writerow([exe, len(mem), "", "", "", f"no-cubin-symbols(rc={p.returncode}):{p.stderr[:80]}"]); continue
    dm = demangle(names)
    for nme in names:
        w.writerow([exe, len(mem), nme, dm.get(nme, ""), int(nme in ent), "ok"])

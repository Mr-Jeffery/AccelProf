#!/usr/bin/env python3
"""X13 step 3a: file:line -> kernel for a binary, `nvdisasm --print-line-info` on every cubin of the binary
(cuobjdump -xelf all). Every (basename, line) frame printed inside a kernel's .text.<name> section, including the
frames after `inlined at`, belongs to that kernel. Output rows: exe, file, line, kernel(mangled), inlined(0/1).
Usage: linemap.py OUT.csv EXE..."""
import csv, glob, os, re, subprocess, sys, tempfile
CB = "/usr/local/cuda-13/bin"
out = sys.argv[1]
w = csv.writer(open(out, "w", newline=""))
w.writerow(["exe", "file", "line", "kernel", "inlined", "status"])
HDR = re.compile(r"^//-+\s+\.text\.(\S+)\s+-+")
FR = re.compile(r'"([^"]+)",\s*line\s+(\d+)')
for exe in sys.argv[2:]:
    if not os.path.exists(exe):
        w.writerow([exe, "", "", "", "", "exe-missing"]); continue
    with tempfile.TemporaryDirectory() as td:
        subprocess.run([f"{CB}/cuobjdump", "-xelf", "all", exe], cwd=td, capture_output=True, text=True)
        cubins = sorted(glob.glob(f"{td}/*.cubin"))
        seen = set()
        for cb in cubins:
            p = subprocess.run([f"{CB}/nvdisasm", "--print-line-info", cb], capture_output=True, text=True)
            cur = None
            for ln in p.stdout.splitlines():
                m = HDR.match(ln)
                if m:
                    cur = m.group(1); continue
                if cur and ln.lstrip().startswith("//##"):
                    fr = FR.findall(ln)
                    for k, (f, l) in enumerate(fr):
                        key = (os.path.basename(f), int(l), cur, int(k > 0 or "inlined" in ln and k > 0))
                        if key not in seen:
                            seen.add(key)
        if not seen:
            w.writerow([exe, "", "", "", "", f"no-line-info({len(cubins)} cubins)"])
        for (f, l, k, inl) in sorted(seen):
            w.writerow([exe, f, l, k, inl, "ok"])

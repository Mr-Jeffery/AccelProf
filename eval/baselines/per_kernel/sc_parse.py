#!/usr/bin/env python3
"""X13 step 3b: re-parse SuperCollider logs for both report headers: "In function F at file:line" and
"Inlined function F at file:line" (the form the artifact prints for device functions inlined into a kernel; the regex of
run_supercollider.py expects only the first). Usage: sc_parse.py OUT.csv LOGROOT -> rows: id, rep, header, function, file, line, type, pc_offset."""
import csv, glob, os, re, sys
out, root = sys.argv[1:3]
R = re.compile(r"(In|Inlined) function (\S+?)(?: at (\S+?):(\d+))?\s*\n\s*Type\s*:\s*([^\n]+)(?:\n\s*PC offset\s*:\s*(\S+))?")
w = csv.writer(open(out, "w", newline=""))
w.writerow(["id", "rep", "header", "function", "file", "line", "type", "pc_offset"])
for d in sorted(glob.glob(f"{root}/*")):
    for f in sorted(glob.glob(f"{d}/sc_rep*.txt")):
        txt = open(f, errors="replace").read()
        rep = re.search(r"sc_rep(\d+)", f).group(1)
        for h, fn, fl, ln, typ, pc in R.findall(txt):
            w.writerow([os.path.basename(d), rep, h, fn, fl, ln, typ.strip(), pc])

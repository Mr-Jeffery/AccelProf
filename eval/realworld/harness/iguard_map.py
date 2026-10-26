#!/usr/bin/env python3
"""Map iGUARD reports (kernel + SASS offset) to source lines via nvdisasm -g.

  iguard_map.py <exe> <iguard_log> -> one line per distinct report:
  kind | instruction | file:line | kernel (short)
iGUARD names a report by the racing instruction's SASS offset in its function;
the line comes from the cubin's line table (the line of the instruction, which
ptxas may tag with the first use instead of the source statement)."""
import os, re, subprocess, sys, tempfile, glob

exe, log = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "baselines"))
norm = lambda s: re.sub(r"\s+", "", s)

tmp = tempfile.mkdtemp()
subprocess.run(["cuobjdump", "-xelf", "all", os.path.abspath(exe)], cwd=tmp,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
funcs = {}   # mangled -> {offset: (line, instr)}
for c in glob.glob(f"{tmp}/*.cubin"):
    if "sm_89" not in c and "sm89" not in c:
        continue
    out = subprocess.run(["nvdisasm", "-g", "-c", c], capture_output=True, text=True).stdout
    cur_f, cur_l = None, None
    for ln in out.splitlines():
        m = re.match(r"\s*\.text\.(\S+):", ln)
        if m:
            cur_f, cur_l = m.group(1), None
            funcs.setdefault(cur_f, {})
            continue
        m = re.search(r'//## File "([^"]+)", line (\d+)', ln)
        if m:
            cur_l = f"{os.path.basename(m.group(1))}:{m.group(2)}"
            continue
        m = re.search(r"/\*([0-9a-f]{4,})\*/\s+(.*?)\s*;", ln)
        if m and cur_f:
            funcs[cur_f][int(m.group(1), 16)] = (cur_l, m.group(2))
names = list(funcs)
dem = subprocess.run(["c++filt"], input="\n".join(names), capture_output=True, text=True).stdout.splitlines()
by_name = {}
for mg, dm in zip(names, dem):
    by_name[norm(mg)] = mg
    by_name[norm(dm)] = mg

text = open(log, errors="replace").read()
seen = []
for m in re.finditer(r"^Race: (.+?)\s*\n(.*?) ; - Kernel (.*?): Sass offset (\d+)", text, re.M | re.S):
    kind, instr, kern, off = m.group(1), m.group(2).strip(), m.group(3), int(m.group(4))
    mg = by_name.get(norm(kern))
    hit = funcs.get(mg, {}).get(off) if mg else None
    if hit is None:   # fall back: any function with this instruction at this offset
        c = [(f, funcs[f][off]) for f in funcs if off in funcs[f] and norm(funcs[f][off][1]) == norm(instr)]
        if len(c) == 1:
            mg, hit = c[0]
    line = hit[0] if hit else "?"
    key = (kind, off, mg)
    if key in seen:
        continue
    seen.append(key)
    k = (dem[names.index(mg)] if mg in names else kern)
    print(f"{kind} | {instr} | {line} | off {off} | {k[:90]}")

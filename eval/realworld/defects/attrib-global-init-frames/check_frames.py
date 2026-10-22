"""Runs eval/realworld/harness/rw_attribute.py:cubin_frames (copied verbatim from f182bb0, lines 29-31 and 39-68;
only `sh` is replaced by subprocess.run) on a cubin and prints the frames of every LDS/STS of each function,
next to the frames the same parser gives on the `-c` (code sections only) listing.
usage: python3 check_frames.py <cubin>"""
import os, re, subprocess, sys

FILE_RE = re.compile(r'File\s+"([^"]+)",\s*line\s+(\d+)')
OFF_RE = re.compile(r"^\s*/\*([0-9a-fA-F]{4,})\*/")
SECTION_RE = re.compile(r'^\s*\.section\s+\.text\.(\S+?),')


def parse(stdout):                      # body of cubin_frames, rw_attribute.py:47-66
    funcs, fn, cur, in_group = {}, None, [], False
    for ln in stdout.splitlines():
        m = SECTION_RE.match(ln)
        if m:
            fn = m.group(1)
            funcs.setdefault(fn, {})
            cur, in_group = [], False
            continue
        t = ln.strip()
        if t.startswith("//##"):
            fr = [{"file": f, "line": int(n)} for f, n in FILE_RE.findall(t)]
            if fr:
                cur = (cur + fr) if in_group else fr
                in_group = True
            continue
        m = OFF_RE.match(ln)
        if m and fn is not None:
            funcs[fn][int(m.group(1), 16)] = [dict(x) for x in cur]
        if t and not t.startswith("//"):
            in_group = False
    return funcs


cubin = sys.argv[1]
harness = subprocess.run(["nvdisasm", "--print-line-info-inline", cubin], capture_output=True, text=True).stdout
code = subprocess.run(["nvdisasm", "-c", "--print-line-info-inline", cubin], capture_output=True, text=True).stdout
fh, fc = parse(harness), parse(code)
ops = {}
fn = None
for ln in code.splitlines():
    m = SECTION_RE.match(ln)
    if m: fn = m.group(1); continue
    m = re.match(r"^\s*/\*([0-9a-f]{4,})\*/\s*(.*?)\s*;", ln)
    if m and fn and re.search(r"\b(LDS|STS)", m.group(2)): ops.setdefault(fn, []).append((int(m.group(1), 16), m.group(2)))
fmt = lambda fr: " <- ".join(f"{os.path.basename(x['file'])}:{x['line']}" for x in fr or [])
bad = 0
for fn, lst in ops.items():
    for pc, op in lst:
        h, c = fmt(fh.get(fn, {}).get(pc)), fmt(fc.get(fn, {}).get(pc))
        bad += h != c
        print(f"{fn} {pc:#06x} {op:28s} harness: {h:40s} code-only listing: {c}")
print("MISMATCH" if bad else "OK", f"({bad} shared-memory pcs attributed differently)")

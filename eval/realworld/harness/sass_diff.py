#!/usr/bin/env python3
"""Compare the SASS of the kernels whose (mangled) name contains SUBSTR in two binaries.
    sass_diff.py <exe-A> <exe-B> <substr> [--arch sm_89]
Prints, per kernel, SAME or DIFFERENT (with a unified diff).  Exit 0 iff every matched kernel is SAME
and at least one kernel matched.  Used by lineinfo_check.sh (T21a step 2: a build with and without
-lineinfo must have the same SASS, otherwise the traced build is the -lineinfo one)."""
import argparse, difflib, re, subprocess, sys


def sass(exe, arch, sub):
    out = subprocess.run(["cuobjdump", "-sass", "-arch", arch, exe], capture_output=True, text=True).stdout
    funcs, cur = {}, None
    for line in out.splitlines():
        m = re.match(r"\s*Function : (\S+)", line)
        if m:
            cur = m.group(1)
            funcs[cur] = [] if sub in cur else None
            continue
        if cur and funcs.get(cur) is not None and line.strip().startswith("/*"):
            funcs[cur].append(line.strip())
    return {k: v for k, v in funcs.items() if v is not None}


ap = argparse.ArgumentParser()
ap.add_argument("a")
ap.add_argument("b")
ap.add_argument("substr")
ap.add_argument("--arch", default="sm_89")
x = ap.parse_args()
A, B = sass(x.a, x.arch, x.substr), sass(x.b, x.arch, x.substr)
ok = bool(A or B)
for k in sorted(set(A) | set(B)):
    if k not in A or k not in B:
        print("DIFFERENT %s: only in %s" % (k, "B" if k in B else "A"))
        ok = False
        continue
    if A[k] == B[k]:
        print("SAME %s (%d lines)" % (k, len(A[k])))
    else:
        ok = False
        print("DIFFERENT %s" % k)
        sys.stdout.writelines(l + "\n" for l in list(difflib.unified_diff(A[k], B[k], "A", "B", lineterm="", n=1))[:60])
if not (A or B):
    print("no kernel named *%s* in %s SASS of either binary" % (x.substr, x.arch))
sys.exit(0 if ok else 1)

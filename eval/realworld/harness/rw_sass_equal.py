#!/usr/bin/env python3
"""rw_sass_equal.py <exe-A> <exe-B> [--arch sm_89]: are the sm_89 SASS of every function of the two binaries identical?
(T21b: the relinked --cudart shared artifact against T21a's static-cudart one.) Prints SAME/DIFFERENT with counts; exit 0 iff SAME."""
import re, subprocess, sys
NORM = re.compile(r"_GLOBAL__N__[0-9a-f]{8}_")


def sass(exe, arch):
    out = subprocess.run(["cuobjdump", "-sass", "-arch", arch, exe], capture_output=True, text=True).stdout
    funcs, cur = {}, None
    for line in out.splitlines():
        m = re.match(r"\s*Function : (\S+)", line)
        if m:
            cur = NORM.sub("_GLOBAL__N__X_", m.group(1)); funcs[cur] = []; continue
        if cur is not None and line.strip().startswith("/*"):
            funcs[cur].append(re.sub(r"\s+", " ", line.strip()))
    return funcs
a, b, arch = sys.argv[1], sys.argv[2], (sys.argv[4] if len(sys.argv) > 4 else "sm_89")
A, B = sass(a, arch), sass(b, arch)
ninstr = sum(len(v) for v in A.values())
diff = [k for k in sorted(set(A) | set(B)) if A.get(k) != B.get(k)]
if A and not diff:
    print(f"SAME: {len(A)} functions, {ninstr} SASS lines identical ({arch})"); sys.exit(0)
print(f"DIFFERENT: {len(A)} vs {len(B)} functions; differing: {diff[:5]} ({len(diff)} total)"); sys.exit(1)

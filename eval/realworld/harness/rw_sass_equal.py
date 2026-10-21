#!/usr/bin/env python3
"""rw_sass_equal.py <exe-A> <exe-B> [--arch sm_89]: are the sm_89 SASS of every function of the two binaries identical?
(T21b: the relinked --cudart shared artifact against T21a's static-cudart one.) Function names are compared after replacing the
compiler-generated hashes of anonymous-namespace / lambda symbols (`_GLOBAL__N__<8 hex>_`, `_cpp_<8 hex>_<digits>`), which differ
between two compilations of the same source; the SASS lines are compared with whitespace collapsed. Functions with equal normalized
names are compared as multisets. Prints SAME/DIFFERENT with counts; exit 0 iff SAME."""
import re, subprocess, sys
from collections import defaultdict

NORM = [(re.compile(r"_GLOBAL__N__[0-9a-f]{8}_"), "_GLOBAL__N__X_"), (re.compile(r"(_cpp|_cu)_[0-9a-f]{8}_\d+"), r"\1_X")]


def norm(s):
    for rx, rep in NORM:
        s = rx.sub(rep, s)
    return s


def sass(exe, arch):
    out = subprocess.run(["cuobjdump", "-sass", "-arch", arch, exe], capture_output=True, text=True).stdout
    funcs, cur = defaultdict(list), None
    body = None
    for line in out.splitlines():
        m = re.match(r"\s*Function : (\S+)", line)
        if m:
            body = []
            funcs[norm(m.group(1))].append(body)
            continue
        if body is not None and line.strip().startswith("/*"):
            body.append(norm(re.sub(r"\s+", " ", line.strip())))
    return {k: sorted(tuple(b) for b in v) for k, v in funcs.items()}


a, b = sys.argv[1], sys.argv[2]
arch = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--arch" else "sm_89"
A, B = sass(a, arch), sass(b, arch)
ninstr = sum(len(x) for v in A.values() for x in v)
diff = [k for k in sorted(set(A) | set(B)) if A.get(k) != B.get(k)]
if A and not diff:
    print(f"SAME: {sum(len(v) for v in A.values())} functions, {ninstr} SASS lines identical ({arch})")
    sys.exit(0)
print(f"DIFFERENT: {sum(len(v) for v in A.values())} vs {sum(len(v) for v in B.values())} functions; differing: {diff[:3]} ({len(diff)} names)")
sys.exit(1)

#!/bin/bash
# X9 step 2: one translation unit compiled to sm_89 SASS with and without -lineinfo (else the build's own nvcc line);
# nvdisasm of every function without line info, diffed. Usage: x9_lineinfo.sh <source substring>
set -u
CB=/mnt/beegfs/fzheng4/cutlass; BLD=$CB/build; O=$CB/lineinfo; rm -rf $O; mkdir -p $O
export PATH=/usr/local/cuda-13.3/bin:/opt/ohpc/pub/compiler/gcc/12.4.0/bin:$PATH
/home/fzheng4/AccelProf/.env/bin/python - "$1" <<'PY'
import json, sys, shlex
cc = json.load(open("/mnt/beegfs/fzheng4/cutlass/build/compile_commands.json"))
e = next(x for x in cc if sys.argv[1] in x["file"])
cmd = e.get("command") or " ".join(shlex.quote(a) for a in e["arguments"])
toks = shlex.split(cmd)
# drop -o <obj> and -c; add -cubin -o
out, skip = [], False
for t in toks:
    if skip: skip = False; continue
    if t == "-o": skip = True; continue
    if t == "-c": continue
    out.append(t)
open("/mnt/beegfs/fzheng4/cutlass/lineinfo/cmd.txt", "w").write(e["directory"] + "\n" + e["file"] + "\n" + " ".join(shlex.quote(t) for t in out) + "\n")
PY
D=$(sed -n 1p $O/cmd.txt); F=$(sed -n 2p $O/cmd.txt); C=$(sed -n 3p $O/cmd.txt)
echo "TU: $F"; echo "cmd: $C"
cd $D
eval "$C -cubin -o $O/with.cubin" 2> $O/with.err; echo "with rc=$?"
C2=$(echo "$C" | sed 's/ -lineinfo//g'); echo "$C2" | grep -c -- -lineinfo | sed 's/^/lineinfo left in C2: /'
eval "$C2 -cubin -o $O/without.cubin" 2> $O/without.err; echo "without rc=$?"
nvdisasm -c $O/with.cubin > $O/with.sass; nvdisasm -c $O/without.cubin > $O/without.sass
echo "functions with=$(grep -c '\.section *\.text\.' $O/with.sass) without=$(grep -c '\.section *\.text\.' $O/without.sass) lines with=$(wc -l < $O/with.sass) without=$(wc -l < $O/without.sass)"
diff -q $O/with.sass $O/without.sass && echo "SASS IDENTICAL" || { echo "SASS DIFFERS: $(diff $O/with.sass $O/without.sass | grep -c '^[<>]') lines"; diff $O/with.sass $O/without.sass | head -20; }

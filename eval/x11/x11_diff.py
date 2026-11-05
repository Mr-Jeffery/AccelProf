#!/usr/bin/env python3
"""X11 Step 0: compare SuperCollider's native binaries with ours (HeCBench-10, cuHadron-27).
Runs inside a SLURM job (needs cuobjdump and /mnt/beegfs). No GPU is used.
  python x11_diff.py OUTDIR
Writes OUTDIR/step0.json (one record per program) and OUTDIR/sass/<id>.{art,ours}.<sm>.json.
"""
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

OUT = sys.argv[1]
AP = "/home/fzheng4/AccelProf"
BASE = f"{AP}/eval/baselines"
SC = f"{BASE}/setup/tools/supercollider/supercollider-artifacts"
CORP = os.path.realpath(f"{BASE}/corpora")
HEC = f"{CORP}/HeCBench"
os.makedirs(f"{OUT}/sass", exist_ok=True)


def cuobjdump():
    for c in [shutil.which("cuobjdump"), *sorted(glob.glob("/usr/local/cuda*/bin/cuobjdump"), reverse=True),
              *sorted(glob.glob("/home/fzheng4/spack/opt/spack/*/cuda-*/bin/cuobjdump"), reverse=True)]:
        if c and os.path.exists(c):
            return c
    raise SystemExit("no cuobjdump")


CUO = cuobjdump()


def sh(cmd, cwd=None):
    r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, cwd=cwd)
    return r.returncode, r.stdout, r.stderr


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def archs(binary):
    _, o, _ = sh([CUO, "--list-elf", binary])
    elf = sorted(set(re.findall(r"\.(sm_\d+[a-z]?)\.cubin", o)))
    _, o, _ = sh([CUO, "--list-ptx", binary])
    ptx = sorted(set(re.findall(r"\.(sm_\d+[a-z]?)\.ptx", o)))
    return elf, ptx


_R = [(re.compile(r"\bUR\d+\b"), "UR"), (re.compile(r"\bUP\d+\b"), "UP"),
      (re.compile(r"\bR\d+\b"), "R"), (re.compile(r"\bP\d+\b"), "P"),
      (re.compile(r"\.L_x_\d+"), ".L"), (re.compile(r"\s+"), " ")]
_INS = re.compile(r"^/\*[0-9a-fA-F]{4,}\*/\s+(.*?)\s*/\*\s*0x[0-9a-fA-F]+\s*\*/\s*$")


def sass(binary, sm):
    """-> {function: [normalized instruction, ...]} in file order (addresses, register numbers,
    comments and label ids removed)."""
    rc, o, e = sh([CUO, "-sass", "-arch", sm, binary])
    funcs, cur = {}, None
    order = []
    for ln in o.splitlines():
        s = ln.strip()
        m = re.match(r"Function\s*:\s*(\S+)", s)
        if m:
            cur = m.group(1)
            funcs[cur] = []
            order.append(cur)
            continue
        if cur is None or not s or s.startswith("/* 0x") or s.startswith(".") or s.startswith("//"):
            continue
        m = _INS.match(s)
        if not m:
            continue
        t = m.group(1).rstrip(" ;")
        for rx, rep in _R:
            t = rx.sub(rep, t)
        if re.match(r"^(@!?U?P\w* )?(BRA|CALL|BSSY|BSYNC|BREAK|JMP|SSY|SYNC|PBK|RET|BRX|JMX|CONT|PCNT|KILL)\b", t):
            t = re.sub(r"0x[0-9a-fA-F]+", "ADDR", t)
        funcs[cur].append(t.strip())
    return funcs, order, rc, e[-200:]


def make_n(d, args):
    rc, o, e = sh(["make", "-n", "-B", *args], cwd=d)
    return [ln for ln in o.splitlines() if "nvcc" in ln or "NVCC" in ln][:6]


def decide(art, our, tag, ref):
    """artifact binary vs our binary -> record (rules in the task, in order)."""
    rec = dict(id=tag)
    rec["art_path"], rec["our_path"] = art, our
    rec["art_sha256"], rec["our_sha256"] = sha(art), sha(our)
    ae, ap = archs(art)
    oe, op = archs(our)
    rec.update(art_elf=ae, art_ptx=ap, our_elf=oe, our_ptx=op)
    common = sorted(set(ae) & set(oe), key=lambda s: int(re.sub(r"\D", "", s)))
    rec["common_arch"] = common
    # (1) the artifact states the source commit
    if ref.get("art_commit") and ref.get("our_commit") and ref["art_commit"] == ref["our_commit"]:
        rec.update(rule=1, same=True, why="source commits equal")
        return rec
    rec["rule1"] = f"artifact {ref.get('art_commit') or 'states none'} vs ours {ref.get('our_commit') or 'unknown'}"
    # pick the SASS arch to compare
    pick = None
    if common:
        pick = common[-1] if "sm_89" not in common else "sm_89"
    elif ae and oe:
        pick = None
    rec["compare_arch"] = pick
    if pick is None:
        # no shared cubin arch: dump the nearest pair so the reader can see why
        a_sm = [s for s in ae if int(re.sub(r"\D", "", s)) <= 89 and s.startswith("sm_8")]
        a_sm = a_sm[-1] if a_sm else (ae[-1] if ae else None)
        o_sm = oe[-1] if oe else None
        rec["note"] = f"no common cubin arch; art {ae} ours {oe}"
        if not (a_sm and o_sm):
            rec.update(rule=2, same=None, why="no SASS in one of the binaries (PTX-only?)")
            return rec
        fa, oa, _, _ = sass(art, a_sm)
        fo, oo, _, _ = sass(our, o_sm)
        rec["compare_arch"] = f"art {a_sm} vs ours {o_sm}"
    else:
        fa, oa, _, ea = sass(art, pick)
        fo, oo, _, eo = sass(our, pick)
    json.dump(dict(order=oa, funcs=fa), open(f"{OUT}/sass/{tag}.art.json", "w"))
    json.dump(dict(order=oo, funcs=fo), open(f"{OUT}/sass/{tag}.ours.json", "w"))
    rec["n_kernels_art"], rec["n_kernels_ours"] = len(fa), len(fo)
    # (2) kernel lists
    if set(fa) != set(fo):
        only_a = [k for k in oa if k not in fo]
        only_o = [k for k in oo if k not in fa]
        rec.update(rule=2, same=False, why="kernel lists differ",
                   only_artifact=only_a[:8], only_ours=only_o[:8], first_diff=(only_a or only_o)[0])
        return rec
    # (3) per-kernel SASS
    diff = [k for k in oa if fa[k] != fo[k]]
    rec["n_kernels_diff"] = len(diff)
    if diff:
        k = diff[0]
        a, o = fa[k], fo[k]
        i = next((j for j in range(min(len(a), len(o))) if a[j] != o[j]), min(len(a), len(o)))
        rec.update(rule=3, same=False, why="per-kernel SASS differs", first_diff=k,
                   first_diff_detail=dict(instr_art=len(a), instr_ours=len(o), at=i,
                                          art=a[i] if i < len(a) else None, ours=o[i] if i < len(o) else None),
                   diff_kernels=diff[:10])
    else:
        rec.update(rule=3, same=True, why="per-kernel SASS identical after normalization")
    return rec


def main():
    res = {"tool": CUO, "recs": []}
    rc, o, _ = sh([CUO, "--version"])
    res["cuobjdump_version"] = o.strip().splitlines()[-1] if o else ""
    ours_commit = sh(["git", "-C", HEC, "rev-parse", "HEAD"])[1].strip()
    ours_date = sh(["git", "-C", HEC, "log", "-1", "--format=%cI"])[1].strip()
    shallow = os.path.exists(f"{HEC}/.git/shallow")
    res["hecbench"] = dict(ours_commit=ours_commit, ours_date=ours_date, shallow=shallow,
                           art_commit="6a8c46c4651dbe85e16a787d9a786cfe8f80e00d (Dockerfile)",
                           has_22574e78=sh(["git", "-C", HEC, "cat-file", "-t", "22574e78"])[1].strip() or "no object")
    sub = json.load(open(f"{SC}/scripts/hecbench/benchmarks/artifact_subset.json"))["benchmarks"]
    mrows = {}
    import csv
    for r in csv.DictReader(open(f"{BASE}/bin/P9/manifest_rows.csv")):
        mrows[r["program"]] = r
    for app, cfg in sub.items():
        art = f"{SC}/bin/hecbench/native/{app}"
        our = f"{BASE}/bin/P9/{app}-cuda"
        rec = decide(art, our, f"hec-{app}",
                     dict(art_commit="6a8c46c4651dbe85e16a787d9a786cfe8f80e00d", our_commit=ours_commit))
        rec.update(suite="HeCBench", program=app, art_args=" ".join(cfg.get("args", [])),
                   art_cwd=f"$HECBENCH_PATH/src/{app}-cuda", our_args=mrows[f"{app}-cuda"]["args"],
                   our_cwd=f"{HEC}/src/{app}-cuda (run_supercollider.py: cwd of the app source dir)")
        rec["our_build"] = make_n(f"{HEC}/src/{app}-cuda", ["ARCH=sm_89", "CC=nvcc",
                                  "EXTRA_CFLAGS=-ccbin /usr/bin/g++ -lineinfo --cudart shared"])
        res["recs"].append(rec)
        json.dump(res, open(f"{OUT}/step0.json", "w"), indent=1)
    # cuHadron
    for art in sorted(glob.glob(f"{SC}/bin/cuhadron/native/*/*.all.out")):
        cat = os.path.basename(os.path.dirname(art))
        name = os.path.basename(art)[:-len(".all.out")]
        our = f"{BASE}/bin/P6/{cat}__{name}__racy.sm86.out"
        if not os.path.exists(our):
            alt = glob.glob(f"{BASE}/bin/P6/{cat}__{name}__*racy*.out")
            our = alt[0] if alt else our
        if not os.path.exists(our):
            res["recs"].append(dict(id=f"cuh-{cat}-{name}", suite="cuHadron", program=f"{cat}/{name}",
                                    note="our binary missing", art_path=art, our_path=our,
                                    art_sha256=sha(art)))
            continue
        rec = decide(art, our, f"cuh-{cat}-{name}", dict(art_commit=None, our_commit=None))
        rec.update(suite="cuHadron", program=f"{cat}/{name}", art_args="", our_args="")
        res["recs"].append(rec)
        json.dump(res, open(f"{OUT}/step0.json", "w"), indent=1)
    res["cuh_build"] = make_n(f"{AP}/cuHadron", ["ARCH=sm_86", "FIXED=0"])
    json.dump(res, open(f"{OUT}/step0.json", "w"), indent=1)
    print("done", len(res["recs"]))


main()

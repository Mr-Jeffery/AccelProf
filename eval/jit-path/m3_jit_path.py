#!/usr/bin/env python3
"""M3: does the profiler read the SASS the driver compiles at load time (PTX-only binary), and are
the pc offsets of its records the offsets of that SASS?

Two programs (ScoR race_interwarp_none-atom_waw, P4 reduction_norace small), each built twice:
  sass: -gencode arch=compute_89,code=sm_89          (AOT SASS, the harness's build)
  ptx : -gencode arch=compute_89,code=compute_89     (PTX only, no SASS: the driver JITs at load)
Each is run under the profiler in both modes. For ptx, the driver's JIT cubin is taken from the
driver's compute cache (CUDA_CACHE_PATH, a fresh directory per run), disassembled, and the dump's
pcs are checked against its instruction offsets; the same dump is also analysed against the AOT
cubin as a control.

Must run on a GPU node (blib.resolve_cuda_home raises on the login node).
  .env/bin/python eval/jit-path/m3_jit_path.py --out DIR [--reps 3]
"""
import argparse
import glob
import json
import os
import re
import shutil
import struct
import subprocess
import sys

APH = os.environ.get("CUVEIN_HOME", "/home/fzheng4/AccelProf")
sys.path.insert(0, f"{APH}/eval/baselines")
import blib  # noqa: E402
sys.path.insert(0, blib.PYDIR)
sys.path.insert(0, f"{APH}/eval")
import run_cuvein as rc  # noqa: E402

LITMUS = f"{APH}/ScoR/microbenchmarks/src/race_interwarp_none-atom_waw.cu"
REDDIR = f"{APH}/ScoR/benchmarks/reduction"
REDIN = f"{APH}/eval/baselines/inputs/reduction.small.in"
GEN = {"sass": "-gencode arch=compute_89,code=sm_89",
       "ptx": "-gencode arch=compute_89,code=compute_89"}
MODES = ["vector-clock", "scalar-clock"]


def sh(cmd, env, cwd=None, check=False, timeout=900):
    r = subprocess.run(cmd, shell=isinstance(cmd, str), env=env, cwd=cwd, capture_output=True,
                       text=True, timeout=timeout)
    if check and r.returncode:
        raise SystemExit(f"FAILED {cmd}\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return r


def elf_slices(blob):
    """All ELF64 images embedded in a driver compute-cache file."""
    out, i = [], 0
    while True:
        i = blob.find(b"\x7fELF", i)
        if i < 0:
            return out
        try:
            phoff, shoff = struct.unpack_from("<QQ", blob, i + 0x20)
            phentsize, phnum, shentsize, shnum = struct.unpack_from("<HHHH", blob, i + 0x36)
            end = i + max(shoff + shentsize * shnum, phoff + phentsize * phnum)
            if blob[i + 4] == 2 and 0 < end <= len(blob):
                out.append(blob[i:end])
        except struct.error:
            pass
        i += 4


def sass_listing(cubin, env):
    """{function: [(offset, text)]} from nvdisasm -c -poff."""
    txt = sh(["nvdisasm", "-c", "-poff", cubin], env).stdout
    funcs, cur = {}, None
    for ln in txt.splitlines():
        m = re.match(r"\s*\.text\.(\S+):", ln)
        if m:
            cur = m.group(1)
            funcs[cur] = []
            continue
        m = re.match(r"\s*/\*([0-9a-f]{4,})\*/\s+(.*?);", ln)
        if m and cur is not None:
            funcs[cur].append((int(m.group(1), 16), m.group(2).strip()))
    return funcs


def compare_listings(a, b):
    """Per function: instruction counts, whether the (offset, text) sequences are equal, first difference."""
    rows = {}
    for fn in sorted(set(a) | set(b)):
        la, lb = a.get(fn), b.get(fn)
        if la is None or lb is None:
            rows[fn] = {"in_sass": la is not None, "in_jit": lb is not None}
            continue
        first = next((k for k, (x, y) in enumerate(zip(la, lb)) if x != y), None)
        rows[fn] = {"n_sass": len(la), "n_jit": len(lb), "identical": la == lb,
                    "first_diff_index": first,
                    "first_diff_sass": la[first] if first is not None else None,
                    "first_diff_jit": lb[first] if first is not None else None}
    return rows


def pcs_in_dump(depdir):
    """Every integer under a key that names a pc in the dump's JSON files, with the file it came from."""
    found = {}
    keyre = re.compile(r"(^|_)pcs?$|^(a|b|u|v)_pc$|^pc_")

    def walk(o, f):
        if isinstance(o, dict):
            for k, v in o.items():
                if keyre.search(k):
                    vs = v if isinstance(v, list) else [v]
                    for x in vs:
                        if isinstance(x, int):
                            found.setdefault(f, set()).add(x)
                walk(v, f)
        elif isinstance(o, list):
            for x in o:
                walk(x, f)
    for p in sorted(glob.glob(f"{depdir}/*.json")):
        try:
            walk(json.load(open(p)), os.path.basename(p))
        except (ValueError, OSError):
            pass
    return found


def build(out, env, cuda, bcuda):
    nvcc = f"{bcuda}/bin/nvcc"
    ver = sh([nvcc, "--version"], env).stdout.strip().splitlines()[-1]
    common = "-lineinfo --cudart shared -ccbin /usr/bin/g++"
    exes = {}
    for kind, gen in GEN.items():
        d = f"{out}/litmus_{kind}"
        os.makedirs(d, exist_ok=True)
        e = f"{d}/race_interwarp_none-atom_waw"
        sh(f"{nvcc} {gen} {common} {LITMUS} -o {e}", env, check=True)
        exes[f"litmus_{kind}"] = dict(exe=e, stdin=None, kind=kind, prog="atom_waw")
        d = f"{out}/reduction_{kind}"
        shutil.rmtree(d, ignore_errors=True)
        shutil.copytree(REDDIR, d)
        e = f"{d}/reduction_norace"
        sh(f"{nvcc} {gen} {common} -std=c++11 -I. -D NTHREADS=512 -D NBLOCKS=30 red_main.cu -o {e}",
           env, cwd=d, check=True)
        exes[f"reduction_{kind}"] = dict(exe=e, stdin=REDIN, kind=kind, prog="reduction")
    for name, x in exes.items():
        x["lelf"] = sh(["cuobjdump", "-lelf", x["exe"]], env).stdout.split()
        x["lptx"] = sh(["cuobjdump", "-lptx", x["exe"]], env).stdout.split()
    return ver, exes


def jit_cubin(cachedir, dest, env):
    """The driver's JIT cubin(s) from a fresh compute cache -> dest/*.cubin (+ listing)."""
    os.makedirs(dest, exist_ok=True)
    files = [f for f in glob.glob(f"{cachedir}/**", recursive=True) if os.path.isfile(f)]
    n = 0
    for f in files:
        for blob in elf_slices(open(f, "rb").read()):
            p = f"{dest}/jit.{n}.sm_89.cubin"
            open(p, "wb").write(blob)
            n += 1
    return files, sorted(glob.glob(f"{dest}/*.cubin"))


def prep_cubindir(d, env):
    """dot per cubin + atomic-scope sidecar, as blib.extract does after cuobjdump."""
    for c in glob.glob(f"{d}/*.cubin"):
        with open(os.path.splitext(c)[0] + ".dot", "w") as f:
            subprocess.run(["nvdisasm", "-bbcfg", "-poff", c], stdout=f, stderr=subprocess.DEVNULL, env=env)
    scope = f"{d}/atomic_scope.txt"
    dots = glob.glob(f"{d}/*.dot")
    if dots:
        r = subprocess.run([f"{APH}/.env/bin/python", blib.SIDECAR, *dots, "-o", scope],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if r.returncode == 0 and os.path.exists(scope):
            return scope
    return ""


def analyse(depdir, cubindir):
    try:
        ids, pcs, raw = rc._analyze_reports(depdir, cubindir)
        return {"verdict": "RACE" if ids else "CLEAN", "reports": len(ids), "report_ids": sorted(ids),
                "pcs": sorted(pcs)}
    except Exception as ex:   # AlignmentError etc.: recorded, not fatal
        return {"verdict": "ANALYSIS-ERROR", "error": f"{type(ex).__name__}: {str(ex)[:300]}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--build-cuda", default="", help="toolkit whose nvcc builds the programs (the runtime/profiler env stays CUDA_HOME)")
    ap.add_argument("--cap", type=int, default=600)
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    cuda = blib.resolve_cuda_home()
    env = blib.base_env(cuda)
    res = {"cuda_home": cuda, "host": os.uname().nodename, "runs": [], "builds": {}}
    res["gpu"] = sh(["nvidia-smi", "--query-gpu=name,driver_version,compute_cap", "--format=csv,noheader"], env).stdout.strip()
    ver, exes = build(out, env, cuda, a.build_cuda or cuda)
    res["nvcc"] = ver
    res["build_cuda"] = a.build_cuda or cuda
    for name, x in exes.items():
        res["builds"][name] = {k: x[k] for k in ("exe", "lelf", "lptx")}
    # AOT cubin dirs (SASS builds) via the harness's own extraction
    cub = {}
    for name, x in exes.items():
        exe_dir = os.path.dirname(x["exe"])
        d = f"{exe_dir}/{os.path.basename(x['exe'])}_eval_cubins"
        if x["kind"] == "sass":
            x["scope"], cubs = blib.extract(os.path.realpath(x["exe"]), d, env)
            x["cubindir"] = d
            x["listing"] = {c: sass_listing(c, env) for c in cubs}
        else:
            # pass A: native run with a fresh cache -> the JIT cubin, its CFG and scope sidecar
            cache = f"{out}/{name}/cacheA"
            shutil.rmtree(cache, ignore_errors=True)
            os.makedirs(cache)
            e2 = dict(env, CUDA_CACHE_PATH=cache, CUDA_CACHE_DISABLE="0")
            w, _, r_, to = blib.run_timed([x["exe"]], e2, exe_dir, 300, stdin_path=x["stdin"])
            files, cubs = jit_cubin(cache, d_ := f"{out}/{name}/jit_cubins", env)
            x["jit_cache_files"] = [os.path.relpath(f, out) for f in files]
            x["jit_cubins"] = cubs
            x["native_rc"] = r_
            x["scope"] = prep_cubindir(d_, env) if cubs else ""
            x["cubindir"] = d_
            x["listing"] = {c: sass_listing(c, env) for c in cubs}
    # SASS-vs-JIT instruction comparison per program
    res["sass_vs_jit"] = {}
    for prog in ("litmus", "reduction"):
        s, j = exes[f"{prog}_sass"], exes[f"{prog}_ptx"]
        ls = {fn: v for d in s["listing"].values() for fn, v in d.items()}
        lj = {fn: v for d in j["listing"].values() for fn, v in d.items()}
        res["sass_vs_jit"][prog] = compare_listings(ls, lj)
    # profiled runs
    for name, x in exes.items():
        exe_dir = os.path.dirname(x["exe"])
        base = os.path.basename(x["exe"])
        for mode in MODES:
            for rep in range(1, a.reps + 1):
                e = blib.base_env(cuda, hb_trace=True, hb_mode=mode, scope_file=x["scope"] or None)
                cache = None
                if x["kind"] == "ptx":
                    cache = f"{out}/{name}/cache_{mode}_{rep}"
                    shutil.rmtree(cache, ignore_errors=True)
                    os.makedirs(cache)
                    e.update(CUDA_CACHE_PATH=cache, CUDA_CACHE_DISABLE="0")
                for d in glob.glob(f"{exe_dir}/dependency_{base}_*"):
                    shutil.rmtree(d, ignore_errors=True)
                accel = ["accelprof", "-t", "pc_dependency_analysis", "-n", "1", f"./{base}"]
                wall, peak, rc_, to = blib.run_timed(accel, e, exe_dir, a.cap, poll_mem=True, stdin_path=x["stdin"])
                deps = sorted(glob.glob(f"{exe_dir}/dependency_{base}_*"), key=os.path.getmtime)
                dep = deps[-1] if deps else ""
                row = {"name": name, "kind": x["kind"], "prog": x["prog"], "mode": mode, "rep": rep,
                       "rc": rc_, "timeout": to, "wall_s": wall,
                       "kernel_jsons": len(glob.glob(f"{dep}/kernel_*.json")) if dep else 0}
                if dep and row["kernel_jsons"]:
                    row["against_own_cubins"] = analyse(dep, x["cubindir"])
                    allpcs = pcs_in_dump(dep)
                    row["dump_pc_keys"] = {f: len(v) for f, v in allpcs.items()}
                    uni = sorted(set().union(*allpcs.values())) if allpcs else []
                    row["dump_pcs"] = uni
                    offs = {o for lst in x["listing"].values() for fl in lst.values() for o, _ in fl}
                    row["dump_pcs_not_instruction_offsets_of_own_cubins"] = [p for p in uni if p not in offs]
                    if x["kind"] == "ptx":
                        # control: the same dump against the AOT cubin of the same source
                        s = exes[name.replace("_ptx", "_sass")]
                        row["against_aot_cubins"] = analyse(dep, s["cubindir"])
                        files, cubs = jit_cubin(cache, f"{out}/{name}/jit_cubins_{mode}_{rep}", env)
                        row["in_run_jit_cubins_equal_pass_A"] = (
                            [open(c, "rb").read() for c in cubs] == [open(c, "rb").read() for c in x["jit_cubins"]])
                    if rep == 1:
                        dst = f"{out}/{name}/dump_{mode}"
                        shutil.rmtree(dst, ignore_errors=True)
                        shutil.copytree(dep, dst)
                for d in glob.glob(f"{exe_dir}/dependency_{base}_*"):
                    shutil.rmtree(d, ignore_errors=True)
                res["runs"].append(row)
                print(json.dumps({k: row[k] for k in ("name", "mode", "rep", "rc", "kernel_jsons")}), flush=True)
    for x in exes.values():
        x.pop("listing", None)
    res["exes"] = exes
    json.dump(res, open(f"{out}/m3_results.json", "w"), indent=1, default=str)
    json.dump({"sass_vs_jit": res["sass_vs_jit"]}, open(f"{out}/m3_sass_vs_jit.json", "w"), indent=1, default=str)
    print("wrote", f"{out}/m3_results.json")


if __name__ == "__main__":
    main()

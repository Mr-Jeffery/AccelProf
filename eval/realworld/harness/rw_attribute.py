#!/usr/bin/env python3
"""T21b step 2: every reported pc pair of one stored run -> file:line (inlined frames included), kernel-aware.

For each kernel JSON of each mode the stored CFG dots are tried in order exactly as run_cuvein._analyze_reports does
(the alignment stage: kernel name, then every traced pc must be a memory opcode in the CFG; AlignmentError -> next dot;
a dot that aligned an earlier launch of the same kernel name is tried first). The chosen dot's cubin is re-extracted from
the run's executable (cuobjdump -xelf all), its CFG regenerated (nvdisasm -bbcfg -poff) and compared with the stored dot
(`dots_regenerated_equal`), and `nvdisasm --print-line-info-inline` of the cubin maps each function's pcs to frames
(innermost first). Output: one JSON per id with the reports deduped on (kernel, pc pair, space) by run_cuvein's class and
a2 rules, the SASS opcode text of both pcs (D20: is there a .STRONG token?), and, with the target's entry in
eval/realworld/recall_pairs.json, `site_verdicts`: every verdict (also ORDERED) and skipped edge between pcs that hit the
oracle's sites, the evidence for a miss (m1 never ran / m2 ordered by an accepted edge / m3 outside the model).

  rw_attribute.py --id X --store S --manifest M --out O.json [--pairs recall_pairs.json]   (compute node: nvdisasm)"""
import argparse, csv, fnmatch, glob, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
APH = os.environ.get("ACCEL_PROF_HOME", "/home/fzheng4/AccelProf")
sys.path.insert(0, f"{WT}/eval/baselines")
sys.path.insert(0, f"{APH}/python")
sys.path.insert(0, f"{APH}/eval")
import blib                                  # noqa: E402
import sync_dominance as sd                  # noqa: E402
import aggregate as agg                      # noqa: E402
import run_cuvein as rc                      # noqa: E402

MODES = ("vector-clock", "scalar-clock")
FILE_RE = re.compile(r'File\s+"([^"]+)",\s*line\s+(\d+)')
OFF_RE = re.compile(r"^\s*/\*([0-9a-fA-F]{4,})\*/")
SECTION_RE = re.compile(r'^\s*\.section\s+\.text\.(\S+?),')
MAX_SITE_VERDICTS = 400


def sh(cmd, env, cwd=None, timeout=600):
    return subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def cubin_frames(cubin, env, cache):
    """-> {function (mangled): {pc: [ {file, line}, ... ]}} from `nvdisasm --print-line-info-inline`.
    Each //## line of -gi is one frame ("File F, line N [inlined at F2, line M]"); a group of consecutive
    //## lines is one instruction's stack, innermost frame first. The listing is split at the
    `.section .text.<function>` lines; /*OFFSET*/ is relative to the function."""
    if cubin in cache:
        return cache[cubin]
    r = sh(["nvdisasm", "-c", "--print-line-info-inline", cubin], env, timeout=3600)   # -c: code sections only (D-T2)
    funcs, fn, cur, in_group = {}, None, [], False
    for ln in r.stdout.splitlines():
        m = SECTION_RE.match(ln)
        if m:
            fn = m.group(1)
            funcs.setdefault(fn, {})
            cur, in_group = [], False
            continue
        if re.match(r"^\s*\.section\s", ln):      # a non-text section (.nv.global.init, ...): its /*offset*/ lines are not code (D-T2)
            fn, cur, in_group = None, [], False
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
    cache[cubin] = funcs
    return funcs


def hits(frames, ranges, tol=2):
    """frames: [ {file, line} ]; ranges: [[file-pattern, l0, l1], ...] -> the matching range or None."""
    for fr in frames or ():
        base = os.path.basename(fr["file"])
        for pat, l0, l1 in ranges:
            if fnmatch.fnmatch(base, pat) and l0 - tol <= fr["line"] <= l1 + tol:
                return [pat, l0, l1]
    return None


def target_ranges(spec):
    out = []
    for p in spec.get("pairs", []):
        out += p["A"] + p["B"]
    for sect in ("both_builds",):
        for p in spec.get(sect, []):
            out += p["A"] + p["B"]
    fx = spec.get("fixed", {})
    for sect in ("equiv", "residual"):
        for p in fx.get(sect, []):
            out += p["A"] + p["B"]
    return out


def compact(v):
    keep = {}
    for k, x in v.items():
        if isinstance(x, (str, int, float, bool)) or x is None:
            keep[k] = x
        elif k in ("hb_chain", "opcodes", "ordering_syncs") and isinstance(x, list):
            keep[k] = x[:6]
    return keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--store", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pairs", default=f"{WT}/eval/realworld/recall_pairs.json")
    a = ap.parse_args()
    row = next(r for r in csv.DictReader(open(a.manifest, newline="")) if r["id"] == a.id)
    target = row.get("target") or a.id.rsplit("-", 1)[0]
    kernel_sub = row.get("kernel") or ""
    exe = os.path.realpath(row["exe"])
    idir = f"{a.store}/{a.id}"
    spec = {}
    if os.path.exists(a.pairs):
        spec = json.load(open(a.pairs)).get(target, {})
    ranges = target_ranges(spec)
    cuda = blib.resolve_cuda_home()
    env = blib.base_env(cuda)
    tmp = tempfile.mkdtemp(prefix=f"rwattr-{a.id}-", dir=os.environ.get("TMPDIR", "/tmp"))
    try:
        cubs = sorted(blib.xelf_all(exe, tmp, env))   # T21c: same extraction as the run (over-long ELF names)
        dots = sorted(glob.glob(f"{idir}/dots/*.dot"))
        cubin_of = {}
        for c in cubs:
            base = os.path.splitext(os.path.basename(c))[0]
            sd_ = f"{idir}/dots/{base}.dot"
            if os.path.exists(sd_):
                cubin_of[sd_] = c
        dot_checked = {}

        def dot_equal(dot):
            if dot not in dot_checked:
                c = cubin_of.get(dot)
                if not c:
                    dot_checked[dot] = None
                else:
                    r = sh(["nvdisasm", "-bbcfg", "-poff", c], env, timeout=3600)
                    dot_checked[dot] = (r.stdout == Path(dot).read_text())
            return dot_checked[dot]

        res = dict(id=a.id, target=target, exe=exe, cuda_home=cuda, n_cubins=len(cubs), n_dots=len(dots),
                   oracle_kernel_substr=kernel_sub, spec_found=bool(spec), modes={})
        cache = {}
        dot_for_name = {}
        for mode in MODES:
            md = blib.hb_modes.resolve_dir(idir, mode)
            if not os.path.isdir(md):
                continue
            kjs = sorted(glob.glob(f"{md}/kernel_*.json"),
                         key=lambda p: int(re.findall(r"(\d+)", os.path.basename(p))[-1]))
            ded, cls, a2s, mbug, seen_in = {}, {}, {}, set(), {}
            kernels, unaligned = [], []
            site_v, site_skip, seen_sv = [], {}, set()
            for kj in kjs:
                try:
                    kname = json.loads(Path(kj).read_text())["kernel"]["kernel_name"]
                except (OSError, ValueError, KeyError):
                    kname = None
                order = dots
                if kname in dot_for_name:
                    order = [dot_for_name[kname]] + [d for d in dots if d != dot_for_name[kname]]
                rep, dot_used = None, None
                for dot in order:
                    try:
                        rep = sd.analyze(dot, kj)
                        dot_used = dot
                        break
                    except sd.AlignmentError:
                        continue
                if rep is None:
                    unaligned.append(os.path.basename(kj))
                    continue
                dot_for_name[kname] = dot_used
                mangled = rep["kernel"]["mangled"]
                kernels.append(dict(kernel_json=os.path.basename(kj), name=rep["kernel"]["name"], mangled=mangled,
                                    dot=os.path.basename(dot_used), summary=rep.get("summary"),
                                    gate_policy=rep.get("gate_policy")))
                frames_k = None
                if ranges and cubin_of.get(dot_used):
                    frames_k = cubin_frames(cubin_of[dot_used], env, cache).get(mangled, {})
                for v in rep["verdicts"]:
                    k = (mangled,) + agg._dedup_key(v)
                    if v.get("model_bug") or v.get("hb_class") == "model_bug":
                        mbug.add(k)
                    if v["verdict"] in ("RACE", "SC"):
                        seen_in.setdefault(k, []).append(os.path.basename(kj))
                    if frames_k is not None and len(site_v) < MAX_SITE_VERDICTS:
                        fa, fb = frames_k.get(v["current_pc"]), frames_k.get(v["ancient_pc"])
                        if hits(fa, ranges) and hits(fb, ranges):
                            sk = (mangled, v["current_pc"], v["ancient_pc"], v["space"], v["verdict"], v.get("hb_class"))
                            if sk not in seen_sv:
                                seen_sv.add(sk)
                                site_v.append(dict(compact(v), kernel=rep["kernel"]["name"], mangled=mangled,
                                                   kernel_json=os.path.basename(kj),
                                                   cur_frames=(fa or [])[:3], anc_frames=(fb or [])[:3]))
                    if v["verdict"] == "RACE":
                        ded.setdefault(k, dict(v, _dot=dot_used))
                        c = v.get("matrix_class", v.get("hb_class")) or "race"
                        if rc._CLASS_RANK.get(c, 2) > rc._CLASS_RANK.get(cls.get(k), -1):
                            cls[k] = c
                        s = a2s.setdefault(k, [False, False, False, False, False])
                        f = v.get("a2_uncertain")
                        s[4] = s[4] or f is not None
                        if c in ("structural", "model_bug"):
                            s[0] = True
                            s[1] = s[1] or f is not True
                            s[3] = s[3] or (f is True and c == "structural" and not v.get("hb_chain"))
                        elif c == "latent":
                            s[2] = True
                    elif v["verdict"] == "SC":
                        ded.setdefault(k + ("SC",), dict(v, _dot=dot_used))
                if frames_k is not None:
                    for e in rep.get("skipped_edges", []):
                        fa, fb = frames_k.get(e.get("current_pc")), frames_k.get(e.get("ancient_pc"))
                        if hits(fa, ranges) and hits(fb, ranges):
                            site_skip[e["reason"]] = site_skip.get(e["reason"], 0) + 1
            reports, opcache = [], {}
            order = sorted(ded.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2], str(kv[0][3:])))
            for k, v in order:
                is_sc = k[-1] == "SC"
                kk = k[:-1] if is_sc else k
                if is_sc and kk in cls:
                    continue            # run_cuvein: an SC pair already reported as RACE is not an SC report
                mangled, pa, pb, space = kk
                dot = v["_dot"]
                if dot not in opcache:
                    opcache[dot] = {m: sd.HBGraph(*b).pc_opcode for m, b in sd.parse_dot(dot).items()}
                ops = opcache[dot][mangled]
                cubin = cubin_of.get(dot)
                fa = fb = None
                if cubin:
                    frames = cubin_frames(cubin, env, cache).get(mangled, {})
                    fa, fb = frames.get(pa), frames.get(pb)
                reports.append(dict(
                    mode=mode, kernel=next((x["name"] for x in kernels if x["mangled"] == mangled), ""),
                    mangled=mangled, dot=os.path.basename(dot), dot_equals_regenerated=dot_equal(dot), space=space,
                    a_pc=pa, b_pc=pb, a_op=ops.get(pa), b_op=ops.get(pb), a_frames=fa, b_frames=fb,
                    verdict="SC" if is_sc else "RACE", race_type=v.get("race_type"), strength=v.get("strength"),
                    hb_class=v.get("hb_class"), hb_chain=v.get("hb_chain"),
                    matrix_class=(v.get("matrix_class") if is_sc else cls[kk]),
                    conflict_class=("SC" if is_sc else v.get("conflict_class")),
                    a2=(None if is_sc else rc._a2_status(a2s[kk])), model_bug=kk in mbug,
                    kernel_jsons=seen_in.get(kk, [])))
            res["modes"][mode] = dict(
                n_kernel_jsons=len(kjs), kernels=kernels, unaligned=unaligned,
                kernel_seen=sum(1 for x in kernels if kernel_sub and kernel_sub in (x["mangled"] + x["name"])),
                n_race=sum(r["verdict"] == "RACE" for r in reports), n_sc=sum(r["verdict"] == "SC" for r in reports),
                reports=reports, site_verdicts=site_v, site_skipped=site_skip)
        res["dots_checked"] = sum(1 for x in dot_checked.values() if x is not None)
        res["dots_regenerated_equal"] = sum(1 for x in dot_checked.values() if x)
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        Path(a.out).write_text(json.dumps(res, indent=1))
        print(f"attribute {a.id}: " + ", ".join(
            f"{m}: {d['n_race']} RACE {d['n_sc']} SC over {d['n_kernel_jsons']} kernel JSONs "
            f"({len(d['unaligned'])} unaligned, oracle kernel seen in {d['kernel_seen']}, {len(d['site_verdicts'])} site verdicts)"
            for m, d in res["modes"].items())
            + f"; dots equal {res['dots_regenerated_equal']}/{res['dots_checked']}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()

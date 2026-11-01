#!/usr/bin/env python3
"""X9 step 4, pair level: every kernel JSON of one stored scalar-clock recording analyzed by the harness's own verdict path
(run_cuvein._analyze_reports, what `parallel.py analyze --both-barrier-orders` runs) with the barrier-ordered rule ON
(scalar-clock mode) and OFF (collector-only mode), captured per kernel launch with x5_common.Capture; every pc of a
reported pair attributed to file:line (inlined frames, innermost first) with `nvdisasm -c --print-line-info-inline` on the
cubin of the dot the alignment stage chose (re-extracted from the executable with cuobjdump -xelf all).

Output (one JSON per id): {"id", "store", "on": {"reason", "elapsed"}, "off": {...}, "kernels": {kid: launches},
  "pairs": [ {kid, kernel (mangled), space, a_pc, b_pc, on: {verdicts, classes, conflict, race_types}, off: {...},
              status: CONFIRMED | BARRIER-ORDERED | RECLASSIFIED | ON-ONLY | -, frames_a, frames_b, sass_a, sass_b,
              ordering_syncs_on} ]}
  a pair is (kernel, unordered pc pair, space class); a half "reports" it when some launch's verdict is RACE or SC there.
  status (collector-only = off half reported it): CONFIRMED  on reports it with the same class set;
  BARRIER-ORDERED  on does not report it and its on verdicts include hb_class barrier-ordered; RECLASSIFIED  both report,
  class sets differ; ON-ONLY  on reports, off does not (a subset violation: stops the task).
usage: x9_pairs.py --id ID --store S --manifest M --out O.json [--cap 82800] [--mem 48]   (compute node)"""
import argparse, csv, glob, json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
WT = HERE.parents[2]
os.environ.setdefault("CUVEIN_HOME", str(WT))
sys.path.insert(0, str(WT / "eval" / "baselines" / "setup"))
import x5_common as xc                 # noqa: E402
from x5_common import rc, blib         # noqa: E402

FILE_RE = re.compile(r'File\s+"([^"]+)",\s*line\s+(\d+)')
OFF_RE = re.compile(r"^\s*/\*([0-9a-fA-F]{4,})\*/(.*)$")
SECTION_RE = re.compile(r'^\s*\.section\s+\.text\.(\S+?),')
REPORTED = ("RACE", "SC")


def cubin_listing(cubin, env):
    """-> {function: {pc: (frames, sass text)}} from `nvdisasm -c --print-line-info-inline` (as T21b's rw_attribute.py)."""
    r = subprocess.run(["nvdisasm", "-c", "--print-line-info-inline", cubin], env=env, capture_output=True, text=True,
                       timeout=7200)
    funcs, fn, cur, in_group = {}, None, [], False
    for ln in r.stdout.splitlines():
        m = SECTION_RE.match(ln)
        if m:
            fn = m.group(1); funcs.setdefault(fn, {}); cur, in_group = [], False
            continue
        if re.match(r"^\s*\.section\s", ln):
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
            funcs[fn][int(m.group(1), 16)] = ([dict(x) for x in cur], m.group(2).strip().rstrip(";").strip())
        if t and not t.startswith("//"):
            in_group = False
    return funcs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--store", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cap", type=int, default=82800)
    ap.add_argument("--mem", type=int, default=48)
    a = ap.parse_args()
    row = next(r for r in csv.DictReader(open(a.manifest, newline="")) if r["id"] == a.id)
    idir = f"{a.store}/{a.id}"
    d = f"{idir}/scalar-clock"
    out = {"id": a.id, "store": a.store, "kernels": {}}
    halves = {}
    for half, envv in (("on", "1"), ("off", "0")):
        os.environ["CUVEIN_BARRIER_ORDER"] = envv
        t0 = time.time()

        def work():
            pairs, launches, kdot = {}, {}, {}

            def fn(dot, kj, rep):
                kid = f"{os.path.basename(dot)}::{rep['kernel']['mangled']}"
                launches[kid] = launches.get(kid, 0) + 1
                kdot[kid] = str(dot)
                for v in rep["verdicts"]:
                    lo, hi = sorted((v["ancient_pc"], v["current_pc"]))
                    key = (kid, v["space"].split("/")[0], lo, hi)
                    e = pairs.setdefault(key, {"verdicts": set(), "hb": set(), "conflict": set(), "rt": set(),
                                               "syncs": set(), "n": 0})
                    e["verdicts"].add(v["verdict"]); e["hb"].add(str(v["hb_class"]))
                    e["conflict"].add(v["conflict_class"]); e["rt"].add(v["race_type"]); e["n"] += 1
                    for s in v.get("ordering_syncs") or ():
                        e["syncs"].add(str(s))
            with xc.Capture(fn):
                rc._analyze_reports(d, f"{idir}/dots")
            return {"launches": launches, "kdot": kdot,
                    "pairs": [[k[0], k[1], k[2], k[3], {x: sorted(y) if isinstance(y, set) else y for x, y in e.items()}]
                              for k, e in pairs.items()]}
        pay, reason = xc.run_capped(work, a.cap, a.mem)
        out[half] = {"reason": reason, "elapsed": round(time.time() - t0, 1)}
        halves[half] = pay or {"launches": {}, "kdot": {}, "pairs": []}
        print(f"{a.id} {half}: {reason or 'ok'} {out[half]['elapsed']} s, {len(halves[half]['pairs'])} pairs", flush=True)
    os.environ.pop("CUVEIN_BARRIER_ORDER", None)
    out["kernels"] = halves["on"]["launches"] or halves["off"]["launches"]
    kdot = {**halves["off"]["kdot"], **halves["on"]["kdot"]}
    on = {tuple(p[:4]): p[4] for p in halves["on"]["pairs"]}
    off = {tuple(p[:4]): p[4] for p in halves["off"]["pairs"]}

    def cls(e):
        return sorted(v for v in e["verdicts"] if v in REPORTED) if e else []
    env = blib.base_env(blib.resolve_cuda_home())
    tmp = tempfile.mkdtemp(prefix=f"x9pairs-{a.id}-", dir=os.environ.get("TMPDIR", "/tmp"))
    listings = {}
    try:
        subprocess.run(["cuobjdump", "-xelf", "all", os.path.realpath(row["exe"])], cwd=tmp, env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cub_of = {os.path.splitext(os.path.basename(c))[0]: c for c in glob.glob(f"{tmp}/*.cubin")}

        def frames(kid, pc):
            dotb, mangled = kid.split("::", 1)
            base = os.path.splitext(dotb)[0]
            c = cub_of.get(base)
            if c is None:
                return None, None
            if c not in listings:
                listings[c] = cubin_listing(c, env)
            fr, sass = listings[c].get(mangled, {}).get(pc, (None, None))
            return fr, sass
        res = []
        for key in sorted(set(on) | set(off)):
            eon, eoff = on.get(key), off.get(key)
            con, coff = cls(eon), cls(eoff)
            if not con and not coff:
                continue
            if coff and con:
                st = "CONFIRMED" if con == coff else "RECLASSIFIED"
            elif coff:
                st = "BARRIER-ORDERED" if eon and "barrier-ordered" in eon["hb"] else "OFF-ONLY-OTHER"
            else:
                st = "ON-ONLY"
            kid, space, lo, hi = key
            fa, sa = frames(kid, lo)
            fb, sb = frames(kid, hi)
            res.append({"kid": kid, "kernel": kid.split("::", 1)[1], "space": space, "a_pc": lo, "b_pc": hi,
                        "on": eon, "off": eoff, "status": st, "frames_a": fa, "frames_b": fb, "sass_a": sa, "sass_b": sb})
        out["pairs"] = res
        out["cubins"] = sorted(os.path.basename(c) for c in cub_of.values())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    from collections import Counter
    out["status_counts"] = dict(Counter(p["status"] for p in out["pairs"]))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out))
    print(f"{a.id}: kernels={len(out['kernels'])} launches={sum(out['kernels'].values())} {out['status_counts']} -> {a.out}")


if __name__ == "__main__":
    main()

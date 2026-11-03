"""C6 part 2: (a) pc-0 memory ops in every distinct CFG; (b) access-size exposure per suite
(+ the dropped-lane deficit derivable from the kernel JSONs). Read-only. Output: c6_static_out.json + stdout."""
import os, sys, json, glob, hashlib, collections, math, time
from multiprocessing import Pool
sys.path.insert(0, "/home/fzheng4/c6-static")
B = "/mnt/beegfs/fzheng4/cuvein_traces"
OUT = "/home/fzheng4/c6-static/c6_static_out.json"
NP = int(os.environ.get("C6_NP", "16"))

def suite_of(store, pid):
    if store == "realworld-2026-10-co": return "RW-recall"
    if store == "realworld-2026-10-t21c-co": return "RW-cand"
    return pid.split("-")[0]

# ---------------- stage A: CFGs
def md5_of(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""): h.update(ch)
    return p, h.hexdigest()

def scan_dot(p):
    import sync_dominance as sd
    r = {"path": p, "kernels": 0, "pc0_mem": [], "pc0_ops": {}, "err": None, "nmem": 0}
    try:
        ks = sd.parse_dot(p)
    except Exception as e:
        r["err"] = f"{type(e).__name__}: {str(e)[:150]}"; return r
    for mangled, (blocks, edges, entry) in ks.items():
        r["kernels"] += 1
        for bname, instrs in blocks.items():
            for pc, op in instrs:
                if sd.classify(op) == "mem": r["nmem"] += 1
                if pc == 0:
                    b = op.split(".")[0]
                    r["pc0_ops"][b] = r["pc0_ops"].get(b, 0) + 1
                    if sd.classify(op) == "mem": r["pc0_mem"].append([mangled, op])
    return r

# ---------------- stage B: kernel JSONs
def prog_scan(a):
    store, pid = a
    d = f"{B}/{store}/{pid}"
    res = {"store": store, "id": pid, "suite": suite_of(store, pid), "program": pid, "nk": 0, "nk_err": 0,
           "pcs": {}, "pc0_nodes": 0, "pc0_edges": 0, "ancient0_edges": 0, "edge_rows": 0}
    try:
        res["program"] = json.load(open(d + "/meta.json")).get("program") or pid
    except Exception: pass
    if store.startswith("realworld"):
        res["program"] = pid
    kd = [x for x in sorted(os.listdir(d)) if x.startswith("collector-only")]
    for sub in kd:
        for fn in sorted(os.listdir(f"{d}/{sub}")):
            if not (fn.startswith("kernel_") and fn.endswith(".json")): continue
            try:
                j = json.load(open(f"{d}/{sub}/{fn}"))
            except Exception:
                res["nk_err"] += 1; continue
            res["nk"] += 1
            kname = (j.get("kernel") or {}).get("kernel_name", "?")
            obs = collections.Counter()
            for e in j.get("edges", []):
                res["edge_rows"] += 1
                c = e.get("current_pc")
                if c == 0: res["pc0_edges"] += 1
                if e.get("ancient_pc") == 0: res["ancient0_edges"] += 1
                obs[c] += sum((e.get("dist") or {}).values())
            for n in j.get("nodes", []):
                pc = n["pc"]
                if pc == 0: res["pc0_nodes"] += 1
                sz = n.get("access_size")
                if sz is None: continue
                fl = n.get("flags") or ""
                k = (kname, pc)
                rec = res["pcs"].get(k)
                if rec is None:
                    rec = res["pcs"][k] = {"sizes": set(), "flags": set(), "exp": 0, "obs": 0, "njson": 0, "ndef": 0}
                rec["sizes"].add(sz); rec["flags"].add(fl); rec["njson"] += 1
                al = n.get("active_lane_count"); di = n.get("distinct_address_count")
                if al is not None and di is not None and "LOCAL" not in fl:
                    A = sum(int(kk) * v for kk, v in al.items())
                    U = sum(int(kk) * v for kk, v in di.items())
                    w = (sz + 3) // 4
                    exp = (A - U) + U * w
                    o = obs.get(pc, 0)
                    rec["exp"] += exp; rec["obs"] += o
                    if o < exp: rec["ndef"] += 1
    res["pcs"] = {f"{k[0]}\x1f{k[1]}": {**v, "sizes": sorted(v["sizes"]), "flags": sorted(v["flags"])}
                  for k, v in res["pcs"].items()}
    return res

if __name__ == "__main__":
    t0 = time.time()
    sv = json.load(open("/home/fzheng4/c6-static/survey.json"))
    out = {}
    # A
    dots = []
    for r in sv:
        for dd in r["dots"]:
            if dd.startswith("dots/") or dd.endswith(".dot"):
                dots.append((r["store"], r["id"], f"{B}/{r['store']}/{r['id']}/{dd}"))
    print("dot files", len(dots), flush=True)
    with Pool(NP) as p:
        mm = dict(p.map(md5_of, [d[2] for d in dots], chunksize=16))
    print("md5 done", round(time.time() - t0), "s", flush=True)
    by_md5 = {}
    for st, pid, path in dots: by_md5.setdefault(mm[path], []).append((st, pid, path))
    reps = [v[0][2] for v in by_md5.values()]
    print("distinct dot contents", len(reps), flush=True)
    with Pool(NP) as p:
        scans = p.map(scan_dot, reps, chunksize=4)
    sc = {s["path"]: s for s in scans}
    A = {"dot_files": len(dots), "distinct_md5": len(reps), "parse_err": [], "kernels": 0, "pc0_mem": [], "pc0_ops": {}, "nmem": 0}
    for m, v in by_md5.items():
        s = sc[v[0][2]]
        if s["err"]: A["parse_err"].append([m, v[0][2], s["err"]]); continue
        A["kernels"] += s["kernels"]; A["nmem"] += s["nmem"]
        for k2, c in s["pc0_ops"].items(): A["pc0_ops"][k2] = A["pc0_ops"].get(k2, 0) + c
        for mg, op in s["pc0_mem"]: A["pc0_mem"].append([m, v[0][2], mg, op, len(v)])
    A["programs_without_dot"] = [[r["store"], r["id"]] for r in sv if not r["dots"]]
    out["A"] = A
    print("A:", {k: (v if not isinstance(v, list) else len(v)) for k, v in A.items()}, "pc0_ops", A["pc0_ops"], round(time.time() - t0), "s", flush=True)
    # B
    items = [(r["store"], r["id"]) for r in sv if r["nk"] > 0]
    with Pool(NP) as p:
        B_res = p.map(prog_scan, items, chunksize=4)
    out["B"] = B_res
    json.dump(out, open(OUT, "w"))
    print("B programs", len(B_res), "kernel jsons", sum(r["nk"] for r in B_res), "errs", sum(r["nk_err"] for r in B_res), round(time.time() - t0), "s", flush=True)

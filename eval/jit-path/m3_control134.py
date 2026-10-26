"""Control: the 13.4-built AOT SASS differs from the driver's JIT of the 13.0 PTX; does the PTX run's dump follow the JIT SASS?
Analyses out130c/<prog>_ptx/dump_<mode> against (a) the JIT cubin, (b) the CUDA 13.4 AOT cubins from out/<prog>_sass."""
import glob, json, os, sys
sys.argv = ["x"]
sys.path.insert(0, "/home/fzheng4/m3work")
import m3_jit_path as m
import blib
env = blib.base_env(blib.resolve_cuda_home())
O130, O134 = "/home/fzheng4/m3work/out130c", "/home/fzheng4/m3work/out"
res = {}
for prog, aot in (("litmus", "litmus_sass/race_interwarp_none-atom_waw_eval_cubins"),
                  ("reduction", "reduction_sass/reduction_norace_eval_cubins")):
    jit = glob.glob(f"{O130}/{prog}_ptx/jit_cubins/*.cubin")[0]
    a134 = glob.glob(f"{O134}/{aot}/*.cubin")[0]
    lj, l134 = m.sass_listing(jit, env), m.sass_listing(a134, env)
    cmp = m.compare_listings(l134, lj)
    res[prog] = {"aot134_vs_jit130": {fn: {k: v for k, v in c.items() if k != "first_diff_index"} for fn, c in cmp.items()},
                 "analysis": {}}
    for mode in m.MODES:
        dep = f"{O130}/{prog}_ptx/dump_{mode}"
        offs134 = {o for fl in l134.values() for o, _ in fl}
        offsj = {o for fl in lj.values() for o, _ in fl}
        pcs = sorted(set().union(*m.pcs_in_dump(dep).values()))
        res[prog]["analysis"][mode] = {
            "dump_pcs": pcs,
            "pcs_not_offsets_of_jit_cubin": [p for p in pcs if p not in offsj],
            "pcs_not_offsets_of_aot134_cubin": [p for p in pcs if p not in offs134],
            "against_jit_cubin": m.analyse(dep, f"{O130}/{prog}_ptx/jit_cubins"),
            "against_aot134_cubin": m.analyse(dep, f"{O134}/{aot}")}
json.dump(res, open("/home/fzheng4/m3work/out130c/m3_control134.json", "w"), indent=1, default=str)
for prog, r in res.items():
    print(prog, {fn: (c.get("n_sass"), c.get("n_jit"), c.get("identical")) for fn, c in list(r["aot134_vs_jit130"].items())[:3]})
    for mode, a in r["analysis"].items():
        print(prog, mode, "notJIT", len(a["pcs_not_offsets_of_jit_cubin"]), "notAOT134", len(a["pcs_not_offsets_of_aot134_cubin"]),
              "| jit:", a["against_jit_cubin"].get("verdict"), a["against_jit_cubin"].get("reports"), a["against_jit_cubin"].get("pcs"),
              "| aot134:", a["against_aot134_cubin"].get("verdict"), a["against_aot134_cubin"].get("reports"), a["against_aot134_cubin"].get("pcs"), (a["against_aot134_cubin"].get("error") or "")[:80])

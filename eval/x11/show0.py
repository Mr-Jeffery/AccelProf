import json
d=json.load(open("/mnt/beegfs/fzheng4/x11_work/step0b/step0.json"))
print(d["cuobjdump_version"]); print(d["hecbench"])
for r in d["recs"]:
    print(r["id"],"|",r.get("rule"),r.get("same"),"|",r.get("why"),"|",r.get("first_diff"),"| art",r.get("art_elf"),r.get("art_ptx"),"| our",r.get("our_elf"),"| cmp",r.get("compare_arch"),"|",r.get("n_kernels_art"),r.get("n_kernels_ours"),r.get("n_kernels_diff"),"|",repr(r.get("art_args")),"~",repr(r.get("our_args")), "|", r.get("note",""))
print(d["recs"][0].get("our_build")); print(d["cuh_build"])

import os, sys, csv
T="/mnt/beegfs/fzheng4/cuvein_traces"
ids=["PI-push_node_neighbors_block-power_law_200n_1000e","PI-pull_node_neighbors_boundsBug-counterDAG_5n_5e","P1-BFS_CUDA_E_Data_IntType_ReadModifyWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NonDeterm_NoUninitializedBug_NoFieldBug_NoOverflowBug-default-1296n"]
for i in ids:
    print("==", i[:60])
    for st in sorted(os.listdir(T)):
        d=f"{T}/{st}/{i}"
        if os.path.isdir(d): print("  ", st, sorted(os.listdir(d)))
for f in ["final-b/merged/baselines-cuvein.csv"]:
    for r in csv.DictReader(open(f"/home/fzheng4/wt-x13/eval/results/{f}")):
        if r["id"] in ids and r["mode"]=="scalar-clock": print(r["id"][:40], r["rep"], r["verdict"], r["notes"][:200])

import csv, glob, json, collections, os, sys
W = "/home/fzheng4/wt-co"
B = "/mnt/beegfs/fzheng4/cuvein_traces"
res = {}
for t in ("a", "b"):
    rows = [r for f in glob.glob(f"{W}/eval/results/collector-only-parity-{t}/baselines-cuvein-shard*.csv") for r in csv.DictReader(open(f))]
    res[t] = collections.defaultdict(list)
    for r in rows: res[t][r["id"]].append(r)
ids = [l.strip() for l in open(f"{W}/eval/baselines/setup/t5b_parity_ids.txt") if l.strip()]
print("ids", len(ids), "A", len(res["a"]), "B", len(res["b"]))
same_node = diff_verdict = 0; repdirs = collections.Counter(); ndiffrep = 0
for i in ids:
    na = json.load(open(f"{B}/final-2026-11-co-parity-a/{i}/meta.json")).get("node") if os.path.exists(f"{B}/final-2026-11-co-parity-a/{i}/meta.json") else None
    nb = json.load(open(f"{B}/final-2026-11-co-parity-b/{i}/meta.json")).get("node") if os.path.exists(f"{B}/final-2026-11-co-parity-b/{i}/meta.json") else None
    if na == nb: same_node += 1
    va = [r["verdict"] for r in res["a"][i]]; vb = [r["verdict"] for r in res["b"][i]]
    if sorted(va) != sorted(vb): diff_verdict += 1; print("DIFF", i[:50], va, vb)
    for t in ("a", "b"):
        n = len(glob.glob(f"{B}/final-2026-11-co-parity-{t}/{i}/collector-only-rep*"))
        repdirs[(t, n)] += 1
    # rep kernel json byte-equality of rep1 vs rep2/3 within A
    d = f"{B}/final-2026-11-co-parity-a/{i}"
print("same node A/B:", same_node, "ids whose per-rep verdict multiset differs A vs B:", diff_verdict)
print("rep dirs per id:", dict(repdirs))
print(collections.Counter((r["verdict"]) for t in "ab" for rs in res[t].values() for r in rs))

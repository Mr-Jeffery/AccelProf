"""T21c step 3 prep: group T21b's other_reports.csv by (target, sorted top-frame line pair).
Writes ~/t21c_triage/{groups.csv,row_groups.csv,<target>.md}."""
import csv, collections, json, os, re
WT = os.path.expanduser("~/wt-t21b"); OUT = os.path.expanduser("~/t21c_triage")
os.makedirs(OUT, exist_ok=True)
rows = list(csv.DictReader(open(f"{WT}/eval/results/realworld/other_reports.csv")))
def top(s):
    m = re.match(r"\s*([^\s<\[]+:\d+)", s or "")
    return m.group(1) if m else (s or "?").strip()[:40]
T = {json.loads(l)["id"]: json.loads(l) for l in open(f"{WT}/eval/realworld/targets.jsonl")}
groups = collections.OrderedDict()
for i, r in enumerate(rows):
    key = (r["target"], tuple(sorted((top(r["a"]), top(r["b"])))))
    groups.setdefault(key, []).append(i)
# site-verdict hints from the attribution files
hints = {}
for t in {r["target"] for r in rows}:
    for v in ("buggy", "fixed"):
        f = f"{WT}/eval/results/realworld/attrib/{t}-{v}.json"
        if not os.path.exists(f): continue
        d = json.load(open(f))
        for m, md in d.get("modes", {}).items():
            for sv in md.get("site_verdicts", []) or []:
                k = (t, v, m, frozenset((sv.get("current_pc"), sv.get("ancient_pc"))))
                hints.setdefault(k, []).append({x: sv.get(x) for x in ("observed_distance", "strength", "ordering_syncs", "race_type", "access_size", "contested_weight")})
gid_of = {}
with open(f"{OUT}/groups.csv", "w", newline="") as fg:
    w = csv.writer(fg); w.writerow(["group", "target", "site_1", "site_2", "rows", "variants_modes", "spaces_types", "classes", "ops", "n_pc_pairs", "kernels"])
    per_t = collections.defaultdict(list); n_t = collections.Counter()
    for (t, pair), idx in groups.items():
        n_t[t] += 1; g = f"{t}#{n_t[t]:02d}"
        for i in idx: gid_of[i] = g
        R = [rows[i] for i in idx]
        vm = collections.Counter(f"{r['variant']}/{r['mode'][:2]}" for r in R)
        st = collections.Counter(f"{r['space']}:{r['race_type']}" for r in R)
        cl = collections.Counter(f"{r['cls']}/{r['matrix_class']}" for r in R)
        ops = collections.Counter(f"{r['a_op']}~{r['b_op']}" for r in R)
        pcs = collections.Counter((r["a_pc"], r["b_pc"]) for r in R)
        ks = collections.Counter(re.sub(r"\s+", " ", r["kernel"])[:160] for r in R)
        w.writerow([g, t, pair[0], pair[1], len(R), dict(vm), dict(st), dict(cl), dict(ops.most_common(6)), len(pcs), " || ".join(k for k, _ in ks.most_common(3))])
        per_t[t].append((g, pair, R, pcs, ks, vm, st, cl, ops))
with open(f"{OUT}/row_groups.csv", "w", newline="") as fr:
    w = csv.writer(fr); w.writerow(["row", "group"]); [w.writerow([i, gid_of[i]]) for i in range(len(rows))]
for t, L in per_t.items():
    tg = T.get(t, {})
    with open(f"{OUT}/{t}.md", "w") as f:
        f.write(f"# {t}: {sum(len(x[2]) for x in L)} other reports in {len(L)} line-pair groups\n\n")
        f.write(f"repo {tg.get('repo')} | buggy {tg.get('buggy_commit')} | fixed {tg.get('fix_commit')} | oracle kernel/location: {tg.get('kernel')} / {tg.get('location_buggy')}\n")
        f.write(f"oracle race (not these): {str(tg.get('race_description'))[:400]}\n\n")
        for g, pair, R, pcs, ks, vm, st, cl, ops in L:
            f.write(f"## {g}: {pair[0]}  vs  {pair[1]}  ({len(R)} rows)\n")
            f.write(f"- variant/mode: {dict(vm)}; space:type {dict(st)}; class {dict(cl)}\n- ops: {dict(ops)}\n")
            for k, n in ks.most_common(4): f.write(f"- kernel ({n}): `{k}`\n")
            seen = set()
            for r in R:
                key = (r["a_pc"], r["b_pc"], r["a"], r["b"])
                if key in seen or len(seen) >= 8: continue
                seen.add(key)
                h = hints.get((t, r["variant"], r["mode"], frozenset((int(r["a_pc"], 16), int(r["b_pc"], 16)))), [])
                hs = "; ".join(f"dist={x['observed_distance']} strength={x['strength']} syncs={x['ordering_syncs']}" for x in h[:2])
                f.write(f"  - pcs {r['a_pc']}/{r['b_pc']} {r['a_op']}/{r['b_op']} {r['space']} {r['race_type']} {r['cls']}/{r['verdict']}/{r['matrix_class']} [{r['variant']} {r['mode']}]\n")
                f.write(f"    - A: {r['a']}\n    - B: {r['b']}\n")
                if hs: f.write(f"    - site verdict: {hs}\n")
            f.write(f"  - ({len(pcs)} distinct pc pairs in this group)\n\n")
print("groups", len(groups), "rows", len(rows), "targets", len(per_t))
print(collections.Counter(g.split('#')[0] for g in set(gid_of.values())))

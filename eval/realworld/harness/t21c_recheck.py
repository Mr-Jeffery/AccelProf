#!/usr/bin/env python3
"""T21c step 1 (login node, git only): fetch each candidate's default branch and diff its racy files
against the pinned commit. Writes eval/realworld/candidates/recheck.json; the .md is written by hand."""
import datetime, json, os, subprocess

WT = os.path.expanduser("~/wt-t21c")
R = os.path.expanduser("~/incoming/realworld")
SPECIAL = {"ggml-org/llama.cpp": f"{R}/llama.cpp.git", "rusty1s/pytorch_cluster": f"{R}/pytorch_cluster.git"}


def git(d, *a, check=True):
    p = subprocess.run(["git", "-C", d, *a], capture_output=True, text=True, timeout=1800)
    if check and p.returncode:
        raise RuntimeError(f"git {' '.join(a)}: {p.stderr.strip()[:300]}")
    return p.stdout.strip()


T = [json.loads(l) for l in open(f"{WT}/eval/realworld/targets.jsonl")]
out, fetched = [], {}
for t in [t for t in T if t.get("tier") == "candidate"]:
    d = SPECIAL.get(t["repo"], f"{R}/cand/{t['repo'].split('/')[1]}.git")
    r = dict(id=t["id"], repo=t["repo"], pinned=t["buggy_commit"], files=t["files"], clone=d)
    try:
        if d not in fetched:
            head = git(d, "ls-remote", "--symref", "origin", "HEAD").splitlines()[0].split()[1]
            git(d, "fetch", "-q", "--no-tags", "origin", f"+{head}:refs/remotes/upstream/default")
            fetched[d] = head
        tip = git(d, "rev-parse", "refs/remotes/upstream/default")
        r.update(default_branch=fetched[d].replace("refs/heads/", ""), tip=tip,
                 tip_date=git(d, "log", "-1", "--format=%cI", tip),
                 pinned_is_ancestor=subprocess.run(["git", "-C", d, "merge-base", "--is-ancestor", t["buggy_commit"], tip]).returncode == 0)
        files = []
        for f in t["files"]:
            f = f.split(" (")[0]   # some records annotate a path, e.g. "x.cu (same pattern, L150-L189)"
            exists = subprocess.run(["git", "-C", d, "cat-file", "-e", f"{tip}:{f}"], capture_output=True).returncode == 0
            log = git(d, "log", "--format=%h %cs %s", f"{t['buggy_commit']}..{tip}", "--", f, check=False)
            stat = git(d, "diff", "--shortstat", t["buggy_commit"], tip, "--", f, check=False)
            files.append(dict(file=f, exists_at_tip=exists, diff=stat or "identical",
                              commits=log.splitlines()[:20], n_commits=len(log.splitlines())))
        r["files_check"] = files
        r["changed"] = any(x["diff"] != "identical" or not x["exists_at_tip"] for x in files)
    except Exception as e:
        r["error"] = str(e)
    out.append(r)
    print(r["id"], r.get("default_branch"), (r.get("tip") or "")[:10], "changed" if r.get("changed") else ("ERROR " + r["error"] if "error" in r else "identical"), flush=True)
    for x in r.get("files_check", []):
        if x["diff"] != "identical" or not x["exists_at_tip"]:
            print("   ", x["file"], x["diff"], "exists" if x["exists_at_tip"] else "GONE", x["n_commits"], "commits")
            for c in x["commits"][:8]:
                print("      ", c)

os.makedirs(f"{WT}/eval/realworld/candidates", exist_ok=True)
json.dump(dict(checked_at=datetime.datetime.now().astimezone().isoformat(timespec="seconds"), candidates=out),
          open(f"{WT}/eval/realworld/candidates/recheck.json", "w"), indent=1)

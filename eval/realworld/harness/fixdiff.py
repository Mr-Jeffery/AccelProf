#!/usr/bin/env python3
"""R2 check (T21a step 2): the harness copies of the kernel sources are byte-for-byte what the two
commits contain, and `diff -r buggy fixed` over them equals the fix commit's diff of those files.

    fixdiff.py <target-id> [--tree eval/realworld/targets/<id>/r2] [--write]

Layout of a tree:  <tree>/buggy/<repo path>   <tree>/fixed/<repo path>   (and <tree>/common/ for the host main,
type/macro stubs and include shims, which are identical for both variants and never compared here).
Runs on the LOGIN node (reads the partial clones in ~/incoming/realworld; blobs that are not local are fetched).
--write stores the verdict as <tree>/fixdiff.check (the file the report cites).  Exit 0 iff PASS.
"""
import argparse, hashlib, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RW = os.path.dirname(HERE)
INCOMING = os.environ.get("REALWORLD_INCOMING", os.path.expanduser("~/incoming/realworld"))


def sh(*a, cwd=None, ok=(0,)):
    r = subprocess.run(a, cwd=cwd, capture_output=True)
    if r.returncode not in ok:
        raise RuntimeError("%s: rc=%d %s" % (" ".join(a), r.returncode, r.stderr.decode()[:300]))
    return r.stdout


def clone_name(slug):
    for line in open(os.path.join(HERE, "repos.tsv")):
        if line.startswith("#") or not line.strip():
            continue
        n, s, _ = line.rstrip("\n").split("\t")
        if s.lower() == slug.lower():
            return n
    raise SystemExit("no clone for %s in repos.tsv" % slug)


def files_under(d):
    out = []
    for root, _, fs in os.walk(d):
        for f in fs:
            out.append(os.path.relpath(os.path.join(root, f), d).replace(os.sep, "/"))
    return sorted(out)


def norm_diff(txt):
    """drop the header lines that name paths / blobs; keep the hunks verbatim"""
    keep = []
    for l in txt.splitlines():
        if l.startswith(("diff --git", "index ", "--- ", "+++ ", "new file mode", "deleted file mode", "similarity")):
            continue
        keep.append(l)
    return "\n".join(keep)


def blob_sha(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--tree")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    T = {}
    for l in open(os.path.join(RW, "targets.jsonl")):
        t = json.loads(l)
        T[t["id"]] = t
    t = T[a.id]
    tree = a.tree or os.path.join(RW, "targets", a.id, "r2")
    repo = os.path.join(INCOMING, clone_name(t["repo"]) + ".git")
    bc, fc = t["buggy_commit"], t["fix_commit"]
    lines, ok = ["target %s  repo %s  buggy %s  fix %s" % (a.id, t["repo"], bc, fc)], True
    sets = {}
    for side, commit in (("buggy", bc), ("fixed", fc)):
        d = os.path.join(tree, side)
        fl = files_under(d)
        sets[side] = fl
        if not fl:
            lines.append("FAIL %s: no files under %s" % (side, d))
            ok = False
        for rel in fl:
            want = sh("git", "-C", repo, "rev-parse", "%s:%s" % (commit, rel), ok=(0, 128)).decode().strip()
            if not want or len(want) != 40:
                lines.append("FAIL %s/%s: not in %s" % (side, rel, commit[:10]))
                ok = False
                continue
            have = open(os.path.join(d, rel), "rb").read()
            same = blob_sha(have) == want
            lines.append("%s %s/%s blob %s %s %s:%s %s" % ("ok  " if same else "FAIL", side, rel, blob_sha(have)[:12],
                                                          "==" if same else "!=", commit[:10], rel, want[:12]))
            ok &= same
    both = sorted(set(sets["buggy"]) & set(sets["fixed"]))
    for rel in sorted(set(sets["buggy"]) ^ set(sets["fixed"])):
        lines.append("FAIL %s present in only one variant" % rel)
        ok = False
    mine, theirs = "", ""
    for rel in both:
        r = subprocess.run(["git", "diff", "--no-index", "--no-color", "buggy/" + rel, "fixed/" + rel],
                           cwd=tree, capture_output=True)
        mine += norm_diff(r.stdout.decode(errors="replace")) + "\n"
        theirs += norm_diff(sh("git", "-C", repo, "diff", "--no-color", bc, fc, "--", rel).decode(errors="replace")) + "\n"
    same = mine == theirs
    lines.append("%s diff -r buggy fixed over %d copied file(s) == git diff %s %s of those files (%d lines, sha1 %s)" % (
        "ok  " if same else "FAIL", len(both), bc[:10], fc[:10], len(mine.splitlines()),
        hashlib.sha1(mine.encode()).hexdigest()[:12]))
    ok &= same
    lines.append("RESULT " + ("PASS" if ok else "FAIL"))
    txt = "\n".join(lines) + "\n"
    sys.stdout.write(txt)
    if a.write:
        open(os.path.join(tree, "fixdiff.check"), "w").write(txt)
    sys.exit(0 if ok else 1)


main()

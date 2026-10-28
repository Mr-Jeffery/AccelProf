#!/bin/bash
# R2 (T21a step 2), LOGIN node: copy kernel source files byte-for-byte from the two commits.
#   r2_extract.sh <id> <repo-path> [<repo-path> ...]
# -> eval/realworld/targets/<id>/r2/{buggy,fixed}/<repo-path>   (git cat-file blob <commit>:<path>; licence header untouched)
# Afterwards: fixdiff.py <id> --write  (blob sha1 == the commit's blob; diff -r buggy fixed == the fix commit's diff of those files).
# The host main, stubs and shims go in eval/realworld/targets/<id>/r2/common/ and are identical for both variants.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); RWD=$(dirname "$HERE")
id=$1; shift
read -r B F REPO < <(python3 - "$RWD/targets.jsonl" "$id" "$HERE/repos.tsv" <<'PYEOF'
import json, sys
names = {l.rstrip("\n").split("\t")[1].lower(): l.split("\t")[0] for l in open(sys.argv[3]) if l.strip() and not l.startswith("#")}
for l in open(sys.argv[1]):
    t = json.loads(l)
    if t["id"] == sys.argv[2]:
        print(t["buggy_commit"], t["fix_commit"], names[t["repo"].lower()])
PYEOF
)
repo=${REALWORLD_INCOMING:-$HOME/incoming/realworld}/$REPO.git
for p in "$@"; do
  pairs="buggy:$B fixed:$F"; case "$F" in None|"") pairs="buggy:$B";; esac   # T21c candidates: pinned commit only
  for pair in $pairs; do
    v=${pair%%:*}; c=${pair#*:}
    mkdir -p "$RWD/targets/$id/r2/$v/$(dirname "$p")"
    git -C "$repo" cat-file blob "$c:$p" > "$RWD/targets/$id/r2/$v/$p"
  done
  echo "r2_extract: $id $p ($(wc -c < "$RWD/targets/$id/r2/buggy/$p") / $(cat "$RWD/targets/$id/r2/fixed/$p" 2>/dev/null | wc -c) bytes)"
done

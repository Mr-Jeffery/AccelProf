#!/bin/bash
# Export a revision (or some paths of it) from a partial bare clone into ONE tarball. LOGIN node, git only.
#   export_rev.sh <repo-name> <sha> <out.tar.gz> [path ...]
# Blobs missing from the partial clone are fetched in batches of 400 first (one round trip per batch instead of
# one per file: ginkgo took 3m26s by lazy fetch, 1,086 kokkos blobs 3 s this way), then `git archive`.  The result is
# a tarball because creating thousands of small files on the NFS home costs ~60 ms each (1,582 files: 90 s);
# the compute-node `stage` phase unpacks it on BeeGFS.  For --filter=tree:0 clones (pytorch, cmssw, opencv) always
# pass explicit file paths: a whole-tree walk would fetch one tree at a time.
set -euo pipefail
name=$1; sha=$2; out=$3; shift 3
repo=${REALWORLD_INCOMING:-$HOME/incoming/realworld}/$name.git
[ -d "$repo" ] || { echo "export_rev: no clone $repo (run clone_repos.sh $name)" >&2; exit 2; }
full=$(git -C "$repo" rev-parse --verify "$sha^{commit}")
mkdir -p "$(dirname "$out")"
git -C "$repo" ls-tree -r "$full" -- "$@" | awk '$2=="blob"{print $3}' | sort -u |
  xargs -r -n 400 git -C "$repo" -c fetch.negotiationAlgorithm=noop fetch --no-tags --no-write-fetch-head -q origin
git -C "$repo" archive --format=tar.gz -o "$out" "$full" -- "$@"
echo "export_rev: $name $full -> $out ($(du -sh "$out" | cut -f1), $(tar -tzf "$out" | grep -vc '/$') files)"

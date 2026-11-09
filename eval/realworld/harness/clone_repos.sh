#!/bin/bash
# Partial bare clones on the LOGIN node (git only; compute nodes have no route to GitHub).
# usage: clone_repos.sh [name ...]   (default: every row of repos.tsv)
# Target: ~/incoming/realworld/<name>.git   (5 GB budget for the whole directory; home is guarded at 35 GB)
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
DEST=${REALWORLD_INCOMING:-$HOME/incoming/realworld}
mkdir -p "$DEST"
want=" $* "
grep -v '^#' "$HERE/repos.tsv" | while IFS=$'\t' read -r name slug filt; do
  [ -z "$name" ] && continue
  [ "$#" -gt 0 ] && case "$want" in *" $name "*) ;; *) continue;; esac
  d="$DEST/$name.git"
  if [ -d "$d" ]; then echo "[$name] exists, fetching"; nice git -C "$d" fetch --no-tags origin '+refs/heads/*:refs/heads/*' 2>&1 | tail -2; continue; fi
  echo "[$name] clone $slug --filter=$filt $(date +%T)"
  nice git clone --bare --no-tags --filter="$filt" "https://github.com/$slug.git" "$d.partial" 2>&1 | tail -3 \
    && mv "$d.partial" "$d" && echo "[$name] done $(du -sh "$d" | cut -f1) $(date +%T)"
done

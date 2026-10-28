# C2 (eval/collector-only-realworld): `source` at the top of the collector-only real-world jobs. SET=recall (T21b set, manifest_t21b.csv)
# or SET=cand (T21c set, manifest_t21c.csv). Same node probes as recall_header.sh.
export W=/home/fzheng4/wt-co-rw
export A=/home/fzheng4/AccelProf
SET=${SET:-recall}
case "$SET" in
  recall) export S0=/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10-co;      export RESNAME=realworld_co;      export MANIFEST=$W/eval/realworld/manifest_t21b.csv ;;
  cand)   export S0=/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10-t21c-co; export RESNAME=realworld_co_t21c; export MANIFEST=$W/eval/realworld/manifest_t21c.csv ;;
  *) echo "co_header: bad SET $SET" >&2; exit 2 ;;
esac
for _d in $A /mnt/beegfs/fzheng4 $W $A/lib/libcompute_sanitizer.so; do
  timeout 10 ls "$_d" >/dev/null 2>&1 || { echo "co_header: host=$(hostname) missing or unreadable $_d" >&2; exit 97; }
done
unset _d
for _k in $(env | grep -E '^(YOSEMITE_|CUVEIN_|BASELINE_)' | cut -d= -f1); do
  [ "$_k" = CUVEIN_HOME ] || unset "$_k"
done
unset _k

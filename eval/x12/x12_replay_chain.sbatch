#!/usr/bin/env bash
#SBATCH --partition=normal
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
# X12: chain-closure analysis of the replay outputs of t26_parity/t20.sh (kernel JSONs under $T26OUT/replay/<id>/<capture>-<lib>/), per id and library,
# then the pair-set comparison installed -n 1 replay vs new N=1 / N=16 / N=16 threaded on the same captured stream.
# Pseudo-stores: <id>/{meta.json (the N=16 recording's), dots -> its dots, collector-only -> the replay's kernel JSONs}.
#   T26OUT=/mnt/beegfs/fzheng4/t26/t20-collector-only-<job> IDFILE=<ids> SRC=final-2026-11-co-sh-p1 W=<harness> sbatch x12_replay_chain.sbatch
set -u
T26OUT=${T26OUT:?}; IDFILE=${IDFILE:?}; SRC=${SRC:?}; W=${W:?}
B=/mnt/beegfs/fzheng4/cuvein_traces; R=/mnt/beegfs/fzheng4/x12_work/replay-stores/$(basename $T26OUT)${SFX:-}; C=/home/fzheng4/wt-x11-cochain
PY=/home/fzheng4/AccelProf/.env/bin/python; OUTD=$W/eval/results/co-sharded-replay/$(basename $T26OUT)${SFX:-}; mkdir -p $OUTD
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$C CUVEIN_HOME=$C
echo "host=$(hostname) $(date -Is)"
for cap in Ic Bc; do for lib in inst n1 n16 n16t; do
  S=$R/$cap-$lib; rm -rf $S; mkdir -p $S
  while read -r id; do
    d=$T26OUT/replay/$id/$cap-$lib; [ -d $d ] || { echo "missing $d"; continue; }
    mkdir -p $S/$id; cp $B/$SRC/$id/meta.json $S/$id/; ln -sfn $B/$SRC/$id/dots $S/$id/dots; ln -sfn $d $S/$id/collector-only
  done < $IDFILE
  BASELINE_TRACE_DIR=$S BASELINE_MODES=collector-only $PY $C/eval/baselines/parallel.py analyze --manifest $C/eval/baselines/manifest.csv --id-file $IDFILE \
     --tag rp-$cap-$lib --results-dir $OUTD/$cap-$lib --confirm --confirm-dir $OUTD/$cap-$lib/confirm --chain-closure --analysis-timeout 14400 --analysis-workers 16 > $OUTD/analyze-$cap-$lib.log 2>&1
  echo "analyzed $cap-$lib rc=$?"
done; done
for cap in Ic Bc; do for lib in n1 n16 n16t; do
  $PY -I $W/eval/x12/x12_pairs.py --a "$cap-installed-n1-replay" $OUTD/$cap-inst/*.csv --b "$cap-new-$lib-replay" $OUTD/$cap-$lib/*.csv | tee -a $OUTD/pairs.txt
done; done
echo "== done $(date -Is)"

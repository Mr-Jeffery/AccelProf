#!/bin/bash
# C2: long re-analysis (CPU only, no collection) of a collector-only recording whose analysis hit the 3,600 s limit (rows ERROR analysis-timeout),
# as T21c did for colmap-new-1. Env: SET, ID. Writes the tagged CSV rean-<id>- next to the normal one, then attributes.
source /home/fzheng4/wt-co-rw/eval/realworld/harness/co_header.sh || exit $?
export ACCEL_PROF_HOME=$A RW_MODES=collector-only
for CH in /usr/local/cuda-13.4 /usr/local/cuda-13.3 /usr/local/cuda; do [ -x $CH/bin/nvdisasm ] && { export CUDA_HOME=$CH; break; }; done
source $W/eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
export BASELINE_TRACE_DIR=$S0 BASELINE_MODES=collector-only
cd $W || exit 1
RES=$W/eval/results/$RESNAME; CONF=$W/eval/baselines/confirm_$RESNAME; LOG=$W/eval/x_logs; mkdir -p $RES/attrib
echo "C2 rean host=$(hostname) job=$SLURM_JOB_ID HEAD=$(git rev-parse --short HEAD) store=$S0 cuda=$CUDA_HOME id=$ID"
echo "=== $(date -Is) analyze $ID"
$PY $W/eval/baselines/parallel.py analyze --manifest $MANIFEST --id $ID --confirm --analysis-timeout 82800 \
   --tag "rean-$ID-" --results-dir $RES --confirm-dir $CONF > $LOG/co-analyze-rean-$ID.out 2>&1
echo "  analyze rc=$? ($(tail -1 $LOG/co-analyze-rean-$ID.out | cut -c1-200))"
echo "=== $(date -Is) attribute $ID"
$PY $W/eval/realworld/harness/rw_attribute.py --id $ID --store $S0 --manifest $MANIFEST --out $RES/attrib/$ID.json > $LOG/co-attrib-rean-$ID.out 2>&1
echo "  attribute rc=$? ($(tail -1 $LOG/co-attrib-rean-$ID.out | cut -c1-400))"
echo "=== $(date -Is) done"

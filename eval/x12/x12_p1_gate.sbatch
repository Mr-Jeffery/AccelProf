#!/usr/bin/env bash
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
# X12 Indigo3 parity gate (see x12_p1_gate.py). W=<harness worktree> sbatch -o ... x12_p1_gate.sbatch
B=/mnt/beegfs/fzheng4/cuvein_traces
W=${W:?}; STORE=${STORE:-final-2026-11-co-sh-p1}; RES=${RES:-co-sharded-p1}
echo "host=$(hostname) $(date -Is)"
/home/fzheng4/AccelProf/.env/bin/python -I $W/eval/x12/x12_p1_gate.py $B/$STORE $B/final-2026-11-co $W/eval/results/$RES/parity \
    --parity-a $B/final-2026-11-co-parity-a --parity-b $B/final-2026-11-co-parity-b
echo "GATE-P1 rc=$? $(date -Is)"

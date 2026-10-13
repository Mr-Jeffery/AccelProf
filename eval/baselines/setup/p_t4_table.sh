#!/usr/bin/env bash
#SBATCH --job-name=t4-table
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=02:00:00
#SBATCH --output=/home/fzheng4/wt-T4/build_logs/t4-table-%j.log
# T4 step 4: the comparison table with the hb_stats columns, which need the kept no-dump dumps
# on BeeGFS (compute nodes only). Output: eval/baselines/setup/t4_sweep_table.md.
#   W=/home/fzheng4/wt-T4 sbatch --dependency=afterany:<reruns> eval/baselines/setup/p_t4_table.sh
W=${W:-/home/fzheng4/wt-T4}
cd $W || exit 1
S=/mnt/beegfs/$USER/cuvein_traces
.env/bin/python eval/baselines/setup/t4_sweep_table.py \
    --tags t4-nodump,t4-nodump-p7p9,t4-nodump-rerun,t4-nodump-rerun2 \
    --store $S/t4-nodump $S/t4-nodump-p7p9 $S/t4-nodump-rerun $S/t4-nodump-rerun2 \
    > eval/baselines/setup/t4_sweep_table.md 2> eval/baselines/setup/t4_sweep_table.err
echo "rc=$? lines=$(wc -l < eval/baselines/setup/t4_sweep_table.md)"
tail -6 eval/baselines/setup/t4_sweep_table.md
echo "== done $(date -Is)"

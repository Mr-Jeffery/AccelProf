#!/usr/bin/env bash
#SBATCH --job-name=hirace-t1
#SBATCH --partition=rtx4060ti8g
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=1-00:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/hirace-table1-%j.log
# The HiRace SC24 artifact's own `make table1`, verbatim (scripts/hirace_experiments.py:
# 590 codes x 6 graphs, 256x1024, uninstrumented + compute-sanitizer + iGUARD + HiRace,
# then scripts/gen_table1.py). Only accommodation: the artifact hard-codes the iGUARD
# detector at iGUARD-SOSP21/nvbit_release/tools/detector/detector.so (an empty submodule
# in our clone) -> symlink to our NVBit-1.8 build. No artifact file is edited.
# Resumable: the driver skips codes already in the sqlite DB (`make -B table1`).
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
# Runs on the rtx4060ti8g partition: its nodes pair the 4060 Ti (sm_89) with an older GPU
# (2080 SUPER / 2060), and NVBit fails with both visible -> expose only the sm_89 one.
# (A first attempt on c67, rtx4060ti16g, was cancelled: under this driver every iGUARD
# process idled after finishing until the driver's 300 s timeout -- cause not established;
# the same unmodified driver completes all four stages here, see smoke_hirace/t1_smoke-*.log.)
source eval/baselines/setup/pin8g.sh
echo "visible GPU: $CUDA_VISIBLE_DEVICES"
A=eval/baselines/setup/tools/HiRace
D=$A/iGUARD-SOSP21/nvbit_release/tools/detector
mkdir -p $D && ln -sfn /home/fzheng4/AccelProf/eval/baselines/setup/iguard/iguard.so $D/detector.so
# the artifact scripts import matplotlib + tabulate: isolated venv (setup/tools/hirace_venv), .env untouched
export PATH=/home/fzheng4/AccelProf/eval/baselines/setup/tools/hirace_venv/bin:$PATH
cd $A || exit 1
echo "start $(date -Is) node=$(hostname) nvcc=$(nvcc --version | tail -2 | head -1)"
make -B table1 2>&1 | tee -a /home/fzheng4/AccelProf/eval/baselines/setup/hirace_table1.log | grep -E "complete \(|Compare to Table|\\\\|&" | tail -40
cd /home/fzheng4/AccelProf && $PY eval/baselines/hirace_table1_to_csv.py
echo "end $(date -Is)"

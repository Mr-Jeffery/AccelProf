#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH -t 01:00:00
#SBATCH -J m5-tests
#SBATCH -o /home/fzheng4/wt-m5/eval/x_logs/m5/tests-%j.log
# M5: python/test_co_chain.py (and the other closure tests) with CUVEIN_CHAIN_ATOMIC_HOP unset/1 and 0. CPU only.
W=/home/fzheng4/wt-m5
PY=/home/fzheng4/AccelProf/.env/bin/python
cd $W || exit 1
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
echo "host=$(hostname) rev=$(git rev-parse --short=12 HEAD) dirty=$(git status --porcelain -uno | wc -l) $(date -Is)"
lscpu | sed -n 's/^Model name:[[:space:]]*//p'
$PY -m py_compile python/sync_dominance.py python/test_co_chain.py && echo compiled
for sw in 1 0; do
  echo "=== CUVEIN_CHAIN_ATOMIC_HOP=$sw"
  CUVEIN_CHAIN_ATOMIC_HOP=$sw $PY -m pytest python/test_co_chain.py python/test_co_rules.py -q -p no:cacheprovider -W ignore --tb=short 2>&1 | tail -25
done
echo "=== all closure/co tests in python/ (switch 1)"
ls python/test_*.py | head -50
echo end $(date -Is)

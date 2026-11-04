# C6b step 4 environment (sourced by every queued command)
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\|BASELINE\)_[A-Z0-9_]*'); do unset $v; done
export CUVEIN_HOME=/home/fzheng4/wt-c6b ACCEL_PROF_HOME=/home/fzheng4/wt-c6b
export PY=/home/fzheng4/AccelProf/.env/bin/python W=/home/fzheng4/wt-c6b S4=/home/fzheng4/c6b-step4
export OUTD=$W/eval/results/co-chain-b/step4
mkdir -p $OUTD

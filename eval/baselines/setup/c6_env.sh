# C6 step 3 environment (sourced by every queued command)
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\|BASELINE\)_[A-Z0-9_]*'); do unset $v; done
export CUVEIN_HOME=/home/fzheng4/wt-c6 ACCEL_PROF_HOME=/home/fzheng4/wt-c6
export PY=/home/fzheng4/AccelProf/.env/bin/python W=/home/fzheng4/wt-c6 S3=/home/fzheng4/c6-step3
export OUTD=$W/eval/results/co-chain/step3
mkdir -p $OUTD

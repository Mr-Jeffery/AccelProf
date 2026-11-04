#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 04:00:00
#SBATCH -x c0,c1,c22,c23,c34,c46,c11,c12,c13,c18
#SBATCH -o /home/fzheng4/wt-c6b/eval/x_logs/c6b-s3-post-%x-%j.log
# C6b step 3 post: merge the three runs, compare with scalar-clock (final-b), classify, write the tables and assert_no_hb.txt
W=/home/fzheng4/wt-c6b
PY=/home/fzheng4/AccelProf/.env/bin/python
S=$W/eval/baselines/setup
cd $W || exit 1
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
echo "host=$(hostname) rev=$(git rev-parse --short=12 HEAD) start=$(date -Is)"
if [ -n "$S3_FINAL" ]; then $PY $S/c6b_s3_post.py && $PY $S/c6b_s3_assert.py; else $PY $S/c6b_s3_post.py; fi
echo "end $(date -Is)"

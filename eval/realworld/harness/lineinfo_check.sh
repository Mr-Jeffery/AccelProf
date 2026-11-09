#!/bin/bash
# Once per route: the SASS of one kernel with and without -lineinfo.  Compute node (needs cuobjdump).
#   lineinfo_check.sh <binary built with -lineinfo> <same build without> <kernel-name-substring> [sm_89]
# Verdict on stdout; the caller saves it as <build>/lineinfo.check and the report cites it.
here=$(cd "$(dirname "$0")" && pwd)
PYTHON=${PYTHON:-python3}
$PYTHON "$here/sass_diff.py" "$1" "$2" "$3" --arch "${4:-sm_89}"
rc=$?
if [ $rc -eq 0 ]; then
  echo "RESULT SAME: -lineinfo does not change the SASS; the traced build may be either."
else
  echo "RESULT DIFFERENT (rc=$rc): the traced build is the -lineinfo one."
fi
exit $rc

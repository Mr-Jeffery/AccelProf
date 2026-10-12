#!/usr/bin/env bash
#SBATCH --job-name=t20-rt-d67
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=00:20:00
# T20: a runtime mirror of the d67ed41 install (T4 + T18, before T19) for same-node timing against
# T4's bar: the backed-up library build/sanalyzer/lib/libsanalyzer.so.pre-t19-9ae97c27dc97fbf1 copied to
# <W>/rt-d67-lib/sanalyzer/libsanalyzer.so, a collector relinked from the d67ed41 objects with RPATH
# to that copy, and <W>/rt-d67 = {bin, build, .env, nv-compute/lib, lib -> rt-d67-lib} for RT=.
#   W=<worktree> sbatch -p rtx4060ti16g -x c54,c2 -o <log> eval/baselines/setup/t20_rt_d67.sh
set -e
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-t20}
A=/home/fzheng4/AccelProf
OBJ=${OBJ:-/home/fzheng4/stage-merge-d67ed41/nvc/obj}
GXX=/opt/ohpc/pub/compiler/gcc/12.4.0/bin/g++
CUDA=/usr/local/cuda
L=$W/rt-d67-lib
mkdir -p $L/sanalyzer
cp -p $A/build/sanalyzer/lib/libsanalyzer.so.pre-t19-9ae97c27dc97fbf1 $L/sanalyzer/libsanalyzer.so
cd $A/nv-compute
$GXX -L$CUDA/compute-sanitizer -L$L/sanalyzer -Wl,-rpath=$L/sanalyzer \
    -L$A/build/tensor_scope/lib -Wl,-rpath=$A/build/tensor_scope/lib \
    -fPIC -shared -o $L/libcompute_sanitizer.so $OBJ/*.o -lsanitizer-public -lsanalyzer -ltorch_scope
R=$W/rt-d67
mkdir -p $R/nv-compute
ln -sfn $A/bin $R/bin; ln -sfn $A/build $R/build; ln -sfn $A/.env $R/.env
ln -sfn $A/nv-compute/lib $R/nv-compute/lib; ln -sfn $L $R/lib
echo "libsanalyzer $(sha256sum $L/sanalyzer/libsanalyzer.so | cut -c1-16) collector $(sha256sum $L/libcompute_sanitizer.so | cut -c1-16) -> $(ldd $L/libcompute_sanitizer.so | awk '/sanalyzer/{print $3}')"
echo "== done $(date -Is)"

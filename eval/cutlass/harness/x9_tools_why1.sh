#!/bin/bash
# TOOLS_ON_STREAMK follow-up step 1 (CPU, `normal`): hashes, SASS from each ATOMG.E.CAS to the next BAR.SYNC, nvcc -M.
source /home/fzheng4/wt-x9/eval/cutlass/harness/x9_env.sh || exit $?
B=$CB/tools_streamk/build; O=$W/eval/cutlass/tools_streamk/why; F=$W/eval/cutlass/findings/streamk-wait-eq-reset
CUT=$CB/src/cutlass-v4.8.1
sha256sum $B/repro $B/repro_fixed $B/repro.cubin $B/repro_fixed.cubin $B/overlay_fixed/cutlass/barrier.h $CUT/include/cutlass/barrier.h | sed "s|$CB|\$CB|" | tee $O/sha256.txt
diff $CUT/include/cutlass/barrier.h $B/overlay_fixed/cutlass/barrier.h > $O/overlay_fixed.diff; echo "overlay diff rc=$?"
for e in repro repro_fixed; do
  cuobjdump -sass $B/$e > $O/$e.exe.sass
  awk '/ATOMG.E.CAS/{on=1} on{print} on && /BAR.SYNC/{on=0; print "----"}' $O/$e.exe.sass > $O/$e.cas_to_bar.txt
  echo "$e: functions=$(grep -c 'Function :' $O/$e.exe.sass) ATOMG.E.CAS=$(grep -c 'ATOMG.E.CAS' $O/$e.exe.sass) MEMBAR=$(grep -c MEMBAR $O/$e.exe.sass) CCTL.IVALL=$(grep -c 'CCTL.IVALL' $O/$e.exe.sass)"
done
for v in stock fixed; do
  inc=(); [ $v = fixed ] && inc=(-I $B/overlay_fixed)
  nvcc -arch=sm_89 -lineinfo -std=c++17 -O3 "${inc[@]}" -I $CUT/include -I $CUT/tools/util/include -M $F/repro.cu > $O/nvcc_M_$v.txt 2>/dev/null
  echo "$v nvcc -M rc=$? barrier.h: $(tr ' \' '\n\n' < $O/nvcc_M_$v.txt | grep 'barrier\.h' | sort -u | tr '\n' ' ')"
done

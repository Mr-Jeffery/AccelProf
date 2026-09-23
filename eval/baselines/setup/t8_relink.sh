#!/usr/bin/env bash
# T8: a PRIVATE copy of the collector (libcompute_sanitizer.so), relinked from the
# existing nv-compute objects exactly as nv-compute/Makefile links it, but with its
# RPATH pointing at the T8 libsanalyzer.so in sanalyzer/t8_install -- so the T8
# library can be tested without touching the shared build/sanalyzer/lib.
set -e
hostname
CUDA=/usr/local/cuda
cd /home/fzheng4/AccelProf/nv-compute
/opt/ohpc/pub/compiler/gcc/12.4.0/bin/g++ -L$CUDA/compute-sanitizer \
    -L/home/fzheng4/wt-T8/sanalyzer/t8_install/lib -Wl,-rpath=/home/fzheng4/wt-T8/sanalyzer/t8_install/lib \
    -L/home/fzheng4/AccelProf/build/tensor_scope/lib -Wl,-rpath=/home/fzheng4/AccelProf/build/tensor_scope/lib \
    -fPIC -shared -o /home/fzheng4/wt-T8/t8_rt_lib/libcompute_sanitizer.so lib/obj/compute_sanitizer.o lib/obj/sanitizer_helper.o \
    -lsanitizer-public -lsanalyzer -ltorch_scope
readelf -d /home/fzheng4/wt-T8/t8_rt_lib/libcompute_sanitizer.so | grep -i "rpath\|NEEDED"
readelf -d /home/fzheng4/AccelProf/lib/libcompute_sanitizer.so | grep -i "NEEDED" > /tmp/n_live; readelf -d /home/fzheng4/wt-T8/t8_rt_lib/libcompute_sanitizer.so | grep -i "NEEDED" > /tmp/n_new
diff /tmp/n_live /tmp/n_new && echo "NEEDED lists identical"
nm -D --defined-only /home/fzheng4/AccelProf/lib/libcompute_sanitizer.so | awk '{print $3}' | sort > /tmp/s_live; nm -D --defined-only /home/fzheng4/wt-T8/t8_rt_lib/libcompute_sanitizer.so | awk '{print $3}' | sort > /tmp/s_new
diff /tmp/s_live /tmp/s_new && echo "exported symbols identical"

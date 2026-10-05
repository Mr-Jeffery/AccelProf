#!/usr/bin/env bash
# T8: build the worktree's sanalyzer with the same toolchain / RPATHs as the live
# library (bin/build line 68), into a scratch INSTALL_DIR -- never the live one.
set -e
cd /home/fzheng4/wt-T8/sanalyzer
hostname; /opt/ohpc/pub/compiler/gcc/12.4.0/bin/g++ --version | head -1
make -j16 install DEBUG=0 EXTRA_CXX_FLAGS="-g -mtune=znver4" CXX=/opt/ohpc/pub/compiler/gcc/12.4.0/bin/g++ \
    SANITIZER_TOOL_DIR=/home/fzheng4/AccelProf/nv-compute NV_NVBIT_DIR=/home/fzheng4/AccelProf/nv-nvbit \
    CPP_TRACE_DIR=/home/fzheng4/AccelProf/build/sanalyzer/cpp_trace PY_FRAME_DIR=/home/fzheng4/AccelProf/build/sanalyzer/py_frame \
    INSTALL_DIR=/home/fzheng4/wt-T8/sanalyzer/t8_install 2>&1 | tail -20
ls -la /home/fzheng4/wt-T8/sanalyzer/t8_install/lib
readelf -d /home/fzheng4/wt-T8/sanalyzer/t8_install/lib/libsanalyzer.so | grep -i rpath
strings /home/fzheng4/wt-T8/sanalyzer/t8_install/lib/libsanalyzer.so | grep -c "YOSEMITE_HB_MODE"

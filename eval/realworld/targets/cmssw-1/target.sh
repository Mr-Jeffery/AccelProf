# cmssw-1: CMSSW multiBlockPrefixScan, missing __threadfence()/volatile in the last-block-done handoff on global memory (R2).
# Fix d1ce91e5 (2020-08-10), parent 37a05c6b.  The CMSSW tree is not built (SCRAM); the headers prefixScan.h and cudaCompat.h (the
# record's files) plus the unchanged cuda_assert.h and cudaCheck.h are copied BYTE-FOR-BYTE from both commits (r2_extract.sh); the only
# stub is FWCore/Utilities/interface/Likely.h (r2/common).  r2/common/driver.cu launches multiBlockPrefixScan like the commit's
# test prefixScan_t.cu, for 2000 and 20000 items.  Global memory: racecheck does not apply.
T_ROUTE=R2; T_KERNEL=multiBlockPrefixScan; T_SPACE=global; T_RACECHECK=na; T_EXE=driver; T_ARTIFACTS="driver"
t_export() { :; }
t_build()  {
  # CMSSW CUDA flags (scram-tools cuda.xml, from memory, not in the cmssw repo): -std=c++17 -O3 --expt-relaxed-constexpr (std::min in the kernel).
  nvcc -std=c++17 -O3 --expt-relaxed-constexpr $RW_NVCC_FLAGS $RW_LINEINFO -I"$SRC" -I"$SRC/common" -o driver "$SRC/common/driver.cu"
}
t_cmd()    { echo "$ART/driver"; }

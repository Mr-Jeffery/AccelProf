// T18: the T15 late-key variant of the pc_dependency device patch (eval/LATE_SEQ.md). The
// default patch (gpu_patch_pc_dependency.cu) contains no late-key code; the collector loads
// this one instead when YOSEMITE_HB_TRACE and YOSEMITE_HB_LATE_SEQ are set.
#define HB_LATE_SEQ 1
#include "gpu_patch_pc_dependency.cu"

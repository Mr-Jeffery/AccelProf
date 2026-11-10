#!/usr/bin/env python3
"""X13 step 4: labels.csv (binary, kernel, label, rule, source lines). Rules of the brief; tridiagonal is the gate (label GATE)."""
import csv, os, re, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
D = f"{APH}/eval/results/per-kernel"
kern = collections.OrderedDict()
for r in csv.DictReader(open(f"{D}/kernel_verdicts_curace.csv")):
    kern[(r["binary"], r["kernel"])] = r["binary_label"]
ncount = collections.Counter(b for b, _ in kern)
rows = []
def add(b, k, lab, rule, lines=""):
    rows.append([b, k, lab, rule, lines])
RACEY = {  # ScoR source: kernel -> RACEY blocks inside the kernel (or in a __device__ helper it calls), in gcol/gcon/mm/r110/uts/red/1dconv
    "convolveKernel": "1dconv_kernel.cu:71-79 (#ifdef RACEY ... #else ... #endif inside convolveKernel, kernel starts :57)",
    "assignColorsKernel": "gcol_kernel.cu:112-121 (two RACEY blocks)",
    "detectConflictsKernel": "gcol_kernel.cu:183-192 (two RACEY blocks)",
    "forbidColorsKernel": "gcol_kernel.cu:256-265 (two RACEY blocks)",
    "linkKernel": "gcon_kernel.cu:148-151,176-180 (RACEY blocks)",
    "compressKernel": "gcon_kernel.cu:226-229,252-256 (RACEY blocks)",
    "initKernel@gcon": "gcon_kernel.cu:74-77 (RACEY block)",
    "matMultKernel": "mm_kernel.cu:100-127 (three RACEY blocks)",
    "rule110Kernel": "r110_kernel.cu:81-85,117-121 (RACEY blocks)",
    "parTreeSearch": "uts_kernel.cu:230-261 (RACEY blocks in the kernel; :124-161 in the helpers it calls)",
    "reduceSinglePass": "red_kernel.cu:180-184 (RACEY block in the kernel), :78-81 in the __device__ helper it calls",
}
for (b, k), L in kern.items():
    base = os.path.basename(b)
    if b.startswith("hecbench:"):
        prog = b.split(":")[1]
        kb = k.replace("void ", "", 1)
        if prog == "tridiagonal":
            PROP = "AGENT'S SOURCE-BASED PROPOSAL, ADOPTED BY JEFFERY WITHOUT REVIEW (2026-11-09). "
            if k.startswith(("cyclic_small_systems_kernel", "cyclic_branch_free_kernel")):
                ln = "cyclic_kernels.cu:104-116 reads b/c/a/d[addr1], [addr2] after the last forward-elimination iteration (writes :81-98) with no __syncthreads() in between" if k.startswith("cyclic_small") else "cyclic_kernels.cu:216-228 reads b/c/a/d[addr1], [addr2] after the last forward-elimination iteration (writes :207-210) with no __syncthreads() in between"
                add(b, k, "RACE", PROP + ln + "; SuperCollider reports cyclic_kernels.cu:108 (R) and :225, :226 (W)", "cyclic_kernels.cu:108,225,226 @6a8c46c4")
            elif k.startswith(("pcr_small_systems_kernel", "pcr_branch_free_kernel")):
                add(b, k, "CLEAN", PROP + "pcr_kernels.cu: __syncthreads() after the loads (:54/:160), between the reads and the writes of every iteration (:100/:186) and after them (:108/:194), and before the final x[] read (:125/:211)", "pcr_kernels.cu @6a8c46c4")
            elif k.startswith("sweep_small_systems_global_vec4_kernel"):
                add(b, k, "CLEAN", PROP + "sweep_kernels.cu:269-357 read in full: no shared memory; thread j owns systems 4j..4j+3 (float4 loads/stores of x_d, w_d at i = 4j; reorder: i + k*num_systems, else a range of 4*system_size starting at 4j*system_size), ranges disjoint across threads", "sweep_kernels.cu:269-357 @6a8c46c4")
            elif k.startswith(("sweep_small_systems_local_kernel", "sweep_small_systems_global_kernel")):
                add(b, k, "CLEAN", PROP + "sweep_kernels.cu:20-106 / :117-: each thread solves its own system i (x_d[base_idx + k*stride]); no shared memory; w_d indexed by i", "sweep_kernels.cu @6a8c46c4")
            elif k.startswith("transpose"):
                add(b, k, "CLEAN", PROP + "sweep_kernels.cu:364-399: shared tile written at :393, __syncthreads() at :395, read transposed at :398", "sweep_kernels.cu:364-399 @6a8c46c4")
            else:
                add(b, k, "GATE", PROP + "UNMAPPED tridiagonal kernel")
        elif prog == "atomicCAS":
            add(b, k, "RACE", "6a8c46c4 kernels.h: every atomic_{min,max,add} overload starts with a plain read `ret = *address;` then atomicCAS on the same address; each launched atomic*Derived<T> kernel calls its overload (SC reports all nine inlined overloads, kernels.h:5,19,33,45,59,73,89,103,119)", "kernels.h:3-60 @6a8c46c4")
        elif prog == "dxtc2":
            add(b, k, "RACE", "single kernel `compress`: the binary's label (SC paper flag; X11 srccheck: label changed upstream)", "dxtc2-cuda @6a8c46c4")
        elif prog == "knn":
            if k.startswith("cuComputeDistanceGlobal"):
                add(b, k, "RACE", "6a8c46c4 main.cu: `__shared__ int begin_A, begin_B, step_A, step_B, end_A` are assigned by every thread of the block (main.cu:60-64, the lines SuperCollider reports); upstream made them thread-local", "main.cu:42-64 @6a8c46c4")
            else:
                add(b, k, "CLEAN", "each thread works on its own column xIndex (p_dist = dist + xIndex; cuParallelSqrt: dist[yIndex*width+xIndex] = sqrt(same element)); no shared memory", "main.cu cuInsertionSort / cuParallelSqrt @6a8c46c4")
        elif prog == "expdist":
            if k.startswith("void distance<"):
                add(b, k, "RACE", "kernel.h:28 `sh_mem[sh_offset+ti*stride] = d_mem[...]` (fill_shared_mem_tiled_1D, inlined via distance_tiled) fills sh_A / sh_scale_A which other threads read at kernel.h:84-87 with no __syncthreads between; FINAL_SWEEP_B.md section 11", "kernel.h:19-30,56-87 @6a8c46c4")
            else:
                add(b, k, "CLEAN", "reduce_cross_term: `sum` (shared) set by thread 0 then __syncthreads(); each thread accumulates a private s_cross_term over cross_term[i], i = tx + k*256; all threads atomicAdd(&sum, s) then __syncthreads() before thread 0 reads sum and writes output[0]; no unsynchronised conflicting access (atomicAdd on a double is an atomic CAS loop, not a plain access)", "kernel.h:124-147 @6a8c46c4")
        else:
            add(b, k, "CLEAN", f"{prog}: labelled race-free by SuperCollider's paper (and our build); every kernel race-free")
        continue
    m = re.search(r"/bin/(P\d)/", b)
    ps = m.group(1) if m else ""
    if ps == "P1":
        if k.startswith("init("):
            add(b, k, "CLEAN", "Indigo3 init kernel: each thread writes only its own element (data[idx] = ...), plus one-thread writes of the worklist size; template quoted in label_sources.md", "Indigo3 generated source, init kernel")
        else:
            add(b, k, L, "Indigo3: the main kernel takes the binary's label")
    elif ps == "PI":
        add(b, k, L, "one kernel launched (test_kernel): the binary's label")
    elif ps == "P4":
        racy = base.endswith("_racy")
        kk = re.sub(r"\(.*", "", k.replace("void ", ""))
        kk = re.sub(r"<.*", "", kk)
        if not racy:
            add(b, k, "CLEAN", "ScoR race-free build: no RACEY block compiled; every kernel race-free")
        else:
            key = kk + ("@gcon" if (kk == "initKernel" and "connectivity" in base) else "")
            if key in RACEY:
                add(b, k, "RACE", "ScoR racy build: the kernel contains a #ifdef RACEY block: " + RACEY[key], RACEY[key].split(" ")[0])
            elif kk == "initKernel":
                add(b, k, "CLEAN", "ScoR racy build, 1dconv initKernel: no RACEY block in initKernel (the block is at 1dconv_kernel.cu:71-79, inside convolveKernel)", "1dconv_kernel.cu:43-56")
            else:
                add(b, k, "RACE" , f"ScoR racy build: UNMAPPED kernel {kk}; binary label")
    elif ps == "P6":
        if ncount[b] == 1:
            add(b, k, L, "one kernel launched: the binary's label")
        else:
            add(b, k, "RACE" if L == "RACE" else "CLEAN", "PROPOSED (cuHadron interkernel, two kernels): the racy build's race is between the two kernels' accesses (producer write vs consumer read, or write_kernel_1 vs write_kernel_2), so both kernels are labelled racy; the fixed build: both race-free. Not in the in-scope view; only SuperCollider's all-34 cell counts it")
    else:
        add(b, k, L, "binary label")
with open(f"{D}/labels.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["binary", "kernel", "label", "rule", "source_lines"]); w.writerows(rows)
c = collections.Counter(r[2] for r in rows); print(len(rows), dict(c))

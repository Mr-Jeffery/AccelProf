[![](./assets/banner.jpg)](https://github.com/AccelProf)
------------------------------------------------------------
[![](https://img.shields.io/badge/license-MIT-green?logo=github)](https://github.com/AccelProf/AccelProf/blob/main/LICENSE)
[![Documentation Status](https://readthedocs.org/projects/accelprofdocs/badge/?version=latest)](https://accelprofdocs.readthedocs.io/en/latest/)
[![Static Badge](https://img.shields.io/badge/build-passing-brightgreen?logo=Linux&label=Linux)](https://github.com/AccelProf/AccelProf)
[![Static Badge](https://img.shields.io/badge/build-passing-brightgreen?logo=NVIDIA&label=NVIDIA)](https://github.com/AccelProf/AccelProf)
[![Static Badge](https://img.shields.io/badge/build-passing-brightgreen?logo=AMD&label=AMD)](https://github.com/AccelProf/AccelProf)

# AccelProf

A Modular Program Analysis Tool Framework for Emerging Accelerators.

## Overview

**AccelProf** is a modular program analysis framework for accelerator workloads spanning NVIDIA CUDA, AMD ROCm, and modern deep-learning systems. It abstracts over heterogeneous profiling APIs and deep-learning frameworks, providing a unified interface for capturing and analyzing runtime events at multiple levels. Its extensible architecture enables researchers and practitioners to rapidly prototype custom analysis tools with minimal overhead.

> **This branch (`cuVein`)** adds a fine-grained memory-reuse analysis pipeline on top of
> AccelProf. **cuVein** reconstructs the runtime **PC Dependency Graph (PCDepGraph)** of a
> CUDA kernel — for every memory-access instruction (PC) it quantifies *where* the data it
> touches was most recently accessed (same thread / warp / block / grid, or a cold miss),
> exposing byte-level data-reuse structure across the GPU memory hierarchy. See
> [Using cuVein](#using-cuvein) below.

## Installation

```bash
# Download
git clone --recursive https://github.com/AccelProf/AccelProf.git
git submodule update --init --recursive

# Check dependences
bash ./bin/utils/check_build_env.sh

# Build and install
./bin/build

# Set env
export ACCEL_PROF_HOME=$(pwd)
export PATH=${ACCEL_PROF_HOME}/bin:${PATH}
export LD_LIBRARY_PATH="$CUDA_HOME/compute-sanitizer:$LD_LIBRARY_PATH"
```

## Basic Usage

Analyze an accelerator application:

```bash
accelprof -v -t app_analysis <executable> [args...]
```

## Using cuVein

cuVein is exposed through AccelProf as a set of analysis tools plus offline
post-processing (a browser GUI and helper Python scripts). The workflow is:
**profile the kernel → inspect the generated PCDepGraph JSON**.

### Architecture

cuVein follows AccelProf's four-stage design (see the paper below). Each stage lives in a
different part of the tree:

| Stage | Location | Role |
|---|---|---|
| **Trace Collector** (GPU) | `nv-compute/gpu_src/gpu_patch_pc_dependency.cu` | Instruments every memory instruction; emits per-warp access records (addresses, PC offset, active-lane / distinct-sector / distinct-address masks). |
| **Event Monitor** (driver) | `nv-compute/src/compute_sanitizer.cpp` | Intercepts module load / kernel launch / (de)allocation via the NVIDIA Sanitizer API; instruments only whitelisted kernels; streams traces GPU→host. |
| **Offline Analyzer** (host) | `sanalyzer/src/tools/pc_dependency_analysis.cpp` | Reconstructs Topological Distance + PCDepGraph using demand-paged shadow memory and a lock-free parallel worker pool; dumps one JSON per kernel launch. |
| **GUI / scripts** | `third_party/pc_dependency_gui/*.html`, `python/*.py` | Visualize the PCDepGraph and flag inefficiency patterns (redundancy, broadcasting, streaming, cross-block reuse). |

### 1. Profile a kernel

```bash
# Reconstruct the PC Dependency Graph for the target application
accelprof -v -t pc_dependency_analysis <executable> [args...]
```

Available cuVein tools (`-t`):

| Tool | Purpose |
|---|---|
| `pc_dependency_analysis` | Reconstruct the per-kernel PCDepGraph (memory reuse structure). |
| `block_divergence_analysis` | Per-block execution-count profile (CSV; feed to `python/cluster_block_distribution.py`). |
| `heatmap_analysis` | Memory-access heatmap for a target block. |

Useful flags (see `accelprof -h` for the full list):

| Flag | Meaning |
|---|---|
| `-w <file>` | Kernel whitelist — only instrument kernels whose name matches a line in `<file>` (one keyword per line). **Strongly recommended** for large apps to keep overhead bounded. |
| `-n <N>` | Number of offline-analyzer worker threads (defaults to the hardware thread count). |
| `-o <dir>` | Directory for the run log / `perf` data. |
| `-b x,y,z` | Target block for `heatmap_analysis`. |
| `-p, --perf` | Additionally wrap the run in `perf record` (for profiling cuVein's own overhead). |
| `-v` | Verbose. |

**Output.** `pc_dependency_analysis` writes one JSON file per kernel launch to a
`dependency_<app_name>_<timestamp>/` directory (created in the current working directory):

```
dependency_<app_name>_<timestamp>/
├── kernel_0.json
├── kernel_1.json
└── ...
```

Each `kernel_<id>.json` contains the PCDepGraph: nodes (memory-access PCs, with access
type / space / size and the active-lane, distinct-sector and distinct-address
distributions) and edges (`PC_current → PC_previous`) labeled by Topological Distance
(intra-thread / intra-warp / intra-block / intra-grid / cold-miss) and accumulated data
volume.

### 2. Inspect the results

**Interactive GUI** — open the self-contained page in a browser and drag-and-drop (or
load) a `kernel_<id>.json`:

```
third_party/pc_dependency_gui/cuVein_GUI.html
```

The central canvas renders the PCDepGraph; the side panel auto-flags detected
inefficiencies (streaming accesses, redundant loads/stores, broadcasting, high
intra-grid / intra-block reuse). Selecting a PC node shows its cold-miss traffic, reuse
intensity, and access distributions. To cross-reference PCs with an external
disassembly, paste the kernel base PC (hex) into the **Kernel Base PC** field —
this converts the recorded PC *offsets* into absolute addresses (e.g. to match
`nvdisasm --print-line-info` or Nsight Compute).

**Command-line scanning** — for batch triage over a whole directory of JSON reports
(same detection logic as the GUI):

```bash
# Flag inefficiency patterns across all kernels in a results directory
python python/pc_inefficiency_scan.py dependency_<app_name>_<timestamp>/ \
       --min-severity LOW --min-traffic 1MB

# Cluster per-block execution profiles from block_divergence_analysis
python python/cluster_block_distribution.py block_distribution/kernel_0.csv

# Extract memory-hierarchy counters from an Nsight Compute report (to validate a fix)
python python/extract_ncu_metrics.py report.ncu-rep --bytes
```

### Notes / tuning

- cuVein instruments **every** access with no sampling, so overhead scales with the
  number of memory instructions — always use `-w` to restrict analysis to the suspicious
  kernel(s) identified by Nsight Compute first.
- Analyzer sizing can be tuned via environment variables, e.g. `YOSEMITE_WORKER_COUNT`
  (same as `-n`), `YOSEMITE_GPU_SM_COUNT`, and
  `YOSEMITE_GPU_MAX_ACTIVE_BLOCKS_PER_SM` (used to pre-size the shared-memory shadow pool).

## Documentation

Full user and developer documentation:
👉 **[https://accelprofdocs.readthedocs.io](https://accelprofdocs.readthedocs.io)**

## Paper

- **[CGO’26]** *PASTA: A Modular Program Analysis Tool Framework for Accelerators.*  
  Mao Lin, Hyeran Jeon, and Keren Zhou.  
  Proceedings of the 23rd ACM/IEEE International Symposium on Code Generation and Optimization (CGO 2026).

- *Reconstructing Fine-grained Memory Reuse Structure in CUDA Kernels.* (cuVein — under review)

## License

Released under the **MIT License**.
See `LICENSE` for details.

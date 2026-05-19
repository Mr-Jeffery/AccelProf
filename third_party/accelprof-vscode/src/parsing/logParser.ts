/**
 * Parser for AccelProf .accelprof.log files.
 *
 * Kernel launch lines:
 *   [SANITIZER INFO] Launching kernel <name> <<<...>>> on device N, pc: 0x<hex>, size: <N>
 *
 * Heatmap dump lines (follow their kernel's launch line):
 *   Dumping heatmap for block (...) to <path>/kernel_N_<name>.csv
 *
 * We build both an ordered list (by launch index) and a map keyed by
 * the CSV basename so callers can look up the kernel for any given CSV
 * without relying on index ordering.
 */

import * as path from 'path';

export interface KernelInfo {
    index: number;
    name: string;
    pc: bigint;
    size: number;
}

export interface ParsedLog {
    /** All kernel launches in order (index = position in log). */
    kernels: KernelInfo[];
    /** CSV basename (e.g. "kernel_0_foo(...).csv") → KernelInfo */
    csvToKernel: Map<string, KernelInfo>;
}

const KERNEL_LAUNCH_RE =
    /\[SANITIZER INFO\] Launching kernel (.+?) <<<.+?>>> on device \d+, pc: (0x[0-9a-fA-F]+), size: (\d+)/;
const DUMP_RE =
    /^Dumping heatmap for block \([^)]*\) to (.+\.csv)/;

export function parseLog(content: string): ParsedLog {
    const kernels: KernelInfo[] = [];
    const csvToKernel = new Map<string, KernelInfo>();
    const lines = content.split('\n');

    let pendingKernel: KernelInfo | null = null;

    for (const line of lines) {
        const lm = KERNEL_LAUNCH_RE.exec(line);
        if (lm) {
            pendingKernel = {
                index: kernels.length,
                name: lm[1].trim(),
                pc: BigInt(lm[2]),
                size: parseInt(lm[3], 10)
            };
            kernels.push(pendingKernel);
            continue;
        }

        const dm = DUMP_RE.exec(line);
        if (dm && pendingKernel) {
            csvToKernel.set(path.basename(dm[1]), pendingKernel);
            pendingKernel = null;   // consumed
        }
    }

    return { kernels, csvToKernel };
}

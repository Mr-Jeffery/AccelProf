"use strict";
/**
 * Parser for nvdisasm --print-line-info output.
 *
 * nvdisasm annotates with lines like:
 *   //## File "/path/to/vectorAdd.cu", line 9
 *
 * These annotations apply to all following instructions until the next
 * //## File annotation. Instruction offsets appear as:
 *   /*00b0*\/   LDG.E R3, [R2.64] ;
 *
 * Kernel functions appear as sections:
 *   .text._Z9vectorAddPKfS0_Pfi:
 *
 * We build per-kernel maps of offset → {file, line} so that two kernels
 * with the same relative offset do not collide.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.parseDisassemblyPerKernel = parseDisassemblyPerKernel;
exports.parseDisassembly = parseDisassembly;
exports.parseSassLines = parseSassLines;
const FILE_ANNO_RE = /^\s*\/\/##\s+File\s+"([^"]+)",\s+line\s+(\d+)/;
const OFFSET_RE = /^[^/]*\/\*([0-9a-fA-F]+)\*\//;
const KERNEL_SECT_RE = /^\.text\.([^:\s]+):/;
/**
 * Parse SASS into a per-kernel map keyed by the mangled kernel symbol name.
 * Each inner Map maps instruction offset (bigint) → source location.
 * Use demangleSymbols() to translate the keys to demangled names.
 */
function parseDisassemblyPerKernel(sassText) {
    const result = new Map();
    const lines = sassText.split('\n');
    let currentLoc = null;
    let kernelMap = null;
    for (const line of lines) {
        const kernelMatch = KERNEL_SECT_RE.exec(line);
        if (kernelMatch) {
            kernelMap = new Map();
            currentLoc = null;
            result.set(kernelMatch[1], kernelMap);
            continue;
        }
        const fileMatch = FILE_ANNO_RE.exec(line);
        if (fileMatch) {
            currentLoc = { file: fileMatch[1], line: parseInt(fileMatch[2], 10) };
            continue;
        }
        if (currentLoc && kernelMap) {
            const offsetMatch = OFFSET_RE.exec(line);
            if (offsetMatch) {
                const offset = BigInt('0x' + offsetMatch[1]);
                if (!kernelMap.has(offset)) {
                    kernelMap.set(offset, currentLoc);
                }
            }
        }
    }
    return result;
}
/**
 * Flat version: merge all per-kernel maps (used as a fallback when the
 * specific kernel cannot be identified).
 */
function parseDisassembly(sassText) {
    const result = new Map();
    for (const kernelMap of parseDisassemblyPerKernel(sassText).values()) {
        for (const [offset, loc] of kernelMap) {
            if (!result.has(offset)) {
                result.set(offset, loc);
            }
        }
    }
    return result;
}
/**
 * Build a map from instruction offset → line number (0-indexed) in the
 * SASS text.  Used to scroll the SASS editor to the right instruction
 * when a PC is clicked in the heatmap.
 */
function parseSassLines(sassText) {
    const result = new Map();
    const lines = sassText.split('\n');
    for (let i = 0; i < lines.length; i++) {
        const m = OFFSET_RE.exec(lines[i]);
        if (m) {
            const offset = BigInt('0x' + m[1]);
            if (!result.has(offset)) {
                result.set(offset, i);
            }
        }
    }
    return result;
}
//# sourceMappingURL=disasmParser.js.map
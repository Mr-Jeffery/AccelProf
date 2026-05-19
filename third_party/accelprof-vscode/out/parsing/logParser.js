"use strict";
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
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.parseLog = parseLog;
const path = __importStar(require("path"));
const KERNEL_LAUNCH_RE = /\[SANITIZER INFO\] Launching kernel (.+?) <<<.+?>>> on device \d+, pc: (0x[0-9a-fA-F]+), size: (\d+)/;
const DUMP_RE = /^Dumping heatmap for block \([^)]*\) to (.+\.csv)/;
function parseLog(content) {
    const kernels = [];
    const csvToKernel = new Map();
    const lines = content.split('\n');
    let pendingKernel = null;
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
            pendingKernel = null; // consumed
        }
    }
    return { kernels, csvToKernel };
}
//# sourceMappingURL=logParser.js.map
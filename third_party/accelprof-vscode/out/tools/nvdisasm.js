"use strict";
/**
 * Wrapper around cuobjdump + nvdisasm for extracting SASS from GPU binaries.
 *
 * Workflow:
 *   1. cuobjdump -xelf all <binary>  → extracts .cubin files into a tmpdir
 *   2. nvdisasm --print-line-info <cubin> → SASS with //## File annotations
 *   3. Clean up tmpdir
 *
 * Results are cached per binary path for the session lifetime.
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
exports.extractCubinAndDisassemble = extractCubinAndDisassemble;
exports.clearSassCache = clearSassCache;
exports.extractPtx = extractPtx;
exports.clearPtxCache = clearPtxCache;
exports.demangleSymbols = demangleSymbols;
const cp = __importStar(require("child_process"));
const fs = __importStar(require("fs"));
const os = __importStar(require("os"));
const path = __importStar(require("path"));
const config_1 = require("../util/config");
/** SASS text cache: binPath → sass output */
const sassCache = new Map();
function exec(cmd, args, cwd) {
    return new Promise((resolve, reject) => {
        cp.execFile(cmd, args, { cwd, maxBuffer: 64 * 1024 * 1024 }, (err, stdout, stderr) => {
            if (err) {
                reject(new Error(`${path.basename(cmd)} failed: ${stderr || err.message}`));
            }
            else {
                resolve(stdout);
            }
        });
    });
}
/**
 * Extract cubins from `binPath` and run nvdisasm on each.
 * Returns concatenated SASS text for all cubins.
 * Results are cached; pass forceRefresh=true to re-run.
 */
async function extractCubinAndDisassemble(binPath, forceRefresh = false) {
    if (!forceRefresh && sassCache.has(binPath)) {
        return sassCache.get(binPath);
    }
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'accelprof-'));
    try {
        const cuobjdump = (0, config_1.getCuobjdumpPath)();
        const nvdisasm = (0, config_1.getNvdisasmPath)();
        // Extract all ELF sections (produces *.cubin files in tmpDir)
        await exec(cuobjdump, ['-xelf', 'all', binPath], tmpDir);
        // Find all extracted cubins
        const cubins = fs.readdirSync(tmpDir).filter(f => f.endsWith('.cubin'));
        if (cubins.length === 0) {
            throw new Error('cuobjdump produced no .cubin files — is this a CUDA binary?');
        }
        const parts = [];
        for (const cubin of cubins) {
            const sass = await exec(nvdisasm, ['--print-line-info', path.join(tmpDir, cubin)], tmpDir);
            parts.push(`// === ${cubin} ===\n` + sass);
        }
        const result = parts.join('\n');
        sassCache.set(binPath, result);
        return result;
    }
    finally {
        // Clean up tmpdir
        try {
            fs.rmSync(tmpDir, { recursive: true, force: true });
        }
        catch {
            // best-effort
        }
    }
}
/** Clear the SASS cache (e.g. after binary rebuild) */
function clearSassCache() {
    sassCache.clear();
}
/** PTX text cache: binPath → ptx output */
const ptxCache = new Map();
/**
 * Extract embedded PTX from a CUDA binary using `cuobjdump --dump-ptx`.
 * No tmpdir needed — cuobjdump reads PTX directly from the fatbinary.
 * Results are cached per binary path for the session lifetime.
 */
async function extractPtx(binPath, forceRefresh = false) {
    if (!forceRefresh && ptxCache.has(binPath)) {
        return ptxCache.get(binPath);
    }
    const cuobjdump = (0, config_1.getCuobjdumpPath)();
    const result = await exec(cuobjdump, ['--dump-ptx', binPath], path.dirname(binPath));
    ptxCache.set(binPath, result);
    return result;
}
/** Clear the PTX cache */
function clearPtxCache() {
    ptxCache.clear();
}
/**
 * Demangle C++ mangled symbol names using `c++filt`.
 * Returns a Map<mangledName, demangledName>.
 * If c++filt is unavailable the map will be empty (callers must fall back).
 */
function demangleSymbols(mangledNames) {
    const result = new Map();
    if (mangledNames.length === 0) {
        return Promise.resolve(result);
    }
    return new Promise(resolve => {
        const proc = cp.spawn('c++filt', [], {});
        let stdout = '';
        proc.stdout.on('data', (d) => { stdout += d.toString(); });
        proc.on('close', () => {
            const demangled = stdout.split('\n');
            for (let i = 0; i < mangledNames.length && i < demangled.length; i++) {
                result.set(mangledNames[i], demangled[i].trim());
            }
            resolve(result);
        });
        proc.on('error', () => resolve(result)); // c++filt not found: empty map
        proc.stdin.write(mangledNames.join('\n') + '\n');
        proc.stdin.end();
    });
}
//# sourceMappingURL=nvdisasm.js.map
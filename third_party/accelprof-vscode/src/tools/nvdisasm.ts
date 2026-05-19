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

import * as cp from 'child_process';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { getCuobjdumpPath, getNvdisasmPath } from '../util/config';

/** SASS text cache: binPath → sass output */
const sassCache = new Map<string, string>();

function exec(cmd: string, args: string[], cwd: string): Promise<string> {
    return new Promise((resolve, reject) => {
        cp.execFile(cmd, args, { cwd, maxBuffer: 64 * 1024 * 1024 }, (err, stdout, stderr) => {
            if (err) {
                reject(new Error(`${path.basename(cmd)} failed: ${stderr || err.message}`));
            } else {
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
export async function extractCubinAndDisassemble(
    binPath: string,
    forceRefresh = false
): Promise<string> {
    if (!forceRefresh && sassCache.has(binPath)) {
        return sassCache.get(binPath)!;
    }

    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'accelprof-'));
    try {
        const cuobjdump = getCuobjdumpPath();
        const nvdisasm = getNvdisasmPath();

        // Extract all ELF sections (produces *.cubin files in tmpDir)
        await exec(cuobjdump, ['-xelf', 'all', binPath], tmpDir);

        // Find all extracted cubins
        const cubins = fs.readdirSync(tmpDir).filter(f => f.endsWith('.cubin'));
        if (cubins.length === 0) {
            throw new Error('cuobjdump produced no .cubin files — is this a CUDA binary?');
        }

        const parts: string[] = [];
        for (const cubin of cubins) {
            const sass = await exec(
                nvdisasm,
                ['--print-line-info', path.join(tmpDir, cubin)],
                tmpDir
            );
            parts.push(`// === ${cubin} ===\n` + sass);
        }

        const result = parts.join('\n');
        sassCache.set(binPath, result);
        return result;
    } finally {
        // Clean up tmpdir
        try {
            fs.rmSync(tmpDir, { recursive: true, force: true });
        } catch {
            // best-effort
        }
    }
}

/** Clear the SASS cache (e.g. after binary rebuild) */
export function clearSassCache(): void {
    sassCache.clear();
}

/** PTX text cache: binPath → ptx output */
const ptxCache = new Map<string, string>();

/**
 * Extract embedded PTX from a CUDA binary using `cuobjdump --dump-ptx`.
 * No tmpdir needed — cuobjdump reads PTX directly from the fatbinary.
 * Results are cached per binary path for the session lifetime.
 */
export async function extractPtx(
    binPath: string,
    forceRefresh = false
): Promise<string> {
    if (!forceRefresh && ptxCache.has(binPath)) {
        return ptxCache.get(binPath)!;
    }

    const cuobjdump = getCuobjdumpPath();
    const result = await exec(cuobjdump, ['--dump-ptx', binPath], path.dirname(binPath));
    ptxCache.set(binPath, result);
    return result;
}

/** Clear the PTX cache */
export function clearPtxCache(): void {
    ptxCache.clear();
}

/**
 * Demangle C++ mangled symbol names using `c++filt`.
 * Returns a Map<mangledName, demangledName>.
 * If c++filt is unavailable the map will be empty (callers must fall back).
 */
export function demangleSymbols(mangledNames: string[]): Promise<Map<string, string>> {
    const result = new Map<string, string>();
    if (mangledNames.length === 0) {
        return Promise.resolve(result);
    }
    return new Promise(resolve => {
        const proc = cp.spawn('c++filt', [], {});
        let stdout = '';
        proc.stdout.on('data', (d: Buffer) => { stdout += d.toString(); });
        proc.on('close', () => {
            const demangled = stdout.split('\n');
            for (let i = 0; i < mangledNames.length && i < demangled.length; i++) {
                result.set(mangledNames[i], demangled[i].trim());
            }
            resolve(result);
        });
        proc.on('error', () => resolve(result));   // c++filt not found: empty map
        proc.stdin.write(mangledNames.join('\n') + '\n');
        proc.stdin.end();
    });
}

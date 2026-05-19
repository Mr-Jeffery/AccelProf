import * as vscode from 'vscode';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { parseCsv, rowsToJson } from '../parsing/csvParser';
import { parseLog } from '../parsing/logParser';
import { extractCubinAndDisassemble, extractPtx, demangleSymbols } from '../tools/nvdisasm';
import { parseDisassembly, parseDisassemblyPerKernel } from '../tools/disasmParser';
import { parsePtxLines } from '../tools/ptxParser';
import { HeatmapPanel } from '../webview/heatmapPanel';

export async function openHeatmapCommand(
    context: vscode.ExtensionContext,
    uri?: vscode.Uri
): Promise<void> {

    // ── 1. Pick CSV ───────────────────────────────────────────────────────
    let csvPath: string;
    if (uri) {
        csvPath = uri.fsPath;
    } else {
        const picks = await vscode.window.showOpenDialog({
            canSelectFiles: true, canSelectFolders: false, canSelectMany: false,
            filters: { 'CSV files': ['csv'] },
            title: 'Select AccelProf kernel CSV'
        });
        if (!picks?.length) { return; }
        csvPath = picks[0].fsPath;
    }

    let content: string;
    try {
        content = fs.readFileSync(csvPath, 'utf8');
    } catch (e: unknown) {
        vscode.window.showErrorMessage(`AccelProf: Cannot read CSV: ${e instanceof Error ? e.message : e}`);
        return;
    }

    const rows = parseCsv(content);
    if (rows.length === 0) {
        vscode.window.showWarningMessage(`AccelProf: No data rows found in ${csvPath}`);
        return;
    }

    // ── 2. Pick log file (optional — Cancel to open heatmap only) ─────────
    const csvDir = path.dirname(csvPath);
    const kernelIdxMatch = /kernel_(\d+)/.exec(path.basename(csvPath, '.csv'));
    const kernelIdx = kernelIdxMatch ? parseInt(kernelIdxMatch[1], 10) : 0;

    const logPicks = await vscode.window.showOpenDialog({
        canSelectFiles: true, canSelectFolders: false, canSelectMany: false,
        filters: { 'AccelProf log': ['log'] },
        title: 'Select .accelprof.log  (Cancel to open heatmap only)',
        defaultUri: vscode.Uri.file(csvDir)
    });
    if (!logPicks?.length) {
        HeatmapPanel.create({ csvPath, rows: rowsToJson(rows), context });
        return;
    }

    let logContent: string;
    try {
        logContent = fs.readFileSync(logPicks[0].fsPath, 'utf8');
    } catch (e: unknown) {
        vscode.window.showErrorMessage(`AccelProf: Cannot read log: ${e instanceof Error ? e.message : e}`);
        return;
    }

    const { kernels, csvToKernel } = parseLog(logContent);

    // Prefer direct CSV-basename lookup (works with kernel_N_<name>.csv format).
    // Fall back to index-based lookup for old-format kernel_N.csv files.
    const csvBasename = path.basename(csvPath);
    const kernelInfo  = csvToKernel.get(csvBasename)
        ?? (kernelIdx < kernels.length ? kernels[kernelIdx] : undefined);

    if (!kernelInfo) {
        vscode.window.showErrorMessage(
            `AccelProf: Log has ${kernels.length} kernel(s) but no entry matches ${csvBasename}`
        );
        return;
    }
    const kernelBase    = kernelInfo.pc;
    const kernelDemName = kernelInfo.name;

    // ── 3. Pick binary ────────────────────────────────────────────────────
    const binPicks = await vscode.window.showOpenDialog({
        canSelectFiles: true, canSelectFolders: false, canSelectMany: false,
        title: 'Select CUDA binary for disassembly',
        defaultUri: vscode.Uri.file(csvDir)
    });
    if (!binPicks?.length) {
        HeatmapPanel.create({ csvPath, rows: rowsToJson(rows), context });
        return;
    }
    const binPath = binPicks[0].fsPath;

    // ── 4. Extract SASS + PTX, open PTX as temp file in col 2 ─────────────
    await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: 'AccelProf: Extracting PTX and SASS…', cancellable: false },
        async () => {
            // SASS: used internally for SASS-offset → source location
            let sass: string;
            try {
                sass = await extractCubinAndDisassemble(binPath);
            } catch (e: unknown) {
                vscode.window.showErrorMessage(`AccelProf: nvdisasm failed: ${e instanceof Error ? e.message : e}`);
                return;
            }

            // PTX: displayed in col 2
            let ptx: string;
            try {
                ptx = await extractPtx(binPath);
            } catch (e: unknown) {
                vscode.window.showErrorMessage(`AccelProf: cuobjdump --dump-ptx failed: ${e instanceof Error ? e.message : e}`);
                return;
            }
            if (!ptx.includes('.version')) {
                vscode.window.showWarningMessage(
                    'AccelProf: No embedded PTX found in binary (compile without -lineinfo-ptx-only, or use a fatbinary).'
                );
                return;
            }

            // Build per-kernel SASS map and pick the section for this kernel.
            // Match by demangled name (c++filt); fall back to function-name-only
            // if c++filt output differs slightly from NVIDIA's demangler.
            const perKernelMap = parseDisassemblyPerKernel(sass);
            const mangledNames = Array.from(perKernelMap.keys());
            const demangledMap = await demangleSymbols(mangledNames);

            // Strip leading "void " and arguments to get bare function name
            const bareName = (s: string) =>
                s.replace(/^void\s+/, '').split('(')[0].trim();

            const matchedMangled =
                // 1st choice: exact demangled match
                mangledNames.find(m => demangledMap.get(m) === kernelDemName) ??
                // 2nd choice: function name only (handles minor demangler differences)
                mangledNames.find(m => {
                    const dem = demangledMap.get(m);
                    return dem !== undefined && bareName(dem) === bareName(kernelDemName);
                });

            const locMap = matchedMangled
                ? perKernelMap.get(matchedMangled)!
                : parseDisassembly(sass);   // last-resort fallback: merge all sections

            const ptxLineMap = parsePtxLines(ptx);

            // Write PTX to a unique temp file each time so VSCode's document
            // cache never serves a stale (empty) buffer for the same path.
            const tmpPtxPath = path.join(
                os.tmpdir(),
                `accelprof_${path.basename(binPath)}_${Date.now()}.ptx`
            );
            fs.writeFileSync(tmpPtxPath, ptx, 'utf8');

            const ptxDoc = await vscode.workspace.openTextDocument(
                vscode.Uri.file(tmpPtxPath)
            );
            await vscode.window.showTextDocument(
                ptxDoc, { viewColumn: vscode.ViewColumn.Two, preserveFocus: true, preview: false }
            );

            // ── 5. Open heatmap in col 3 ──────────────────────────────────
            HeatmapPanel.create({
                csvPath,
                rows: rowsToJson(rows),
                context,
                kernelBase,
                locMap,
                ptxLineMap,
                ptxDoc
            });
        }
    );
}

"use strict";
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
exports.openHeatmapCommand = openHeatmapCommand;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const os = __importStar(require("os"));
const path = __importStar(require("path"));
const csvParser_1 = require("../parsing/csvParser");
const logParser_1 = require("../parsing/logParser");
const nvdisasm_1 = require("../tools/nvdisasm");
const disasmParser_1 = require("../tools/disasmParser");
const ptxParser_1 = require("../tools/ptxParser");
const heatmapPanel_1 = require("../webview/heatmapPanel");
async function openHeatmapCommand(context, uri) {
    // ── 1. Pick CSV ───────────────────────────────────────────────────────
    let csvPath;
    if (uri) {
        csvPath = uri.fsPath;
    }
    else {
        const picks = await vscode.window.showOpenDialog({
            canSelectFiles: true, canSelectFolders: false, canSelectMany: false,
            filters: { 'CSV files': ['csv'] },
            title: 'Select AccelProf kernel CSV'
        });
        if (!picks?.length) {
            return;
        }
        csvPath = picks[0].fsPath;
    }
    let content;
    try {
        content = fs.readFileSync(csvPath, 'utf8');
    }
    catch (e) {
        vscode.window.showErrorMessage(`AccelProf: Cannot read CSV: ${e instanceof Error ? e.message : e}`);
        return;
    }
    const rows = (0, csvParser_1.parseCsv)(content);
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
        heatmapPanel_1.HeatmapPanel.create({ csvPath, rows: (0, csvParser_1.rowsToJson)(rows), context });
        return;
    }
    let logContent;
    try {
        logContent = fs.readFileSync(logPicks[0].fsPath, 'utf8');
    }
    catch (e) {
        vscode.window.showErrorMessage(`AccelProf: Cannot read log: ${e instanceof Error ? e.message : e}`);
        return;
    }
    const { kernels, csvToKernel } = (0, logParser_1.parseLog)(logContent);
    // Prefer direct CSV-basename lookup (works with kernel_N_<name>.csv format).
    // Fall back to index-based lookup for old-format kernel_N.csv files.
    const csvBasename = path.basename(csvPath);
    const kernelInfo = csvToKernel.get(csvBasename)
        ?? (kernelIdx < kernels.length ? kernels[kernelIdx] : undefined);
    if (!kernelInfo) {
        vscode.window.showErrorMessage(`AccelProf: Log has ${kernels.length} kernel(s) but no entry matches ${csvBasename}`);
        return;
    }
    const kernelBase = kernelInfo.pc;
    const kernelDemName = kernelInfo.name;
    // ── 3. Pick binary ────────────────────────────────────────────────────
    const binPicks = await vscode.window.showOpenDialog({
        canSelectFiles: true, canSelectFolders: false, canSelectMany: false,
        title: 'Select CUDA binary for disassembly',
        defaultUri: vscode.Uri.file(csvDir)
    });
    if (!binPicks?.length) {
        heatmapPanel_1.HeatmapPanel.create({ csvPath, rows: (0, csvParser_1.rowsToJson)(rows), context });
        return;
    }
    const binPath = binPicks[0].fsPath;
    // ── 4. Extract SASS + PTX, open PTX as temp file in col 2 ─────────────
    await vscode.window.withProgress({ location: vscode.ProgressLocation.Notification, title: 'AccelProf: Extracting PTX and SASS…', cancellable: false }, async () => {
        // SASS: used internally for SASS-offset → source location
        let sass;
        try {
            sass = await (0, nvdisasm_1.extractCubinAndDisassemble)(binPath);
        }
        catch (e) {
            vscode.window.showErrorMessage(`AccelProf: nvdisasm failed: ${e instanceof Error ? e.message : e}`);
            return;
        }
        // PTX: displayed in col 2
        let ptx;
        try {
            ptx = await (0, nvdisasm_1.extractPtx)(binPath);
        }
        catch (e) {
            vscode.window.showErrorMessage(`AccelProf: cuobjdump --dump-ptx failed: ${e instanceof Error ? e.message : e}`);
            return;
        }
        if (!ptx.includes('.version')) {
            vscode.window.showWarningMessage('AccelProf: No embedded PTX found in binary (compile without -lineinfo-ptx-only, or use a fatbinary).');
            return;
        }
        // Build per-kernel SASS map and pick the section for this kernel.
        // Match by demangled name (c++filt); fall back to function-name-only
        // if c++filt output differs slightly from NVIDIA's demangler.
        const perKernelMap = (0, disasmParser_1.parseDisassemblyPerKernel)(sass);
        const mangledNames = Array.from(perKernelMap.keys());
        const demangledMap = await (0, nvdisasm_1.demangleSymbols)(mangledNames);
        // Strip leading "void " and arguments to get bare function name
        const bareName = (s) => s.replace(/^void\s+/, '').split('(')[0].trim();
        const matchedMangled = 
        // 1st choice: exact demangled match
        mangledNames.find(m => demangledMap.get(m) === kernelDemName) ??
            // 2nd choice: function name only (handles minor demangler differences)
            mangledNames.find(m => {
                const dem = demangledMap.get(m);
                return dem !== undefined && bareName(dem) === bareName(kernelDemName);
            });
        const locMap = matchedMangled
            ? perKernelMap.get(matchedMangled)
            : (0, disasmParser_1.parseDisassembly)(sass); // last-resort fallback: merge all sections
        const ptxLineMap = (0, ptxParser_1.parsePtxLines)(ptx);
        // Write PTX to a unique temp file each time so VSCode's document
        // cache never serves a stale (empty) buffer for the same path.
        const tmpPtxPath = path.join(os.tmpdir(), `accelprof_${path.basename(binPath)}_${Date.now()}.ptx`);
        fs.writeFileSync(tmpPtxPath, ptx, 'utf8');
        const ptxDoc = await vscode.workspace.openTextDocument(vscode.Uri.file(tmpPtxPath));
        await vscode.window.showTextDocument(ptxDoc, { viewColumn: vscode.ViewColumn.Two, preserveFocus: true, preview: false });
        // ── 5. Open heatmap in col 3 ──────────────────────────────────
        heatmapPanel_1.HeatmapPanel.create({
            csvPath,
            rows: (0, csvParser_1.rowsToJson)(rows),
            context,
            kernelBase,
            locMap,
            ptxLineMap,
            ptxDoc
        });
    });
}
//# sourceMappingURL=openHeatmap.js.map
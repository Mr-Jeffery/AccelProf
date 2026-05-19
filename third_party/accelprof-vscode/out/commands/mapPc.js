"use strict";
/**
 * Map a GPU PC (virtual address) from the heatmap to a source location.
 *
 * Pipeline:
 *   1. User clicks PC in webview → message arrives with pc string + csvPath
 *   2. Prompt user to pick the .accelprof.log → parseLog() → kernelInfos
 *   3. Determine kernel index from csvPath (kernel_N.csv → N)
 *   4. kernelBase = kernelInfos[N].pc
 *   5. offset = clickedPc - kernelBase
 *   6. Prompt user to pick the binary
 *   7. extractCubinAndDisassemble() → parseDisassembly() → Map<offset, {file,line}>
 *   8. Open source file at that line
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
exports.mapPcCommand = mapPcCommand;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const logParser_1 = require("../parsing/logParser");
const nvdisasm_1 = require("../tools/nvdisasm");
const disasmParser_1 = require("../tools/disasmParser");
async function mapPcCommand(pcStr, csvPath) {
    let clickedPc;
    try {
        clickedPc = BigInt(pcStr);
    }
    catch {
        vscode.window.showErrorMessage(`AccelProf: Invalid PC value: ${pcStr}`);
        return;
    }
    // Determine kernel index from filename
    const baseName = path.basename(csvPath, '.csv'); // e.g. "kernel_0"
    const idxMatch = /kernel_(\d+)/.exec(baseName);
    if (!idxMatch) {
        vscode.window.showErrorMessage(`AccelProf: Cannot determine kernel index from filename: ${baseName}`);
        return;
    }
    const kernelIdx = parseInt(idxMatch[1], 10);
    // Pick log file
    const logPicks = await vscode.window.showOpenDialog({
        canSelectFiles: true,
        canSelectFolders: false,
        canSelectMany: false,
        filters: { 'AccelProf log': ['log'] },
        title: 'Select .accelprof.log file',
        defaultUri: vscode.Uri.file(path.dirname(csvPath))
    });
    if (!logPicks || logPicks.length === 0) {
        return;
    }
    const logPath = logPicks[0].fsPath;
    let logContent;
    try {
        logContent = fs.readFileSync(logPath, 'utf8');
    }
    catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        vscode.window.showErrorMessage(`AccelProf: Cannot read log: ${msg}`);
        return;
    }
    const { kernels } = (0, logParser_1.parseLog)(logContent);
    if (kernelIdx >= kernels.length) {
        vscode.window.showErrorMessage(`AccelProf: Log has ${kernels.length} kernel(s) but kernel index is ${kernelIdx}`);
        return;
    }
    const kernelBase = kernels[kernelIdx].pc;
    const offset = clickedPc - kernelBase;
    if (offset < 0n) {
        vscode.window.showErrorMessage(`AccelProf: PC ${pcStr} is below kernel base ${kernelBase.toString(16)}`);
        return;
    }
    // Pick binary
    const binPicks = await vscode.window.showOpenDialog({
        canSelectFiles: true,
        canSelectFolders: false,
        canSelectMany: false,
        title: 'Select CUDA binary for disassembly'
    });
    if (!binPicks || binPicks.length === 0) {
        return;
    }
    const binPath = binPicks[0].fsPath;
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: `AccelProf: Mapping PC ${pcStr} → source…`,
        cancellable: false
    }, async () => {
        let sass;
        try {
            sass = await (0, nvdisasm_1.extractCubinAndDisassemble)(binPath);
        }
        catch (e) {
            const msg = e instanceof Error ? e.message : String(e);
            vscode.window.showErrorMessage(`AccelProf: nvdisasm failed: ${msg}`);
            return;
        }
        const locMap = (0, disasmParser_1.parseDisassembly)(sass);
        const loc = locMap.get(offset);
        if (!loc) {
            vscode.window.showWarningMessage(`AccelProf: No source annotation for offset 0x${offset.toString(16)} (PC ${pcStr})`);
            return;
        }
        // Resolve file path: try absolute, then relative to workspace folders
        let filePath = loc.file;
        if (!path.isAbsolute(filePath)) {
            const wsFolders = vscode.workspace.workspaceFolders;
            if (wsFolders) {
                for (const ws of wsFolders) {
                    const candidate = path.join(ws.uri.fsPath, filePath);
                    if (fs.existsSync(candidate)) {
                        filePath = candidate;
                        break;
                    }
                }
            }
        }
        let doc;
        try {
            doc = await vscode.workspace.openTextDocument(filePath);
        }
        catch {
            // Fall back to file name only
            vscode.window.showWarningMessage(`AccelProf: Source at ${loc.file}:${loc.line} (could not open file)`);
            return;
        }
        const line0 = Math.max(0, loc.line - 1); // VSCode lines are 0-indexed
        const range = new vscode.Range(line0, 0, line0, 0);
        await vscode.window.showTextDocument(doc, {
            selection: range,
            preview: false
        });
    });
}
//# sourceMappingURL=mapPc.js.map
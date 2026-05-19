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

import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { parseLog } from '../parsing/logParser';
import { extractCubinAndDisassemble } from '../tools/nvdisasm';
import { parseDisassembly } from '../tools/disasmParser';

export async function mapPcCommand(pcStr: string, csvPath: string): Promise<void> {
    let clickedPc: bigint;
    try {
        clickedPc = BigInt(pcStr);
    } catch {
        vscode.window.showErrorMessage(`AccelProf: Invalid PC value: ${pcStr}`);
        return;
    }

    // Determine kernel index from filename
    const baseName = path.basename(csvPath, '.csv'); // e.g. "kernel_0"
    const idxMatch = /kernel_(\d+)/.exec(baseName);
    if (!idxMatch) {
        vscode.window.showErrorMessage(
            `AccelProf: Cannot determine kernel index from filename: ${baseName}`
        );
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

    let logContent: string;
    try {
        logContent = fs.readFileSync(logPath, 'utf8');
    } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        vscode.window.showErrorMessage(`AccelProf: Cannot read log: ${msg}`);
        return;
    }

    const { kernels } = parseLog(logContent);
    if (kernelIdx >= kernels.length) {
        vscode.window.showErrorMessage(
            `AccelProf: Log has ${kernels.length} kernel(s) but kernel index is ${kernelIdx}`
        );
        return;
    }

    const kernelBase = kernels[kernelIdx].pc;
    const offset = clickedPc - kernelBase;

    if (offset < 0n) {
        vscode.window.showErrorMessage(
            `AccelProf: PC ${pcStr} is below kernel base ${kernelBase.toString(16)}`
        );
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

    await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: `AccelProf: Mapping PC ${pcStr} → source…`,
            cancellable: false
        },
        async () => {
            let sass: string;
            try {
                sass = await extractCubinAndDisassemble(binPath);
            } catch (e: unknown) {
                const msg = e instanceof Error ? e.message : String(e);
                vscode.window.showErrorMessage(`AccelProf: nvdisasm failed: ${msg}`);
                return;
            }

            const locMap = parseDisassembly(sass);
            const loc = locMap.get(offset);

            if (!loc) {
                vscode.window.showWarningMessage(
                    `AccelProf: No source annotation for offset 0x${offset.toString(16)} (PC ${pcStr})`
                );
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

            let doc: vscode.TextDocument;
            try {
                doc = await vscode.workspace.openTextDocument(filePath);
            } catch {
                // Fall back to file name only
                vscode.window.showWarningMessage(
                    `AccelProf: Source at ${loc.file}:${loc.line} (could not open file)`
                );
                return;
            }

            const line0 = Math.max(0, loc.line - 1); // VSCode lines are 0-indexed
            const range = new vscode.Range(line0, 0, line0, 0);
            await vscode.window.showTextDocument(doc, {
                selection: range,
                preview: false
            });
        }
    );
}

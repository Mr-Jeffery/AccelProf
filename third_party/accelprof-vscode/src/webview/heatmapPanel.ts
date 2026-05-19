import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { SectorRowJson } from '../parsing/csvParser';
import { SourceLocation } from '../tools/disasmParser';
import { highlightLine, clearHighlight } from '../util/decorations';

export interface HeatmapPanelOptions {
    csvPath:      string;
    rows:         SectorRowJson[];
    context:      vscode.ExtensionContext;
    /** undefined when log/binary were not provided at open time */
    kernelBase?:  bigint;
    locMap?:      Map<bigint, SourceLocation>;   // SASS offset → source {file,line}
    ptxLineMap?:  Map<string, number[]>;          // "file:line" → all PTX line indices (col 2)
    ptxDoc?:      vscode.TextDocument;            // temp file opened in col 2
}

export class HeatmapPanel {
    private static panels = new Map<string, HeatmapPanel>();

    private readonly panel: vscode.WebviewPanel;
    private readonly opts:  HeatmapPanelOptions;

    private prevSourceEditor?: vscode.TextEditor;
    private prevPtxEditor?:    vscode.TextEditor;

    private constructor(opts: HeatmapPanelOptions) {
        this.opts = opts;
        const title = path.basename(opts.csvPath);

        this.panel = vscode.window.createWebviewPanel(
            'accelprofHeatmap',
            `Heatmap: ${title}`,
            vscode.ViewColumn.Three,
            { enableScripts: true, retainContextWhenHidden: true }
        );

        this.panel.webview.html = this.buildHtml();

        this.panel.webview.onDidReceiveMessage(msg => {
            if (msg.command === 'mapPc') {
                this.handleMapPc(msg.pc);
            }
        });

        this.panel.onDidDispose(() => {
            HeatmapPanel.panels.delete(opts.csvPath);
        });
    }

    static create(opts: HeatmapPanelOptions): HeatmapPanel {
        const existing = HeatmapPanel.panels.get(opts.csvPath);
        if (existing) {
            existing.panel.reveal(vscode.ViewColumn.Three);
            return existing;
        }
        const p = new HeatmapPanel(opts);
        HeatmapPanel.panels.set(opts.csvPath, p);
        return p;
    }

    private async handleMapPc(pcStr: string): Promise<void> {
        const { kernelBase, locMap, ptxLineMap, ptxDoc } = this.opts;

        if (!kernelBase || !locMap || !ptxLineMap || !ptxDoc) {
            vscode.window.showWarningMessage(
                'AccelProf: Open the heatmap with a log and binary to enable PC→source mapping.'
            );
            return;
        }

        let clickedPc: bigint;
        try { clickedPc = BigInt(pcStr); } catch {
            vscode.window.showErrorMessage(`AccelProf: Invalid PC: ${pcStr}`);
            return;
        }

        const offset = clickedPc - kernelBase;
        if (offset < 0n) {
            vscode.window.showErrorMessage(`AccelProf: PC ${pcStr} is below kernel base`);
            return;
        }

        const loc = locMap.get(offset);

        // ── Col 2: reveal PTX and highlight the .loc line ─────────────────
        if (loc) {
            const ptxKey  = `${loc.file}:${loc.line}`;
            const ptxLine = ptxLineMap.get(ptxKey);

            if (ptxLine !== undefined) {
                const ptxEditor = await vscode.window.showTextDocument(
                    ptxDoc, { viewColumn: vscode.ViewColumn.Two, preserveFocus: true, preview: false }
                );
                if (this.prevPtxEditor) {
                    clearHighlight(this.prevPtxEditor, 'sass');
                }
                highlightLine(ptxEditor, ptxLine, 'sass');
                this.prevPtxEditor = ptxEditor;
            }

            // ── Col 1: reveal source and highlight line ───────────────────
            let filePath = loc.file;
            if (!path.isAbsolute(filePath)) {
                for (const ws of vscode.workspace.workspaceFolders ?? []) {
                    const candidate = path.join(ws.uri.fsPath, filePath);
                    if (fs.existsSync(candidate)) { filePath = candidate; break; }
                }
            }
            try {
                const srcDoc = await vscode.workspace.openTextDocument(filePath);
                const srcEditor = await vscode.window.showTextDocument(
                    srcDoc, { viewColumn: vscode.ViewColumn.One, preserveFocus: true, preview: false }
                );
                if (this.prevSourceEditor) {
                    clearHighlight(this.prevSourceEditor, 'source');
                }
                highlightLine(srcEditor, Math.max(0, loc.line - 1), 'source');
                this.prevSourceEditor = srcEditor;
            } catch {
                vscode.window.showWarningMessage(
                    `AccelProf: Source at ${loc.file}:${loc.line} (could not open file)`
                );
            }
        } else {
            vscode.window.showWarningMessage(
                `AccelProf: No source annotation for offset 0x${offset.toString(16)}`
            );
        }

        // Keep heatmap focused in col 3
        this.panel.reveal(vscode.ViewColumn.Three, true);
    }

    private buildHtml(): string {
        const htmlPath = path.join(this.opts.context.extensionPath, 'media', 'heatmap.html');
        let html = fs.readFileSync(htmlPath, 'utf8');
        const dataJson = JSON.stringify(this.opts.rows);
        html = html.replace(
            '<!-- DATA_INJECTION -->',
            `<script>const HEATMAP_DATA = ${dataJson};</script>`
        );
        return html;
    }
}

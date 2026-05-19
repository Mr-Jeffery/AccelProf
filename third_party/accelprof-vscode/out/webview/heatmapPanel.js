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
exports.HeatmapPanel = void 0;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const decorations_1 = require("../util/decorations");
class HeatmapPanel {
    constructor(opts) {
        this.opts = opts;
        const title = path.basename(opts.csvPath);
        this.panel = vscode.window.createWebviewPanel('accelprofHeatmap', `Heatmap: ${title}`, vscode.ViewColumn.Three, { enableScripts: true, retainContextWhenHidden: true });
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
    static create(opts) {
        const existing = HeatmapPanel.panels.get(opts.csvPath);
        if (existing) {
            existing.panel.reveal(vscode.ViewColumn.Three);
            return existing;
        }
        const p = new HeatmapPanel(opts);
        HeatmapPanel.panels.set(opts.csvPath, p);
        return p;
    }
    async handleMapPc(pcStr) {
        const { kernelBase, locMap, ptxLineMap, ptxDoc } = this.opts;
        if (!kernelBase || !locMap || !ptxLineMap || !ptxDoc) {
            vscode.window.showWarningMessage('AccelProf: Open the heatmap with a log and binary to enable PC→source mapping.');
            return;
        }
        let clickedPc;
        try {
            clickedPc = BigInt(pcStr);
        }
        catch {
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
            const ptxKey = `${loc.file}:${loc.line}`;
            const ptxLine = ptxLineMap.get(ptxKey);
            if (ptxLine !== undefined) {
                const ptxEditor = await vscode.window.showTextDocument(ptxDoc, { viewColumn: vscode.ViewColumn.Two, preserveFocus: true, preview: false });
                if (this.prevPtxEditor) {
                    (0, decorations_1.clearHighlight)(this.prevPtxEditor, 'sass');
                }
                (0, decorations_1.highlightLine)(ptxEditor, ptxLine, 'sass');
                this.prevPtxEditor = ptxEditor;
            }
            // ── Col 1: reveal source and highlight line ───────────────────
            let filePath = loc.file;
            if (!path.isAbsolute(filePath)) {
                for (const ws of vscode.workspace.workspaceFolders ?? []) {
                    const candidate = path.join(ws.uri.fsPath, filePath);
                    if (fs.existsSync(candidate)) {
                        filePath = candidate;
                        break;
                    }
                }
            }
            try {
                const srcDoc = await vscode.workspace.openTextDocument(filePath);
                const srcEditor = await vscode.window.showTextDocument(srcDoc, { viewColumn: vscode.ViewColumn.One, preserveFocus: true, preview: false });
                if (this.prevSourceEditor) {
                    (0, decorations_1.clearHighlight)(this.prevSourceEditor, 'source');
                }
                (0, decorations_1.highlightLine)(srcEditor, Math.max(0, loc.line - 1), 'source');
                this.prevSourceEditor = srcEditor;
            }
            catch {
                vscode.window.showWarningMessage(`AccelProf: Source at ${loc.file}:${loc.line} (could not open file)`);
            }
        }
        else {
            vscode.window.showWarningMessage(`AccelProf: No source annotation for offset 0x${offset.toString(16)}`);
        }
        // Keep heatmap focused in col 3
        this.panel.reveal(vscode.ViewColumn.Three, true);
    }
    buildHtml() {
        const htmlPath = path.join(this.opts.context.extensionPath, 'media', 'heatmap.html');
        let html = fs.readFileSync(htmlPath, 'utf8');
        const dataJson = JSON.stringify(this.opts.rows);
        html = html.replace('<!-- DATA_INJECTION -->', `<script>const HEATMAP_DATA = ${dataJson};</script>`);
        return html;
    }
}
exports.HeatmapPanel = HeatmapPanel;
HeatmapPanel.panels = new Map();
//# sourceMappingURL=heatmapPanel.js.map
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
exports.dumpSassCommand = dumpSassCommand;
const vscode = __importStar(require("vscode"));
const nvdisasm_1 = require("../tools/nvdisasm");
async function dumpSassCommand(uri) {
    let binPath;
    if (uri) {
        binPath = uri.fsPath;
    }
    else {
        const picks = await vscode.window.showOpenDialog({
            canSelectFiles: true,
            canSelectFolders: false,
            canSelectMany: false,
            title: 'Select CUDA binary (ELF or .cubin)'
        });
        if (!picks || picks.length === 0) {
            return;
        }
        binPath = picks[0].fsPath;
    }
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'AccelProf: Disassembling with nvdisasm…',
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
        // Open SASS in a read-only virtual document
        const uri = vscode.Uri.parse('untitled:' + binPath + '.sass');
        const doc = await vscode.workspace.openTextDocument(vscode.Uri.parse('untitled:accelprof-sass'));
        const editor = await vscode.window.showTextDocument(doc, { preview: false });
        await editor.edit(edit => {
            const full = new vscode.Range(doc.lineAt(0).range.start, doc.lineAt(doc.lineCount - 1).range.end);
            edit.replace(full, sass);
        });
        void uri; // suppress unused warning
    });
}
//# sourceMappingURL=dumpSass.js.map
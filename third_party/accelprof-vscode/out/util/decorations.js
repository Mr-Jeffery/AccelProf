"use strict";
/**
 * Shared decoration types for highlighting the active source line (col 1)
 * and the active SASS instruction (col 2) when a PC is clicked in the heatmap.
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
exports.highlightLine = highlightLine;
exports.clearHighlight = clearHighlight;
exports.disposeDecorations = disposeDecorations;
const vscode = __importStar(require("vscode"));
let _sourceDecor;
let _sassDecor;
function sourceDecor() {
    if (!_sourceDecor) {
        _sourceDecor = vscode.window.createTextEditorDecorationType({
            isWholeLine: true,
            backgroundColor: new vscode.ThemeColor('editor.findMatchHighlightBackground'),
            overviewRulerColor: new vscode.ThemeColor('editorOverviewRuler.findMatchForeground'),
            overviewRulerLane: vscode.OverviewRulerLane.Center,
        });
    }
    return _sourceDecor;
}
function sassDecor() {
    if (!_sassDecor) {
        _sassDecor = vscode.window.createTextEditorDecorationType({
            isWholeLine: true,
            backgroundColor: new vscode.ThemeColor('editor.findMatchHighlightBackground'),
            overviewRulerColor: new vscode.ThemeColor('editorOverviewRuler.findMatchForeground'),
            overviewRulerLane: vscode.OverviewRulerLane.Center,
        });
    }
    return _sassDecor;
}
/** Highlight one or more lines in an editor and scroll the first into view. */
function highlightLine(editor, line0, // 0-indexed; array for multi-line highlight
type) {
    const decor = type === 'source' ? sourceDecor() : sassDecor();
    const lines = Array.isArray(line0) ? line0 : [line0];
    const ranges = lines
        .filter(l => l >= 0 && l < editor.document.lineCount)
        .map(l => editor.document.lineAt(l).range);
    editor.setDecorations(decor, ranges);
    if (ranges.length > 0) {
        editor.revealRange(ranges[0], vscode.TextEditorRevealType.InCenterIfOutsideViewport);
    }
}
/** Clear highlights from an editor. */
function clearHighlight(editor, type) {
    const decor = type === 'source' ? sourceDecor() : sassDecor();
    editor.setDecorations(decor, []);
}
function disposeDecorations() {
    _sourceDecor?.dispose();
    _sassDecor?.dispose();
    _sourceDecor = undefined;
    _sassDecor = undefined;
}
//# sourceMappingURL=decorations.js.map
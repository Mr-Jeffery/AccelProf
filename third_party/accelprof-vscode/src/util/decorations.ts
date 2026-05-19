/**
 * Shared decoration types for highlighting the active source line (col 1)
 * and the active SASS instruction (col 2) when a PC is clicked in the heatmap.
 */

import * as vscode from 'vscode';

let _sourceDecor: vscode.TextEditorDecorationType | undefined;
let _sassDecor:   vscode.TextEditorDecorationType | undefined;

function sourceDecor(): vscode.TextEditorDecorationType {
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

function sassDecor(): vscode.TextEditorDecorationType {
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
export function highlightLine(
    editor: vscode.TextEditor,
    line0: number | number[],   // 0-indexed; array for multi-line highlight
    type: 'source' | 'sass'
): void {
    const decor  = type === 'source' ? sourceDecor() : sassDecor();
    const lines  = Array.isArray(line0) ? line0 : [line0];
    const ranges = lines
        .filter(l => l >= 0 && l < editor.document.lineCount)
        .map(l => editor.document.lineAt(l).range);
    editor.setDecorations(decor, ranges);
    if (ranges.length > 0) {
        editor.revealRange(ranges[0], vscode.TextEditorRevealType.InCenterIfOutsideViewport);
    }
}

/** Clear highlights from an editor. */
export function clearHighlight(
    editor: vscode.TextEditor,
    type: 'source' | 'sass'
): void {
    const decor = type === 'source' ? sourceDecor() : sassDecor();
    editor.setDecorations(decor, []);
}

export function disposeDecorations(): void {
    _sourceDecor?.dispose();
    _sassDecor?.dispose();
    _sourceDecor = undefined;
    _sassDecor = undefined;
}

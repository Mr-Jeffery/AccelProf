/**
 * TextDocumentContentProvider for accelprof-sass:// virtual documents.
 *
 * URI structure: accelprof-sass:///path/to/binary.ptx
 *   - scheme    : accelprof-sass
 *   - authority : (empty)
 *   - path      : binPath + ".ptx"
 *
 * We store content keyed by uri.path (stable across VSCode URI round-trips).
 */

import * as vscode from 'vscode';

export const SASS_SCHEME = 'accelprof-sass';

export class SassDocumentProvider implements vscode.TextDocumentContentProvider {
    private static _instance: SassDocumentProvider;

    private readonly _store = new Map<string, string>(); // uri.path → text
    private readonly _onDidChange = new vscode.EventEmitter<vscode.Uri>();
    readonly onDidChange = this._onDidChange.event;

    static get instance(): SassDocumentProvider {
        if (!SassDocumentProvider._instance) {
            SassDocumentProvider._instance = new SassDocumentProvider();
        }
        return SassDocumentProvider._instance;
    }

    /** Store PTX/SASS text for a binary and return the URI to open. */
    set(binPath: string, text: string): vscode.Uri {
        const uri = vscode.Uri.from({
            scheme: SASS_SCHEME,
            path: binPath + '.ptx'   // full path in URI path component — stable
        });
        this._store.set(uri.path, text);
        this._onDidChange.fire(uri);
        return uri;
    }

    provideTextDocumentContent(uri: vscode.Uri): string {
        return this._store.get(uri.path) ?? '// No PTX content';
    }
}

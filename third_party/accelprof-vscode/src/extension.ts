import * as vscode from 'vscode';
import { openHeatmapCommand } from './commands/openHeatmap';
import { dumpSassCommand } from './commands/dumpSass';
import { SassDocumentProvider, SASS_SCHEME } from './util/sassDocument';
import { disposeDecorations } from './util/decorations';

export function activate(context: vscode.ExtensionContext): void {
    // Register virtual document provider for SASS column
    context.subscriptions.push(
        vscode.workspace.registerTextDocumentContentProvider(
            SASS_SCHEME,
            SassDocumentProvider.instance
        )
    );

    context.subscriptions.push(
        vscode.commands.registerCommand(
            'accelprof.openHeatmap',
            (uri?: vscode.Uri) => openHeatmapCommand(context, uri)
        ),
        vscode.commands.registerCommand(
            'accelprof.dumpSass',
            (uri?: vscode.Uri) => dumpSassCommand(uri)
        )
    );
}

export function deactivate(): void {
    disposeDecorations();
}

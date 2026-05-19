import * as vscode from 'vscode';
import { extractCubinAndDisassemble } from '../tools/nvdisasm';

export async function dumpSassCommand(uri?: vscode.Uri): Promise<void> {
    let binPath: string;

    if (uri) {
        binPath = uri.fsPath;
    } else {
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

    await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'AccelProf: Disassembling with nvdisasm…',
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

            // Open SASS in a read-only virtual document
            const uri = vscode.Uri.parse('untitled:' + binPath + '.sass');
            const doc = await vscode.workspace.openTextDocument(
                vscode.Uri.parse('untitled:accelprof-sass')
            );
            const editor = await vscode.window.showTextDocument(doc, { preview: false });
            await editor.edit(edit => {
                const full = new vscode.Range(
                    doc.lineAt(0).range.start,
                    doc.lineAt(doc.lineCount - 1).range.end
                );
                edit.replace(full, sass);
            });
            void uri; // suppress unused warning
        }
    );
}

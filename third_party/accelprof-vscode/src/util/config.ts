import * as vscode from 'vscode';
import * as path from 'path';

export function getCudaToolkitPath(): string {
    const cfg = vscode.workspace.getConfiguration('accelprof');
    return cfg.get<string>('cudaToolkitPath', '/usr/local/cuda');
}

export function getNvdisasmPath(): string {
    return path.join(getCudaToolkitPath(), 'bin', 'nvdisasm');
}

export function getCuobjdumpPath(): string {
    return path.join(getCudaToolkitPath(), 'bin', 'cuobjdump');
}

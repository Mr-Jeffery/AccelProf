"use strict";
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
exports.SassDocumentProvider = exports.SASS_SCHEME = void 0;
const vscode = __importStar(require("vscode"));
exports.SASS_SCHEME = 'accelprof-sass';
class SassDocumentProvider {
    constructor() {
        this._store = new Map(); // uri.path → text
        this._onDidChange = new vscode.EventEmitter();
        this.onDidChange = this._onDidChange.event;
    }
    static get instance() {
        if (!SassDocumentProvider._instance) {
            SassDocumentProvider._instance = new SassDocumentProvider();
        }
        return SassDocumentProvider._instance;
    }
    /** Store PTX/SASS text for a binary and return the URI to open. */
    set(binPath, text) {
        const uri = vscode.Uri.from({
            scheme: exports.SASS_SCHEME,
            path: binPath + '.ptx' // full path in URI path component — stable
        });
        this._store.set(uri.path, text);
        this._onDidChange.fire(uri);
        return uri;
    }
    provideTextDocumentContent(uri) {
        return this._store.get(uri.path) ?? '// No PTX content';
    }
}
exports.SassDocumentProvider = SassDocumentProvider;
//# sourceMappingURL=sassDocument.js.map
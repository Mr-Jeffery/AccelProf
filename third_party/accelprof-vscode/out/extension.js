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
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const openHeatmap_1 = require("./commands/openHeatmap");
const dumpSass_1 = require("./commands/dumpSass");
const sassDocument_1 = require("./util/sassDocument");
const decorations_1 = require("./util/decorations");
function activate(context) {
    // Register virtual document provider for SASS column
    context.subscriptions.push(vscode.workspace.registerTextDocumentContentProvider(sassDocument_1.SASS_SCHEME, sassDocument_1.SassDocumentProvider.instance));
    context.subscriptions.push(vscode.commands.registerCommand('accelprof.openHeatmap', (uri) => (0, openHeatmap_1.openHeatmapCommand)(context, uri)), vscode.commands.registerCommand('accelprof.dumpSass', (uri) => (0, dumpSass_1.dumpSassCommand)(uri)));
}
function deactivate() {
    (0, decorations_1.disposeDecorations)();
}
//# sourceMappingURL=extension.js.map
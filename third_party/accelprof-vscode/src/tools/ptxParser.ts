/**
 * Parser for PTX output from `cuobjdump --dump-ptx`.
 *
 * PTX carries source location via:
 *   .file N "/absolute/path/to/file.cu"   (may appear anywhere; often at end)
 *   .loc  N  line  col                     (precedes the instruction it annotates)
 *
 * We build Map<"file:line", number> → first PTX line index (0-based) for that
 * source location.  This is used to scroll the PTX editor when a PC is clicked.
 *
 * Note: .file directives sometimes appear after the code in cuobjdump output,
 * so we do a two-pass parse.
 */

const FILE_RE = /^\.file\s+(\d+)\s+"([^"]+)"/;
const LOC_RE  = /^\.loc\s+(\d+)\s+(\d+)\s+\d+/;

/**
 * key: "absoluteFilePath:lineNumber"  (1-indexed line, matching SourceLocation)
 * value: all 0-indexed PTX line indices where a .loc directive for that source
 *        location appears.  Multiple .loc entries for the same source line are
 *        common (one per PTX instruction that maps back to that line).
 */
export function parsePtxLines(ptxText: string): Map<string, number[]> {
    const result  = new Map<string, number[]>();
    const fileMap = new Map<number, string>(); // index → absolute path
    const lines   = ptxText.split('\n');

    // Pass 1: collect all .file directives
    for (const line of lines) {
        const m = FILE_RE.exec(line.trim());
        if (m) {
            fileMap.set(parseInt(m[1]), m[2]);
        }
    }

    // Pass 2: collect every .loc occurrence for each source location
    for (let i = 0; i < lines.length; i++) {
        const m = LOC_RE.exec(lines[i].trim());
        if (!m) { continue; }

        const fileIdx = parseInt(m[1]);
        const srcLine = parseInt(m[2]);
        const file    = fileMap.get(fileIdx);
        if (!file) { continue; }

        const key = `${file}:${srcLine}`;
        const arr = result.get(key);
        if (arr) {
            arr.push(i);
        } else {
            result.set(key, [i]);
        }
    }

    return result;
}

/**
 * Parser for AccelProf heatmap_analysis CSV output.
 *
 * CSV format (tab-tab delimited logical columns):
 *   Header: "Sector Tag,\t\tDistinct Warp Count,\tAccess Count,\t\t\tTouched PC"
 *   Data:   "0x3fb82060000,\t\t1,1,1,1,1,1,1,1,1,\t\t1,1,1,1,1,1,1,1,8,\t\t0x7f70472834b0,"
 *
 * Each data row has:
 *   col0: sector tag (hex)
 *   col1: 9 warp counts (w0-w7, whole-sector)
 *   col2: 9 access counts (w0-w7, whole-sector)
 *   col3+: touched PCs (one per tab-separated field)
 */

export interface SectorRow {
    sectorTag: bigint;
    warpCounts: number[];   // length 9: w0-w7, whole
    accessCounts: number[]; // length 9: w0-w7, whole
    touchedPcs: bigint[];
}

function parseCommaSepNumbers(field: string): number[] {
    return field.split(',').filter(s => s.trim() !== '').map(s => parseInt(s.trim(), 10));
}

function parseCommaSepBigints(field: string): bigint[] {
    return field.split(',').filter(s => s.trim() !== '').map(s => BigInt(s.trim()));
}

export function parseCsv(content: string): SectorRow[] {
    const lines = content.split('\n');
    const rows: SectorRow[] = [];

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trimEnd();
        if (!line || line.startsWith('Sector Tag')) {
            continue;
        }

        // Split on \t\t to get logical columns
        const cols = line.split('\t\t');
        if (cols.length < 3) {
            continue;
        }

        // col0: "0x3fb82060000,"  → strip trailing comma
        const sectorStr = cols[0].replace(/,\s*$/, '').trim();
        let sectorTag: bigint;
        try {
            sectorTag = BigInt(sectorStr);
        } catch {
            continue;
        }

        // col1: "1,1,1,1,1,1,1,1,1," → 9 warp counts
        const warpCounts = parseCommaSepNumbers(cols[1]);

        // col2: "1,1,1,1,1,1,1,1,8," → 9 access counts
        const accessCounts = parseCommaSepNumbers(cols[2]);

        // col3+: "0x7f70472834b0," → PCs (may span multiple tab-cols)
        const touchedPcs: bigint[] = [];
        for (let c = 3; c < cols.length; c++) {
            const pcStrs = cols[c].split(',').map(s => s.trim()).filter(s => s.startsWith('0x'));
            for (const pcStr of pcStrs) {
                try {
                    touchedPcs.push(BigInt(pcStr));
                } catch {
                    // ignore malformed
                }
            }
        }

        rows.push({ sectorTag, warpCounts, accessCounts, touchedPcs });
    }

    return rows;
}

/** Serializable form for JSON injection into webview */
export interface SectorRowJson {
    sectorTag: string;
    warpCounts: number[];
    accessCounts: number[];
    touchedPcs: string[];
}

export function rowsToJson(rows: SectorRow[]): SectorRowJson[] {
    return rows.map(r => ({
        sectorTag: '0x' + r.sectorTag.toString(16),
        warpCounts: r.warpCounts,
        accessCounts: r.accessCounts,
        touchedPcs: r.touchedPcs.map(pc => '0x' + pc.toString(16))
    }));
}

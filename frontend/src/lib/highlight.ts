// Split text into plain and highlighted segments for the marker effect.

export interface Mark {
  id: number;
  highlight: string;
}

export interface Segment {
  text: string;
  markId: number | null;
}

// Same-length replacements so indices in the normalized copy match the original.
function normalizeForMatch(text: string): string {
  return text.replace(/[‘’]/g, "'").replace(/[“”]/g, '"').toLowerCase();
}

/** Mark the first non-overlapping occurrence of each highlight (case/quote-insensitive). */
export function splitHighlights(text: string, marks: Mark[]): Segment[] {
  const haystack = normalizeForMatch(text);
  const ranges: { start: number; end: number; markId: number }[] = [];

  for (const mark of marks) {
    const needle = normalizeForMatch(mark.highlight.trim());
    if (!needle) continue;
    let from = 0;
    while (from <= haystack.length) {
      const start = haystack.indexOf(needle, from);
      if (start === -1) break;
      const end = start + needle.length;
      const overlaps = ranges.some((r) => start < r.end && end > r.start);
      if (!overlaps) {
        ranges.push({ start, end, markId: mark.id });
        break;
      }
      from = start + 1;
    }
  }

  ranges.sort((a, b) => a.start - b.start);
  const segments: Segment[] = [];
  let cursor = 0;
  for (const range of ranges) {
    if (range.start > cursor)
      segments.push({ text: text.slice(cursor, range.start), markId: null });
    segments.push({ text: text.slice(range.start, range.end), markId: range.markId });
    cursor = range.end;
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor), markId: null });
  return segments;
}

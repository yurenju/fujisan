// Pure mapping from tilt delta to (row, col) index. No DOM, no events.
// sv = vertical sensitivity (degrees that span the full row range),
// sh = horizontal sensitivity (same, for columns).
const clamp = (v, min, max) => Math.min(max, Math.max(min, v));

export function tiltToIndex({ db, dg }, baseRow01, baseCol01, { sv, sh }, rows) {
  const rowCount = rows.length;
  const rowIndex01 = clamp(baseRow01 + db / sv, 0, 1);
  const colIndex01 = clamp(baseCol01 + dg / sh, 0, 1);

  const row = Math.round(rowIndex01 * (rowCount - 1));
  const len = rows[row].photos.length;
  const col = clamp(Math.floor(colIndex01 * len), 0, len - 1);

  return { row, col };
}

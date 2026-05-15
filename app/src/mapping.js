// Velocity-based mapping. tiltToVelocity is pure: tilt → speed.
// advance is pure: (state, velocity, dt, rows) → next state with wrap and
// cross-row column rescaling.

const clamp = (v, min, max) => Math.min(max, Math.max(min, v));

// Floor-mod that handles negatives correctly.
function wrap(x, mod) {
  return ((x % mod) + mod) % mod;
}

// Linear with dead zone. Returns 0 inside the dead zone, otherwise
// (|tilt| - deadzone) / sensitivity with the original sign.
function speedFrom(tilt, sensitivity, deadzone) {
  const m = Math.abs(tilt);
  if (m <= deadzone) return 0;
  return Math.sign(tilt) * (m - deadzone) / sensitivity;
}

export function tiltToVelocity({ db, dg }, { sv, sh, deadzone }) {
  return {
    vRow: speedFrom(db, sv, deadzone),  // rows / sec
    vCol: speedFrom(dg, sh, deadzone),  // photos / sec
  };
}

// state: { rowFloat, colFloat }
// velocity: { vRow, vCol }
// dt: seconds since last tick
// rows: [{ photos: [...] }, ...]
// Returns: { rowFloat, colFloat, row, col }
export function advance(state, velocity, dt, rows) {
  const rowCount = rows.length;
  const prevRow = clamp(Math.floor(state.rowFloat), 0, rowCount - 1);

  // Integrate and wrap row.
  let rowFloat = wrap(state.rowFloat + velocity.vRow * dt, rowCount);
  const newRow = Math.floor(rowFloat);

  // Cross-row column rescale to preserve normalized horizontal position.
  let colFloat = state.colFloat;
  if (newRow !== prevRow) {
    const prevLen = rows[prevRow].photos.length;
    const newLen  = rows[newRow].photos.length;
    const ratio = prevLen > 0 ? colFloat / prevLen : 0;
    colFloat = ratio * newLen;
  }

  // Integrate and wrap column on the current row's length.
  const len = rows[newRow].photos.length;
  colFloat = wrap(colFloat + velocity.vCol * dt, len);

  return {
    rowFloat,
    colFloat,
    row: newRow,
    col: Math.floor(colFloat),
  };
}

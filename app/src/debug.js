// URL-hash backed live-tunable parameters: sensitivity (s), tilt damping
// (d), highlight intensity (h). Renders three sliders that other modules
// read via the returned tuning object.

export function parseHash(hash) {
  if (!hash || hash === '#') return {};
  const out = {};
  const body = hash.startsWith('#') ? hash.slice(1) : hash;
  for (const part of body.split('&')) {
    const [k, v] = part.split('=');
    if (!k) continue;
    const num = Number(v);
    if (!Number.isNaN(num)) out[k] = num;
  }
  return out;
}

export function formatHash(values) {
  return '#' + Object.entries(values).map(([k, v]) => `${k}=${v}`).join('&');
}

export function createTuning({ defaults }) {
  const fromHash = parseHash(location.hash);
  const values = { ...defaults, ...fromHash };

  function set(key, value) {
    values[key] = value;
    history.replaceState(null, '', location.pathname + location.search + formatHash(values));
  }

  return { values, set };
}

export function mountSliders(container, tuning, ranges) {
  const wrap = document.createElement('div');
  wrap.className = 'debug-sliders';
  wrap.innerHTML = `
    <label>sensitivity <span data-out="s">${tuning.values.s}</span>°</label>
    <input type="range" min="${ranges.s[0]}" max="${ranges.s[1]}" step="0.5" value="${tuning.values.s}" data-key="s">
    <label>tilt damping <span data-out="d">${tuning.values.d}</span></label>
    <input type="range" min="${ranges.d[0]}" max="${ranges.d[1]}" step="0.05" value="${tuning.values.d}" data-key="d">
    <label>highlight <span data-out="h">${tuning.values.h}</span></label>
    <input type="range" min="${ranges.h[0]}" max="${ranges.h[1]}" step="0.05" value="${tuning.values.h}" data-key="h">
  `;
  container.appendChild(wrap);
  wrap.addEventListener('input', (e) => {
    const key = e.target.dataset.key;
    if (!key) return;
    const v = Number(e.target.value);
    tuning.set(key, v);
    const out = wrap.querySelector(`[data-out="${key}"]`);
    if (out) out.textContent = v;
  });
  return wrap;
}

// Photo map: 6 rows × variable columns (each row's width is divided evenly
// among its own photo count). Highlights the currently displayed photo so
// the user can see exactly which (row, col) the tilt has navigated to.
// Highlight persists after release.
export function mountPhotoMap(container, rows) {
  const wrap = document.createElement('div');
  wrap.className = 'photo-map';

  const header = document.createElement('div');
  header.className = 'pm-header';
  header.textContent = 'photo map';
  wrap.appendChild(header);

  const grid = document.createElement('div');
  grid.className = 'pm-grid';
  const cells = [];
  rows.forEach((row, rowIdx) => {
    const rowEl = document.createElement('div');
    rowEl.className = 'pm-row';
    cells[rowIdx] = [];
    row.photos.forEach((_, colIdx) => {
      const cell = document.createElement('div');
      cell.className = 'pm-cell';
      cell.title = `${row.label} #${colIdx + 1}`;
      rowEl.appendChild(cell);
      cells[rowIdx][colIdx] = cell;
    });
    grid.appendChild(rowEl);
  });
  wrap.appendChild(grid);

  const readout = document.createElement('div');
  readout.className = 'pm-readout';
  wrap.appendChild(readout);

  container.appendChild(wrap);

  let active = null;
  return {
    highlight(rowIdx, colIdx) {
      if (active) active.classList.remove('active');
      const cell = cells[rowIdx]?.[colIdx];
      if (cell) {
        cell.classList.add('active');
        active = cell;
      }
      const r = rows[rowIdx];
      if (r) readout.textContent = `${r.label}  ${colIdx + 1} / ${r.photos.length}`;
    },
  };
}

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

// Toggle button: collapses sibling debug content when active. State is
// stored in tuning under `hide` (0/1) so it persists in the URL hash.
export function mountToggle(container, tuning) {
  const btn = document.createElement('button');
  btn.className = 'debug-toggle';
  btn.type = 'button';
  btn.textContent = '≡';
  btn.title = 'toggle debug panel';
  const apply = () => container.classList.toggle('collapsed', !!tuning.values.hide);
  btn.addEventListener('click', () => {
    tuning.set('hide', tuning.values.hide ? 0 : 1);
    apply();
  });
  apply();
  container.appendChild(btn);
  return btn;
}

// configs: array of { key, label, min, max, step, unit? }
// Each entry renders one labelled slider bound to tuning.set(key, value).
export function mountSliders(container, tuning, configs) {
  const wrap = document.createElement('div');
  wrap.className = 'debug-sliders';

  for (const c of configs) {
    const label = document.createElement('label');
    const out = document.createElement('span');
    out.dataset.out = c.key;
    out.textContent = String(tuning.values[c.key]);
    label.append(`${c.label} `, out, c.unit || '');
    wrap.appendChild(label);

    const input = document.createElement('input');
    input.type = 'range';
    input.min = c.min;
    input.max = c.max;
    input.step = c.step;
    input.value = tuning.values[c.key];
    input.dataset.key = c.key;
    wrap.appendChild(input);
  }

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

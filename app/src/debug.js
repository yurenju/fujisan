// URL-hash backed live-tunable parameters. mountSliders renders one
// slider per config entry; createTuning persists changes back to the hash.

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

// Photo map: 6 rows × variable columns, rendered as a miniature film
// contact sheet sitting in the polaroid's bottom-left margin. Each row is
// a strip of negatives with sprocket holes on top and bottom; the current
// photo is highlighted as a brightly exposed frame.
export function mountPhotoMap(container, rows) {
  const wrap = document.createElement('div');
  wrap.className = 'photo-map';

  const cells = [];
  rows.forEach((row, rowIdx) => {
    const rowEl = document.createElement('div');
    rowEl.className = 'pm-row';
    const inner = document.createElement('div');
    inner.className = 'pm-strip';
    cells[rowIdx] = [];
    row.photos.forEach((_, colIdx) => {
      const cell = document.createElement('div');
      cell.className = 'pm-cell';
      cell.title = `${row.label} #${colIdx + 1}`;
      inner.appendChild(cell);
      cells[rowIdx][colIdx] = cell;
    });
    rowEl.appendChild(inner);
    wrap.appendChild(rowEl);
  });

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
    },
  };
}

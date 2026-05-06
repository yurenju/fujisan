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

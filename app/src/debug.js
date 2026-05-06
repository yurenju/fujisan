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

// Visualize current tilt delta inside a square: dot inside the box = within
// sensitivity range; dot outside (and red) = clamped — photo index has hit
// the edge while polaroid keeps rotating.
export function mountTiltScope(container) {
  const wrap = document.createElement('div');
  wrap.className = 'tilt-scope';
  wrap.innerHTML = `
    <div class="scope-box">
      <div class="scope-cross"></div>
      <div class="scope-dot"></div>
    </div>
    <div class="scope-readout"><span data-out="db">0.0</span>° / <span data-out="dg">0.0</span>°</div>
  `;
  container.appendChild(wrap);
  const dot = wrap.querySelector('.scope-dot');
  const dbOut = wrap.querySelector('[data-out="db"]');
  const dgOut = wrap.querySelector('[data-out="dg"]');

  return {
    update({ db, dg, sensitivityDeg }) {
      const xUnit = dg / sensitivityDeg;
      const yUnit = db / sensitivityDeg;
      const xPx = Math.max(-1.5, Math.min(1.5, xUnit)) * 60;
      const yPx = Math.max(-1.5, Math.min(1.5, yUnit)) * 60;
      dot.style.transform = `translate(${xPx}px, ${yPx}px)`;
      const clamped = Math.abs(xUnit) > 1 || Math.abs(yUnit) > 1;
      dot.classList.toggle('clamped', clamped);
      dbOut.textContent = db.toFixed(1);
      dgOut.textContent = dg.toFixed(1);
    },
    reset() {
      dot.style.transform = 'translate(0, 0)';
      dot.classList.remove('clamped');
      dbOut.textContent = '0.0';
      dgOut.textContent = '0.0';
    },
  };
}

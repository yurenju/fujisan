import { loadAll, showPhoto } from './src/loader.js';
import { probePermission, ensurePermission, createGyroSource } from './src/gyro.js';
import { createPointerSource } from './src/pointer.js';
import { tiltToVelocity, advance } from './src/mapping.js';
import { applyTiltVisual } from './src/polaroid.js';
import { createTuning, mountSliders, mountPhotoMap, mountToggle } from './src/debug.js';

const polaroid = document.getElementById('polaroid');
const photoFrame = document.getElementById('photo-frame');
const stage = document.getElementById('stage');
const stageClip = document.getElementById('stage-clip');
const caption = document.getElementById('caption');
const tiltBtn = document.getElementById('tilt-button');
const debugPanel = document.getElementById('debug-panel');
const progress = document.getElementById('progress');

const tuning = createTuning({
  defaults: { sv: 25, sh: 12, dz: 2, d: 0.4, h: 0.5, inv: 1, hide: 0 },
});
mountToggle(debugPanel, tuning);
mountSliders(debugPanel, tuning, [
  { key: 'sv',  label: 'deg / (row/sec)',   min: 10, max: 40, step: 0.5, unit: '°' },
  { key: 'sh',  label: 'deg / (photo/sec)', min: 5,  max: 30, step: 0.5, unit: '°' },
  { key: 'dz',  label: 'deadzone',          min: 0,  max: 5,  step: 0.1, unit: '°' },
  { key: 'd',   label: 'tilt damping',      min: 0,  max: 1,  step: 0.05 },
  { key: 'h',   label: 'highlight',         min: 0,  max: 1,  step: 0.05 },
  { key: 'inv', label: 'invert',            min: 0,  max: 1,  step: 1 },
]);
let photoMap = null;

let CANVAS = 1568;
let rows = [];
let imgByFile = {};
let currentFile = null;
let currentRow = 0;
let currentCol = 0;
let rowFloat = 0;
let colFloat = 0;
let rafHandle = null;
let lastTickMs = 0;
let tiltSource = null;

function fitStage() {
  const w = photoFrame.clientWidth;
  const h = photoFrame.clientHeight;
  const s = Math.min(w / CANVAS, h / CANVAS);
  stageClip.style.width = (CANVAS * s) + 'px';
  stageClip.style.height = (CANVAS * s) + 'px';
  stage.style.width = CANVAS + 'px';
  stage.style.height = CANVAS + 'px';
  stage.style.transform = `scale(${s})`;
}
window.addEventListener('resize', fitStage);

function setPhoto(rowIdx, colIdx) {
  currentRow = rowIdx;
  currentCol = colIdx;
  const file = rows[rowIdx].photos[colIdx];
  if (file !== currentFile) {
    currentFile = showPhoto(imgByFile, currentFile, file);
    const m = file.match(/PXL_(\d{8})_(\d{6})/);
    if (m) {
      const [, d, t] = m;
      caption.textContent = `${d.slice(0,4)}/${d.slice(4,6)}/${d.slice(6,8)}  ${t.slice(0,2)}:${t.slice(2,4)}`;
    } else {
      caption.textContent = file;
    }
  }
  photoMap?.highlight(rowIdx, colIdx);
}

function isCoarsePointer() {
  return matchMedia('(hover: none) and (pointer: coarse)').matches;
}

function tick(nowMs) {
  const dt = Math.min((nowMs - lastTickMs) / 1000, 0.1); // cap dt to avoid jumps after tab blur
  lastTickMs = nowMs;

  const raw = tiltSource.latest();
  const sign = tuning.values.inv ? -1 : 1;
  const tilt = { db: raw.db * sign, dg: raw.dg * sign };

  const velocity = tiltToVelocity(tilt, {
    sv: tuning.values.sv,
    sh: tuning.values.sh,
    deadzone: tuning.values.dz,
  });

  const next = advance({ rowFloat, colFloat }, velocity, dt, rows);
  rowFloat = next.rowFloat;
  colFloat = next.colFloat;

  if (next.row !== currentRow || next.col !== currentCol) {
    setPhoto(next.row, next.col);
  }

  rafHandle = requestAnimationFrame(tick);
}

function startLoop() {
  if (rafHandle != null) return;
  lastTickMs = performance.now();
  rafHandle = requestAnimationFrame(tick);
}

function stopLoop() {
  if (rafHandle != null) {
    cancelAnimationFrame(rafHandle);
    rafHandle = null;
  }
}

function startPress(source) {
  tiltSource = source;
  source.startCalibrated();
  tiltBtn?.classList.add('active');
  startLoop();
}

function endPress(source) {
  stopLoop();
  applyTiltVisual(polaroid, { db: 0, dg: 0 }, { tiltDamping: tuning.values.d, highlightIntensity: tuning.values.h });
  tiltBtn?.classList.remove('active');
  source?.endCalibrated?.();
}

function onTiltVisual(ev) {
  applyTiltVisual(polaroid, ev, { tiltDamping: tuning.values.d, highlightIntensity: tuning.values.h });
}

function wireMobile(source, initialPermission) {
  let permission = initialPermission;

  // iOS Safari requires DeviceOrientationEvent.requestPermission() to be
  // called from a 'click' (or 'touchend')-level user gesture; calling it
  // from 'touchstart' is rejected as not-a-gesture. So request on click
  // (which fires on tap completion), and only run the press lifecycle on
  // touchstart/touchend after permission is granted.
  const handleClick = async () => {
    if (permission === 'granted') return;
    permission = await ensurePermission();
    if (permission !== 'granted') {
      tiltBtn.classList.add('denied');
      wireTouchDragFallback();
    }
  };

  const handleTouchStart = (e) => {
    if (permission !== 'granted') return;
    e.preventDefault();
    startPress(source);
  };

  const handleTouchEnd = () => {
    if (permission !== 'granted') return;
    endPress(source);
  };

  tiltBtn.addEventListener('click', handleClick);
  tiltBtn.addEventListener('touchstart', handleTouchStart, { passive: false });
  tiltBtn.addEventListener('touchend', handleTouchEnd);
  tiltBtn.addEventListener('touchcancel', handleTouchEnd);
  source.onTilt(onTiltVisual);
}

let touchFallbackInstalled = false;
function wireTouchDragFallback() {
  if (touchFallbackInstalled) return;
  touchFallbackInstalled = true;
  const fb = createPointerSource({ maxV: 30, maxH: 30 });
  let active = false;
  const fakeMouse = (type, t) =>
    window.dispatchEvent(new MouseEvent(type, { clientX: t.clientX, clientY: t.clientY, button: 0 }));
  document.addEventListener('touchstart', (e) => {
    if (e.target === tiltBtn || tiltBtn.contains(e.target)) return;
    active = true;
    fakeMouse('mousedown', e.touches[0]);
  });
  document.addEventListener('touchmove', (e) => {
    if (!active) return;
    fakeMouse('mousemove', e.touches[0]);
  });
  document.addEventListener('touchend', () => {
    if (!active) return;
    active = false;
    fakeMouse('mouseup', { clientX: 0, clientY: 0 });
  });
  fb.onPressStart(() => startPress(fb));
  fb.onPressEnd(() => endPress(fb));
  fb.onTilt(onTiltVisual);
}

function wireDesktop(source) {
  source.onPressStart(() => startPress(source));
  source.onPressEnd(() => endPress(source));
  source.onTilt(onTiltVisual);
}

function onLoadProgress(loaded, total) {
  progress.textContent = `${loaded} / ${total}`;
  if (loaded === total) progress.classList.add('done');
}

async function init() {
  const data = await loadAll({ stage, onProgress: onLoadProgress });
  rows = data.rows;
  imgByFile = data.imgByFile;
  CANVAS = data.alignment.calibration_unit_px;
  fitStage();
  photoMap = mountPhotoMap(debugPanel, rows);
  setPhoto(0, 0);

  const initialPermission = await probePermission(500);
  if (isCoarsePointer()) {
    wireMobile(createGyroSource({ alpha: 0.18 }), initialPermission);
  } else {
    wireDesktop(createPointerSource({ maxV: 30, maxH: 30 }));
  }
}

init().catch(err => { caption.textContent = 'load error: ' + err.message; });

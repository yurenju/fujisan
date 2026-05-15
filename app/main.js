import { loadAll, showPhoto } from './src/loader.js';
import { probePermission, ensurePermission, createGyroSource } from './src/gyro.js';
import { createPointerSource } from './src/pointer.js';
import { tiltToVelocity, advance } from './src/mapping.js';
import { applyTiltVisual } from './src/polaroid.js';
import { createTuning, mountSliders, mountPhotoMap, mountToggle } from './src/debug.js';
import { showIntroModal } from './src/intro-modal.js';

const polaroid = document.getElementById('polaroid');
const photoFrame = document.getElementById('photo-frame');
const stage = document.getElementById('stage');
const stageClip = document.getElementById('stage-clip');
const caption = document.getElementById('caption');
const tape = document.getElementById('tape');
const tiltBtn = document.getElementById('tilt-button');
const debugPanel = document.getElementById('debug-panel');
const progress = document.getElementById('progress');

const POLAROID_PAD = 22;    // matches polaroid CSS padding-top / padding-left
const TAPE_HALF_H = 12.5;   // half of #tape height (25 / 2)

const tuning = createTuning({
  defaults: { sv: 20, sh: 2, dz: 2, d: 0.4, h: 0.5, inv: 1, hide: 0 },
});
// Debug panel (toggle + sliders) is opt-in via `?debug=1` so the released
// UI stays clean. URL hash still carries tunings for sharing presets.
const debugEnabled = new URLSearchParams(location.search).get('debug') === '1';
if (debugEnabled) {
  mountToggle(debugPanel, tuning);
  mountSliders(debugPanel, tuning, [
    { key: 'sv',  label: 'deg / (row/sec)',   min: 10, max: 40, step: 0.5, unit: '°' },
    { key: 'sh',  label: 'deg / (photo/sec)', min: 5,  max: 30, step: 0.5, unit: '°' },
    { key: 'dz',  label: 'deadzone',          min: 0,  max: 5,  step: 0.1, unit: '°' },
    { key: 'd',   label: 'tilt damping',      min: 0,  max: 1,  step: 0.05 },
    { key: 'h',   label: 'highlight',         min: 0,  max: 1,  step: 0.05 },
    { key: 'inv', label: 'invert',            min: 0,  max: 1,  step: 1 },
  ]);
}
let photoMap = null;

let CANVAS = 1568;
let rows = [];
let imgByFile = {};
let alignItems = {};
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
  if (currentFile) positionTape(currentFile);
}
window.addEventListener('resize', fitStage);

// Place the washi tape over the visible photo's top-center, but only when
// the photo doesn't reach the canvas top — otherwise there's no cream
// margin for the tape to sit on. Ported from poc/index.html.
function positionTape(file) {
  if (!tape) return;
  const item = alignItems[file];
  const img = imgByFile[file];
  if (!item || !item.matrix || !img || !img.naturalWidth) {
    tape.style.visibility = 'hidden';
    return;
  }
  const [[a, b, tx], [c, d, ty]] = item.matrix;
  const W = img.naturalWidth, H = img.naturalHeight;
  const corners = [
    [tx,             ty],
    [a*W + tx,       c*W + ty],
    [b*H + tx,       d*H + ty],
    [a*W + b*H + tx, c*W + d*H + ty],
  ];
  const xs = corners.map(p => p[0]);
  const ys = corners.map(p => p[1]);
  // Clamp to canvas bounds — when the source image extends past the canvas,
  // the visible photo edge sits at the canvas edge, not the geometric one.
  const imgTop   = Math.max(0,      Math.min(...ys));
  const imgLeft  = Math.max(0,      Math.min(...xs));
  const imgRight = Math.min(CANVAS, Math.max(...xs));
  const imgCx    = (imgLeft + imgRight) / 2;
  const s = stageClip.clientWidth / CANVAS;

  const TAPE_MIN_TOP_MARGIN = CANVAS * 0.04;  // ~63 px in canvas coords
  if (imgTop < TAPE_MIN_TOP_MARGIN) {
    tape.style.visibility = 'hidden';
    return;
  }
  tape.style.visibility = 'visible';
  tape.style.top  = (POLAROID_PAD + imgTop * s - TAPE_HALF_H) + 'px';
  tape.style.left = (POLAROID_PAD + imgCx  * s) + 'px';
}

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
    positionTape(file);
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
  // Both axes use raw directly (no inversion) for the natural physical
  // feel. `inv` toggles the vertical axis only — default inv=1 gives the
  // natural up/down feel; inv=0 flips it.
  const vSign = tuning.values.inv ? 1 : -1;
  const tilt = { db: raw.db * vSign, dg: raw.dg };

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
  // Fixed 30° virtual range — sv/sh now mean deg per unit-speed, not max tilt.
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
  const data = await loadAll({
    stage,
    onProgress: onLoadProgress,
    // Re-position tape once an asynchronously-loaded image finishes —
    // before load, naturalWidth is 0 and positionTape would hide the tape.
    onPhotoLoaded: (file) => { if (file === currentFile) positionTape(file); },
  });
  rows = data.rows;
  imgByFile = data.imgByFile;
  alignItems = data.alignment.items;
  CANVAS = data.alignment.calibration_unit_px;
  fitStage();
  photoMap = mountPhotoMap(polaroid, rows);
  setPhoto(0, 0);

  const initialPermission = await probePermission(500);
  const mode = await showIntroModal({ debug: debugEnabled });
  if (mode === 'mobile') {
    wireMobile(createGyroSource({ alpha: 0.18 }), initialPermission);
  } else if (mode === 'desktop-debug') {
    wireDesktop(createPointerSource({ maxV: 30, maxH: 30 }));
  }
}

init().catch(err => { caption.textContent = 'load error: ' + err.message; });

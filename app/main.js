import { loadAll, showPhoto } from './src/loader.js';
import { probePermission, ensurePermission, createGyroSource } from './src/gyro.js';
import { createPointerSource } from './src/pointer.js';
import { tiltToIndex } from './src/mapping.js';
import { applyTiltVisual } from './src/polaroid.js';
import { createTuning, mountSliders, mountPhotoMap } from './src/debug.js';

const polaroid = document.getElementById('polaroid');
const photoFrame = document.getElementById('photo-frame');
const stage = document.getElementById('stage');
const stageClip = document.getElementById('stage-clip');
const caption = document.getElementById('caption');
const tiltBtn = document.getElementById('tilt-button');
const debugPanel = document.getElementById('debug-panel');
const progress = document.getElementById('progress');

const tuning = createTuning({ defaults: { s: 20, d: 0.4, h: 0.5 } });
mountSliders(debugPanel, tuning, { s: [10, 40], d: [0, 1], h: [0, 1] });
let photoMap = null;

let CANVAS = 1568;
let rows = [];
let imgByFile = {};
let currentFile = null;
let currentRow = 0;
let currentCol = 0;
let baseRow01 = 0;
let baseCol01 = 0;

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

function startPress(source) {
  baseRow01 = currentRow / (rows.length - 1);
  const len = rows[currentRow].photos.length;
  baseCol01 = len > 1 ? currentCol / (len - 1) : 0;
  source.startCalibrated();
  tiltBtn?.classList.add('active');
}

function endPress(source) {
  applyTiltVisual(polaroid, { db: 0, dg: 0 }, { tiltDamping: tuning.values.d, highlightIntensity: tuning.values.h });
  tiltBtn?.classList.remove('active');
  source?.endCalibrated?.();
}

function onTiltUpdate(ev) {
  applyTiltVisual(polaroid, ev, { tiltDamping: tuning.values.d, highlightIntensity: tuning.values.h });
  const { row, col } = tiltToIndex(ev, baseRow01, baseCol01, tuning.values.s, rows);
  if (row !== currentRow || col !== currentCol) setPhoto(row, col);
}

function wireMobile(source, initialPermission) {
  let permission = initialPermission;
  const handlerDown = async (e) => {
    e.preventDefault();
    if (permission !== 'granted') {
      permission = await ensurePermission();
      if (permission !== 'granted') {
        tiltBtn.classList.add('denied');
        wireTouchDragFallback();
        return;
      }
    }
    startPress(source);
  };
  const handlerUp = () => endPress(source);
  tiltBtn.addEventListener('touchstart', handlerDown, { passive: false });
  tiltBtn.addEventListener('touchend', handlerUp);
  tiltBtn.addEventListener('touchcancel', handlerUp);
  source.onTilt(onTiltUpdate);
}

let touchFallbackInstalled = false;
function wireTouchDragFallback() {
  if (touchFallbackInstalled) return;
  touchFallbackInstalled = true;
  const fb = createPointerSource({ maxDeg: tuning.values.s });
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
  fb.onTilt(onTiltUpdate);
}

function wireDesktop(source) {
  source.onPressStart(() => startPress(source));
  source.onPressEnd(() => endPress(source));
  source.onTilt(onTiltUpdate);
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
    wireDesktop(createPointerSource({ maxDeg: tuning.values.s }));
  }
}

init().catch(err => { caption.textContent = 'load error: ' + err.message; });

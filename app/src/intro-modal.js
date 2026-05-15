// Intro modal: device detection, content selection, QR generation,
// and gating user entry into the appropriate interaction mode.
//
// Returns a Promise that resolves with the chosen mode:
//   'mobile'        — Android / iPhone, run the gyro flow
//   'desktop-debug' — Desktop with ?debug=1, run the pointer fallback
// The promise NEVER resolves for plain desktop — that's the block.

import qrcode from '../vendor/qrcode.js';
import { ensurePermission } from './gyro.js';

function detectDevice(debug) {
  const coarse = matchMedia('(hover: none) and (pointer: coarse)').matches;
  if (!coarse) return debug ? 'desktop-debug' : 'desktop';
  const D = window.DeviceOrientationEvent;
  if (D && typeof D.requestPermission === 'function') return 'ios';
  return 'android';
}

export function showIntroModal({ debug = false } = {}) {
  const dialog = document.getElementById('intro-modal');
  const device = detectDevice(debug);
  dialog.dataset.device = device;

  if (device === 'desktop' || device === 'desktop-debug') {
    const container = document.getElementById('intro-qrcode');
    const qr = qrcode(0, 'M');
    qr.addData(location.href);
    qr.make();
    // cellSize=6, margin=2 — tune in styling task if needed
    container.innerHTML = qr.createSvgTag({ cellSize: 6, margin: 2, scalable: true });
  }

  // Block Esc / cancel on plain desktop — there is no exit.
  dialog.addEventListener('cancel', (e) => {
    if (device === 'desktop') e.preventDefault();
  });

  if (device === 'android' || device === 'ios') {
    const startBtn = document.getElementById('intro-start-btn');
    const errorEl = dialog.querySelector('.intro-permission-error');
    if (device === 'ios') startBtn.textContent = '允許動作感應並開始';

    startBtn.addEventListener('click', async () => {
      if (device === 'ios') {
        // Must be the first await — ensurePermission needs to be called
        // synchronously in the click handler for iOS Safari to accept it
        // as a user gesture.
        const permission = await ensurePermission();
        if (permission !== 'granted') {
          errorEl.hidden = false;
          startBtn.disabled = true;
          return;
        }
      }
      dialog.close();
      dialog._resolveIntro('mobile');
    });
  }

  if (device === 'desktop-debug') {
    const debugBtn = document.getElementById('intro-debug-btn');
    debugBtn.addEventListener('click', () => {
      dialog.close();
      dialog._resolveIntro('desktop-debug');
    });
  }

  dialog.showModal();

  return new Promise((resolve) => {
    // Stash the resolver so the click handlers above can call it.
    // Safe ordering: the Promise constructor body runs synchronously
    // right after this `return`, before any click event can dispatch.
    dialog._resolveIntro = resolve;
  });
}

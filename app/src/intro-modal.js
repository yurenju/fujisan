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

  // Block Esc / cancel on plain desktop — there is no exit.
  dialog.addEventListener('cancel', (e) => {
    if (device === 'desktop') e.preventDefault();
  });

  dialog.showModal();

  return new Promise((resolve) => {
    // Wiring for each device variant is added in later tasks.
    // For now, just hold the promise open so the caller waits.
    dialog._resolveIntro = resolve;
  });
}

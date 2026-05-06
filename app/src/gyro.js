// Wrap DeviceOrientation events: permission probing, request, and a
// calibrated tilt stream emitting {db, dg} (delta beta/gamma) relative
// to the orientation captured at the most recent startCalibrated().

export function probePermission(timeoutMs = 500) {
  return new Promise(resolve => {
    let received = false;
    const onEvent = (e) => {
      if (e.beta != null || e.gamma != null) received = true;
    };
    window.addEventListener('deviceorientation', onEvent);
    setTimeout(() => {
      window.removeEventListener('deviceorientation', onEvent);
      resolve(received ? 'granted' : 'unknown');
    }, timeoutMs);
  });
}

export async function ensurePermission() {
  const D = window.DeviceOrientationEvent;
  if (D && typeof D.requestPermission === 'function') {
    return D.requestPermission();
  }
  return 'granted';
}

export function createGyroSource({ alpha = 0.18 } = {}) {
  const listeners = [];
  let smoothedBeta = 0;
  let smoothedGamma = 0;
  let initialized = false;
  let neutralBeta = 0;
  let neutralGamma = 0;
  let calibrated = false;

  const handler = (e) => {
    const b = e.beta ?? 0;
    const g = e.gamma ?? 0;
    if (!initialized) {
      smoothedBeta = b;
      smoothedGamma = g;
      initialized = true;
    } else {
      smoothedBeta = alpha * b + (1 - alpha) * smoothedBeta;
      smoothedGamma = alpha * g + (1 - alpha) * smoothedGamma;
    }
    if (calibrated) {
      const ev = {
        db: smoothedBeta - neutralBeta,
        dg: smoothedGamma - neutralGamma,
      };
      listeners.forEach(fn => fn(ev));
    }
  };

  window.addEventListener('deviceorientation', handler);

  return {
    onTilt(fn) { listeners.push(fn); },
    startCalibrated() {
      neutralBeta = smoothedBeta;
      neutralGamma = smoothedGamma;
      calibrated = true;
    },
    endCalibrated() {
      calibrated = false;
    },
    stop() {
      calibrated = false;
      window.removeEventListener('deviceorientation', handler);
      listeners.length = 0;
    },
  };
}

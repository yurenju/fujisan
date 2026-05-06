// Mouse-position simulation of the gyro tilt stream. Same shape as gyro:
// onTilt({db, dg}), startCalibrated(), stop(). Also exposes onPressStart /
// onPressEnd so main.js can drive the same press-to-recalibrate flow.

export function createPointerSource({ maxDeg = 20 } = {}) {
  const tiltListeners = [];
  const pressStartListeners = [];
  const pressEndListeners = [];

  let pressed = false;
  let neutralX = 0;
  let neutralY = 0;
  let lastX = 0;
  let lastY = 0;
  let calibrated = false;

  const onMouseDown = (e) => {
    pressed = true;
    lastX = e.clientX;
    lastY = e.clientY;
    pressStartListeners.forEach(fn => fn());
  };

  const onMouseMove = (e) => {
    if (!pressed) return;
    lastX = e.clientX;
    lastY = e.clientY;
    if (!calibrated) return;
    const dg = ((lastX - neutralX) / window.innerWidth)  * maxDeg;
    const db = ((lastY - neutralY) / window.innerHeight) * maxDeg;
    tiltListeners.forEach(fn => fn({ db, dg }));
  };

  const onMouseUp = () => {
    if (!pressed) return;
    pressed = false;
    calibrated = false;
    pressEndListeners.forEach(fn => fn());
  };

  window.addEventListener('mousedown', onMouseDown);
  window.addEventListener('mousemove', onMouseMove);
  window.addEventListener('mouseup', onMouseUp);
  window.addEventListener('blur', onMouseUp);

  return {
    onTilt(fn) { tiltListeners.push(fn); },
    onPressStart(fn) { pressStartListeners.push(fn); },
    onPressEnd(fn) { pressEndListeners.push(fn); },
    startCalibrated() {
      neutralX = lastX;
      neutralY = lastY;
      calibrated = true;
    },
    stop() {
      window.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      window.removeEventListener('blur', onMouseUp);
      tiltListeners.length = 0;
      pressStartListeners.length = 0;
      pressEndListeners.length = 0;
    },
  };
}

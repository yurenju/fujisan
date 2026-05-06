// Apply the polaroid's per-frame visual transform: 3D rotation, specular
// highlight position, and shadow offset. Pure DOM mutation — no event
// subscription, no calibration logic.

export function applyTiltVisual(el, { db, dg }, { tiltDamping = 0.4, highlightIntensity = 0.5 } = {}) {
  const rx = (-db * tiltDamping).toFixed(3);
  const ry = ( dg * tiltDamping).toFixed(3);
  el.style.transform = `rotateX(${rx}deg) rotateY(${ry}deg)`;

  const shineX = 50 - dg * 1.5;
  const shineY = 30 - db * 1.5;
  const intensityScale = highlightIntensity / 0.5;
  const shineOpacity = 0.35 + Math.min(0.4, (Math.abs(db) + Math.abs(dg)) * 0.015) * intensityScale;
  el.style.setProperty('--shine-x', `${shineX}%`);
  el.style.setProperty('--shine-y', `${shineY}%`);
  el.style.setProperty('--shine-opacity', shineOpacity.toFixed(3));

  const sx = -dg * 0.6;
  const sy = 12 + db * 0.4;
  el.style.boxShadow =
    `${sx}px ${sy}px 40px rgba(0,0,0,0.55), ${sx/3}px ${sy/4}px 6px rgba(0,0,0,0.4)`;
}

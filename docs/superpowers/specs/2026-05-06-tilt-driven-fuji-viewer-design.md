# Tilt-driven Fuji Viewer — Design

**Date:** 2026-05-06
**Status:** Approved for implementation planning

## Goal

Promote the existing `poc/index.html` photo browser into a near-production single-page experience under a new `app/` directory. Replace the desktop floating pad with a unified input model: on mobile, the user presses a red dashed circle in the bottom-right corner and tilts the phone to scan through the photo grid; on desktop, the same model is driven by mouse position relative to a click-anchor.

The polaroid itself responds with a damped 3D tilt and shifting specular highlight so it feels like a physical photo held in the hand, while the photo content snaps between discrete frames.

## Interaction Model

| Aspect | Decision |
|---|---|
| Trigger | Press-and-hold the red dashed circle (mobile) or mouse-down anywhere on the canvas (desktop). |
| Recalibration | The moment of press captures the current device orientation as the new neutral. All tilt is interpreted as a delta from neutral. Releasing freezes the photo at its current row/column. Re-pressing redefines neutral, so the user can rotate back to a comfortable hand position before continuing. |
| Vertical axis (Δβ) | Selects one of 6 rows: top rest, sequences 1–4, bottom rest. |
| Horizontal axis (Δγ) | Selects a column within the current row, mapped linearly across that row's photo count. |
| Sensitivity | ±20° spans the full range by default. A debug slider on the left edge tunes it live; the chosen value is then hard-coded and the slider removed. |
| Edge behavior | Photo index clamps at row/column edges. The polaroid's 3D rotation continues past the clamp so the user feels they have hit a wall but the canvas still reads their motion. |
| Photo transition | Hard cut. No crossfade. |
| Polaroid 3D | Damped: device tilt of 20° drives a polaroid rotation of ~8°. A radial specular highlight and offset drop shadow shift accordingly. |
| Permission | On load, silently probe `deviceorientation` events for 500 ms. If readings arrive, the red circle is immediately ready. Otherwise the first press triggers `DeviceOrientationEvent.requestPermission()` from inside the user gesture. |
| Permission denied | Fallback: touch-drag on the canvas emits the same Δβ/Δγ events. |
| Desktop input | `pointer.js` simulates tilt: the mouse-down position becomes neutral; mouse movement maps `(Δx / window.innerWidth, Δy / window.innerHeight)` to Δγ/Δβ over a ±20° simulated range. |

## Directory Structure

```
app/
  index.html              # entry, minimal markup
  styles.css              # all styles (extracted from current inline)
  main.js                 # bootstrapping, event wiring
  src/
    loader.js             # fetch data + alignments, preload images
    gyro.js               # DeviceOrientation + permission detection + EMA filter
    pointer.js            # desktop mouse-position simulation (same interface as gyro)
    mapping.js            # tilt delta → (row, col) index
    polaroid.js           # 3D transform + specular highlight + shadow
    debug.js              # tunable sensitivity slider
  data/
    photos.json           # 6 rows × variable columns
    alignments.json       # copy of alignment/aligned-all/alignments-normalized.json
  images/                 # 125 referenced photos copied from alignment/images-resized/
```

`app/` is self-contained: it does not reference `alignment/` or `poc/` at runtime.

## Data Schema

`app/data/photos.json` flattens the current top-rest / sequences / bottom-rest split into a single uniform row list. Each row carries an id, label, and ordered photos array. Columns within a row are simply array indices.

```json
{
  "rows": [
    { "id": "top-rest",    "label": "早上的散張",  "photos": ["..."] },
    { "id": "seq-1",       "label": "2025/12/31", "photos": ["..."] },
    { "id": "seq-2",       "label": "2026/01/19", "photos": ["..."] },
    { "id": "seq-3",       "label": "2026/01/22", "photos": ["..."] },
    { "id": "seq-4",       "label": "2026/01/26", "photos": ["..."] },
    { "id": "bottom-rest", "label": "其他散張",    "photos": ["..."] }
  ]
}
```

Photo counts: 29, 7, 10, 30, 20, 29 (total 125, matching every file in `alignment/images-resized/`).

`alignments.json` is copied verbatim from `alignment/aligned-all/alignments-normalized.json` and consumed the same way the existing PoC does — denormalize by `calibration_unit_px` and apply the matrix as the image's CSS transform within `#stage`.

## Module Contracts

### `loader.js`

```
loadAll() → { rows, alignment, imgByFile }
```
Loads `data/photos.json` and `data/alignments.json`, instantiates an `<img>` for every referenced file with the per-image alignment matrix as its CSS transform, and attaches them to the stage hidden. Returns the full structure.

### `gyro.js`

```
probePermission()       → Promise<'granted' | 'unknown'>
ensurePermission()      → Promise<'granted' | 'denied'>     // call from user gesture
createGyroSource()      → { onTilt(cb), startCalibrated(), stop() }
```
`createGyroSource` wraps `deviceorientation`, applies an EMA filter (`α ≈ 0.18`) on β/γ, and emits `{Δβ, Δγ}` relative to whatever orientation was current at the latest `startCalibrated()` call.

### `pointer.js`

Same shape as `createGyroSource` — exposes `onTilt`, `startCalibrated`, `stop` — but driven by mouse events. Used on desktop and as the touch-drag fallback when iOS denies orientation permission.

### `mapping.js`

```
tiltToIndex({Δβ, Δγ}, baseRow01, baseCol01, sensitivityDeg, rows) → { row, col }
```
Pure function: applies the index formula and clamps. `baseRow01`/`baseCol01` are the normalized [0,1] positions captured at press time so re-press preserves the freeze position.

### `polaroid.js`

```
applyTiltVisual({Δβ, Δγ}, { tiltDamping, highlightIntensity }) → void
```
Updates the polaroid element's `transform`, `box-shadow`, and the `--shine-x` / `--shine-y` / `--shine-opacity` CSS variables. Call once per animation frame while pressing; call once with `{0,0}` on release to trigger the CSS transition back to neutral.

### `debug.js`

Renders the sensitivity / damping / highlight sliders on the left edge, persists values to `location.hash`, and exposes them as a reactive object that other modules read.

## Mapping Math

Using `S = sensitivityDeg` (default 20):

```
rowIndex01 = clamp(baseRow01 + Δβ / S, 0, 1)
colIndex01 = clamp(baseCol01 + Δγ / S, 0, 1)

row = round(rowIndex01 * 5)               // 0..5
col = floor(colIndex01 * rows[row].photos.length)
col = clamp(col, 0, rows[row].photos.length - 1)
```

`baseRow01 = pressedRowIndex / 5` and `baseCol01 = pressedCol / (rowLen - 1)` are captured the moment `pressstart` fires, so re-pressing without moving keeps the same photo and the new neutral becomes the current device orientation.

## Visual Transform Math

Using `D = tiltDamping` (default 0.4) and `I = highlightIntensity` (default 0.5):

```
polaroid.transform =
  rotateX(-Δβ * D deg) rotateY(Δγ * D deg)

shineX = 50 - Δγ * 1.5     // %
shineY = 30 - Δβ * 1.5     // %
shineOpacity = 0.35 + min(0.4, (|Δβ| + |Δγ|) * 0.015) * (I / 0.5)

shadowOffsetX = -Δγ * 0.6  px
shadowOffsetY =  12 + Δβ * 0.4  px

box-shadow: ${shadowOffsetX}px ${shadowOffsetY}px 40px rgba(0,0,0,0.55),
            ${shadowOffsetX/3}px ${shadowOffsetY/4}px 6px rgba(0,0,0,0.4)
```

The polaroid sits inside a parent with `perspective: 1200px`. The specular highlight is a `radial-gradient` on a `::after` overlay with `mix-blend-mode: screen`.

On press release, all of the above transition back to neutral over 300 ms `ease-out`.

## Permission Flow

1. Page load → call `probePermission()`. The probe attaches a `deviceorientation` listener for 500 ms; if any event arrives with non-null β or γ, resolve `'granted'`.
2. If `'granted'`: red circle renders in `idle` state and is immediately usable. No dialog.
3. If `'unknown'`: red circle still renders in `idle` state. The first `pressstart` handler awaits `ensurePermission()` before subscribing to `gyro.js`.
   - If `requestPermission()` returns `'granted'`: subscribe and proceed.
   - If `'denied'`: fall back to `pointer.js` driven by touch events on the polaroid surface; render the red circle in its `denied` state.
4. Browsers without `requestPermission` (Android Chrome, etc.) skip step 3 entirely.

## Red Circle UX (mobile only)

- Position: `position: fixed; right: 24px; bottom: 24px`
- Diameter: 80 px
- Style: `border: 2px dashed #d34d4d; background: rgba(211,77,77,0.08); border-radius: 50%`
- Content: a small icon (crossed tilt arrows or a 3-by-3 dot grid) plus 11px text label `按住傾斜` below it
- States:
  - **idle** — 0.7→1.0 opacity breathing loop, 2 s
  - **active** — solid red border, soft red glow, breathing stops
  - **denied** — dashed border desaturates, icon switches to a finger-drag glyph

Hidden on desktop (where `pointer.js` runs against the whole canvas).

## Debug Slider (temporary)

Vertical strip on the left edge, present on both mobile and desktop during tuning:

- Sensitivity range — ±10° to ±40° (default ±20°)
- Tilt damping — 0.0 to 1.0 (default 0.4)
- Highlight intensity — 0.0 to 1.0 (default 0.5)

Values persist in `location.hash` (`#s=20&d=0.4&h=0.5`) so reloads keep the user's last setting. Once the values are settled the slider is removed and the constants hard-coded into the relevant modules.

## Tunable Constants Summary

| Constant | Default | Owner |
|---|---|---|
| `SENSITIVITY_DEG` | 20 | `mapping.js` |
| `TILT_DAMPING` | 0.4 | `polaroid.js` |
| `HIGHLIGHT_INTENSITY` | 0.5 | `polaroid.js` |
| `EMA_ALPHA` | 0.18 | `gyro.js` |
| `IDLE_TRANSITION_MS` | 300 | CSS |

## Out of Scope

- Animation between rows (e.g., a vertical scroll feel). Hard-cut only.
- Sound / haptics on transition.
- Persisting the user's last viewed photo across reloads.
- Production hosting / deployment configuration.
- Removing or rewriting `poc/`. The existing PoC stays as historical reference.

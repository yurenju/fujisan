// Fetches photos.json + alignments.json, denormalizes alignment matrices,
// and creates two <img> elements per photo: a 200×200 LQIP placeholder
// that stays mounted (visibility:hidden when not current) and a full-size
// hi-res img that's display:none and only painted while current.
//
// The placeholder layer keeps a decoded fallback alive for every photo
// (~20MB total) — when the user jumps to a row whose hi-res bitmap iOS
// Safari has evicted, the thumb appears immediately instead of a flash.
//
// The first photo's hi-res is fetched synchronously so the caller can
// show the scene; the rest stream in via N parallel background workers.

const CONCURRENCY = 6;
const HI_MAX_SIDE = 1568;  // long-side pixels in app/images/*.webp
const LO_MAX_SIDE = 200;   // long-side pixels in app/images-thumb/*.webp
const LO_SCALE = HI_MAX_SIDE / LO_MAX_SIDE;  // CSS scale to make a thumb
                                              // render at the hi-res box.

export async function loadAll({
  stage,
  photosUrl = 'data/photos.json',
  alignmentsUrl = 'data/alignments.json',
  onProgress,
  onPhotoLoaded,
} = {}) {
  const [photos, alignmentsRaw] = await Promise.all([
    fetch(photosUrl).then(r => r.json()),
    fetch(alignmentsUrl).then(r => r.json()),
  ]);

  const K = alignmentsRaw.calibration_unit_px || HI_MAX_SIDE;
  const items = {};
  for (const [name, r] of Object.entries(alignmentsRaw.items || {})) {
    if (!r.matrix) continue;
    const [a, b, txN] = r.matrix[0];
    const [c, d, tyN] = r.matrix[1];
    items[name] = { matrix: [[a, b, txN * K], [c, d, tyN * K]] };
  }
  const alignment = { calibration_unit_px: K, items };

  const ordered = [];
  for (const row of photos.rows) for (const f of row.photos) ordered.push(f);

  const imgByFile = {};
  for (const file of ordered) {
    const lo = createLayer(items[file], { thumb: true });
    const hi = createLayer(items[file], { thumb: false });
    stage.appendChild(lo);
    stage.appendChild(hi);
    imgByFile[file] = { lo, hi };
  }

  // Synchronously load the first photo's hi-res so the caller can show
  // the scene; its thumb loads in the background too.
  let loaded = 0;
  const total = ordered.length;
  const first = ordered[0];
  await assignSrc(imgByFile[first].hi, `images/${first}`);
  imgByFile[first].hi.style.display = '';
  loaded++;
  onProgress?.(loaded, total);

  // Background workers fetch the rest in row-major order. Each iteration
  // loads the lo first (much smaller, ~1.7KB) and then the hi, so by the
  // time hi is ready for a given file, its placeholder is already in
  // memory as a fallback.
  const queue = ordered.slice(1);
  const startWorker = async () => {
    while (queue.length) {
      const file = queue.shift();
      if (!file) return;
      try { await assignSrc(imgByFile[file].lo, `images-thumb/${file}`); }
      catch { /* swallow */ }
      try { await assignSrc(imgByFile[file].hi, `images/${file}`); }
      catch { /* swallow */ }
      loaded++;
      onProgress?.(loaded, total);
      onPhotoLoaded?.(file);
    }
  };
  // Fire and forget; do not block loadAll's caller.
  Promise.all(Array.from({ length: CONCURRENCY }, startWorker));

  // Also kick off the first photo's thumb in the background — it's not
  // needed for the first paint (hi is already up) but we want it decoded
  // before the user navigates away and back.
  assignSrc(imgByFile[first].lo, `images-thumb/${first}`);

  return { rows: photos.rows, alignment, imgByFile };
}

function createLayer(item, { thumb }) {
  const img = document.createElement('img');
  img.style.position = 'absolute';
  img.style.top = '0';
  img.style.left = '0';
  img.style.transformOrigin = '0 0';
  // Don't lock width/height — the source WebPs are aspect-preserved
  // (long side 1568 for hi, 200 for thumb). The alignment matrix was
  // computed against the hi-res natural size, so we apply it as-is to
  // hi and scale it up by LO_SCALE for thumb (its natural size is
  // 1/LO_SCALE × hi's natural size, uniform on both axes).
  if (thumb) {
    // Thumbs stay in the render tree always (visibility, not display).
    // iOS Safari evicts bitmaps of detached display:none images; keeping
    // them in layout preserves their decoded form (only ~160KB each).
    img.style.visibility = 'hidden';
    img.style.zIndex = '1';
  } else {
    img.style.display = 'none';
    img.style.willChange = 'transform';
    img.style.zIndex = '2';
  }
  if (item && item.matrix) {
    const [[a, b, tx], [c, d, ty]] = item.matrix;
    const s = thumb ? LO_SCALE : 1;
    img.style.transform = `matrix(${a*s}, ${c*s}, ${b*s}, ${d*s}, ${tx}, ${ty})`;
  }
  return img;
}

function assignSrc(img, url) {
  return new Promise((resolve) => {
    img.onload = () => resolve();
    img.onerror = () => resolve();
    img.src = url;
  });
}

export function showPhoto(imgByFile, currentFile, nextFile) {
  if (currentFile && imgByFile[currentFile]) {
    imgByFile[currentFile].hi.style.display = 'none';
    imgByFile[currentFile].lo.style.visibility = 'hidden';
  }
  if (imgByFile[nextFile]) {
    imgByFile[nextFile].lo.style.visibility = 'visible';
    imgByFile[nextFile].hi.style.display = '';
  }
  return nextFile;
}

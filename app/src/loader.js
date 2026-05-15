// Fetches photos.json + alignments.json, denormalizes alignment matrices,
// creates a hidden <img> per referenced file with its alignment transform.
// The first photo is fetched synchronously so the UI has something to show
// before returning; the rest are loaded by N parallel background workers
// and emit onProgress(loaded, total) per completion.

const CONCURRENCY = 6;

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

  const K = alignmentsRaw.calibration_unit_px || 1568;
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
    const img = document.createElement('img');
    img.style.display = 'none';
    img.style.position = 'absolute';
    img.style.top = '0';
    img.style.left = '0';
    img.style.transformOrigin = '0 0';
    img.style.willChange = 'transform';
    const item = items[file];
    if (item) {
      const [[a, b, tx], [c, d, ty]] = item.matrix;
      img.style.transform = `matrix(${a}, ${c}, ${b}, ${d}, ${tx}, ${ty})`;
    }
    stage.appendChild(img);
    imgByFile[file] = img;
  }

  // Synchronously load the first photo so the caller can show it immediately.
  let loaded = 0;
  const total = ordered.length;
  await assignSrc(imgByFile[ordered[0]], `images/${ordered[0]}`);
  loaded++;
  onProgress?.(loaded, total);

  // Background workers fetch the rest in row-major order.
  const queue = ordered.slice(1);
  const startWorker = async () => {
    while (queue.length) {
      const file = queue.shift();
      if (!file) return;
      try { await assignSrc(imgByFile[file], `images/${file}`); }
      catch { /* swallow — img.onerror still resolves */ }
      loaded++;
      onProgress?.(loaded, total);
      onPhotoLoaded?.(file);
    }
  };
  // Fire and forget; do not block loadAll's caller.
  Promise.all(Array.from({ length: CONCURRENCY }, startWorker));

  return { rows: photos.rows, alignment, imgByFile };
}

function assignSrc(img, url) {
  return new Promise((resolve) => {
    img.onload = () => resolve();
    img.onerror = () => resolve();
    img.src = url;
  });
}

export function showPhoto(imgByFile, currentFile, nextFile) {
  if (currentFile && imgByFile[currentFile]) imgByFile[currentFile].style.display = 'none';
  if (imgByFile[nextFile]) imgByFile[nextFile].style.display = '';
  return nextFile;
}

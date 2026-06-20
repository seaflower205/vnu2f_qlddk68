// ============================================================
// spatial_index.js — Grid spatial index nhẹ cho lớp phụ
// ============================================================

export function createSpatialIndex(items, bbox, options = {}) {
  const validItems = items.filter(item => item?.feature?._bbox);
  if (typeof globalThis.RBush === "function") {
    const tree = new globalThis.RBush(options.maxEntries || 12);
    const indexedItems = validItems.map(item => {
      const [minX, minY, maxX, maxY] = item.feature._bbox;
      return { minX, minY, maxX, maxY, item };
    });
    tree.load(indexedItems);
    return {
      type: "rbush",
      bbox,
      tree,
      items: validItems,
    };
  }

  const index = {
    type: "grid",
    bbox,
    cellSize: chooseCellSize(validItems, bbox, options),
    cells: new Map(),
    items: validItems,
  };

  for (const item of validItems) {
    forEachCell(item.feature._bbox, index.cellSize, (cx, cy) => {
      const key = `${cx}:${cy}`;
      let bucket = index.cells.get(key);
      if (!bucket) {
        bucket = [];
        index.cells.set(key, bucket);
      }
      bucket.push(item);
    });
  }

  return index;
}

export function querySpatialIndex(index, bbox, options = {}) {
  if (!index || !bbox) return [];
  const padding = Number(options.padding) || 0;
  const expanded = [
    bbox[0] - padding,
    bbox[1] - padding,
    bbox[2] + padding,
    bbox[3] + padding,
  ];
  if (index.type === "rbush" && index.tree) {
    return index.tree.search({
      minX: expanded[0],
      minY: expanded[1],
      maxX: expanded[2],
      maxY: expanded[3],
    }).map(entry => entry.item);
  }

  const seen = new Set();
  const result = [];
  forEachCell(expanded, index.cellSize, (cx, cy) => {
    const bucket = index.cells.get(`${cx}:${cy}`);
    if (!bucket) return;
    for (const item of bucket) {
      if (seen.has(item)) continue;
      seen.add(item);
      if (bboxIntersects(item.feature._bbox, expanded)) result.push(item);
    }
  });
  return result;
}

export function bboxIntersects(a, b) {
  if (!a || !b) return true;
  return !(a[2] < b[0] || a[0] > b[2] || a[3] < b[1] || a[1] > b[3]);
}

function chooseCellSize(items, bbox, options) {
  const requested = Number(options.cellSize);
  if (Number.isFinite(requested) && requested > 0) return requested;
  if (!items.length || !bbox) return 1;

  const width = Math.max(bbox[2] - bbox[0], 1);
  const height = Math.max(bbox[3] - bbox[1], 1);
  const targetCells = Math.max(16, Math.sqrt(items.length) * 2.5);
  return Math.max(Math.min(width, height) / targetCells, Math.max(width, height) / 320);
}

function forEachCell(bbox, cellSize, cb) {
  const minX = Math.floor(bbox[0] / cellSize);
  const minY = Math.floor(bbox[1] / cellSize);
  const maxX = Math.floor(bbox[2] / cellSize);
  const maxY = Math.floor(bbox[3] / cellSize);
  for (let cx = minX; cx <= maxX; cx++) {
    for (let cy = minY; cy <= maxY; cy++) cb(cx, cy);
  }
}

// ============================================================
// geo.js — Tính toán hình học (BBox, Point-in-Polygon)
// ============================================================

export function polygonsOf(feature) {
  const g = feature.geometry || {};
  if (g.type === "Polygon") return [g.coordinates || []];
  if (g.type === "MultiPolygon") return g.coordinates || [];
  return [];
}

export function ringsOf(feature) { return polygonsOf(feature).flat(); }

export function isFiniteBBox(bbox) {
  return Array.isArray(bbox) && bbox.length === 4 && bbox.every(v => Number.isFinite(Number(v)));
}

export function computeFeatureBBox(feature) {
  const bbox = [Infinity, Infinity, -Infinity, -Infinity];
  for (const ring of ringsOf(feature)) {
    for (const [x, y] of ring) {
      bbox[0] = Math.min(bbox[0], x); bbox[1] = Math.min(bbox[1], y);
      bbox[2] = Math.max(bbox[2], x); bbox[3] = Math.max(bbox[3], y);
    }
  }
  feature._bbox = bbox[0] === Infinity ? [0,0,0,0] : bbox;
}

export function computeCollectionBBox(features) {
  const bbox = [Infinity, Infinity, -Infinity, -Infinity];
  for (const f of features) {
    computeFeatureBBox(f);
    const b = f._bbox;
    if (!isFiniteBBox(b) || b[0] === b[2] || b[1] === b[3]) continue;
    bbox[0] = Math.min(bbox[0], b[0]); bbox[1] = Math.min(bbox[1], b[1]);
    bbox[2] = Math.max(bbox[2], b[2]); bbox[3] = Math.max(bbox[3], b[3]);
  }
  return bbox[0] === Infinity ? null : bbox;
}

export function pointInFeature(point, feature) {
  const b = feature._bbox;
  if (point.x < b[0] || point.x > b[2] || point.y < b[1] || point.y > b[3]) return false;
  return polygonsOf(feature).some(polygon => {
    let inside = false;
    for (const ring of polygon) {
      for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        const xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
        if (yi > point.y !== yj > point.y && point.x < ((xj - xi) * (point.y - yi)) / (yj - yi || 1e-12) + xi)
          inside = !inside;
      }
    }
    return inside;
  });
}

// ============================================================
// worker.js — Web Worker for parsing and computing BBox
// ============================================================

self.onmessage = async function(e) {
  const { dataUrl } = e.data;
  try {
    const resp = await fetch(dataUrl);
    if (!resp.ok) {
      self.postMessage({ type: 'error', error: resp.statusText });
      return;
    }
    const data = await resp.json();
    const features = data.features || [];
    const contextLayers = data.context_layers || [];
    
    // Compute feature bboxes
    const bbox = [Infinity, Infinity, -Infinity, -Infinity];
    for (let i = 0; i < features.length; i++) {
      const f = features[i];
      f._webgisIndex = i;
      
      // Compute single feature BBox
      const featureBBox = [Infinity, Infinity, -Infinity, -Infinity];
      const g = f.geometry || {};
      let polygons = [];
      if (g.type === "Polygon") {
        polygons = [g.coordinates || []];
      } else if (g.type === "MultiPolygon") {
        polygons = g.coordinates || [];
      }
      
      const rings = polygons.flat();
      for (let r = 0; r < rings.length; r++) {
        const ring = rings[r];
        for (let p = 0; p < ring.length; p++) {
          const pt = ring[p];
          const x = pt[0];
          const y = pt[1];
          if (x < featureBBox[0]) featureBBox[0] = x;
          if (y < featureBBox[1]) featureBBox[1] = y;
          if (x > featureBBox[2]) featureBBox[2] = x;
          if (y > featureBBox[3]) featureBBox[3] = y;
        }
      }
      f._bbox = featureBBox[0] === Infinity ? [0, 0, 0, 0] : featureBBox;
      
      const b = f._bbox;
      if (b[0] !== Infinity && b[0] !== b[2] && b[1] !== b[3]) {
        if (b[0] < bbox[0]) bbox[0] = b[0];
        if (b[1] < bbox[1]) bbox[1] = b[1];
        if (b[2] > bbox[2]) bbox[2] = b[2];
        if (b[3] > bbox[3]) bbox[3] = b[3];
      }
    }
    
    const collectionBBox = bbox[0] === Infinity ? null : bbox;
    
    self.postMessage({
      type: 'success',
      features: features,
      contextLayers: contextLayers,
      collectionBBox: collectionBBox,
      collection: {
        type: data.type,
        name: data.name,
        crs: data.crs,
        metadata: data.metadata,
        context_layers: contextLayers
      }
    });
  } catch (err) {
    self.postMessage({ type: 'error', error: err.message });
  }
};

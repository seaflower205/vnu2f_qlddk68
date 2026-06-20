// ============================================================
// map.js — Canvas transform + Map rendering
// ============================================================

import { state, isLightMode, landCode, landColor, selectedBasemap } from "../store.js";
import { polygonsOf } from "../utils/geo.js";
import { bboxIntersects, querySpatialIndex } from "../utils/spatial_index.js";
import * as maplibreAdapter from "./maplibre_adapter.js";

let mapLibreActive = false;
export function isMapLibreActive() { return mapLibreActive; }
export function setMapLibreActive(v) { mapLibreActive = v; }


const TILE_SIZE = 256;
const MERCATOR_LIMIT = 20037508.342789244;
const tileCache = new Map();
const tileLoading = new Set();
let tileRedrawPending = false;

function scheduleTileRedraw(ctx, canvas) {
  if (tileRedrawPending) return;
  tileRedrawPending = true;
  requestAnimationFrame(() => {
    tileRedrawPending = false;
    draw(ctx, canvas);
  });
}

/* ---------- Transform ---------- */
export function baseTransform(canvas) {
  if (!state.bbox) return { minX: 0, minY: 0, maxY: 0, scale: 1, originX: 0, originY: 0 };
  const [minX, minY, maxX, maxY] = state.bbox;
  const rect = canvas.getBoundingClientRect();
  const padding = 46;
  const worldW = Math.max(maxX - minX, 1e-9), worldH = Math.max(maxY - minY, 1e-9);
  const scale = Math.min((rect.width - padding * 2) / worldW, (rect.height - padding * 2) / worldH);
  const baseScale = Math.max(scale, 0.001);
  const mapW = worldW * baseScale * state.zoom, mapH = worldH * baseScale * state.zoom;
  return { minX, minY, maxY, scale: baseScale * state.zoom,
    originX: (rect.width - mapW) / 2 + state.panX,
    originY: (rect.height - mapH) / 2 + state.panY };
}

export function worldToScreen(x, y, canvas) {
  if (isMapLibreActive()) {
    const map = maplibreAdapter.getMapInstance();
    if (map) {
      const ll = worldToLonLat(x, y);
      const pixel = map.project([ll.lon, ll.lat]);
      return { x: pixel.x, y: pixel.y };
    }
  }
  const t = baseTransform(canvas);
  return { x: t.originX + (x - t.minX) * t.scale, y: t.originY + (t.maxY - y) * t.scale };
}

function worldToScreenWithTransform(x, y, t) {
  return { x: t.originX + (x - t.minX) * t.scale, y: t.originY + (t.maxY - y) * t.scale };
}

export function screenToWorld(x, y, canvas) {
  if (isMapLibreActive()) {
    const map = maplibreAdapter.getMapInstance();
    if (map) {
      const lngLat = map.unproject([x, y]);
      const w = lonLatToWorld(lngLat.lng, lngLat.lat);
      return { x: w.x, y: w.y };
    }
  }
  const t = baseTransform(canvas);
  return { x: (x - t.originX) / t.scale + t.minX, y: t.maxY - (y - t.originY) / t.scale };
}

export function worldToLonLat(x, y) {
  const lon = (x / MERCATOR_LIMIT) * 180;
  const lat = (Math.atan(Math.exp((y / MERCATOR_LIMIT) * Math.PI)) * 360) / Math.PI - 90;
  return { lon, lat };
}

/* ---------- Drawing ---------- */
function hasWebMercatorData() {
  return state.collection?.metadata?.map_crs === "EPSG:3857";
}

function tileZoomForScale(scale) {
  const z = Math.round(Math.log2((scale * MERCATOR_LIMIT * 2) / TILE_SIZE));
  return Math.max(3, Math.min(20, z));
}

function tileBounds(x, y, z) {
  const resolution = (MERCATOR_LIMIT * 2) / (TILE_SIZE * 2 ** z);
  return {
    minX: x * TILE_SIZE * resolution - MERCATOR_LIMIT,
    maxX: (x + 1) * TILE_SIZE * resolution - MERCATOR_LIMIT,
    maxY: MERCATOR_LIMIT - y * TILE_SIZE * resolution,
    minY: MERCATOR_LIMIT - (y + 1) * TILE_SIZE * resolution,
  };
}

function drawBasemap(ctx, canvas) {
  const basemap = selectedBasemap();
  if (!hasWebMercatorData() || !basemap.url) return false;
  const rect = canvas.getBoundingClientRect();
  const t = baseTransform(canvas);
  const z = Math.max(basemap.zmin ?? 0, Math.min(basemap.zmax ?? 22, tileZoomForScale(t.scale)));
  const resolution = (MERCATOR_LIMIT * 2) / (TILE_SIZE * 2 ** z);
  const nw = screenToWorld(0, 0, canvas);
  const se = screenToWorld(rect.width, rect.height, canvas);
  // Tải thừa ra 1 mảnh bản đồ ở các rìa lề màn hình (buffer = 1) để khi pan kéo bản đồ không bị xuất hiện khoảng trắng/đen
  const bufferTiles = 1;
  const minTileX = Math.floor((Math.min(nw.x, se.x) + MERCATOR_LIMIT) / (TILE_SIZE * resolution)) - bufferTiles;
  const maxTileX = Math.floor((Math.max(nw.x, se.x) + MERCATOR_LIMIT) / (TILE_SIZE * resolution)) + bufferTiles;
  const minTileY = Math.floor((MERCATOR_LIMIT - Math.max(nw.y, se.y)) / (TILE_SIZE * resolution)) - bufferTiles;
  const maxTileY = Math.floor((MERCATOR_LIMIT - Math.min(nw.y, se.y)) / (TILE_SIZE * resolution)) + bufferTiles;
  const tileMax = 2 ** z;
  let drewAny = false;

  // Giới hạn tải bản đồ nền xung quanh khu vực dự án (đệm rộng 10km) để chống tải thừa toàn thế giới gây lag
  let activeBBox = null;
  if (state.bbox) {
    const pad = 10000; // Đệm 10km đủ rộng để người dùng zoom/pan mượt mà mà không thấy cạnh đen
    activeBBox = [state.bbox[0] - pad, state.bbox[1] - pad, state.bbox[2] + pad, state.bbox[3] + pad];
  }

  for (let x = minTileX; x <= maxTileX; x++) {
    const wrappedX = ((x % tileMax) + tileMax) % tileMax;
    for (let y = minTileY; y <= maxTileY; y++) {
      if (y < 0 || y >= tileMax) continue;
      
      const bounds = tileBounds(x, y, z);
      
      // Bỏ qua các mảnh bản đồ nằm ngoài vùng đệm 10km của dự án
      if (activeBBox) {
        if (bounds.maxX < activeBBox[0] || bounds.minX > activeBBox[2] || bounds.maxY < activeBBox[1] || bounds.minY > activeBBox[3]) {
          continue;
        }
      }
      
      const tilePath = `${z}/${wrappedX}/${y}`;
      const key = `${basemap.id}/${tilePath}`;
      const p1 = worldToScreen(bounds.minX, bounds.maxY, canvas);
      const p2 = worldToScreen(bounds.maxX, bounds.minY, canvas);
      const img = tileCache.get(key);
      if (img?.complete && img.naturalWidth > 0) {
        ctx.drawImage(img, p1.x, p1.y, p2.x - p1.x, p2.y - p1.y);
        drewAny = true;
      } else if (!tileLoading.has(key)) {
        tileLoading.add(key);
        const tile = new Image();
        tile.crossOrigin = "anonymous";
        tile.onload = () => { tileCache.set(key, tile); tileLoading.delete(key); scheduleTileRedraw(ctx, canvas); };
        tile.onerror = () => tileLoading.delete(key);
        tile.src = basemapTileUrl(basemap, wrappedX, y, z);
      }
    }
  }
  return drewAny;
}

function basemapTileUrl(basemap, x, y, z) {
  const subdomains = basemap.subdomains || ["a"];
  const subdomain = subdomains[Math.abs(x + y + z) % subdomains.length];
  return basemap.url
    .replace(/\{s\}/g, subdomain)
    .replace(/\{x\}/g, x)
    .replace(/\{y\}/g, y)
    .replace(/\{z\}/g, z)
    .replace(/\{q\}/g, quadKey(x, y, z));
}

function quadKey(x, y, z) {
  let key = "";
  for (let i = z; i > 0; i--) {
    let digit = 0;
    const mask = 1 << (i - 1);
    if ((x & mask) !== 0) digit += 1;
    if ((y & mask) !== 0) digit += 2;
    key += digit;
  }
  return key;
}

function contextGeometries(feature) {
  const g = feature.geometry || {};
  if (g.type === "Point") return [[g.coordinates]];
  if (g.type === "MultiPoint") return [g.coordinates || []];
  if (g.type === "LineString") return [g.coordinates || []];
  if (g.type === "MultiLineString") return g.coordinates || [];
  if (g.type === "Polygon") return g.coordinates || [];
  if (g.type === "MultiPolygon") return (g.coordinates || []).flat();
  return [];
}

function contextLabel(feature) {
  return String(feature.properties?.webgis_label || "").trim();
}

export function visibleWorldBBox(canvas) {
  const rect = canvas.getBoundingClientRect();
  const nw = screenToWorld(0, 0, canvas);
  const se = screenToWorld(rect.width, rect.height, canvas);
  return [
    Math.min(nw.x, se.x),
    Math.min(nw.y, se.y),
    Math.max(nw.x, se.x),
    Math.max(nw.y, se.y),
  ];
}

function shouldDrawLabel(canvas, kind) {
  const t = baseTransform(canvas);
  if (kind === "cafe" || kind === "school" || kind === "food" || kind === "point") return t.scale > 0.045 || state.zoom > 4;
  if (kind === "place" || kind === "area") return t.scale > 0.025 || state.zoom > 2.2;
  return t.scale > 0.018 || state.zoom > 1.6;
}

function shouldDrawPoint(kind) {
  if (kind === "cafe" || kind === "school" || kind === "food" || kind === "point") return state.zoom > 1.5;
  return true;
}

function createLabelBudget() {
  return {
    boxes: [],
    max: state.zoom > 4 ? 120 : state.zoom > 2 ? 70 : 35,
  };
}

function drawContextLine(ctx, canvas, feature, labelBudget) {
  const color = feature.properties?.webgis_color || "#f97316";
  const kind = feature.properties?.webgis_kind || "";
  const label = shouldDrawLabel(canvas, kind) ? contextLabel(feature) : "";
  let labelPoint = null;
  ctx.save();
  ctx.lineWidth = 2.4;
  ctx.strokeStyle = color;
  ctx.globalAlpha = 0.88;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  for (const line of contextGeometries(feature)) {
    ctx.beginPath();
    line.forEach(([x, y], index) => {
      const pt = worldToScreen(x, y, canvas);
      if (index === 0) ctx.moveTo(pt.x, pt.y); else ctx.lineTo(pt.x, pt.y);
    });
    ctx.stroke();
    if (!labelPoint) labelPoint = lineLabelPoint(line);
  }
  ctx.restore();
  if (label && labelPoint) {
    const pt = worldToScreen(labelPoint[0], labelPoint[1], canvas);
    drawLabel(ctx, label, pt.x + 6, pt.y - 6, color, labelBudget);
  }
}

function drawContextPolygon(ctx, canvas, feature, labelBudget) {
  const color = feature.properties?.webgis_color || "#22c55e";
  const kind = feature.properties?.webgis_kind || "area";
  const label = shouldDrawLabel(canvas, kind) ? contextLabel(feature) : "";
  let labelPoint = null;
  ctx.save();
  ctx.fillStyle = color;
  ctx.strokeStyle = color;
  ctx.globalAlpha = 0.14;
  ctx.beginPath();
  for (const ring of contextGeometries(feature)) {
    ring.forEach(([x, y], index) => {
      const pt = worldToScreen(x, y, canvas);
      if (index === 0) ctx.moveTo(pt.x, pt.y); else ctx.lineTo(pt.x, pt.y);
    });
    ctx.closePath();
    if (!labelPoint) labelPoint = ringLabelPoint(ring);
  }
  ctx.fill("evenodd");
  ctx.globalAlpha = 0.45;
  ctx.lineWidth = 1.2;
  ctx.stroke();
  ctx.restore();
  if (label && labelPoint) {
    const pt = worldToScreen(labelPoint[0], labelPoint[1], canvas);
    drawLabel(ctx, label, pt.x + 6, pt.y - 6, color, labelBudget);
  }
}

function lineLabelPoint(line) {
  if (!line?.length) return null;
  if (line.length === 1) return line[0];
  let total = 0;
  for (let i = 1; i < line.length; i++) total += Math.hypot(line[i][0] - line[i - 1][0], line[i][1] - line[i - 1][1]);
  const half = total / 2;
  let walked = 0;
  for (let i = 1; i < line.length; i++) {
    const a = line[i - 1], b = line[i];
    const segment = Math.hypot(b[0] - a[0], b[1] - a[1]);
    if (walked + segment >= half) {
      const t = segment ? (half - walked) / segment : 0;
      return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
    }
    walked += segment;
  }
  return line[Math.floor(line.length / 2)];
}

function ringLabelPoint(ring) {
  if (!ring?.length) return null;
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const [x, y] of ring) {
    minX = Math.min(minX, x); minY = Math.min(minY, y);
    maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
  }
  return minX === Infinity ? null : [(minX + maxX) / 2, (minY + maxY) / 2];
}

function drawPointSymbol(ctx, x, y, kind, color) {
  ctx.save();
  ctx.translate(x, y);
  ctx.fillStyle = "#ffffff";
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  const VN_LAND_KIND_MAP = {
    'ONT': 'residential',
    'CLN': 'garden',
    'LUC': 'rice',
    'NTS': 'aquaculture',
    'TMD': 'commercial',
    'DGD': 'education',
    'YTE': 'medical',
    'TSC': 'office',
    'SKC': 'industrial',
    'CSD': 'public',
  };
  const normalizedKind = VN_LAND_KIND_MAP[kind] || kind;

  if (normalizedKind === "school" || normalizedKind === "education") {
    ctx.beginPath();
    ctx.moveTo(0, -9); ctx.lineTo(9, -2); ctx.lineTo(9, 8); ctx.lineTo(-9, 8); ctx.lineTo(-9, -2);
    ctx.closePath(); ctx.fill(); ctx.stroke();
  } else if (normalizedKind === "food" || normalizedKind === "commercial") {
    ctx.beginPath(); ctx.arc(0, 0, 8, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(-3, -5); ctx.lineTo(-3, 5); ctx.moveTo(3, -5); ctx.lineTo(3, 5); ctx.stroke();
  } else if (normalizedKind === "cafe" || normalizedKind === "office") {
    ctx.beginPath(); ctx.roundRect(-8, -6, 13, 10, 3); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.arc(6, -1, 4, -Math.PI / 2, Math.PI / 2); ctx.stroke();
  } else {
    ctx.beginPath(); ctx.arc(0, 0, 7, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.arc(0, 0, 2.5, 0, Math.PI * 2); ctx.fillStyle = color; ctx.fill();
  }
  ctx.restore();
}

function drawContextPoint(ctx, canvas, feature, labelBudget) {
  const kind = feature.properties?.webgis_kind || "point";
  if (!shouldDrawPoint(kind)) return;
  const color = feature.properties?.webgis_color || "#7c3aed";
  const label = shouldDrawLabel(canvas, kind) ? contextLabel(feature) : "";
  for (const points of contextGeometries(feature)) {
    for (const [x, y] of points) {
      const pt = worldToScreen(x, y, canvas);
      drawPointSymbol(ctx, pt.x, pt.y, kind, color);
      if (label) drawLabel(ctx, label, pt.x + 11, pt.y - 11, color, labelBudget);
    }
  }
}

function drawLabel(ctx, text, x, y, color, budget) {
  if (budget && budget.boxes.length >= budget.max) return false;
  ctx.save();
  ctx.font = "600 12px Inter, system-ui, sans-serif";
  const width = ctx.measureText(text).width;
  const box = [x - 4, y - 14, x + width + 4, y + 4];
  if (budget?.boxes.some(existing => bboxIntersects(existing, box))) {
    ctx.restore();
    return false;
  }
  ctx.fillStyle = isLightMode ? "rgba(255,255,255,0.92)" : "rgba(9,9,11,0.74)";
  ctx.strokeStyle = isLightMode ? "rgba(0,0,0,0.12)" : "rgba(255,255,255,0.12)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.roundRect(x - 4, y - 14, width + 8, 18, 5);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = color || (isLightMode ? "#18181b" : "#fafafa");
  ctx.fillText(text, x, y);
  ctx.restore();
  budget?.boxes.push(box);
  return true;
}

function drawContextLayers(ctx, canvas) {
  const viewBBox = visibleWorldBBox(canvas);
  const indexedItems = state.contextIndex ? querySpatialIndex(state.contextIndex, viewBBox) : null;
  const items = indexedItems || (state.contextLayers || []).flatMap(layer => (layer.features || []).map(feature => ({ layer, feature })));
  const labelBudget = createLabelBudget();

  for (const item of items) {
    const feature = item.feature;
    if (!bboxIntersects(feature._bbox, viewBBox)) continue;
    const type = feature.geometry?.type || "";
    if (type.includes("Polygon")) drawContextPolygon(ctx, canvas, feature, labelBudget);
    else if (type.includes("LineString")) drawContextLine(ctx, canvas, feature, labelBudget);
  }
  for (const item of items) {
    const feature = item.feature;
    if (!bboxIntersects(feature._bbox, viewBBox)) continue;
    if ((feature.geometry?.type || "").includes("Point")) drawContextPoint(ctx, canvas, feature, labelBudget);
  }
}

function getFeatureHeight(feature) {
  const code = landCode(feature).toUpperCase();
  if (code.startsWith("ON") || code.startsWith("OD")) return 15; // ONT, ODT: Đất ở
  if (code.startsWith("SK") || code.startsWith("TM")) return 18; // SKC, TMD: Thương mại, sản xuất
  if (code.startsWith("TS") || code.startsWith("CQ")) return 12; // TSC, CQP: Trụ sở, công cộng
  if (code.startsWith("LU") || code.startsWith("BH") || code.startsWith("CL")) return 2.5; // LUC, BHK, CLN: Đất nông nghiệp
  if (code.startsWith("SO") || code.startsWith("MN")) return 0.2; // Sông ngòi, mặt nước
  return 7; // Khác
}

function shadeColor(hex, percent) {
  let num = parseInt(hex.replace("#", ""), 16);
  let amt = Math.round(2.55 * percent);
  let R = (num >> 16) + amt;
  let G = ((num >> 8) & 0x00ff) + amt;
  let B = (num & 0x0000ff) + amt;
  return (
    "#" +
    (
      0x1000000 +
      (R < 255 ? (R < 0 ? 0 : R) : 255) * 0x10000 +
      (G < 255 ? (G < 0 ? 0 : G) : 255) * 0x100 +
      (B < 255 ? (B < 0 ? 0 : B) : 255)
    )
      .toString(16)
      .slice(1)
  );
}

function drawFeature3D(ctx, canvas, feature, mode = "normal", t = baseTransform(canvas)) {
  const fill = landColor(landCode(feature));
  const height = getFeatureHeight(feature);
  
  if (height <= 0.5) {
    drawFeature2D(ctx, canvas, feature, mode, t);
    return;
  }
  
  for (const polygon of polygonsOf(feature)) {
    if (!polygon?.length) continue;
    const ring = polygon[0]; // Exterior boundary
    if (ring.length < 3) continue;
    
    const ptsBase = ring.map(pt => worldToScreenWithTransform(pt[0], pt[1], t));
    
    // Oblique projection offset calculation
    const h_px = height * t.scale * 0.45;
    const angle = 25 * Math.PI / 180; // 25 degree tilt
    const dx = h_px * Math.sin(angle);
    const dy = -h_px * Math.cos(angle);
    
    const ptsRoof = ptsBase.map(pt => ({
      x: pt.x + dx,
      y: pt.y + dy
    }));
    
    // 1. Draw side walls
    ctx.save();
    for (let i = 0; i < ring.length - 1; i++) {
      ctx.beginPath();
      ctx.moveTo(ptsBase[i].x, ptsBase[i].y);
      ctx.lineTo(ptsBase[i+1].x, ptsBase[i+1].y);
      ctx.lineTo(ptsRoof[i+1].x, ptsRoof[i+1].y);
      ctx.lineTo(ptsRoof[i].x, ptsRoof[i].y);
      ctx.closePath();
      
      const wallDx = ring[i+1][0] - ring[i][0];
      const wallDy = ring[i+1][1] - ring[i][1];
      const wallAngle = Math.atan2(wallDy, wallDx);
      const intensity = Math.round(22 * Math.sin(wallAngle)); // Shading from -22% to +22%
      
      try {
        ctx.fillStyle = shadeColor(fill, intensity);
      } catch (e) {
        ctx.fillStyle = fill;
      }
      
      const isFilteredOut = feature.properties?.qgis_filtered_out;
      ctx.globalAlpha = isFilteredOut ? 0.04 : (mode === "selected" ? 0.85 : mode === "hovered" ? 0.75 : 0.6);
      ctx.fill();
      
      ctx.strokeStyle = isFilteredOut ? "rgba(0,0,0,0.02)" : "rgba(0,0,0,0.15)";
      ctx.lineWidth = 0.5;
      ctx.stroke();
    }
    ctx.restore();
    
    // 2. Draw roof (supporting holes)
    ctx.save();
    ctx.beginPath();
    for (const r of polygon) {
      r.forEach((pt, idx) => {
        const pt2d = worldToScreenWithTransform(pt[0], pt[1], t);
        const rx = pt2d.x + dx;
        const ry = pt2d.y + dy;
        if (idx === 0) ctx.moveTo(rx, ry);
        else ctx.lineTo(rx, ry);
      });
      ctx.closePath();
    }
    
    const isFilteredOut = feature.properties?.qgis_filtered_out;
    ctx.fillStyle = mode === "selected" ? "#fcd34d" : fill;
    ctx.globalAlpha = isFilteredOut ? 0.05 : (mode === "selected" ? 0.9 : mode === "hovered" ? 0.8 : 0.55);
    ctx.fill("evenodd");
    
    ctx.strokeStyle = isFilteredOut ? "rgba(255,255,255,0.05)" : (mode === "selected" ? "#fcd34d" : mode === "hovered" ? "#60a5fa" : "rgba(255,255,255,0.4)");
    ctx.lineWidth = mode === "selected" ? 2.5 : mode === "hovered" ? 2 : 1;
    ctx.stroke();
    ctx.restore();
  }
}

function drawFeature2D(ctx, canvas, feature, mode = "normal", t = baseTransform(canvas)) {
  const fill = landColor(landCode(feature));
  ctx.beginPath();
  for (const polygon of polygonsOf(feature)) {
    for (const ring of polygon) {
      ring.forEach(([x, y], idx) => {
        const pt = worldToScreenWithTransform(x, y, t);
        if (idx === 0) ctx.moveTo(pt.x, pt.y); else ctx.lineTo(pt.x, pt.y);
      });
      ctx.closePath();
    }
  }
  
  const isFilteredOut = feature.properties?.qgis_filtered_out;
  ctx.fillStyle = mode === "selected" ? "#fcd34d" : fill;
  ctx.globalAlpha = isFilteredOut ? 0.05 : (mode === "selected" ? 0.85 : mode === "hovered" ? 0.7 : 0.45);
  ctx.fill("evenodd");
  ctx.globalAlpha = 1;
  ctx.lineWidth = mode === "selected" ? 2.5 : mode === "hovered" ? 2 : 1;
  const baseStroke = isLightMode ? "rgba(0,0,0,0.15)" : "rgba(255,255,255,0.15)";
  ctx.strokeStyle = isFilteredOut ? "rgba(0,0,0,0.02)" : (mode === "selected" ? "#fcd34d" : mode === "hovered" ? "#60a5fa" : baseStroke);
  if (isFilteredOut) {
    ctx.globalAlpha = 0.05;
  }
  ctx.stroke();
  ctx.globalAlpha = 1;
}

function drawFeature(ctx, canvas, feature, mode = "normal", t = baseTransform(canvas)) {
  if (state.view3d) {
    drawFeature3D(ctx, canvas, feature, mode, t);
  } else {
    drawFeature2D(ctx, canvas, feature, mode, t);
  }
}


export function draw(ctx, canvas) {
  if (!state.collection) return;
  const rect = canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, rect.width, rect.height);
  if (isMapLibreActive()) {
    // Chỉ clear để làm trong suốt canvas, vẽ đè các nét đo (nếu có)
    return;
  }
  ctx.fillStyle = isLightMode ? "#e5e7eb" : "#030712";
  ctx.fillRect(0, 0, rect.width, rect.height);
  drawBasemap(ctx, canvas);
  drawContextLayers(ctx, canvas);

  const t = baseTransform(canvas);
  const viewBBox = visibleWorldBBox(canvas);
  const visibleItems = state.featureIndex ? querySpatialIndex(state.featureIndex, viewBBox) : null;
  const visibleFeatures = visibleItems ? visibleItems.map(item => item.feature) : state.features;

  for (const f of visibleFeatures) {
    if (f !== state.selected && f !== state.hovered) drawFeature(ctx, canvas, f, "normal", t);
  }
  if (state.hovered && state.hovered !== state.selected) drawFeature(ctx, canvas, state.hovered, "hovered", t);
  if (state.selected) drawFeature(ctx, canvas, state.selected, "selected", t);
}

/* ---------- Navigation ---------- */
export function zoomToFeature(feature, canvas) {
  if (isMapLibreActive()) {
    maplibreAdapter.flyToFeature(feature);
    return;
  }
  if (!feature?._bbox) return;
  const [minX, minY, maxX, maxY] = feature._bbox;
  if (minX === maxX || minY === maxY) return;
  state.zoom = 1; state.panX = 0; state.panY = 0;
  const rect = canvas.getBoundingClientRect();
  const padding = Math.min(250, Math.max(120, Math.min(rect.width, rect.height) * 0.25));
  const [wMinX, wMinY, wMaxX, wMaxY] = state.bbox;
  const baseScale = Math.min((rect.width - 92) / (wMaxX - wMinX), (rect.height - 92) / (wMaxY - wMinY));
  const targetScale = Math.min((rect.width - padding * 2) / (maxX - minX), (rect.height - padding * 2) / (maxY - minY)) * 0.6;
  state.zoom = Math.max(1.2, Math.min(12, targetScale / baseScale));
  state.panX = 0; state.panY = 0;
  const sc = worldToScreen((minX + maxX) / 2, (minY + maxY) / 2, canvas);
  state.panX += rect.width / 2 - sc.x;
  state.panY += rect.height / 2 - sc.y;
}

export function zoomAt(factor, cx, cy, canvas, drawCb) {
  if (isMapLibreActive()) {
    // Zoom ở chế độ MapLibre được xử lý trực tiếp bởi chuột của MapLibre.
    return;
  }
  const before = screenToWorld(cx, cy, canvas);
  state.zoom = Math.max(0.45, Math.min(24, state.zoom * factor));
  const after = worldToScreen(before.x, before.y, canvas);
  state.panX += cx - after.x; state.panY += cy - after.y;
  drawCb();
}

export function resetView(drawCb) {
  if (isMapLibreActive()) {
    if (state.collection && state.collection.bbox) {
      const bbox = state.collection.bbox;
      const llMin = worldToLonLat(bbox[0], bbox[1]);
      const llMax = worldToLonLat(bbox[2], bbox[3]);
      const map = maplibreAdapter.getMapInstance();
      if (map) {
        map.fitBounds([[llMin.lon, llMin.lat], [llMax.lon, llMax.lat]], {
          padding: 50,
          duration: 1000
        });
      }
    }
    return;
  }
  state.zoom = 1; state.panX = 0; state.panY = 0; drawCb();
}

export function lonLatToWorld(lon, lat) {
  const x = (lon * MERCATOR_LIMIT) / 180;
  const y = Math.log(Math.tan(((90 + lat) * Math.PI) / 360)) / (Math.PI / MERCATOR_LIMIT);
  return { x, y };
}

export function zoomToCoordinate(lon, lat, canvas) {
  if (isMapLibreActive()) {
    maplibreAdapter.flyToCoordinate(lon, lat);
    return;
  }
  const w = lonLatToWorld(lon, lat);
  state.zoom = 12; // zoom in close
  state.panX = 0; state.panY = 0;
  const rect = canvas.getBoundingClientRect();
  const sc = worldToScreen(w.x, w.y, canvas);
  state.panX = rect.width / 2 - sc.x;
  state.panY = rect.height / 2 - sc.y;
}

// ============================================================
// app.js — Entry Point (ES Module)
// Kết nối store, map, chart, và thiết lập tất cả Event Listeners
// ============================================================

import { state, BASEMAPS, selectedBasemap, isLightMode, setLightMode, formatNumber, escapeHtml, prop, landCode, landColor, landGroup, featureTitle, featureArea, LAND_GROUPS } from "./store.js";
import { computeCollectionBBox, pointInFeature } from "./utils/geo.js";
import { createSpatialIndex, querySpatialIndex } from "./utils/spatial_index.js";
import { draw, worldToScreen, screenToWorld, worldToLonLat, lonLatToWorld, zoomToFeature, zoomAt, resetView, zoomToCoordinate, isMapLibreActive, setMapLibreActive, visibleWorldBBox } from "./map/map.js";
import * as maplibreAdapter from "./map/maplibre_adapter.js";
import { landSummary, groupSummary, drawDonut, sliceAt, animateChartSelection } from "./components/chart.js";
import { searchAddress, reverseGeocode, localFilterParcels } from "./search.js";
import { calculateDistance, calculateArea, loadTurf } from "./measure.js";
import { switchBasemap } from "./basemap.js";


const DATA_URL = `data/parcels.geojson?ts=${Date.now()}`;

// ---- DOM ----
const canvas   = document.querySelector("#mapCanvas");
const ctx      = canvas.getContext("2d");
const landChart   = document.querySelector("#landChart");
const chartCtx    = landChart.getContext("2d");
const groupChart  = document.querySelector("#groupChart");
const groupChartCtx = groupChart.getContext("2d");
const searchInput  = document.querySelector("#searchInput");
const searchModal       = document.querySelector("#searchModal");
const closeSearchModalBtn = document.querySelector("#closeSearchModal");
const modalSearchInput  = document.querySelector("#modalSearchInput");
const modalClearSearchBtn = document.querySelector("#modalClearSearch");
const resultList     = document.querySelector("#resultList");
const resultCount    = document.querySelector("#resultCount");
const modalResultList  = document.querySelector("#modalResultList");
const modalResultCount = document.querySelector("#modalResultCount");
const mapStatus  = document.querySelector("#mapStatus");
const coordStatus = document.querySelector("#coordStatus");
const themeToggle = document.querySelector("#themeToggle");
const basemapSelect = document.querySelector("#basemapSelect");

// ---- Tab System DOM ----
const tabBtns = document.querySelectorAll(".rail-tab-btn[data-tab]");
const tabPanels = document.querySelectorAll(".tab-panel");
const tabTitle = document.querySelector("#tabTitle");
const pillBtns = document.querySelectorAll(".pill-btn");
const landChartWrap = document.querySelector("#landChartWrap");
const groupChartWrap = document.querySelector("#groupChartWrap");
const detailsEmptyWrap = document.querySelector("#detailsEmptyWrap");
const detailsActiveWrap = document.querySelector("#detailsActiveWrap");
const zoomToParcelBtn = document.querySelector("#zoomToParcel");
const clearSelectionBtn = document.querySelector("#clearSelection");

// ---- Measurement state & drawing ----
let measureMode = null; // "dist" | "area" | null
let measurePoints = []; // [[x, y], ...] in Web Mercator
let mouseWorldPos = null; // {x, y}

function syncCanvasPointerEvents() {
  if (isMapLibreActive()) {
    if (measureMode) {
      canvas.style.pointerEvents = "auto";
    } else {
      canvas.style.pointerEvents = "none";
    }
  } else {
    canvas.style.pointerEvents = "auto";
  }
}

function drawMeasureOverlay() {
  if (!measureMode || measurePoints.length === 0) return;
  ctx.save();
  
  // Vẽ các đường nối
  ctx.beginPath();
  measurePoints.forEach((pt, idx) => {
    const scr = worldToScreen(pt[0], pt[1], canvas);
    if (idx === 0) ctx.moveTo(scr.x, scr.y);
    else ctx.lineTo(scr.x, scr.y);
  });
  
  // Vẽ đường nối nháp tới vị trí chuột
  if (mouseWorldPos) {
    const scrMouse = worldToScreen(mouseWorldPos.x, mouseWorldPos.y, canvas);
    ctx.lineTo(scrMouse.x, scrMouse.y);
  }
  
  if (measureMode === "area") {
    ctx.closePath();
    ctx.fillStyle = "rgba(96, 165, 250, 0.18)";
    ctx.fill();
  }
  
  ctx.strokeStyle = "#60a5fa";
  ctx.lineWidth = 2.5;
  ctx.setLineDash([6, 4]);
  ctx.stroke();
  
  // Vẽ các chấm điểm nút
  measurePoints.forEach((pt, idx) => {
    const scr = worldToScreen(pt[0], pt[1], canvas);
    ctx.beginPath();
    ctx.arc(scr.x, scr.y, 5, 0, Math.PI * 2);
    ctx.fillStyle = "#ffffff";
    ctx.fill();
    ctx.strokeStyle = "#3b82f6";
    ctx.lineWidth = 2;
    ctx.stroke();
  });
  
  ctx.restore();
}

function finishMeasurement() {
  if (measurePoints.length < 2) {
    cancelMeasurement();
    return;
  }
  
  let resultText = "";
  if (measureMode === "dist") {
    const dist = calculateDistance(measurePoints);
    resultText = dist >= 1000 ? `${(dist / 1000).toFixed(2)} km` : `${dist.toFixed(1)} m`;
    mapStatus.textContent = `Đo khoảng cách: ${resultText}`;
  } else if (measureMode === "area") {
    const area = calculateArea(measurePoints);
    resultText = area >= 10000 ? `${(area / 10000).toFixed(2)} ha` : `${area.toFixed(1)} m²`;
    mapStatus.textContent = `Đo diện tích: ${resultText}`;
  }
  
  measureMode = null;
  document.querySelector("#measureDist")?.classList.remove("active");
  document.querySelector("#measureArea")?.classList.remove("active");
  syncCanvasPointerEvents();
  redraw();
}

function cancelMeasurement() {
  measureMode = null;
  measurePoints = [];
  mouseWorldPos = null;
  document.querySelector("#measureDist")?.classList.remove("active");
  document.querySelector("#measureArea")?.classList.remove("active");
  mapStatus.textContent = "Đã hủy chế độ đo";
  syncCanvasPointerEvents();
  redraw();
}

// ---- Shorthand draw helpers ----
let redrawPending = false;
const redraw = () => {
  if (redrawPending) return;
  redrawPending = true;
  requestAnimationFrame(() => {
    redrawPending = false;
    draw(ctx, canvas);
    drawMeasureOverlay();
  });
};
const redrawNow = () => {
  redrawPending = false;
  draw(ctx, canvas);
  drawMeasureOverlay();
};
const drawLand    = () => drawDonut(landChart, chartCtx, landSummary(), "#chartTotal", undefined, "land");
const drawGroup   = () => { const s = groupSummary(); drawDonut(groupChart, groupChartCtx, s, "#groupChartTotal", s.length, "group"); };

// ---- Tab Switcher ----
function switchTab(tabId) {
  tabBtns.forEach(btn => {
    btn.classList.toggle("active", btn.dataset.tab === tabId);
  });
  tabPanels.forEach(panel => {
    panel.classList.toggle("active", panel.id === `panel-${tabId}`);
  });
  
  if (tabId === "dashboard") {
    tabTitle.textContent = "Tổng quan";
    updateSubtitle();
    // Re-render chart on tab activation to ensure dimensions match
    setTimeout(() => {
      resizeChart();
    }, 50);
  } else if (tabId === "search") {
    tabTitle.textContent = "Tìm kiếm";
    document.querySelector("#datasetName").textContent = "Tra cứu & lọc thửa đất nhanh";
  } else if (tabId === "details") {
    tabTitle.textContent = "Chi tiết thửa";
    document.querySelector("#datasetName").textContent = "Thông tin thuộc tính thửa đất";
  } else if (tabId === "share") {
    tabTitle.textContent = "Chia sẻ";
    document.querySelector("#datasetName").textContent = "Cấu hình chia sẻ bản đồ Internet";
    const shareBtn = document.getElementById("shareTabBtn");
    if (shareBtn && shareBtn.style.display !== "none") {
      fetch("api/share/status")
        .then(r => r.json())
        .then(data => {
          const uView = document.getElementById("share-active-view");
          const iView = document.getElementById("share-inactive-view");
          const lView = document.getElementById("share-loading-view");
          const urlInput = document.getElementById("txtShareUrl");
          const codeInput = document.getElementById("txtSharePasscode");
          if (data.active) {
            iView.style.display = "none";
            lView.style.display = "none";
            uView.style.display = "flex";
            urlInput.value = data.url;
            codeInput.value = data.passcode;
          } else {
            uView.style.display = "none";
            lView.style.display = "none";
            iView.style.display = "block";
          }
        })
        .catch(err => {});
    }
  }
}

function updateSubtitle() {
  if (!state.collection) return;
  const md = state.collection.metadata || {};
  const crs = md.source_crs || state.collection.crs?.properties?.name || md.crs || "VN-2000";
  const layerName = md.layer_name || state.collection.name || "Layer QGIS";
  const subtitleEl = document.querySelector("#datasetName");
  if (subtitleEl && document.querySelector(".rail-tab-btn[data-tab='dashboard']")?.classList.contains("active")) {
    subtitleEl.textContent = `${layerName} · ${crs}`;
  }
}

function basemapOptions(items) {
  return items.map(item => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.label)}</option>`).join("");
}

function initBasemapSelect() {
  if (!basemapSelect) return;
  const stable = BASEMAPS.filter(item => !item.experimental);
  const experimental = BASEMAPS.filter(item => item.experimental);
  basemapSelect.innerHTML = [
    `<optgroup label="Ổn định">${basemapOptions(stable)}</optgroup>`,
    `<optgroup label="Thử nghiệm">${basemapOptions(experimental)}</optgroup>`,
  ].join("");
  basemapSelect.value = state.basemapId;
  updateAttribution();
}

function updateAttribution() {
  const el = document.querySelector(".map-attribution");
  if (!el) return;
  const basemap = selectedBasemap();
  el.textContent = basemap.attribution || "";
  el.style.display = basemap.attribution ? "block" : "none";
}

// Tab button events
tabBtns.forEach(btn => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

// ---- Segmented control (Pill Switcher) ----
pillBtns.forEach(btn => {
  btn.addEventListener("click", () => {
    pillBtns.forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    const chartType = btn.dataset.chart;
    if (chartType === "land") {
      landChartWrap.style.display = "flex";
      groupChartWrap.style.display = "none";
    } else {
      landChartWrap.style.display = "none";
      groupChartWrap.style.display = "flex";
    }
    resizeChart(); // Resize và vẽ lại chart có kích thước thực khi được hiển thị
  });
});

// ---- Canvas sizing ----
function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width  = Math.max(1, Math.floor(rect.width * dpr));
  canvas.height = Math.max(1, Math.floor(rect.height * dpr));
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  if (isMapLibreActive()) {
    const map = maplibreAdapter.getMapInstance();
    if (map) map.resize();
  }
  redrawNow();
}
function resizeChart() {
  const dpr = window.devicePixelRatio || 1;
  
  if (landChartWrap.style.display !== "none") {
    const r1 = landChart.getBoundingClientRect();
    landChart.width  = Math.max(1, Math.floor(r1.width * dpr));
    landChart.height = Math.max(1, Math.floor(r1.height * dpr));
    chartCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
    drawLand();
  }
  
  if (groupChartWrap.style.display !== "none") {
    const r2 = groupChart.getBoundingClientRect();
    groupChart.width  = Math.max(1, Math.floor(r2.width * dpr));
    groupChart.height = Math.max(1, Math.floor(r2.height * dpr));
    groupChartCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
    drawGroup();
  }
}

// ---- Feature lookup ----
function featureAt(sx, sy) {
  const world = screenToWorld(sx, sy, canvas);
  const nw = screenToWorld(sx - 5, sy - 5, canvas);
  const se = screenToWorld(sx + 5, sy + 5, canvas);
  const queryBox = [
    Math.min(nw.x, se.x),
    Math.min(nw.y, se.y),
    Math.max(nw.x, se.x),
    Math.max(nw.y, se.y),
  ];
  const candidates = state.featureIndex
    ? querySpatialIndex(state.featureIndex, queryBox).map(item => item.feature)
    : state.features;
  for (let i = candidates.length - 1; i >= 0; i--) {
    if (pointInFeature(world, candidates[i])) return candidates[i];
  }
  return null;
}

// ---- Selection ----
function setSelected(feature, opts = {}) {
  state.selected = feature;
  updateDetails(feature);
  syncResultActive();
  if (isMapLibreActive()) {
    maplibreAdapter.setSelected(feature);
  }
  if (feature) {
    switchTab("details");
    if (opts.zoom !== false) zoomToFeature(feature, canvas);
  } else {
    // If details tab is open, we can stay there but it shows empty state
    // Or we can let them see the empty state
  }
  redraw();
}

// ---- Nearby context helpers ----
function contextFeatureItems() {
  return state.contextItems || [];
}

function geometryCoordinates(geometry) {
  const out = [];
  const visit = value => {
    if (!Array.isArray(value)) return;
    if (value.length >= 2 && Number.isFinite(Number(value[0])) && Number.isFinite(Number(value[1]))) {
      out.push([Number(value[0]), Number(value[1])]);
      return;
    }
    value.forEach(visit);
  };
  visit(geometry?.coordinates || []);
  return out;
}

function geometryCenter(feature) {
  if (feature?._bbox) {
    const [minX, minY, maxX, maxY] = feature._bbox;
    return { x: (minX + maxX) / 2, y: (minY + maxY) / 2 };
  }
  const coords = geometryCoordinates(feature?.geometry);
  if (!coords.length) return null;
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const [x, y] of coords) {
    minX = Math.min(minX, x); minY = Math.min(minY, y);
    maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
  }
  return { x: (minX + maxX) / 2, y: (minY + maxY) / 2 };
}

function computeGenericBBox(feature) {
  const coords = geometryCoordinates(feature?.geometry);
  if (!coords.length) return [0, 0, 0, 0];
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const [x, y] of coords) {
    minX = Math.min(minX, x); minY = Math.min(minY, y);
    maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
  }
  return [minX, minY, maxX, maxY];
}

function prepareContextLayers() {
  const items = [];
  const contextBBox = [Infinity, Infinity, -Infinity, -Infinity];
  for (const layer of state.contextLayers || []) {
    for (const feature of layer.features || []) {
      feature._bbox = computeGenericBBox(feature);
      contextBBox[0] = Math.min(contextBBox[0], feature._bbox[0]);
      contextBBox[1] = Math.min(contextBBox[1], feature._bbox[1]);
      contextBBox[2] = Math.max(contextBBox[2], feature._bbox[2]);
      contextBBox[3] = Math.max(contextBBox[3], feature._bbox[3]);
      items.push({ layer, feature });
    }
  }
  state.contextItems = items;
  state.contextIndex = createSpatialIndex(items, contextBBox[0] === Infinity ? null : contextBBox);
}

function contextLabel(item) {
  const props = item.feature.properties || {};
  return props.webgis_label || props.TEN_DUONG || props.TEN || props.name || item.layer.name || "";
}

function contextKind(item) {
  return item.feature.properties?.webgis_kind || item.layer.kind || item.layer.geometry_type || "context";
}

function contextGeometryType(item) {
  return item.layer.geometry_type || item.feature.geometry?.type || "";
}

function normalizedText(value) {
  return String(value || "").toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d");
}

function contextText(item) {
  return normalizedText(`${item.layer.name || ""} ${contextLabel(item)} ${Object.values(item.feature.properties || {}).join(" ")}`);
}

function isRoadContext(item) {
  const kind = contextKind(item);
  const text = contextText(item);
  return (kind === "road" || text.includes("duong") || text.includes("road") || text.includes("street")) && !isWaterContext(item);
}

function isWaterContext(item) {
  const kind = contextKind(item);
  const text = contextText(item);
  return kind === "water" || ["song", "kenh", "suoi", "thuy", "mat nuoc", "water", "river", "canal"].some(key => text.includes(key));
}

function isPlaceContext(item) {
  const kind = contextKind(item);
  return kind === "place" || kind === "area";
}

function isPoiContext(item) {
  return ["cafe", "school", "food", "point"].includes(contextKind(item));
}

function distanceText(distance) {
  if (!Number.isFinite(distance)) return "";
  if (state.collection?.metadata?.map_crs === "EPSG:3857") {
    return distance >= 1000 ? `${formatNumber(distance / 1000, 2)} km` : `${formatNumber(distance, 0)} m`;
  }
  return formatNumber(distance, 1);
}

function nearestContext(feature, predicate, limit = 1) {
  const center = geometryCenter(feature);
  if (!center) return [];
  return nearbyContextItems(feature)
    .map(item => {
      const itemCenter = geometryCenter(item.feature);
      const label = contextLabel(item);
      if (!itemCenter || !label || !predicate(item)) return null;
      return {
        ...item,
        label,
        distance: Math.hypot(itemCenter.x - center.x, itemCenter.y - center.y),
      };
    })
    .filter(Boolean)
    .sort((a, b) => a.distance - b.distance)
    .slice(0, limit);
}

function pointSegmentDistance(p, a, b) {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  if (dx === 0 && dy === 0) return Math.hypot(p[0] - a[0], p[1] - a[1]);
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)));
  return Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy));
}

function segmentDistance(a, b, c, d) {
  return Math.min(
    pointSegmentDistance(a, c, d),
    pointSegmentDistance(b, c, d),
    pointSegmentDistance(c, a, b),
    pointSegmentDistance(d, a, b),
  );
}

function polygonBoundarySegments(feature) {
  const geometry = feature.geometry || {};
  const polygons = geometry.type === "MultiPolygon" ? geometry.coordinates || [] : [geometry.coordinates || []];
  const segments = [];
  for (const polygon of polygons) {
    for (const ring of polygon || []) {
      for (let i = 1; i < ring.length; i++) segments.push([ring[i - 1], ring[i]]);
    }
  }
  return segments;
}

function contextSegments(item) {
  const g = item.feature.geometry || {};
  if (g.type === "Point") return [[g.coordinates, g.coordinates]];
  if (g.type === "MultiPoint") return (g.coordinates || []).map(point => [point, point]);
  const lines = [];
  if (g.type === "LineString") lines.push(g.coordinates || []);
  else if (g.type === "MultiLineString") lines.push(...(g.coordinates || []));
  else if (g.type === "Polygon") lines.push(...(g.coordinates || []));
  else if (g.type === "MultiPolygon") lines.push(...(g.coordinates || []).flat());

  const segments = [];
  for (const line of lines) {
    for (let i = 1; i < line.length; i++) segments.push([line[i - 1], line[i]]);
  }
  return segments;
}

function bboxDistance(a, b) {
  const dx = a[2] < b[0] ? b[0] - a[2] : b[2] < a[0] ? a[0] - b[2] : 0;
  const dy = a[3] < b[1] ? b[1] - a[3] : b[3] < a[1] ? a[1] - b[3] : 0;
  return Math.hypot(dx, dy);
}

function boundaryDistance(feature, item) {
  const boundary = polygonBoundarySegments(feature);
  const target = contextSegments(item);
  if (!boundary.length || !target.length) return Infinity;
  let best = Infinity;
  for (const [a, b] of boundary) {
    for (const [c, d] of target) {
      const distance = segmentDistance(a, b, c, d);
      if (distance < best) best = distance;
      if (best === 0) return 0;
    }
  }
  return best;
}

function nearestBoundaryContext(feature, predicate, limit = 1) {
  const parcelBox = feature._bbox || computeGenericBBox(feature);
  return nearbyContextItems(feature)
    .filter(item => predicate(item) && contextLabel(item))
    .map(item => ({
      ...item,
      label: contextLabel(item),
      roughDistance: bboxDistance(parcelBox, item.feature._bbox || computeGenericBBox(item.feature)),
    }))
    .sort((a, b) => a.roughDistance - b.roughDistance)
    .slice(0, 80)
    .map(item => ({ ...item, distance: boundaryDistance(feature, item) }))
    .sort((a, b) => a.distance - b.distance)
    .slice(0, limit);
}

function nearbyContextItems(feature) {
  const bbox = feature?._bbox || computeGenericBBox(feature);
  if (!state.contextIndex || !bbox) return contextFeatureItems();
  const width = Math.max(bbox[2] - bbox[0], 1);
  const height = Math.max(bbox[3] - bbox[1], 1);
  const padding = Math.max(width, height, 80);
  const candidates = querySpatialIndex(state.contextIndex, bbox, { padding });
  return candidates.length ? candidates : contextFeatureItems();
}

function nearbyDetailRows(feature) {
  const road = nearestBoundaryContext(feature, isRoadContext)[0];
  const water = nearestBoundaryContext(feature, isWaterContext)[0];
  const place = nearestContext(feature, isPlaceContext)[0];
  const poi = nearestContext(feature, isPoiContext, 3);

  const rows = [];
  if (road) {
    const label = road.distance <= 25 ? "Mặt đường" : "Đường gần nhất";
    rows.push([label, `${road.label} (${distanceText(road.distance)})`]);
  }
  if (water) {
    const label = water.distance <= 35 ? "Giáp sông/kênh" : "Sông/kênh gần nhất";
    rows.push([label, `${water.label} (${distanceText(water.distance)})`]);
  }
  if (place) rows.push(["Địa danh gần nhất", `${place.label} (${distanceText(place.distance)})`]);
  if (poi.length) rows.push(["Điểm lân cận", poi.map(item => `${item.label} (${distanceText(item.distance)})`).join("; ")]);
  return rows;
}

// ---- Details panel ----
function updateDetails(feature) {
  const title = document.querySelector("#parcelTitle");
  const type  = document.querySelector("#parcelType");
  const details = document.querySelector("#parcelDetails");
  
  if (!feature) {
    detailsActiveWrap.style.display = "none";
    detailsEmptyWrap.style.display = "flex";
    title.textContent = "--";
    type.textContent = "--";
    details.innerHTML = "";
    return;
  }
  
  detailsEmptyWrap.style.display = "none";
  detailsActiveWrap.style.display = "flex";
  
  title.textContent = featureTitle(feature);
  type.textContent = landCode(feature);
  
  const owner   = prop(feature, ["TENCHU","CHUSUDUNG","HOTEN","OWNER"]);
  let address = prop(feature, ["DIACHI","DIACHI_THUA","ADDRESS"]);
  const place   = prop(feature, ["DIADANH","XU","XAID"]);
  const area    = prop(feature, ["area_m2","DIENTICH","DIENTICHPL","AREA","Shape_Area"]);
  const land    = prop(feature, ["KHLOAIDAT","MALOAIDAT","LOAIDAT","MDSD","MDSD2003"]);
  const pid     = prop(feature, ["THUAID","ID","OBJECTID","FID"]);
  
  // Tự động giải mã địa chỉ ngược qua Nominatim nếu thuộc tính trống
  if (!address || address === "--") {
    if (feature.properties.qgis_reverse_address) {
      address = feature.properties.qgis_reverse_address;
    } else {
      address = "Đang tra cứu địa chỉ...";
      const center = geometryCenter(feature);
      if (center) {
        const ll = worldToLonLat(center.x, center.y);
        reverseGeocode(ll.lat, ll.lon).then(addr => {
          if (addr) {
            feature.properties.qgis_reverse_address = addr;
            if (state.selected === feature) {
              updateDetails(feature);
            }
          }
        }).catch(() => {});
      }
    }
  }
  
  const rows = [
    ["Diện tích", `${formatNumber(area,1)} m²`],
    ["Loại đất", land || "--"],
    ["Chủ sử dụng", owner || "--"],
    ["Địa chỉ", address || "--"],
    ["Địa danh", place || "--"],
    ["Thửa ID", pid || "--"],
    ...nearbyDetailRows(feature),
  ];

  details.innerHTML = rows.map(([k,v]) => `
    <div class="detail-row">
      <dt>${escapeHtml(k)}</dt>
      <dd>${escapeHtml(v)}</dd>
    </div>
  `).join("");
}

// ---- Stats & Legend ----
function updateStats() {
  const md = state.collection.metadata || {};
  const fs = state.features;
  const totalArea = fs.reduce((s,f) => s + (Number(f.properties.area_m2)||0), 0);
  const classes = new Set(fs.map(landCode));
  
  document.querySelector("#totalParcels").textContent  = formatNumber(fs.length);
  document.querySelector("#totalArea").textContent     = formatNumber(totalArea/10000, 2);
  document.querySelector("#landClassCount").textContent = formatNumber(classes.size);
  
  const crs = md.source_crs || state.collection.crs?.properties?.name || md.crs || "VN-2000";
  const contextCount = (state.contextLayers || []).reduce((sum, layer) => sum + (layer.features?.length || 0), 0);
  const contextText = contextCount ? `<span>|</span><span>${formatNumber(contextCount)} đối tượng phụ</span>` : "";
  mapStatus.innerHTML = `<span><b>${formatNumber(fs.length)}</b> thửa</span>${contextText}<span>|</span><span>${crs}</span>`;
  updateSubtitle();
}

function updateLegend() {
  const items = landSummary();
  const total = items.reduce((s,i) => s + i.count, 0);
  document.querySelector("#legend").innerHTML = items.map(i => {
    const pct = total ? ((i.count/total)*100).toFixed(1) : 0;
    const activeClass = state.selectedChartSlice.land === i.code ? " active" : "";
    return `<div class="legend-item interactive-legend-item${activeClass}" data-chart="land" data-key="${escapeHtml(i.code)}"><i class="swatch" style="background-color:${i.color}"></i><b title="${escapeHtml(i.code)}">${escapeHtml(i.code)}</b><span>${formatNumber(i.count)} (${pct}%) · ${formatNumber(i.area/10000,2)} ha</span></div>`;
  }).join("");
  drawLand();
  updateGroupLegend();
  drawGroup();
}

function updateGroupLegend() {
  const items = groupSummary();
  const total = items.reduce((s,i) => s + i.count, 0);
  document.querySelector("#groupLegend").innerHTML = items.map(i => {
    const pct = total ? ((i.count/total)*100).toFixed(1) : 0;
    const activeClass = state.selectedChartSlice.group === i.key ? " active" : "";
    return `<div class="legend-item interactive-legend-item${activeClass}" data-chart="group" data-key="${escapeHtml(i.key)}"><i class="swatch" style="background-color:${i.color}"></i><b title="${escapeHtml(i.label)}">${escapeHtml(i.label)}</b><span>${formatNumber(i.count)} (${pct}%) · ${formatNumber(i.area/10000,2)} ha</span></div>`;
  }).join("");
}

// ---- Chart info panels ----
function updateLandChartInfo(item) {
  const info = document.querySelector("#landChartInfo");
  const total = state.features.length, pct = total ? (item.count/total)*100 : 0;
  const grp = landGroup(item.code);
  info.innerHTML = `<div class="chart-info-head">${escapeHtml(item.code)} · ${escapeHtml(grp.label)}</div>
    <div class="chart-info-grid"><span class="info-cell"><b>${formatNumber(item.count)}</b><small>thửa</small></span><span class="info-cell"><b>${formatNumber(pct,1)}%</b><small>tỷ lệ</small></span><span class="info-cell"><b>${formatNumber(item.area/10000,2)}</b><small>ha</small></span></div>`;
}
function updateGroupChartInfo(item) {
  const info = document.querySelector("#groupChartInfo");
  const total = state.features.length, pct = total ? (item.count/total)*100 : 0;
  const codes = landSummary().filter(l => landGroup(l.code).key === item.key).map(l => l.code).join(", ");
  info.innerHTML = `<div class="chart-info-head">${escapeHtml(item.label)}</div>
    <div class="chart-info-grid"><span class="info-cell"><b>${formatNumber(item.count)}</b><small>thửa</small></span><span class="info-cell"><b>${formatNumber(pct,1)}%</b><small>tỷ lệ</small></span><span class="info-cell"><b>${formatNumber(item.area/10000,2)}</b><small>ha</small></span></div>
    <span style="font-size:10px;color:var(--text-muted);margin-top:4px;display:block">Mã đất: ${escapeHtml(codes||"--")}</span>`;
}
function resetChartInfo(chartKey) {
  const info = document.querySelector(chartKey === "land" ? "#landChartInfo" : "#groupChartInfo");
  const t = chartKey === "land" ? "Chọn một lát biểu đồ" : "Chọn một nhóm đất";
  const d = chartKey === "land" ? "Xem số thửa, diện tích và nhóm sử dụng đất." : "Xem cơ cấu nhóm và các mã loại đất bên trong.";
  info.innerHTML = `<div class="chart-info-head">${t}</div><span style="font-size:var(--text-xs);color:var(--text-muted)">${d}</span>`;
}
function syncLegendActiveState(chartKey) {
  const containerId = chartKey === "land" ? "#legend" : "#groupLegend";
  const container = document.querySelector(containerId);
  if (!container) return;
  const selectedKey = state.selectedChartSlice[chartKey];
  container.querySelectorAll(".interactive-legend-item").forEach(item => {
    const itemKey = item.dataset.key;
    item.classList.toggle("active", itemKey === selectedKey);
  });
}

function clearChartSelection(chartKey) {
  state.selectedChartSlice[chartKey] = null;
  if (state.chartAnimation.key === chartKey) state.chartAnimation.key = null;
  resetChartInfo(chartKey);
  animateChartSelection(chartKey, drawLand, drawGroup);
  syncLegendActiveState(chartKey);
}

// ---- Search ----
function resultItemHtml(feature, cls) {
  const active = feature === state.selected ? " active" : "";
  const owner = prop(feature, ["TENCHU","CHUSUDUNG","HOTEN","OWNER","DIADANH"]);
  const area = featureArea(feature);
  return `<button class="${cls}${active}" type="button" data-index="${feature._webgisIndex}">
    <div class="result-item-info"><b>${escapeHtml(featureTitle(feature))}</b><span>${escapeHtml(owner||"Không có tên chủ")}</span></div>
    <div class="result-item-meta"><b>${escapeHtml(landCode(feature))}</b><small>${formatNumber(area,1)} m²</small></div>
  </button>`;
}

let searchTimeout = null;

function updateResults() {
  const query = searchInput.value.trim();
  const hadFilter = state.filtered.length > 0;

  // 1. Chạy bộ lọc highlight cục bộ khi có từ khóa. Lúc mở WebGIS
  // ô tìm kiếm rỗng, nên tránh quét lại toàn bộ thửa và vẽ lại thêm một lần.
  const matched = query || hadFilter ? localFilterParcels(query) : state.features;
  if (query || hadFilter) redraw();
  
  resultCount.textContent = formatNumber(matched.length);
  resultList.innerHTML = matched.slice(0, 80).map(f => resultItemHtml(f, "result-item")).join("");
  if (modalResultCount) modalResultCount.textContent = `${formatNumber(matched.length)} thửa đất khớp`;
  if (modalResultList)  modalResultList.innerHTML = matched.slice(0, 160).map(f => resultItemHtml(f, "result-item")).join("");

  // Cập nhật hộp thống kê kết quả tìm kiếm nhanh (Đơn giản hóa tra cứu)
  const searchSummary = document.querySelector("#searchSummary");
  const summaryCount = document.querySelector("#summaryCount");
  const summaryArea = document.querySelector("#summaryArea");
  
  if (searchSummary && summaryCount && summaryArea) {
    if (query && matched.length > 0) {
      searchSummary.style.display = "grid";
      summaryCount.textContent = formatNumber(matched.length);
      
      const totalArea = matched.reduce((sum, f) => sum + (Number(featureArea(f)) || 0), 0);
      if (totalArea >= 10000) {
        summaryArea.textContent = `${formatNumber(totalArea / 10000, 2)} ha`;
      } else {
        summaryArea.textContent = `${formatNumber(totalArea, 1)} m²`;
      }
    } else {
      searchSummary.style.display = "none";
    }
  }
  
  // 2. Tra cứu địa điểm qua Nominatim API (Debounced)
  if (searchTimeout) clearTimeout(searchTimeout);
  if (query.length >= 3) {
    searchTimeout = setTimeout(async () => {
      const addresses = await searchAddress(query);
      if (addresses && addresses.length > 0) {
        const addressHtml = `<div class="result-group-title" style="padding: 8px 12px 4px; font-size:10px; text-transform:uppercase; color:var(--text-muted); font-weight:bold; letter-spacing:0.5px; border-top:1px solid var(--border); margin-top:8px;">Gợi ý địa điểm bản đồ</div>` + 
          addresses.map(item => {
            return `<button class="result-item address-item" type="button" data-lat="${item.lat}" data-lon="${item.lon}" style="border-left: 3px solid var(--accent, #60a5fa);">
              <div class="result-item-info">
                <b style="font-size:11px;">${escapeHtml(item.name || "Địa điểm")}</b>
                <span style="font-size:10px; opacity:0.8; max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(item.display_name)}</span>
              </div>
              <div class="result-item-meta"><small style="color:var(--accent, #60a5fa); font-weight:bold;">Bản đồ</small></div>
            </button>`;
          }).join("");
        
        resultList.insertAdjacentHTML("beforeend", addressHtml);
      }
    }, 500);
  }
}

function syncResultActive() {
  for (const c of [resultList, modalResultList]) {
    if (!c) continue;
    for (const el of c.querySelectorAll(".result-item"))
      el.classList.toggle("active", state.selected && Number(el.dataset.index) === state.selected._webgisIndex);
  }
}

// ================================================================
// EVENT LISTENERS
// ================================================================

// -- Map drag / hover / click --
canvas.addEventListener("pointerdown", e => {
  state.dragging = true; state.moved = false;
  state.lastX = e.clientX; state.lastY = e.clientY;
  canvas.classList.add("dragging"); canvas.setPointerCapture(e.pointerId);
});
canvas.addEventListener("pointermove", e => {
  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;
  
  if (measureMode) {
    mouseWorldPos = screenToWorld(mouseX, mouseY, canvas);
    redraw();
    
    // Cập nhật tọa độ đo
    if (state.collection?.metadata?.map_crs === "EPSG:3857") {
      const ll = worldToLonLat(mouseWorldPos.x, mouseWorldPos.y);
      coordStatus.textContent = `Đo đạc WGS84: ${formatNumber(ll.lat,6)}, ${formatNumber(ll.lon,6)}`;
    } else {
      coordStatus.textContent = `Đo đạc VN-2000: ${formatNumber(mouseWorldPos.x,1)}, ${formatNumber(mouseWorldPos.y,1)}`;
    }
    return;
  }
  
  if (state.dragging) {
    const dx = e.clientX - state.lastX, dy = e.clientY - state.lastY;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) state.moved = true;
    state.panX += dx; state.panY += dy;
    state.lastX = e.clientX; state.lastY = e.clientY;
    redraw(); return;
  }
  
  const f = featureAt(mouseX, mouseY);
  if (f !== state.hovered) {
    state.hovered = f;
    redraw();
    if (f) {
      const coord = screenToWorld(mouseX, mouseY, canvas);
      if (state.collection?.metadata?.map_crs === "EPSG:3857") {
        const ll = worldToLonLat(coord.x, coord.y);
        coordStatus.textContent = `WGS84: ${formatNumber(ll.lat,6)}, ${formatNumber(ll.lon,6)}`;
      } else {
        coordStatus.textContent = `VN-2000: ${formatNumber(coord.x,1)}, ${formatNumber(coord.y,1)}`;
      }
    }
  }
});
canvas.addEventListener("pointerup", e => {
  if (!state.dragging) return;
  state.dragging = false; canvas.classList.remove("dragging"); canvas.releasePointerCapture(e.pointerId);
  if (!state.moved) {
    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;
    
    if (measureMode) {
      const worldPt = screenToWorld(clickX, clickY, canvas);
      measurePoints.push([worldPt.x, worldPt.y]);
      mouseWorldPos = { x: worldPt.x, y: worldPt.y };
      mapStatus.textContent = `Đã chọn ${measurePoints.length} điểm đo. Double-click/R-Click để kết thúc.`;
      redraw();
    } else {
      setSelected(featureAt(clickX, clickY), { zoom: false });
    }
  } else {
    checkAndLoadBBox();
  }
});
canvas.addEventListener("wheel", e => {
  e.preventDefault(); const rect = canvas.getBoundingClientRect();
  zoomAt(e.deltaY < 0 ? 1.25 : 0.8, e.clientX - rect.left, e.clientY - rect.top, canvas, redraw);
  checkAndLoadBBox();
});

// Kết thúc đo khi double-click hoặc right-click
canvas.addEventListener("dblclick", e => {
  if (measureMode) {
    e.preventDefault();
    finishMeasurement();
  }
});
canvas.addEventListener("contextmenu", e => {
  if (measureMode) {
    e.preventDefault();
    finishMeasurement();
  }
});

// -- Zoom & Tools buttons --
document.querySelector("#zoomIn")?.addEventListener("click", () => { const r = canvas.getBoundingClientRect(); zoomAt(1.5, r.width/2, r.height/2, canvas, redraw); checkAndLoadBBox(); });
document.querySelector("#zoomOut")?.addEventListener("click", () => { const r = canvas.getBoundingClientRect(); zoomAt(0.667, r.width/2, r.height/2, canvas, redraw); checkAndLoadBBox(); });
document.querySelector("#resetView")?.addEventListener("click", () => { resetView(redraw); checkAndLoadBBox(); });

const toggle3DBtn = document.querySelector("#toggle3D");
toggle3DBtn?.addEventListener("click", () => {
  state.view3d = !state.view3d;
  toggle3DBtn.classList.toggle("active", state.view3d);
  if (isMapLibreActive()) {
    maplibreAdapter.set3DMode(state.view3d);
  }
  redraw();
});

const btnDist = document.querySelector("#measureDist");
const btnArea = document.querySelector("#measureArea");

btnDist?.addEventListener("click", () => {
  if (measureMode === "dist") {
    cancelMeasurement();
  } else {
    cancelMeasurement();
    measureMode = "dist";
    loadTurf();
    btnDist.classList.add("active");
    mapStatus.textContent = "Chế độ đo khoảng cách: Nhấp chuột lên bản đồ để vẽ, R-Click/Dbl-Click để hoàn tất.";
    syncCanvasPointerEvents();
  }
});

btnArea?.addEventListener("click", () => {
  if (measureMode === "area") {
    cancelMeasurement();
  } else {
    cancelMeasurement();
    measureMode = "area";
    loadTurf();
    btnArea.classList.add("active");
    mapStatus.textContent = "Chế độ đo diện tích: Nhấp chuột để khoanh vùng, R-Click/Dbl-Click để xem kết quả.";
    syncCanvasPointerEvents();
  }
});

// -- Details tab actions --
zoomToParcelBtn?.addEventListener("click", () => {
  if (state.selected) {
    zoomToFeature(state.selected, canvas);
    redraw();
  }
});
clearSelectionBtn?.addEventListener("click", () => {
  setSelected(null);
});

// -- Theme --
themeToggle?.addEventListener("click", () => {
  setLightMode(!isLightMode);
  document.body.classList.toggle("theme-light", isLightMode);
  document.body.classList.toggle("theme-dark", !isLightMode);
  
  if (isMapLibreActive()) {
    maplibreAdapter.setParcelsStyle(!isLightMode);
    if (state.basemapId === "osm") {
      maplibreAdapter.setBasemap("osm");
    }
  }
  
  redraw(); resizeChart();
});

basemapSelect?.addEventListener("change", () => {
  state.basemapId = basemapSelect.value;
  updateAttribution();
  
  if (isMapLibreActive()) {
    maplibreAdapter.setBasemap(state.basemapId);
  }
  
  redraw();
});

// -- Print Map / Export PNG --
const printMapBtn = document.querySelector("#printMap");
printMapBtn?.addEventListener("click", () => {
  // Trực tiếp vẽ watermark lên canvas hiện tại trước khi xuất
  redraw(); // Đảm bảo bản đồ sạch
  
  // Vẽ chữ "ẢNH MẪU" chéo giữa màn hình bản đồ
  ctx.save();
  const rect = canvas.getBoundingClientRect();
  const w = rect.width;
  const h = rect.height;
  
  ctx.fillStyle = "rgba(239, 68, 68, 0.25)"; // Màu đỏ mờ nhạt (rose-500)
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  
  // Vẽ chữ chéo chéo chính giữa bản đồ
  ctx.font = "bold 36px sans-serif";
  ctx.translate(w / 2, h / 2);
  ctx.rotate(-Math.PI / 8); // Xoay khoảng -22.5 độ
  ctx.fillText("ẢNH MẪU - SAMPLE MAP", 0, -15);
  
  ctx.font = "bold 14px sans-serif";
  ctx.fillText("Không dùng cho giao dịch chính thức", 0, 20);
  ctx.restore();

  // Tạo liên kết tải ảnh về
  try {
    const dataURL = canvas.toDataURL("image/png");
    const link = document.createElement("a");
    link.download = `ban-do-mau-${Date.now()}.png`;
    link.href = dataURL;
    link.click();
  } catch (err) {
    console.error("Lỗi xuất ảnh bản đồ:", err);
    alert("Không thể xuất ảnh do chính sách bảo mật của bản đồ nền (CORS). Hãy thử chuyển sang bản đồ khác.");
  }

  // Redraw lại bản đồ để xóa watermark trên màn hình tương tác
  setTimeout(() => {
    redraw();
  }, 100);
});

// -- Search --
searchInput?.addEventListener("input", () => {
  updateResults();
  // Auto-switch to search tab if they type from somewhere else (not needed since input is in search panel)
});
// Remove modal trigger button bindings from sidebar (since we have search in sidebar), but keep modal bindings for QGIS RPC compatibility
closeSearchModalBtn?.addEventListener("click", () => { searchModal?.classList.remove("active"); document.body.classList.remove("modal-open"); });
modalSearchInput?.addEventListener("input", () => { searchInput.value = modalSearchInput.value; updateResults(); });
modalClearSearchBtn?.addEventListener("click", () => { searchInput.value = ""; modalSearchInput.value = ""; updateResults(); });

// -- Result clicks (event delegation) --
document.addEventListener("click", e => {
  const btn = e.target.closest(".result-item");
  if (!btn) return;
  const f = state.features.find(f => f._webgisIndex === Number(btn.dataset.index));
  if (f) { setSelected(f); searchModal?.classList.remove("active"); document.body.classList.remove("modal-open"); }
});

// -- Chart Hover & Tooltip Interaction --
let tooltipEl = document.querySelector(".chart-tooltip");
if (!tooltipEl) {
  tooltipEl = document.createElement("div");
  tooltipEl.className = "chart-tooltip";
  document.body.appendChild(tooltipEl);
}

function showTooltip(e, chartKey, slice) {
  const item = slice.item;
  const total = state.features.length;
  const pct = total ? ((item.count / total) * 100).toFixed(1) : 0;
  
  let html = "";
  if (chartKey === "land") {
    const grp = landGroup(item.code);
    html = `
      <div style="font-weight: 700; border-bottom: 1px solid var(--border-subtle); padding-bottom: 4px; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
        <i class="swatch" style="background-color:${item.color}; border-radius:50%; width:8px; height:8px; display:inline-block;"></i>
        <span>${escapeHtml(item.code)} · ${escapeHtml(grp.label)}</span>
      </div>
      <div style="display: flex; flex-direction: column; gap: 4px;">
        <span style="color: var(--text-muted); font-size: 11px;">Số thửa: <b style="color: var(--text-main); font-weight: 600;">${formatNumber(item.count)}</b></span>
        <span style="color: var(--text-muted); font-size: 11px;">Tỷ lệ: <b style="color: var(--text-main); font-weight: 600;">${pct}%</b></span>
        <span style="color: var(--text-muted); font-size: 11px;">Diện tích: <b style="color: var(--text-main); font-weight: 600;">${formatNumber(item.area / 10000, 2)} ha</b></span>
      </div>
    `;
  } else {
    html = `
      <div style="font-weight: 700; border-bottom: 1px solid var(--border-subtle); padding-bottom: 4px; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
        <i class="swatch" style="background-color:${item.color}; border-radius:50%; width:8px; height:8px; display:inline-block;"></i>
        <span>${escapeHtml(item.label)}</span>
      </div>
      <div style="display: flex; flex-direction: column; gap: 4px;">
        <span style="color: var(--text-muted); font-size: 11px;">Số thửa: <b style="color: var(--text-main); font-weight: 600;">${formatNumber(item.count)}</b></span>
        <span style="color: var(--text-muted); font-size: 11px;">Tỷ lệ: <b style="color: var(--text-main); font-weight: 600;">${pct}%</b></span>
        <span style="color: var(--text-muted); font-size: 11px;">Diện tích: <b style="color: var(--text-main); font-weight: 600;">${formatNumber(item.area / 10000, 2)} ha</b></span>
      </div>
    `;
  }
  
  tooltipEl.innerHTML = html;
  tooltipEl.style.left = `${e.pageX}px`;
  tooltipEl.style.top = `${e.pageY}px`;
  tooltipEl.classList.add("active");
}

function hideTooltip() {
  tooltipEl.classList.remove("active");
}

function handleChartMouseMove(e, chartKey, canvasEl) {
  if (!state.collection) return;
  const rect = canvasEl.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;
  const slice = sliceAt(chartKey, mouseX, mouseY);
  
  const oldHovered = state.hoveredChartSlice[chartKey];
  const newHovered = slice ? slice.key : null;
  
  if (oldHovered !== newHovered) {
    state.hoveredChartSlice[chartKey] = newHovered;
    animateChartSelection(chartKey, drawLand, drawGroup);
  }
  
  if (slice) {
    canvasEl.style.cursor = "pointer";
    showTooltip(e, chartKey, slice);
  } else {
    canvasEl.style.cursor = "default";
    hideTooltip();
  }
}

function handleChartMouseLeave(chartKey) {
  if (state.hoveredChartSlice[chartKey] !== null) {
    state.hoveredChartSlice[chartKey] = null;
    animateChartSelection(chartKey, drawLand, drawGroup);
  }
  hideTooltip();
}

// -- Chart clicks --
function handleChartClick(e, chartKey, canvasEl) {
  if (!state.collection) return;
  const rect = canvasEl.getBoundingClientRect();
  const slice = sliceAt(chartKey, e.clientX - rect.left, e.clientY - rect.top);
  if (!slice) return;
  if (state.selectedChartSlice[chartKey] === slice.key) { 
    clearChartSelection(chartKey); 
    return; 
  }
  state.selectedChartSlice[chartKey] = slice.key;
  if (chartKey === "land") updateLandChartInfo(slice.item); else updateGroupChartInfo(slice.item);
  animateChartSelection(chartKey, drawLand, drawGroup);
  syncLegendActiveState(chartKey);
}

landChart.addEventListener("click", e => handleChartClick(e, "land", landChart));
groupChart.addEventListener("click", e => handleChartClick(e, "group", groupChart));

landChart.addEventListener("mousemove", e => handleChartMouseMove(e, "land", landChart));
groupChart.addEventListener("mousemove", e => handleChartMouseMove(e, "group", groupChart));

landChart.addEventListener("mouseleave", () => handleChartMouseLeave("land"));
groupChart.addEventListener("mouseleave", () => handleChartMouseLeave("group"));

// -- Legend click events (event delegation) --
document.addEventListener("click", e => {
  const legendItem = e.target.closest(".interactive-legend-item");
  if (!legendItem) return;
  
  const chartKey = legendItem.dataset.chart;
  const key = legendItem.dataset.key;
  
  let item = null;
  if (chartKey === "land") {
    item = landSummary().find(i => i.code === key);
  } else {
    item = groupSummary().find(i => i.key === key);
  }
  if (!item) return;

  if (state.selectedChartSlice[chartKey] === key) {
    clearChartSelection(chartKey);
    return;
  }
  
  state.selectedChartSlice[chartKey] = key;
  if (chartKey === "land") updateLandChartInfo(item); else updateGroupChartInfo(item);
  animateChartSelection(chartKey, drawLand, drawGroup);
  syncLegendActiveState(chartKey);
});

// -- Resize --
window.addEventListener("resize", () => { resizeCanvas(); resizeChart(); });

// ================================================================
// LIVE BBOX STREAMING & FALLBACK SYSTEM
// ================================================================
let currentLoadedBBox = null;
let isLoadingLive = false;
let hasLiveAPI = false;
let bboxLoadTimeout = null;

async function checkLiveAPI() {
  try {
    const resp = await fetch("api/parcels?bbox=0,0,1,1");
    if (resp.ok) {
      hasLiveAPI = true;
      console.log("Live API detected, switching to BBox streaming.");
    }
  } catch (e) {
    hasLiveAPI = false;
  }
}

async function loadLiveBBoxData(bbox) {
  if (isLoadingLive) return;
  isLoadingLive = true;
  mapStatus.textContent = "Đang tải dữ liệu...";
  
  const dx = (bbox[2] - bbox[0]) * 0.5;
  const dy = (bbox[3] - bbox[1]) * 0.5;
  const bufferedBBox = [
    bbox[0] - dx,
    bbox[1] - dy,
    bbox[2] + dx,
    bbox[3] + dy
  ];
  
  try {
    const resp = await fetch(`api/parcels?bbox=${bufferedBBox.map(v => v.toFixed(2)).join(",")}`);
    if (!resp.ok) throw new Error(resp.statusText);
    const data = await resp.json();
    
    const features = data.features || [];
    features.forEach((f, i) => f._webgisIndex = i);
    
    state.features = features;
    state.featureIndex = createSpatialIndex(state.features.map(f => ({ feature: f })), bufferedBBox);
    currentLoadedBBox = bufferedBBox;
    
    if (isMapLibreActive()) {
      maplibreAdapter.setGeoJSON({ ...state.collection, features });
    }
    
    mapStatus.textContent = `Đã nạp ${features.length} thửa`;
    redraw();
    updateStats();
    updateResults();
  } catch (err) {
    console.error("Live BBox error:", err);
    mapStatus.textContent = "Lỗi kết nối server";
  } finally {
    isLoadingLive = false;
  }
}

function checkAndLoadBBox() {
  if (!hasLiveAPI) return;
  clearTimeout(bboxLoadTimeout);
  bboxLoadTimeout = setTimeout(() => {
    const viewBBox = visibleWorldBBox(canvas);
    if (!currentLoadedBBox || 
        viewBBox[0] < currentLoadedBBox[0] || 
        viewBBox[1] < currentLoadedBBox[1] || 
        viewBBox[2] > currentLoadedBBox[2] || 
        viewBBox[3] > currentLoadedBBox[3]) {
      loadLiveBBoxData(viewBBox);
    }
  }, 300);
}

// ================================================================
// INIT
// ================================================================
(async function init() {
  document.body.classList.add("theme-dark");
  initBasemapSelect();
  await checkLiveAPI();

  try {
    maplibreAdapter.initMapLibre("mapgl", {
      darkMode: true,
      basemapId: state.basemapId,
      view3d: state.view3d,
      onMouseMove: (lngLat) => {
        if (state.collection?.metadata?.map_crs === "EPSG:3857") {
          const world = lonLatToWorld(lngLat.lng, lngLat.lat);
          coordStatus.textContent = `WGS84: ${formatNumber(lngLat.lat, 6)}, ${formatNumber(lngLat.lng, 6)} | VN-2000: ${formatNumber(world.x, 1)}, ${formatNumber(world.y, 1)}`;
        } else {
          coordStatus.textContent = `WGS84: ${formatNumber(lngLat.lat, 6)}, ${formatNumber(lngLat.lng, 6)}`;
        }
      }
    });

    maplibreAdapter.onFeatureClick(feature => {
      setSelected(feature, { zoom: false });
    });

    maplibreAdapter.onFeatureHover((feature, lngLat) => {
      state.hovered = feature;
      if (feature && lngLat) {
        if (state.collection?.metadata?.map_crs === "EPSG:3857") {
          const world = lonLatToWorld(lngLat.lng, lngLat.lat);
          coordStatus.textContent = `WGS84: ${formatNumber(lngLat.lat, 6)}, ${formatNumber(lngLat.lng, 6)} | VN-2000: ${formatNumber(world.x, 1)}, ${formatNumber(world.y, 1)}`;
        } else {
          coordStatus.textContent = `WGS84: ${formatNumber(lngLat.lat, 6)}, ${formatNumber(lngLat.lng, 6)}`;
        }
      }
      redraw();
    });

    setMapLibreActive(true);
    canvas.classList.add("maplibre-active");
    syncCanvasPointerEvents();
  } catch (err) {
    console.error("MapLibre GL JS initialization failed, fallback to Canvas:", err);
    setMapLibreActive(false);
    canvas.classList.remove("maplibre-active");
    syncCanvasPointerEvents();
  }

  const handleLoadedData = (features, contextLayers, collectionBBox, collection) => {
    features.forEach(f => {
      if (!f._bbox) {
        f._bbox = computeGenericBBox(f);
      }
    });
    state.collection = collection;
    state.features = features;
    state.contextLayers = contextLayers;
    state.bbox = collectionBBox;
    mapStatus.textContent = "Đang tính toán...";
    
    state.featureIndex = createSpatialIndex(state.features.map(feature => ({ feature })), state.bbox);
    prepareContextLayers();
    
    if (isMapLibreActive()) {
      maplibreAdapter.setGeoJSON({ ...collection, features });
      if (collectionBBox) {
        const llMin = worldToLonLat(collectionBBox[0], collectionBBox[1]);
        const llMax = worldToLonLat(collectionBBox[2], collectionBBox[3]);
        const map = maplibreAdapter.getMapInstance();
        if (map) {
          map.fitBounds([[llMin.lon, llMin.lat], [llMax.lon, llMax.lat]], {
            padding: 50,
            duration: 1000
          });
        }
      }
    }
    
    resizeCanvas(); updateStats(); updateLegend(); resizeChart(); updateResults(); initShareUI(); initMobileShare();
    const initialSelected = state.features.find(f => f.properties.qgis_selected === true);
    setSelected(initialSelected || null);
  };

  const loadFallback = async () => {
    try {
      const resp = await fetch(DATA_URL);
      if (!resp.ok) throw new Error(resp.statusText);
      const data = await resp.json();
      const features = data.features || [];
      const contextLayers = data.context_layers || [];
      features.forEach((f, i) => f._webgisIndex = i);
      const collectionBBox = computeCollectionBBox(features);
      handleLoadedData(features, contextLayers, collectionBBox, data);
    } catch (err) {
      mapStatus.textContent = "Lỗi tải dữ liệu";
      console.error(err);
    }
  };

  if (hasLiveAPI) {
    try {
      mapStatus.textContent = "Đang kết nối Live API...";
      const resp = await fetch("api/parcels");
      if (!resp.ok) throw new Error(resp.statusText);
      const data = await resp.json();
      
      const features = data.features || [];
      const contextLayers = data.context_layers || [];
      features.forEach((f, i) => f._webgisIndex = i);
      const collectionBBox = data.bbox || computeCollectionBBox(features);
      
      handleLoadedData(features, contextLayers, collectionBBox, data);
      currentLoadedBBox = collectionBBox;
    } catch (err) {
      console.warn("Live initial fetch failed, falling back to static file:", err);
      hasLiveAPI = false;
      await loadFallback();
    }
  } else {
    const absoluteDataUrl = new URL(DATA_URL, window.location.href).href;
    if (typeof Worker !== "undefined") {
      try {
        const worker = new Worker("js/worker.js");
        worker.postMessage({ dataUrl: absoluteDataUrl });
        worker.onmessage = function(e) {
          if (e.data.type === "success") {
            handleLoadedData(e.data.features, e.data.contextLayers, e.data.collectionBBox, e.data.collection);
          } else {
            console.warn("Worker error:", e.data.error, ". Falling back to main thread.");
            loadFallback();
          }
        };
        worker.onerror = function(err) {
          console.warn("Worker error, falling back to main thread:", err);
          loadFallback();
        };
      } catch (err) {
        console.warn("Could not start Web Worker, falling back to main thread:", err);
        loadFallback();
      }
    } else {
      loadFallback();
    }
  }
  // ================================================================
  // WEBGIS SHARE CONTROL
  // Controls the SSH internet tunnel from the browser.
  // Restricted only to localhost/127.0.0.1 for security.
  // ================================================================
  function initShareUI() {
    const shareTabBtn = document.getElementById("shareTabBtn");
    const panelShare = document.getElementById("panel-share");
    if (!shareTabBtn || !panelShare) return;

    const host = window.location.hostname;
    const isLocal = host === "localhost" || host === "127.0.0.1";
    
    const btnQuickShare = document.getElementById("btnQuickShare");

    if (!isLocal) {
      shareTabBtn.style.display = "none";
      if (btnQuickShare) btnQuickShare.style.display = "none";
      return;
    }

    const inactiveView = document.getElementById("share-inactive-view");
    const activeView = document.getElementById("share-active-view");
    const loadingView = document.getElementById("share-loading-view");
    const errorMsg = document.getElementById("share-error-msg");
    
    const btnStartShare = document.getElementById("btnStartShare");
    const btnStopShare = document.getElementById("btnStopShare");
    
    const txtShareUrl = document.getElementById("txtShareUrl");
    const txtSharePasscode = document.getElementById("txtSharePasscode");
    
    const btnCopyShareUrl = document.getElementById("btnCopyShareUrl");
    const btnCopySharePasscode = document.getElementById("btnCopySharePasscode");

    if (btnQuickShare) {
      btnQuickShare.style.display = "flex";
      btnQuickShare.addEventListener("click", () => {
        switchTab("share");
        if (inactiveView.style.display !== "none") {
          btnStartShare.click();
        }
      });
    }

    async function checkStatus() {
      try {
        const resp = await fetch("api/share/status");
        if (!resp.ok) return;
        const data = await resp.json();
        updateUI(data);
      } catch (err) {
        console.warn("Failed to check share status:", err);
      }
    }

    function updateUI(data) {
      const shareDot = btnQuickShare ? btnQuickShare.querySelector(".share-dot") : null;
      const quickShareText = document.getElementById("quickShareText");

      if (data.lan_url) {
        const txtLanShareUrl = document.getElementById("txtLanShareUrl");
        if (txtLanShareUrl) txtLanShareUrl.value = data.lan_url;
      }

      if (data.active) {
        inactiveView.style.display = "none";
        loadingView.style.display = "none";
        activeView.style.display = "flex";
        
        txtShareUrl.value = data.url;
        txtSharePasscode.value = data.passcode;
        errorMsg.style.display = "none";

        if (shareDot) shareDot.classList.add("active");
        if (quickShareText) quickShareText.textContent = "Đang chia sẻ";
        if (btnQuickShare) {
          btnQuickShare.classList.remove("btn-primary");
          btnQuickShare.classList.add("btn-outline");
          btnQuickShare.title = "Đang chia sẻ bản đồ ra Internet. Bấm để xem chi tiết.";
        }
      } else {
        activeView.style.display = "none";
        loadingView.style.display = "none";
        inactiveView.style.display = "block";
        errorMsg.style.display = "none";

        if (shareDot) shareDot.classList.remove("active");
        if (quickShareText) quickShareText.textContent = "Chia sẻ";
        if (btnQuickShare) {
          btnQuickShare.classList.remove("btn-outline");
          btnQuickShare.classList.add("btn-primary");
          btnQuickShare.title = "Chia sẻ bản đồ ra Internet nhanh";
        }
      }
    }

    btnStartShare.addEventListener("click", async () => {
      inactiveView.style.display = "none";
      activeView.style.display = "none";
      errorMsg.style.display = "none";
      loadingView.style.display = "block";
      
      const quickShareText = document.getElementById("quickShareText");
      if (quickShareText) quickShareText.textContent = "Đang kết nối...";
      
      try {
        const resp = await fetch("api/share/activate");
        if (!resp.ok) throw new Error("Server returned error status " + resp.status);
        const data = await resp.json();
        
        if (data.active) {
          updateUI(data);
        } else {
          loadingView.style.display = "none";
          inactiveView.style.display = "block";
          errorMsg.textContent = data.error || "Không khởi động được SSH tunnel. Vui lòng thử lại.";
          errorMsg.style.display = "block";
        }
      } catch (err) {
        loadingView.style.display = "none";
        inactiveView.style.display = "block";
        errorMsg.textContent = "Lỗi mạng: Không kết nối được với QGIS server local.";
        errorMsg.style.display = "block";
        console.error(err);
      }
    });

    btnStopShare.addEventListener("click", async () => {
      activeView.style.display = "none";
      loadingView.style.display = "none";
      inactiveView.style.display = "none";
      
      const quickShareText = document.getElementById("quickShareText");
      if (quickShareText) quickShareText.textContent = "Đang dừng...";
      
      try {
        const resp = await fetch("api/share/deactivate");
        if (!resp.ok) throw new Error();
        const data = await resp.json();
        updateUI(data);
      } catch (err) {
        await checkStatus();
        errorMsg.textContent = "Không dừng được chia sẻ: Kết nối lỗi.";
        errorMsg.style.display = "block";
      }
    });

    btnCopyShareUrl.addEventListener("click", () => {
      navigator.clipboard.writeText(txtShareUrl.value);
      const originalText = btnCopyShareUrl.textContent;
      btnCopyShareUrl.textContent = "Đã chép";
      setTimeout(() => { btnCopyShareUrl.textContent = originalText; }, 2000);
    });

    btnCopySharePasscode.addEventListener("click", () => {
      navigator.clipboard.writeText(txtSharePasscode.value);
      const originalText = btnCopySharePasscode.textContent;
      btnCopySharePasscode.textContent = "Đã chép";
      setTimeout(() => { btnCopySharePasscode.textContent = originalText; }, 2000);
    });

    const btnCopyLanShareUrl = document.getElementById("btnCopyLanShareUrl");
    if (btnCopyLanShareUrl) {
      btnCopyLanShareUrl.addEventListener("click", () => {
        const txtLanShareUrl = document.getElementById("txtLanShareUrl");
        if (txtLanShareUrl && txtLanShareUrl.value) {
          navigator.clipboard.writeText(txtLanShareUrl.value);
          const originalText = btnCopyLanShareUrl.textContent;
          btnCopyLanShareUrl.textContent = "Đã chép";
          setTimeout(() => { btnCopyLanShareUrl.textContent = originalText; }, 2000);
        }
      });
    }

    checkStatus();
  }

  function initMobileShare() {
    const btnMobileShare = document.getElementById("btnMobileShare");
    const qrModal = document.getElementById("qrModal");
    const closeQrModal = document.getElementById("closeQrModal");
    const qrContainer = document.getElementById("qrContainer");
    const txtQrUrl = document.getElementById("txtQrUrl");
    const btnCopyQrUrl = document.getElementById("btnCopyQrUrl");
    
    if (!btnMobileShare || !qrModal) return;

    btnMobileShare.addEventListener("click", () => {
      let shareUrl = window.location.href;
      
      const host = window.location.hostname;
      const isLocal = host === "localhost" || host === "127.0.0.1";
      if (isLocal) {
        const txtShareUrl = document.getElementById("txtShareUrl");
        const txtLanShareUrl = document.getElementById("txtLanShareUrl");
        const activeView = document.getElementById("share-active-view");
        
        if (activeView && activeView.style.display !== "none" && txtShareUrl && txtShareUrl.value) {
          shareUrl = txtShareUrl.value;
        } else if (txtLanShareUrl && txtLanShareUrl.value) {
          shareUrl = txtLanShareUrl.value;
        }
      }
      
      showQRModal(shareUrl);
    });

    function showQRModal(url) {
      if (!window.QRCode) {
        console.error("qrcode.js library not loaded!");
        return;
      }
      
      qrContainer.innerHTML = "";
      new window.QRCode(qrContainer, {
        text: url,
        width: 200,
        height: 200,
        colorDark: "#18181b",
        colorLight: "#ffffff",
        correctLevel: window.QRCode.CorrectLevel.H
      });
      
      txtQrUrl.value = url;
      qrModal.classList.add("active");
    }

    closeQrModal.addEventListener("click", () => {
      qrModal.classList.remove("active");
    });
    
    qrModal.addEventListener("click", (e) => {
      if (e.target === qrModal) {
        qrModal.classList.remove("active");
      }
    });

    btnCopyQrUrl.addEventListener("click", () => {
      navigator.clipboard.writeText(txtQrUrl.value);
      const originalText = btnCopyQrUrl.textContent;
      btnCopyQrUrl.textContent = "Đã chép";
      setTimeout(() => { btnCopyQrUrl.textContent = originalText; }, 2000);
    });

    const btnQrLanShare = document.getElementById("btnQrLanShare");
    if (btnQrLanShare) {
      btnQrLanShare.addEventListener("click", () => {
        const txtLanShareUrl = document.getElementById("txtLanShareUrl");
        if (txtLanShareUrl && txtLanShareUrl.value) {
          showQRModal(txtLanShareUrl.value);
        }
      });
    }

    const btnQrPublicShare = document.getElementById("btnQrPublicShare");
    if (btnQrPublicShare) {
      btnQrPublicShare.addEventListener("click", () => {
        const txtShareUrl = document.getElementById("txtShareUrl");
        if (txtShareUrl && txtShareUrl.value) {
          showQRModal(txtShareUrl.value);
        }
      });
    }
  }
})();

// ================================================================
// VISITOR COUNTER BADGE
// Chỉ kích hoạt khi chạy trên domain công khai (không phải localhost)
// Dịch vụ: hits.seeyoufarm.com — hiện "Hôm nay / Tổng lượt xem"
// ================================================================
(function initVisitorBadge() {
  const badge = document.getElementById("visitorBadge");
  if (!badge) return;

  const host = window.location.hostname;
  const isPublic = host && host !== "localhost" && host !== "127.0.0.1" && host !== "0.0.0.0";
  if (!isPublic) return;

  // Chuẩn hoá URL trang hiện tại (bỏ query string & hash để đếm ổn định)
  const pageUrl = encodeURIComponent(
    window.location.origin + window.location.pathname
  );

  // Badge SVG trả về hình ảnh dạng: [👁 icon] [Hôm nay: N / Tổng: M]
  const badgeUrl =
    "https://hits.seeyoufarm.com/api/count/incr/badge.svg" +
    "?url=" + pageUrl +
    "&count_bg=%232563eb" +    // Màu số đếm: xanh dương Zinc
    "&title_bg=%2318181b" +    // Màu nhãn: đen Zinc
    "&icon=eye&icon_color=%23ffffff" +
    "&title=L%C6%B0%E1%BB%A3t+xem" +  // "Lượt xem"
    "&edge_flat=true";           // Bo góc phẳng (flat style)

  badge.src = badgeUrl;
  badge.alt = "Lượt xem hôm nay / tổng";
})();

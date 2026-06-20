// ============================================================
// store.js — Quản lý State + Constants + Helpers dùng chung
// ============================================================

import { BASEMAPS } from "./config/basemaps.js";
export { BASEMAPS };

export const state = {
  collection: null,
  features: [],
  contextLayers: [],
  contextItems: [],
  contextIndex: null,
  featureIndex: null,
  filtered: [],
  bbox: null,
  selected: null,
  hovered: null,
  zoom: 1,
  panX: 0,
  panY: 0,
  dragging: false,
  moved: false,
  lastX: 0,
  lastY: 0,
  chartSlices: { land: [], group: [] },
  selectedChartSlice: { land: null, group: null },
  hoveredChartSlice: { land: null, group: null },
  chartAnimation: { key: null, startedAt: 0 },
  basemapId: "osm",
  view3d: false,
};

export let isLightMode = false;
export function setLightMode(v) { isLightMode = v; }

export function selectedBasemap() {
  return BASEMAPS.find(item => item.id === state.basemapId) || BASEMAPS[1];
}

export const LAND_GROUPS = [
  { key: "agriculture", label: "Đất nông nghiệp", color: "#f7d154",
    codes: ["NNP","SXN","CHN","LUA","LUC","LUK","LUN","HNK","BHK","NHK","CLN","LNP","RSX","RSN","RST","RSM","RPH","RPN","RPT","RPM","RDD","RDN","RDT","RDM","NTS","LMU","NKH"] },
  { key: "residential", label: "Đất ở", color: "#f0a6f0", codes: ["OTC","ONT","ODT"] },
  { key: "industrial", label: "Sản xuất/công nghiệp", color: "#d28bd2",
    codes: ["CSK","SKK","SKN","SKT","TMD","SKC","SKS","SKX","CCC"] },
  { key: "public", label: "Công cộng - hạ tầng", color: "#ff9b76",
    codes: ["PNN","CDG","COC","TSC","CQP","CAN","DSN","DTS","DVH","DXH","DYT","DGD","DTT","DKH","DNG","DSK","DGT","DTL","DDT","DDL","DSH","DKV","DNL","DBV","DCH","DRA","DCK","TON","TIN","NTD","SON","MNC","PNK","MVB","MVT","MVR","MVK"] },
  { key: "unused", label: "Đất chưa sử dụng", color: "#e6e6c8", codes: ["CSD","BCS","DCS","NCS"] },
  { key: "other", label: "Khác", color: "#8ab4f8", codes: [] },
];

const LAND_GROUP_BY_CODE = new Map();
for (const g of LAND_GROUPS) for (const c of g.codes) LAND_GROUP_BY_CODE.set(c, g);

const FALLBACK_LAND_COLORS = { Khac: "#8ab4f8" };

// ---------- Helpers ----------
export function formatNumber(value, decimals = 0) {
  if (value === null || value === undefined || value === "") return "--";
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  return n.toLocaleString("vi-VN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function escapeHtml(v) {
  return String(v ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
}

export function prop(feature, names) {
  const props = feature.properties || {};
  const lookup = new Map(Object.keys(props).map(k => [k.toLowerCase(), k]));
  for (const name of names) {
    const key = lookup.get(name.toLowerCase());
    if (key && props[key] !== null && props[key] !== undefined && props[key] !== "") return props[key];
  }
  return "";
}

export function landCode(feature) {
  return prop(feature, ["land_code","KHLOAIDAT","MALOAIDAT","LOAIDAT","MDSD","MDSD2003"]) || "Khac";
}

export function landColor(featureOrCode) {
  const code = typeof featureOrCode === "string" ? featureOrCode : landCode(featureOrCode);
  const normalized = String(code || "Khac").toUpperCase();
  const metadataColors = state.collection?.metadata?.land_type_colors || {};
  const featureColor = typeof featureOrCode === "string" ? "" : prop(featureOrCode, ["land_color"]);
  return featureColor || metadataColors[normalized] || landGroup(normalized).color || FALLBACK_LAND_COLORS[code] || FALLBACK_LAND_COLORS.Khac;
}

export function landGroup(featureOrCode) {
  const code = typeof featureOrCode === "string" ? featureOrCode : landCode(featureOrCode);
  return LAND_GROUP_BY_CODE.get(String(code || "").toUpperCase()) || LAND_GROUPS[LAND_GROUPS.length - 1];
}

export function featureTitle(feature) {
  const p = feature.properties;
  if (p.parcel_label) return `Thửa ${p.parcel_label}`;
  const sheet = prop(feature, ["SHBANDO","SOTO","SOTOBD","TOBD","MAPSHEET"]);
  const parcel = prop(feature, ["SHTHUA","SOTHUA","THUA","SOTHUTUTHUA"]);
  if (sheet || parcel) return `Tờ ${sheet || "--"} · Thửa ${parcel || "--"}`;
  return `Đối tượng ${feature.id || "--"}`;
}

export function featureArea(feature) {
  return prop(feature, ["area_m2","DIENTICH","DIENTICHPL","AREA","Shape_Area"]);
}

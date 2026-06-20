// ============================================================
// basemaps.js — Cấu hình nguồn bản đồ nền
// ============================================================

export const BASEMAPS = [
  {
    id: "none",
    label: "Không nền",
    url: "",
    attribution: "",
    zmin: 0,
    zmax: 22,
    experimental: false,
  },
  {
    id: "osm",
    label: "OSM Standard",
    url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: "© OpenStreetMap contributors",
    zmin: 0,
    zmax: 19,
    experimental: false,
  },
  {
    id: "carto_light",
    label: "Carto Light",
    url: "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
    attribution: "© CARTO, © OpenStreetMap contributors",
    zmin: 0,
    zmax: 20,
    experimental: false,
  },
  {
    id: "carto_dark",
    label: "Carto Dark",
    url: "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
    attribution: "© CARTO, © OpenStreetMap contributors",
    zmin: 0,
    zmax: 20,
    experimental: false,
  },
  {
    id: "esri_street",
    label: "Esri Street",
    url: "https://server.arcgisonline.com/arcgis/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    attribution: "Tiles © Esri",
    zmin: 0,
    zmax: 22,
    experimental: false,
  },
  {
    id: "esri_imagery",
    label: "Esri Imagery",
    url: "https://server.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attribution: "Imagery © Esri",
    zmin: 0,
    zmax: 22,
    experimental: false,
  },
  {
    id: "google_hybrid",
    label: "Google Hybrid (thử nghiệm)",
    url: "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
    attribution: "Google Hybrid (experimental)",
    zmin: 0,
    zmax: 22,
    experimental: true,
  },
];

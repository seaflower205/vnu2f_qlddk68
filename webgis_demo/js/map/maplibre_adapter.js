// ============================================================
// maplibre_adapter.js — MapLibre GL JS Renderer Adapter
// ============================================================

import { BASEMAPS } from "../store.js";

let map = null;
let currentGeoJSON = null;
let currentWGS84Collection = null;
let currentBasemap = null;
let currentDarkMode = false;
let current3DMode = false;
let selectedFeatureId = null;
let hoveredFeatureId = null;

let clickCallback = null;
let hoverCallback = null;

const MERCATOR_LIMIT = 20037508.342789244;

// Chuyển đổi tọa độ EPSG:3857 sang EPSG:4326 (WGS84)
function mercatorToLonLat(x, y) {
  return [
    (x / MERCATOR_LIMIT) * 180,
    (Math.atan(Math.exp((y / MERCATOR_LIMIT) * Math.PI)) * 360) / Math.PI - 90
  ];
}

function transformCoords(coords, type) {
  if (!coords) return coords;
  if (type === "Point") {
    return mercatorToLonLat(coords[0], coords[1]);
  }
  if (type === "LineString" || type === "MultiPoint") {
    return coords.map(c => mercatorToLonLat(c[0], c[1]));
  }
  if (type === "Polygon" || type === "MultiLineString") {
    return coords.map(ring => ring.map(c => mercatorToLonLat(c[0], c[1])));
  }
  if (type === "MultiPolygon") {
    return coords.map(poly => poly.map(ring => ring.map(c => mercatorToLonLat(c[0], c[1]))));
  }
  return coords;
}

function convertGeoJSONToWGS84(geojson) {
  if (!geojson) return null;
  const clone = JSON.parse(JSON.stringify(geojson));
  
  if (clone.type === "FeatureCollection") {
    if (clone.features) {
      clone.features.forEach(f => {
        if (f.geometry) {
          f.geometry.coordinates = transformCoords(f.geometry.coordinates, f.geometry.type);
        }
      });
    }
    if (clone.context_layers) {
      clone.context_layers.forEach(layer => {
        if (layer.features) {
          layer.features.forEach(f => {
            if (f.geometry) {
              f.geometry.coordinates = transformCoords(f.geometry.coordinates, f.geometry.type);
            }
          });
        }
      });
    }
  } else if (clone.type === "Feature") {
    if (clone.geometry) {
      clone.geometry.coordinates = transformCoords(clone.geometry.coordinates, clone.geometry.type);
    }
  }
  return clone;
}

function getStyleForBasemap(basemap, darkMode) {
  if (basemap.id === "osm") {
    return darkMode 
      ? "https://tiles.openfreemap.org/styles/dark"
      : "https://tiles.openfreemap.org/styles/liberty";
  }
  if (basemap.id === "none" || !basemap.url) {
    return {
      version: 8,
      sources: {},
      layers: [
        {
          id: "background",
          type: "background",
          paint: {
            "background-color": darkMode ? "#030712" : "#e5e7eb"
          }
        }
      ]
    };
  }
  
  let tilesUrls = [basemap.url];
  if (basemap.url.includes("{s}")) {
    const subdomains = basemap.subdomains || ["a", "b", "c"];
    tilesUrls = subdomains.map(s => basemap.url.replace("{s}", s));
  }
  return {
    version: 8,
    sources: {
      "raster-tiles": {
        type: "raster",
        tiles: tilesUrls,
        tileSize: 256,
        attribution: basemap.attribution || ""
      }
    },
    layers: [
      {
        id: "raster-tiles-layer",
        type: "raster",
        source: "raster-tiles",
        minzoom: basemap.zmin ?? 0,
        maxzoom: basemap.zmax ?? 22
      }
    ]
  };
}

const heightExpression = [
  "match",
  ["upcase", ["coalesce", ["get", "land_code"], "KHAC"]],
  ["ONT", "ODT"], 15,
  ["SKC", "TMD"], 18,
  ["TSC", "CQP"], 12,
  ["LUC", "BHK", "CLN"], 2.5,
  ["SON", "MNC"], 0.2,
  7 // default height
];

function addParcelsSourcesAndLayers() {
  if (!map) return;
  if (map.getSource("parcels")) return;

  const features = currentWGS84Collection ? currentWGS84Collection.features : [];

  map.addSource("parcels", {
    type: "geojson",
    data: {
      type: "FeatureCollection",
      features: features
    }
  });

  const opacityExpression = [
    "case",
    ["boolean", ["get", "qgis_filtered_out"], false], 0.05,
    0.45
  ];

  const strokeOpacityExpression = [
    "case",
    ["boolean", ["get", "qgis_filtered_out"], false], 0.02,
    1.0
  ];

  const baseStrokeColor = currentDarkMode ? "rgba(255,255,255,0.15)" : "rgba(0,0,0,0.15)";

  // 1. Normal fill
  map.addLayer({
    id: "parcels-fill",
    type: "fill",
    source: "parcels",
    paint: {
      "fill-color": ["coalesce", ["get", "land_color"], "#8ab4f8"],
      "fill-opacity": opacityExpression
    },
    layout: {
      visibility: current3DMode ? "none" : "visible"
    }
  });

  // 2. Normal stroke
  map.addLayer({
    id: "parcels-stroke",
    type: "line",
    source: "parcels",
    paint: {
      "line-color": baseStrokeColor,
      "line-width": 1,
      "line-opacity": strokeOpacityExpression
    },
    layout: {
      visibility: current3DMode ? "none" : "visible"
    }
  });

  // 3. Hovered fill
  map.addLayer({
    id: "parcels-hover-fill",
    type: "fill",
    source: "parcels",
    paint: {
      "fill-color": ["coalesce", ["get", "land_color"], "#8ab4f8"],
      "fill-opacity": 0.7
    },
    filter: ["==", ["id"], hoveredFeatureId !== null ? hoveredFeatureId : -1],
    layout: {
      visibility: current3DMode ? "none" : "visible"
    }
  });

  // 4. Hovered stroke
  map.addLayer({
    id: "parcels-hover-stroke",
    type: "line",
    source: "parcels",
    paint: {
      "line-color": "#60a5fa",
      "line-width": 2
    },
    filter: ["==", ["id"], hoveredFeatureId !== null ? hoveredFeatureId : -1],
    layout: {
      visibility: current3DMode ? "none" : "visible"
    }
  });

  // 5. Selected fill
  map.addLayer({
    id: "parcels-selected-fill",
    type: "fill",
    source: "parcels",
    paint: {
      "fill-color": "#fcd34d",
      "fill-opacity": 0.85
    },
    filter: ["==", ["id"], selectedFeatureId !== null ? selectedFeatureId : -1],
    layout: {
      visibility: current3DMode ? "none" : "visible"
    }
  });

  // 6. Selected stroke
  map.addLayer({
    id: "parcels-selected-stroke",
    type: "line",
    source: "parcels",
    paint: {
      "line-color": "#fcd34d",
      "line-width": 2.5
    },
    filter: ["==", ["id"], selectedFeatureId !== null ? selectedFeatureId : -1],
    layout: {
      visibility: current3DMode ? "none" : "visible"
    }
  });

  // 3D Extrusion normal
  map.addLayer({
    id: "parcels-extrusion",
    type: "fill-extrusion",
    source: "parcels",
    paint: {
      "fill-extrusion-color": [
        "case",
        ["boolean", ["get", "qgis_filtered_out"], false],
        "rgba(128, 128, 128, 0.05)",
        ["coalesce", ["get", "land_color"], "#8ab4f8"]
      ],
      "fill-extrusion-height": heightExpression,
      "fill-extrusion-base": 0,
      "fill-extrusion-opacity": 0.6
    },
    layout: {
      visibility: current3DMode ? "visible" : "none"
    }
  });

  // 3D Extrusion hovered
  map.addLayer({
    id: "parcels-extrusion-hovered",
    type: "fill-extrusion",
    source: "parcels",
    paint: {
      "fill-extrusion-color": ["coalesce", ["get", "land_color"], "#8ab4f8"],
      "fill-extrusion-height": heightExpression,
      "fill-extrusion-base": 0,
      "fill-extrusion-opacity": 0.8
    },
    filter: ["==", ["id"], hoveredFeatureId !== null ? hoveredFeatureId : -1],
    layout: {
      visibility: current3DMode ? "visible" : "none"
    }
  });

  // 3D Extrusion selected
  map.addLayer({
    id: "parcels-extrusion-selected",
    type: "fill-extrusion",
    source: "parcels",
    paint: {
      "fill-extrusion-color": "#fcd34d",
      "fill-extrusion-height": heightExpression,
      "fill-extrusion-base": 0,
      "fill-extrusion-opacity": 0.9
    },
    filter: ["==", ["id"], selectedFeatureId !== null ? selectedFeatureId : -1],
    layout: {
      visibility: current3DMode ? "visible" : "none"
    }
  });
}

function addContextLayersSourcesAndLayers() {
  if (!map || !currentWGS84Collection) return;
  const layers = currentWGS84Collection.context_layers || [];

  layers.forEach(layer => {
    const sourceId = `context-${layer.name}`;
    if (map.getSource(sourceId)) return;

    map.addSource(sourceId, {
      type: "geojson",
      data: {
        type: "FeatureCollection",
        features: layer.features || []
      }
    });

    const geomType = layer.geometry_type;
    
    if (geomType === "polygon") {
      map.addLayer({
        id: `context-layer-fill-${layer.name}`,
        type: "fill",
        source: sourceId,
        paint: {
          "fill-color": ["coalesce", ["get", "webgis_color"], "#22c55e"],
          "fill-opacity": 0.14
        }
      });
      map.addLayer({
        id: `context-layer-line-${layer.name}`,
        type: "line",
        source: sourceId,
        paint: {
          "line-color": ["coalesce", ["get", "webgis_color"], "#22c55e"],
          "line-width": 1.2,
          "line-opacity": 0.45
        }
      });
      map.addLayer({
        id: `context-layer-label-${layer.name}`,
        type: "symbol",
        source: sourceId,
        layout: {
          "text-field": ["coalesce", ["get", "webgis_label"], ""],
          "text-size": 11,
          "symbol-placement": "point"
        },
        paint: {
          "text-color": ["coalesce", ["get", "webgis_color"], "#22c55e"],
          "text-halo-color": currentDarkMode ? "#09090b" : "#ffffff",
          "text-halo-width": 1.5
        }
      });
    } else if (geomType === "line") {
      map.addLayer({
        id: `context-layer-line-${layer.name}`,
        type: "line",
        source: sourceId,
        paint: {
          "line-color": ["coalesce", ["get", "webgis_color"], "#f97316"],
          "line-width": 2.4,
          "line-opacity": 0.88
        }
      });
      map.addLayer({
        id: `context-layer-label-${layer.name}`,
        type: "symbol",
        source: sourceId,
        layout: {
          "text-field": ["coalesce", ["get", "webgis_label"], ""],
          "text-size": 11,
          "symbol-placement": "line"
        },
        paint: {
          "text-color": ["coalesce", ["get", "webgis_color"], "#f97316"],
          "text-halo-color": currentDarkMode ? "#09090b" : "#ffffff",
          "text-halo-width": 1.5
        }
      });
    } else if (geomType === "point") {
      map.addLayer({
        id: `context-layer-point-${layer.name}`,
        type: "circle",
        source: sourceId,
        paint: {
          "circle-color": ["coalesce", ["get", "webgis_color"], "#7c3aed"],
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2,
          "circle-radius": 6
        }
      });
      map.addLayer({
        id: `context-layer-label-${layer.name}`,
        type: "symbol",
        source: sourceId,
        layout: {
          "text-field": ["coalesce", ["get", "webgis_label"], ""],
          "text-size": 11,
          "text-offset": [0, 1.2],
          "text-anchor": "top"
        },
        paint: {
          "text-color": ["coalesce", ["get", "webgis_color"], "#7c3aed"],
          "text-halo-color": currentDarkMode ? "#09090b" : "#ffffff",
          "text-halo-width": 1.5
        }
      });
    }
  });
}

function onStyleLoad() {
  addParcelsSourcesAndLayers();
  addContextLayersSourcesAndLayers();
  updateSelectionHighlight();
  updateHoverHighlight();
}

function updateSelectionHighlight() {
  if (!map) return;
  const id = selectedFeatureId !== null ? selectedFeatureId : -1;
  
  if (map.getLayer("parcels-selected-fill")) {
    map.setFilter("parcels-selected-fill", ["==", ["id"], id]);
  }
  if (map.getLayer("parcels-selected-stroke")) {
    map.setFilter("parcels-selected-stroke", ["==", ["id"], id]);
  }
  if (map.getLayer("parcels-extrusion-selected")) {
    map.setFilter("parcels-extrusion-selected", ["==", ["id"], id]);
  }
}

function updateHoverHighlight() {
  if (!map) return;
  const id = hoveredFeatureId !== null ? hoveredFeatureId : -1;
  
  if (map.getLayer("parcels-hover-fill")) {
    map.setFilter("parcels-hover-fill", ["==", ["id"], id]);
  }
  if (map.getLayer("parcels-hover-stroke")) {
    map.setFilter("parcels-hover-stroke", ["==", ["id"], id]);
  }
  if (map.getLayer("parcels-extrusion-hovered")) {
    map.setFilter("parcels-extrusion-hovered", ["==", ["id"], id]);
  }
}

function getFeatureWGS84BBox(feature) {
  if (feature._wgs84_bbox) return feature._wgs84_bbox;
  if (feature._bbox) {
    const [minX, minY, maxX, maxY] = feature._bbox;
    const llMin = mercatorToLonLat(minX, minY);
    const llMax = mercatorToLonLat(maxX, maxY);
    feature._wgs84_bbox = [
      Math.min(llMin[0], llMax[0]),
      Math.min(llMin[1], llMax[1]),
      Math.max(llMin[0], llMax[0]),
      Math.max(llMin[1], llMax[1])
    ];
    return feature._wgs84_bbox;
  }
  return null;
}

// ---- Exported API ----

export function initMapLibre(containerId, options = {}) {
  currentDarkMode = options.darkMode || false;
  const basemapId = options.basemapId || "osm";
  const basemap = BASEMAPS.find(b => b.id === basemapId) || BASEMAPS[1];
  currentBasemap = basemap;
  current3DMode = options.view3d || false;

  const style = getStyleForBasemap(basemap, currentDarkMode);

  map = new maplibregl.Map({
    container: containerId,
    style: style,
    pitch: current3DMode ? 45 : 0,
    bearing: current3DMode ? -15 : 0,
    attributionControl: false
  });

  map.on("style.load", () => {
    onStyleLoad();
  });

  map.on("styledata", () => {
    if (map && !map.getSource("parcels") && currentWGS84Collection) {
      onStyleLoad();
    }
  });

  map.on("click", e => {
    const features = map.queryRenderedFeatures(e.point, {
      layers: ["parcels-fill", "parcels-extrusion"]
    });
    
    if (features && features.length > 0) {
      const fId = features[0].id;
      const origFeature = currentGeoJSON?.features?.find(f => f.id === fId);
      if (origFeature && clickCallback) {
        clickCallback(origFeature);
      }
    } else {
      if (clickCallback) {
        clickCallback(null);
      }
    }
  });

  map.on("mousemove", e => {
    const features = map.queryRenderedFeatures(e.point, {
      layers: ["parcels-fill", "parcels-extrusion"]
    });

    if (features && features.length > 0) {
      map.getCanvas().style.cursor = "pointer";
      const fId = features[0].id;
      if (fId !== hoveredFeatureId) {
        hoveredFeatureId = fId;
        updateHoverHighlight();
        const origFeature = currentGeoJSON?.features?.find(f => f.id === fId);
        if (hoverCallback) {
          hoverCallback(origFeature, e.lngLat);
        }
      }
    } else {
      map.getCanvas().style.cursor = "";
      if (hoveredFeatureId !== null) {
        hoveredFeatureId = null;
        updateHoverHighlight();
        if (hoverCallback) {
          hoverCallback(null, e.lngLat);
        }
      } else {
        if (hoverCallback) {
          hoverCallback(null, e.lngLat);
        }
      }
    }
  });

  return map;
}

export function setGeoJSON(collection) {
  currentGeoJSON = collection;
  currentWGS84Collection = convertGeoJSONToWGS84(collection);
  
  if (map && map.getSource("parcels")) {
    map.getSource("parcels").setData({
      type: "FeatureCollection",
      features: currentWGS84Collection ? currentWGS84Collection.features : []
    });
    
    const layers = currentWGS84Collection ? currentWGS84Collection.context_layers || [] : [];
    layers.forEach(layer => {
      const sourceId = `context-${layer.name}`;
      const source = map.getSource(sourceId);
      if (source) {
        source.setData({
          type: "FeatureCollection",
          features: layer.features || []
        });
      }
    });
  }
}

export function setParcelsStyle(darkMode) {
  currentDarkMode = darkMode;
  if (!map) return;

  const baseStrokeColor = darkMode ? "rgba(255,255,255,0.15)" : "rgba(0,0,0,0.15)";
  
  if (map.getLayer("parcels-stroke")) {
    map.setPaintProperty("parcels-stroke", "line-color", baseStrokeColor);
  }

  if (currentWGS84Collection && currentWGS84Collection.context_layers) {
    currentWGS84Collection.context_layers.forEach(layer => {
      const labelLayerId = `context-layer-label-${layer.name}`;
      if (map.getLayer(labelLayerId)) {
        map.setPaintProperty(labelLayerId, "text-halo-color", darkMode ? "#09090b" : "#ffffff");
      }
    });
  }
}

export function setBasemap(basemapId) {
  const basemap = BASEMAPS.find(b => b.id === basemapId) || BASEMAPS[1];
  currentBasemap = basemap;
  if (!map) return;

  const style = getStyleForBasemap(basemap, currentDarkMode);
  map.setStyle(style);
}

export function set3DMode(enabled) {
  current3DMode = enabled;
  if (!map) return;

  const pitch = enabled ? 45 : 0;
  const bearing = enabled ? -15 : 0;
  map.easeTo({ pitch, bearing, duration: 800 });

  const layers2D = [
    "parcels-fill", "parcels-stroke", 
    "parcels-hover-fill", "parcels-hover-stroke",
    "parcels-selected-fill", "parcels-selected-stroke"
  ];
  const layers3D = [
    "parcels-extrusion", 
    "parcels-extrusion-hovered", 
    "parcels-extrusion-selected"
  ];

  layers2D.forEach(layer => {
    if (map.getLayer(layer)) {
      map.setLayoutProperty(layer, "visibility", enabled ? "none" : "visible");
    }
  });

  layers3D.forEach(layer => {
    if (map.getLayer(layer)) {
      map.setLayoutProperty(layer, "visibility", enabled ? "visible" : "none");
    }
  });
}

export function setSelected(feature) {
  selectedFeatureId = feature ? feature.id : null;
  updateSelectionHighlight();
}

export function setHovered(feature) {
  hoveredFeatureId = feature ? feature.id : null;
  updateHoverHighlight();
}

export function onFeatureClick(cb) {
  clickCallback = cb;
}

export function onFeatureHover(cb) {
  hoverCallback = cb;
}

export function flyToFeature(feature) {
  if (!map || !feature) return;
  const bbox = getFeatureWGS84BBox(feature);
  if (bbox) {
    map.fitBounds([[bbox[0], bbox[1]], [bbox[2], bbox[3]]], {
      padding: 120,
      maxZoom: 18,
      duration: 1000
    });
  }
}

export function flyToCoordinate(lon, lat) {
  if (!map) return;
  map.flyTo({
    center: [lon, lat],
    zoom: 17,
    duration: 1000
  });
}

export function getMapInstance() {
  return map;
}

export function destroy() {
  if (map) {
    map.remove();
    map = null;
  }
}

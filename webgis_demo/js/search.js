// ============================================================
// search.js — Nominatim search + local highlight filter + reverse geocoding
// ============================================================

import { state } from "./store.js";

// Cache for geocoding queries and reverse geocoding coordinates
const searchCache = new Map();
const reverseCache = new Map();

// Track timestamp of last API call to enforce rate limiting
let lastNominatimCall = 0;

async function rateLimitNominatim() {
  const now = Date.now();
  const wait = 1100 - (now - lastNominatimCall);
  if (wait > 0) {
    await new Promise(resolve => setTimeout(resolve, wait));
  }
  lastNominatimCall = Date.now();
}

function showFriendlyError(message) {
  console.warn("WebGIS Geocoding Warning:", message);
  const statusEl = document.getElementById("mapStatus");
  if (statusEl) {
    statusEl.innerHTML = `<span style="color:#ef4444; font-weight:bold;">${message}</span>`;
    setTimeout(() => {
      statusEl.innerHTML = "Sẵn sàng";
    }, 4000);
  }
}

export async function searchAddress(query) {
  if (!query) return [];
  
  const cacheKey = query.trim().toLowerCase();
  if (searchCache.has(cacheKey)) {
    return searchCache.get(cacheKey);
  }

  // Rate limiting throttle
  await rateLimitNominatim();

  const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&countrycodes=vn&format=json&accept-language=vi`;
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 6000);

  try {
    const res = await fetch(url, { 
      headers: { "User-Agent": "VNU2F-WebGIS-Demo" },
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (res.status === 429) {
      showFriendlyError("Yêu cầu quá nhanh. Đang sử dụng dữ liệu offline.");
      return [];
    }

    if (res.ok) {
      const data = await res.json();
      searchCache.set(cacheKey, data);
      return data;
    }
  } catch (e) {
    clearTimeout(timeoutId);
    if (e.name === 'AbortError') {
      showFriendlyError("Không phản hồi từ Nominatim (Timeout).");
    } else {
      console.error("Nominatim search error:", e);
    }
  }
  return [];
}

export async function reverseGeocode(lat, lon) {
  const cacheKey = `${Number(lat).toFixed(5)},${Number(lon).toFixed(5)}`;
  if (reverseCache.has(cacheKey)) {
    return reverseCache.get(cacheKey);
  }

  // Rate limiting throttle
  await rateLimitNominatim();

  const url = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&accept-language=vi`;
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 6000);

  try {
    const res = await fetch(url, { 
      headers: { "User-Agent": "VNU2F-WebGIS-Demo" },
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (res.status === 429) {
      showFriendlyError("Yêu cầu quá nhanh. Đang sử dụng dữ liệu offline.");
      return "";
    }

    if (res.ok) {
      const data = await res.json();
      const displayName = data.display_name || "";
      reverseCache.set(cacheKey, displayName);
      return displayName;
    }
  } catch (e) {
    clearTimeout(timeoutId);
    if (e.name === 'AbortError') {
      showFriendlyError("Không phản hồi từ Nominatim (Timeout).");
    } else {
      console.error("Nominatim reverse geocoding error:", e);
    }
  }
  return "";
}

export function localFilterParcels(query) {
  if (!query) {
    state.filtered = [];
    state.features.forEach(f => {
      if (f.properties) f.properties.qgis_filtered_out = false;
    });
    return state.features;
  }
  
  const q = query.toLowerCase().trim();
  const matched = [];
  
  state.features.forEach(f => {
    const p = f.properties || {};
    const name = String(p.TENCHU || p.chusudung || p.TEN_CHU || p.chu_sd || p.name || "").toLowerCase();
    const type = String(p.land_code || p.KHLOAIDAT || p.MALOAIDAT || p.LOAIDAT || "").toLowerCase();
    const label = String(p.parcel_label || "").toLowerCase();
    const sothua = String(p.SHTHUA || p.SOTHUA || p.THUA || "").toLowerCase();
    const soto = String(p.SHBANDO || p.SOTO || p.SOTOBD || "").toLowerCase();
    
    // So khớp nếu chứa từ khóa
    const isMatch = name.includes(q) || type.includes(q) || label.includes(q) || sothua === q || soto === q;
    
    if (isMatch) {
      p.qgis_filtered_out = false;
      matched.push(f);
    } else {
      p.qgis_filtered_out = true;
    }
  });
  
  state.filtered = matched;
  return matched;
}

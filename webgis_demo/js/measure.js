// ============================================================
// measure.js — Polyline distance + Polygon area measurements
// ============================================================

import { worldToLonLat } from "./map/map.js";

let turfLoadPromise = null;

export function loadTurf() {
  if (window.turf) return Promise.resolve(window.turf);
  if (turfLoadPromise) return turfLoadPromise;

  turfLoadPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "js/vendor/turf.min.js?v=6.5.0";
    script.async = true;
    script.onload = () => resolve(window.turf);
    script.onerror = () => reject(new Error("Không tải được Turf local"));
    document.head.appendChild(script);
  }).catch(error => {
    console.warn(error.message);
    turfLoadPromise = null;
    return null;
  });

  return turfLoadPromise;
}

// Tính khoảng cách giữa 2 điểm dạng Web Mercator (EPSG:3857)
export function calculateDistance(points) {
  if (points.length < 2) return 0;
  
  // Nếu Turf local đã nạp, dùng geodesic chính xác hơn.
  if (window.turf) {
    try {
      const lonlats = points.map(p => {
        const ll = worldToLonLat(p[0], p[1]);
        return [ll.lon, ll.lat];
      });
      const line = window.turf.lineString(lonlats);
      return window.turf.length(line, { units: "meters" });
    } catch (e) {
      console.error("Turf.js distance error:", e);
    }
  }
  
  // Fallback: Euclidean corrected by latitude scale factor
  let dist = 0;
  for (let i = 1; i < points.length; i++) {
    const dx = points[i][0] - points[i - 1][0];
    const dy = points[i][1] - points[i - 1][1];
    dist += Math.hypot(dx, dy);
  }
  
  // Áp dụng hệ số co dãn Mercator dựa trên vĩ độ trung bình để tăng độ chính xác
  try {
    const mid = worldToLonLat(points[0][0], points[0][1]);
    const cosLat = Math.cos((mid.lat * Math.PI) / 180);
    return dist * cosLat;
  } catch (e) {
    return dist;
  }
}

// Tính diện tích đa giác (Polygon) dạng Web Mercator
export function calculateArea(points) {
  if (points.length < 3) return 0;
  
  // Đảm bảo vòng lặp khép kín
  const ring = [...points];
  if (ring[0][0] !== ring[ring.length - 1][0] || ring[0][1] !== ring[ring.length - 1][1]) {
    ring.push(ring[0]);
  }
  
  // Nếu Turf local đã nạp, dùng geodesic chính xác hơn.
  if (window.turf) {
    try {
      const lonlats = ring.map(p => {
        const ll = worldToLonLat(p[0], p[1]);
        return [ll.lon, ll.lat];
      });
      const poly = window.turf.polygon([lonlats]);
      return window.turf.area(poly);
    } catch (e) {
      console.error("Turf.js area error:", e);
    }
  }
  
  // Fallback: Shoelace formula corrected by cos^2(lat)
  let area = 0;
  for (let i = 0; i < ring.length - 1; i++) {
    area += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1];
  }
  area = Math.abs(area) / 2;
  
  try {
    const mid = worldToLonLat(ring[0][0], ring[0][1]);
    const cosLat = Math.cos((mid.lat * Math.PI) / 180);
    return area * cosLat * cosLat;
  } catch (e) {
    return area;
  }
}

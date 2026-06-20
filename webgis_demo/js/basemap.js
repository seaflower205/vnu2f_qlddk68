// ============================================================
// basemap.js — Basemap switcher utilities
// ============================================================

import { state, BASEMAPS } from "./store.js";

export function switchBasemap(id) {
  const found = BASEMAPS.find(b => b.id === id);
  if (found) {
    state.basemapId = id;
    return found;
  }
  return null;
}

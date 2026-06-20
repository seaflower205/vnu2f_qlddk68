import { state, isLightMode, formatNumber, landCode, landGroup, landColor, LAND_GROUPS } from "../store.js";

export function landSummary() {
  const counts = new Map(), areas = new Map();
  for (const f of state.features) {
    const code = landCode(f);
    counts.set(code, (counts.get(code) || 0) + 1);
    areas.set(code, (areas.get(code) || 0) + (Number(f.properties.area_m2) || 0));
  }
  return [...counts.keys()].sort((a, b) => counts.get(b) - counts.get(a))
    .map(code => ({ code, count: counts.get(code), area: areas.get(code) || 0, color: landColor(code) }));
}

export function groupSummary() {
  const groups = new Map();
  for (const g of LAND_GROUPS) groups.set(g.key, { ...g, count: 0, area: 0 });
  for (const f of state.features) {
    const g = landGroup(f); const item = groups.get(g.key);
    item.count += 1; item.area += Number(f.properties.area_m2) || 0;
  }
  return [...groups.values()].filter(i => i.count > 0);
}

function chartSliceKey(item) { return item.code || item.key || item.label; }

const sliceAnimState = { land: {}, group: {} };
const animatingCharts = { land: false, group: false };

function getSliceAnim(chartKey, key) {
  if (!sliceAnimState[chartKey][key]) {
    const isSelected = state.selectedChartSlice[chartKey] === key ? 1 : 0;
    const isHovered = state.hoveredChartSlice[chartKey] === key ? 1 : 0;
    const opacity = (state.hoveredChartSlice[chartKey] === null || state.hoveredChartSlice[chartKey] === key) ? 1.0 : 0.55;
    sliceAnimState[chartKey][key] = { selected: isSelected, hovered: isHovered, opacity };
  }
  return sliceAnimState[chartKey][key];
}

export function drawDonut(canvasEl, context, summary, totalSelector, totalValue, chartKey) {
  if (!state.collection || !canvasEl) return;
  const rect = canvasEl.getBoundingClientRect();
  if (rect.width <= 0 || rect.height <= 0) return; // Guard against hidden canvas throwing negative radius DOMException
  context.clearRect(0, 0, rect.width, rect.height);
  state.chartSlices[chartKey] = [];
  const total = summary.reduce((s, i) => s + i.count, 0);
  
  const totalEl = document.querySelector(totalSelector);
  if (totalEl) {
    totalEl.textContent = formatNumber(totalValue ?? total);
  }

  const cx = rect.width / 2, cy = rect.height / 2;
  const radius = Math.min(rect.width, rect.height) / 2 - 26; // Tăng biên an toàn để tránh bị khuất ở cạnh dưới/phải
  if (radius <= 0) return; // Guard chống lỗi DOMException bán kính âm khi canvas ẩn hoặc đang dựng
  const innerRadius = radius * 0.72; // Donut mảnh hơn kiểu modern/Shadcn (0.72 thay vì 0.58)
  
  if (!total) {
    context.beginPath(); context.arc(cx, cy, radius, 0, Math.PI * 2);
    context.strokeStyle = "rgba(128,128,128,0.15)"; context.lineWidth = radius - innerRadius; context.stroke(); return;
  }

  let start = -Math.PI / 2;
  for (const item of summary) {
    const key = chartSliceKey(item);
    const angle = (item.count / total) * Math.PI * 2, end = start + angle, mid = start + angle / 2;
    
    // Get dynamically animated progress values
    const anim = getSliceAnim(chartKey, key);
    const offset = 4.5 * anim.selected + 2.5 * anim.hovered; // Tinh tế, vừa phải hơn (4.5px / 2.5px)
    const dcx = cx + Math.cos(mid) * offset, dcy = cy + Math.sin(mid) * offset;
    const dr = radius + 1.5 * anim.selected + 1.0 * anim.hovered;
    
    // Save displaced coordinates for precise hit testing
    state.chartSlices[chartKey].push({ 
      key, 
      item, 
      start, 
      end, 
      cx: dcx, 
      cy: dcy, 
      innerRadius, 
      outerRadius: dr + 10 
    });
    
    context.save();
    context.globalAlpha = anim.opacity; // Dim các phần không active
    
    context.beginPath(); context.moveTo(dcx, dcy); context.arc(dcx, dcy, dr, start, end); context.closePath();
    context.fillStyle = item.color; context.fill();
    
    // Smooth border width and contrast
    const highlight = Math.max(anim.selected, anim.hovered);
    const hasHighlight = highlight > 0.15;
    context.strokeStyle = hasHighlight ? (isLightMode ? "#09090b" : "#fafafa") : (isLightMode ? "#e4e4e7" : "#1f1f23");
    context.lineWidth = 1.5 + 1.0 * highlight; 
    context.stroke();
    
    context.restore();
    
    start = end;
  }
  
  // Đục lỗ ở giữa để thành vòng Donut
  context.beginPath(); context.arc(cx, cy, innerRadius, 0, Math.PI * 2);
  context.globalCompositeOperation = "destination-out"; context.fill();
  context.globalCompositeOperation = "source-over";
}

export function sliceAt(chartKey, x, y) {
  for (const s of (state.chartSlices[chartKey] || [])) {
    const dx = x - s.cx, dy = y - s.cy, d = Math.hypot(dx, dy);
    if (d < s.innerRadius || d > s.outerRadius) continue;
    let a = Math.atan2(dy, dx); if (a < -Math.PI / 2) a += Math.PI * 2;
    if (a >= s.start && a <= s.end) return s;
  }
  return null;
}

export function animateChartSelection(chartKey, drawLandCb, drawGroupCb) {
  const cb = (chartKey === "land") ? drawLandCb : drawGroupCb;
  if (animatingCharts[chartKey]) return;
  animatingCharts[chartKey] = true;
  
  const tick = () => {
    let needsMore = false;
    const slices = state.chartSlices[chartKey] || [];
    const anims = sliceAnimState[chartKey];
    
    // Ensure active slices are initialized
    slices.forEach(s => {
      if (!anims[s.key]) {
        anims[s.key] = { selected: 0, hovered: 0, opacity: 1.0 };
      }
    });
    
    const selectedKey = state.selectedChartSlice[chartKey];
    const hoveredKey = state.hoveredChartSlice[chartKey];
    
    for (const key of Object.keys(anims)) {
      const anim = anims[key];
      const targetSelected = (selectedKey === key) ? 1 : 0;
      const targetHovered = (hoveredKey === key) ? 1 : 0;
      const targetOpacity = (hoveredKey === null || hoveredKey === key) ? 1.0 : 0.55;
      
      const diffSel = targetSelected - anim.selected;
      const diffHov = targetHovered - anim.hovered;
      const diffOpa = targetOpacity - anim.opacity;
      
      // Lerp selection progress (nhanh hơn xíu)
      if (Math.abs(diffSel) > 0.001) {
        anim.selected += diffSel * 0.18; 
        needsMore = true;
      } else {
        anim.selected = targetSelected;
      }
      
      // Lerp hover progress (phản hồi cực nhạy)
      if (Math.abs(diffHov) > 0.001) {
        anim.hovered += diffHov * 0.25; 
        needsMore = true;
      } else {
        anim.hovered = targetHovered;
      }
      
      // Lerp opacity mượt mà
      if (Math.abs(diffOpa) > 0.001) {
        anim.opacity += diffOpa * 0.18;
        needsMore = true;
      } else {
        anim.opacity = targetOpacity;
      }
    }
    
    cb();
    
    if (needsMore) {
      requestAnimationFrame(tick);
    } else {
      animatingCharts[chartKey] = false;
    }
  };
  
  requestAnimationFrame(tick);
}

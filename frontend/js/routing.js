// 路径规划: 起点/终点设置 + 调用 A* API + 绘制路径
const MCRouting = {
  routeLayers: [],     // 路径折线图层
  endpointMarkers: [], // 起点/终点标记
};

// 设置起点/终点 (由 POI 详情卡或地图点击调用)
function setRouteEndpoint(which, dim, x, z, label) {
  MCMap.routeEndpoints[which] = { dim, x, z, label: label || `${x},${z}` };
  // 如果终点维度与起点不同, 自动切换地图到该维度显示
  if (which === 'from' && dim !== MCMap.currentDim) {
    switchDimension(dim);
  }
  updateRouteInputs();
  drawEndpointMarkers();
}

// 地图点击: 智能分配起点/终点
function onMapClick(coord) {
  const { from, to } = MCMap.routeEndpoints;
  if (!from) {
    setRouteEndpoint('from', coord.dim, coord.x, coord.z, `${coord.x},${coord.z}`);
  } else if (!to) {
    setRouteEndpoint('to', coord.dim, coord.x, coord.z, `${coord.x},${coord.z}`);
  } else {
    // 都已设置, 重新开始: 清空并设为新起点
    MCRouting.endpointMarkers.forEach(m => MCMap.map.removeLayer(m));
    MCRouting.endpointMarkers = [];
    MCMap.routeEndpoints.to = null;
    setRouteEndpoint('from', coord.dim, coord.x, coord.z, `${coord.x},${coord.z}`);
  }
}

function updateRouteInputs() {
  const fromEl = document.getElementById('route-from');
  const toEl = document.getElementById('route-to');
  const { from, to } = MCMap.routeEndpoints;
  fromEl.value = from ? `[${DIM_NAME[from.dim] ?? from.dim}] ${from.label} (${from.x},${from.z})` : '';
  toEl.value = to ? `[${DIM_NAME[to.dim] ?? to.dim}] ${to.label} (${to.x},${to.z})` : '';
}

function drawEndpointMarkers() {
  MCRouting.endpointMarkers.forEach(m => MCMap.map.removeLayer(m));
  MCRouting.endpointMarkers = [];
  const { from, to } = MCMap.routeEndpoints;
  if (from && from.dim === MCMap.currentDim) {
    const m = L.marker(mcToLatLng(from.x, from.z), {
      icon: L.divIcon({ className: '', html: '<div class="mc-route-endpoint from"></div>', iconSize: [14, 14], iconAnchor: [7, 7] }),
    }).addTo(MCMap.map);
    MCRouting.endpointMarkers.push(m);
  }
  if (to && to.dim === MCMap.currentDim) {
    const m = L.marker(mcToLatLng(to.x, to.z), {
      icon: L.divIcon({ className: '', html: '<div class="mc-route-endpoint to"></div>', iconSize: [14, 14], iconAnchor: [7, 7] }),
    }).addTo(MCMap.map);
    MCRouting.endpointMarkers.push(m);
  }
}

// 客户端路径规划: 复刻后端 routing.py (障碍为空 → 直线; 传送门为空 → 跨维度不可达)
// PORTAL_COST 与后端一致 (传送门固定开销), DIST 精度取欧氏距离。
const PORTAL_COST = 10;

function computeRoute(from, to) {
  const dist = (x1, z1, x2, z2) => Math.hypot(x2 - x1, z2 - z1);
  if (from.dim === to.dim) {
    const d = dist(from.x, from.z, to.x, to.z);
    return {
      segments: [{
        dim: from.dim,
        path: [[from.x, from.z], [to.x, to.z]],
        distance: d,
        type: 'walk',
      }],
      total_distance: d,
      portals_used: [],
    };
  }
  // 跨维度: 仅支持主世界(0) ↔ 下界(-1), 经传送门联动
  const pair = new Set([from.dim, to.dim]);
  if (pair.size !== 2 || !pair.has(0) || !pair.has(-1)) {
    throw new Error('跨维度路径仅支持主世界↔下界');
  }
  const portals = window.__portals || [];
  if (portals.length === 0) {
    throw new Error('无传送门数据, 无法跨维度寻路');
  }
  let best = null;
  for (const portal of portals) {
    const p_from = from.dim === 0 ? portal.overworld : portal.nether;
    const p_to = to.dim === 0 ? portal.overworld : portal.nether;
    const seg1 = [[from.x, from.z], [p_from.x, p_from.z]];
    const seg2 = [[p_to.x, p_to.z], [to.x, to.z]];
    const d1 = dist(from.x, from.z, p_from.x, p_from.z);
    const d2 = dist(p_to.x, p_to.z, to.x, to.z);
    const total = d1 + PORTAL_COST + d2;
    if (best === null || total < best.total_distance) {
      best = {
        segments: [
          { dim: from.dim, path: seg1, distance: d1, type: 'walk' },
          { dim: from.dim, path: [[p_from.x, p_from.z], [p_from.x, p_from.z]], distance: 0, type: 'portal_exit' },
          { dim: to.dim, path: [[p_to.x, p_to.z], [p_to.x, p_to.z]], distance: 0, type: 'portal_enter' },
          { dim: to.dim, path: seg2, distance: d2, type: 'walk' },
        ],
        total_distance: total,
        portals_used: [portal],
      };
    }
  }
  return best;
}

function planRoute() {
  const { from, to } = MCMap.routeEndpoints;
  if (!from || !to) {
    alert('请先设置起点和终点');
    return;
  }
  const resultEl = document.getElementById('route-result');
  resultEl.classList.remove('hidden');
  resultEl.innerHTML = '<div style="color:#1890ff;">规划中...</div>';
  try {
    const r = computeRoute(from, to);
    drawRoute(r);
    renderRouteResult(r);
  } catch (e) {
    resultEl.innerHTML = `<div style="color:#f5222d;">路径规划失败: ${e.message}</div>`;
  }
}

function drawRoute(routeData) {
  // 清除旧路径
  MCRouting.routeLayers.forEach(l => MCMap.map.removeLayer(l));
  MCRouting.routeLayers = [];

  const dim = MCMap.currentDim;
  // 只绘制当前维度的段
  for (const seg of routeData.segments) {
    if (seg.dim !== dim) continue;
    if (seg.path.length < 2) continue;
    const latlngs = seg.path.map(([x, z]) => mcToLatLng(x, z));
    let color = '#0084ff';
    let weight = 4;
    let dashArray = null;
    if (seg.type === 'portal_exit' || seg.type === 'portal_enter') {
      color = '#722ed1';
      weight = 3;
      dashArray = '6,4';
    }
    const line = L.polyline(latlngs, { color, weight, dashArray, opacity: 0.9 }).addTo(MCMap.map);
    MCRouting.routeLayers.push(line);
  }

  // 跨维度时, 跳到起点维度
  if (routeData.segments.length > 0 && routeData.segments[0].dim !== dim) {
    switchDimension(routeData.segments[0].dim);
    setTimeout(() => drawRoute(routeData), 200);
  }
}

function renderRouteResult(routeData) {
  const resultEl = document.getElementById('route-result');
  const segHtml = routeData.segments.map(seg => {
    if (seg.type === 'portal_exit' || seg.type === 'portal_enter') {
      return `<div class="rr-segment"><span class="seg-portal">⇄ 传送门</span> → ${DIM_NAME[seg.dim] ?? seg.dim}</div>`;
    }
    return `<div class="rr-segment">${DIM_NAME[seg.dim] ?? seg.dim}: 步行 ${seg.distance.toFixed(0)}m (${seg.path.length} 节点)</div>`;
  }).join('');
  const portalInfo = routeData.portals_used.length > 0
    ? `<div class="rr-segment">使用传送门: ${routeData.portals_used.length} 个</div>`
    : '';
  resultEl.innerHTML = `
    <div class="rr-total">总距离: ${routeData.total_distance.toFixed(0)}m</div>
    ${segHtml}
    ${portalInfo}
  `;
}

function resetRoute() {
  MCMap.routeEndpoints.from = null;
  MCMap.routeEndpoints.to = null;
  MCRouting.routeLayers.forEach(l => MCMap.map.removeLayer(l));
  MCRouting.endpointMarkers.forEach(m => MCMap.map.removeLayer(m));
  MCRouting.routeLayers = [];
  MCRouting.endpointMarkers = [];
  updateRouteInputs();
  document.getElementById('route-result').classList.add('hidden');
}

// 维度切换时重绘起点/终点标记
function onDimensionChangeRoute() {
  drawEndpointMarkers();
  // 重绘当前维度的路径段
  // (路径已绘制, 切换维度后只显示该维度的段)
}

function initRouting() {
  document.getElementById('route-plan-btn').addEventListener('click', planRoute);
  document.getElementById('route-reset-btn').addEventListener('click', resetRoute);
  document.querySelectorAll('.route-clear').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.target;
      MCMap.routeEndpoints[target] = null;
      updateRouteInputs();
      drawEndpointMarkers();
    });
  });
}

window.addEventListener('DOMContentLoaded', () => {
  const wait = setInterval(() => {
    if (MCMap.map) {
      clearInterval(wait);
      initRouting();
    }
  }, 100);
});

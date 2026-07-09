// POI 标记 + 列表 + 详情卡 + 类别筛选
const MCPoi = {
  pois: [],
  players: [],
  markers: [],
  playerMarkers: [],
  activeCategories: new Set(['landmark', 'resource', 'player', 'portal']),
};

// POI 类别颜色 (Apple 大头针颜色, 与 style.css .mc-poi-marker.cat-* 一致)
const CATEGORY_COLOR = {
  landmark: '#ff453a',   // 红 (Apple 默认)
  resource: '#ff9f0a',   // 橙
  player: '#0a84ff',     // 蓝
  portal: '#bf5af2',     // 紫
};

async function initPoi() {
  MCPoi.pois = await fetchJSON('data/pois.json');
  MCPoi.players = await fetchJSON('data/players.json');
  renderPoiList();
  renderMarkers();
  bindCategoryFilter();
}

// 渲染地图上的标记
function renderMarkers() {
  for (const m of MCPoi.markers) MCMap.map.removeLayer(m);
  for (const m of MCPoi.playerMarkers) MCMap.map.removeLayer(m);
  MCPoi.markers = [];
  MCPoi.playerMarkers = [];

  const dim = MCMap.currentDim;

  for (const poi of MCPoi.pois) {
    if (poi.dim !== dim) continue;
    if (!MCPoi.activeCategories.has(poi.category)) continue;
    const marker = createPoiMarker(poi);
    marker.addTo(MCMap.map);
    MCPoi.markers.push(marker);
  }

  // 传送门标记
  if (MCPoi.activeCategories.has('portal') && (dim === 0 || dim === -1)) {
    const portals = await_get_portals_sync();
    for (const p of portals) {
      const coord = dim === 0 ? p.overworld : p.nether;
      const marker = L.marker(mcToLatLng(coord.x, coord.z), {
        icon: L.divIcon({ className: '', html: '<div class="mc-portal-marker"></div>', iconSize: [18, 18] }),
        title: `传送门 (${coord.x}, ${coord.z})`,
      });
      marker.on('click', () => showPortalDetail(p, dim));
      marker.addTo(MCMap.map);
      MCPoi.markers.push(marker);
    }
  }

  // 玩家标记
  if (MCPoi.activeCategories.has('player')) {
    for (const pl of MCPoi.players) {
      if (pl.dim !== dim) continue;
      const marker = L.marker(mcToLatLng(pl.x, pl.z), {
        icon: L.divIcon({ className: '', html: `<div class="mc-player-marker"></div>`, iconSize: [14, 14] }),
        title: pl.name,
      });
      marker.on('click', () => showPlayerDetail(pl));
      marker.addTo(MCMap.map);
      MCPoi.playerMarkers.push(marker);
    }
  }
}

let _portalsCache = null;
function await_get_portals_sync() {
  if (_portalsCache) return _portalsCache;
  _portalsCache = window.__portals || [];
  return _portalsCache;
}

async function loadPortals() {
  window.__portals = await fetchJSON('data/portals.json');
  _portalsCache = window.__portals;
}

function createPoiMarker(poi) {
  // Apple 大头针样式: 通过 cat-{category} 类设置颜色 (见 style.css)
  const icon = L.divIcon({
    className: '',
    html: `<div class="mc-poi-marker cat-${poi.category || 'landmark'}"><span>${poi.name.charAt(0)}</span></div>`,
    iconSize: [28, 36],
    iconAnchor: [14, 36],   // 锚点在针尖底部
  });
  const marker = L.marker(mcToLatLng(poi.x, poi.z), { icon, title: poi.name });
  marker.on('click', () => showPoiDetail(poi));
  return marker;
}

// POI 列表
function renderPoiList() {
  const el = document.getElementById('poi-list');
  el.innerHTML = '';
  const dim = MCMap.currentDim;
  const filtered = MCPoi.pois.filter(p => p.dim === dim);
  if (filtered.length === 0) {
    el.innerHTML = '<div style="color:#8c8c8c;font-size:12px;padding:16px;text-align:center;">当前维度无地点</div>';
    return;
  }
  for (const poi of filtered) {
    const item = document.createElement('div');
    item.className = 'poi-item';
    const color = CATEGORY_COLOR[poi.category] || CATEGORY_COLOR.landmark;
    item.innerHTML = `
      <span class="poi-dot" style="background:${color}"></span>
      <span class="poi-name">${poi.name}</span>
      <span class="poi-coord">${poi.x},${poi.z}</span>
    `;
    item.onclick = () => {
      MCMap.map.setView(mcToLatLng(poi.x, poi.z), MCMap.dimMeta.max_zoom);
      showPoiDetail(poi);
    };
    el.appendChild(item);
  }
}

// POI 详情卡
function showPoiDetail(poi) {
  const card = document.getElementById('poi-detail');
  const content = document.getElementById('detail-content');
  content.innerHTML = `
    <div class="detail-header">
      <strong style="font-size:17px;">${poi.name}</strong>
    </div>
    <div class="detail-body">
      <div class="detail-row"><span class="dr-label">类别</span><span>${poi.category}</span></div>
      <div class="detail-row"><span class="dr-label">维度</span><span>${DIM_NAME[poi.dim] ?? poi.dim}</span></div>
      <div class="detail-row"><span class="dr-label">坐标</span><span>x=${poi.x}, z=${poi.z}</span></div>
      <div class="detail-row"><span class="dr-label">描述</span><span>${poi.desc || '-'}</span></div>
    </div>
    <div class="detail-actions">
      <button onclick="MCMap.map.setView(mcToLatLng(${poi.x},${poi.z}),${MCMap.dimMeta.max_zoom});">跳转</button>
      <button onclick="setRouteEndpoint('from',${poi.dim},${poi.x},${poi.z},'${poi.name}')">设为起点</button>
      <button onclick="setRouteEndpoint('to',${poi.dim},${poi.x},${poi.z},'${poi.name}')">设为终点</button>
    </div>
  `;
  card.classList.remove('hidden');
}

function showPlayerDetail(pl) {
  const card = document.getElementById('poi-detail');
  const content = document.getElementById('detail-content');
  content.innerHTML = `
    <div class="detail-header">
      <strong style="font-size:17px;">${pl.name}</strong>
    </div>
    <div class="detail-body">
      <div class="detail-row"><span class="dr-label">维度</span><span>${DIM_NAME[pl.dim] ?? pl.dim}</span></div>
      <div class="detail-row"><span class="dr-label">坐标</span><span>x=${pl.x}, z=${pl.z}</span></div>
      <div class="detail-row"><span class="dr-label">朝向</span><span>${pl.yaw}°</span></div>
    </div>
    <div class="detail-actions">
      <button onclick="MCMap.map.setView(mcToLatLng(${pl.x},${pl.z}),${MCMap.dimMeta.max_zoom});">跳转</button>
      <button onclick="setRouteEndpoint('from',${pl.dim},${pl.x},${pl.z},'${pl.name}')">设为起点</button>
      <button onclick="setRouteEndpoint('to',${pl.dim},${pl.x},${pl.z},'${pl.name}')">设为终点</button>
    </div>
  `;
  card.classList.remove('hidden');
}

function showPortalDetail(portal, dim) {
  const card = document.getElementById('poi-detail');
  const content = document.getElementById('detail-content');
  const ow = portal.overworld, ne = portal.nether;
  content.innerHTML = `
    <div class="detail-header">
      <strong style="font-size:17px;">传送门</strong>
    </div>
    <div class="detail-body">
      <div class="detail-row"><span class="dr-label">主世界</span><span>x=${ow.x}, z=${ow.z}</span></div>
      <div class="detail-row"><span class="dr-label">下界</span><span>x=${ne.x}, z=${ne.z}</span></div>
      <div class="detail-row"><span class="dr-label">比例</span><span>1:8</span></div>
    </div>
    <div class="detail-actions">
      <button onclick="switchDimension(0);MCMap.map.setView(mcToLatLng(${ow.x},${ow.z}),${MCMap.dimMeta.max_zoom});">主世界端</button>
      <button onclick="switchDimension(-1);MCMap.map.setView(mcToLatLng(${ne.x},${ne.z}),${MCMap.dimMeta.max_zoom});">下界端</button>
    </div>
  `;
  card.classList.remove('hidden');
}

// 类别筛选 (chip 风格)
function bindCategoryFilter() {
  const bar = document.getElementById('category-list') || document.querySelector('.category-bar');
  if (!bar) return;
  bar.addEventListener('change', (e) => {
    if (e.target.type !== 'checkbox') return;
    const val = e.target.value;
    if (e.target.checked) MCPoi.activeCategories.add(val);
    else MCPoi.activeCategories.delete(val);
    renderMarkers();
  });
}

// 维度切换时重新渲染
function onDimensionChange() {
  renderPoiList();
  renderMarkers();
  if (typeof drawEndpointMarkers === 'function') drawEndpointMarkers();
}

document.getElementById('detail-close').addEventListener('click', () => {
  document.getElementById('poi-detail').classList.add('hidden');
});

window.addEventListener('DOMContentLoaded', async () => {
  await loadPortals();
  const wait = setInterval(() => {
    if (MCMap.map) {
      clearInterval(wait);
      initPoi();
    }
  }, 100);
});

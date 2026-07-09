// Leaflet 地图核心: 快照瓦片源 + 维度切换 (仅筛 POI) + 坐标显示
// 数据源: map_source/{snapshot}/*.png (1024x1024, 1px=1block)
// 坐标映射: Minecraft (x, z) → Leaflet LatLng [-z, x] (北=上, 原点 mc 0,0)

const MCMap = {
  map: null,
  tileLayer: null,
  dimensions: [],
  snapshots: [],
  currentSnapshot: null,
  currentDim: 0,
  dimMeta: { max_zoom: 0, tile_size: 1024, origin_x: 0, origin_z: 0 },
  routeEndpoints: { from: null, to: null },
  userLocationMarker: null,
};

const DIM_NAME = { 0: '主世界', '-1': '下界', 1: '末地' };

async function fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

// CRS: baseScale = 1/2^maxZoom, 让 zoom=maxZoom 时 1px=1block
// offsetX/offsetZ: 导出图网格偏移 (mc 坐标), 使 tile (0,0) 对齐图片实际原点
function makeCRS(maxZoom, offsetX, offsetZ) {
  const baseScale = 1 / Math.pow(2, maxZoom);
  return L.extend({}, L.CRS.Simple, {
    // lng = baseScale*px + offsetX, lat = -baseScale*py - offsetZ
    transformation: L.transformation(baseScale, offsetX, -baseScale, -offsetZ),
  });
}

// 加载快照 (建图 + 瓦片层 + fitBounds)
function loadSnapshot(snapshot) {
  if (MCMap.map) {
    MCMap.map.remove();
    MCMap.map = null;
    MCMap.tileLayer = null;
  }

  MCMap.currentSnapshot = snapshot;
  // dimMeta 兼容外部模块访问 max_zoom
  MCMap.dimMeta = {
    max_zoom: snapshot.max_zoom,
    tile_size: snapshot.tile_size,
    origin_x: 0,
    origin_z: 0,
  };

  const maxZoom = snapshot.max_zoom;
  MCMap.map = L.map('map', {
    crs: makeCRS(maxZoom, snapshot.offset_x, snapshot.offset_z),
    // zoom=0 是 1px=1block; 负 zoom 缩远看大范围, 正 zoom 放大看细节
    // minZoom=-4 ≈ 0.06x, maxZoom=5 ≈ 32x (覆盖用户期望 0.05x ~ 20x)
    minZoom: -4,
    maxZoom: 5,
    zoomSnap: 0.5,              // 允许半级缩放, 滚轮体验更顺滑
    zoomControl: false,         // 关闭默认 topleft, 自定义 Apple 风格控件
    scrollWheelZoom: true,
    attributionControl: false,
  });

  // 右下角 +/- 缩放控件 (Apple 药丸形, 见 style.css)
  L.control.zoom({ position: 'bottomright' }).addTo(MCMap.map);

  // 瓦片层: tiles/{snapshot_id}/{z}/{x}/{y}.png (相对路径, 兼容 GH Pages 子路径)
  // 原生瓦片仅在 zoom=0; zoom>0 用 zoom=0 放大, zoom<0 用 zoom=0 缩小
  MCMap.tileLayer = L.tileLayer(
    `tiles/${snapshot.id}/{z}/{x}/{y}.png`,
    {
      tms: false,
      minZoom: -4,               // 与 map.minZoom 一致, 允许 tileLayer 在负 zoom 提供 (复用 zoom=0)
      maxZoom: 5,                // 与 map.maxZoom 一致
      maxNativeZoom: maxZoom,    // 真实瓦片只到 maxZoom (=0), 其他 zoom 复用
      minNativeZoom: maxZoom,    // 真实瓦片最低也只到 maxZoom (=0)
      tileSize: snapshot.tile_size,
      noWrap: true,
    }
  ).addTo(MCMap.map);

  // 视野聚焦主区域 bounds (排除离群点)
  const b = snapshot.bounds;
  MCMap.map.fitBounds([
    [-b.max_z, b.min_x],
    [-b.min_z, b.max_x],
  ]);

  // 允许平移到 bounds 外 (POI 可能在地图外), 留 50% padding
  const padX = (b.max_x - b.min_x) * 0.5;
  const padZ = (b.max_z - b.min_z) * 0.5;
  MCMap.map.setMaxBounds([
    [-(b.max_z + padZ), b.min_x - padX],
    [-(b.min_z - padZ), b.max_x + padX],
  ]);

  L.control.scale({ position: 'bottomleft', imperial: false }).addTo(MCMap.map);

  // 坐标显示
  MCMap.map.on('mousemove', (e) => {
    const mc = latLngToMc(e.latlng);
    document.getElementById('coord-text').textContent = `坐标: x=${mc.x}, z=${mc.z}`;
    document.getElementById('dim-text').textContent = `维度: ${DIM_NAME[MCMap.currentDim] ?? MCMap.currentDim}`;
  });

  // 点击地图: 设为路径起点/终点
  MCMap.map.on('click', (e) => {
    const mc = latLngToMc(e.latlng);
    if (typeof onMapClick === 'function') onMapClick({ dim: MCMap.currentDim, x: mc.x, z: mc.z });
  });

  updateSnapshotLabel();
}

// 初始化
async function initMap() {
  MCMap.dimensions = await fetchJSON('data/dimensions.json');
  MCMap.snapshots = await fetchJSON('data/snapshots.json');

  if (MCMap.snapshots.length === 0) {
    document.getElementById('coord-text').textContent = '无地图快照 (map_source 为空)';
    return;
  }

  initToolbar();
  loadSnapshot(MCMap.snapshots[0]);

  // 通知其他模块刷新标记
  if (typeof onDimensionChange === 'function') onDimensionChange(MCMap.currentDim);
}

// 切换快照 (重建地图)
function switchSnapshot(snapshotId) {
  const s = MCMap.snapshots.find(s => s.id === snapshotId);
  if (!s) return;
  if (MCMap.currentSnapshot && s.id === MCMap.currentSnapshot.id) return;

  loadSnapshot(s);

  // 通知其他模块重建标记
  if (typeof onDimensionChange === 'function') onDimensionChange(MCMap.currentDim);
}

// 切换维度 (仅更新 currentDim + POI/routing 筛选, 不重建地图;
// 因瓦片源只有主世界快照, 下界/末地无对应瓦片)
function switchDimension(dimId) {
  if (dimId === MCMap.currentDim) return;
  MCMap.currentDim = dimId;
  updateDimButton();

  if (typeof onDimensionChange === 'function') onDimensionChange(dimId);
  document.getElementById('dim-text').textContent = `维度: ${DIM_NAME[dimId] ?? dimId}`;
}

// 工具栏: 快照下拉 + 维度下拉 + tab 切换 + 全屏
function initToolbar() {
  updateDimButton();
  updateSnapshotLabel();

  // 快照下拉
  const snapBtn = document.getElementById('snapshot-btn');
  const snapDropdown = document.getElementById('snapshot-dropdown');
  if (snapBtn && snapDropdown) {
    snapDropdown.innerHTML = MCMap.snapshots.map(s =>
      `<div class="dim-item snapshot-item" data-snapshot="${s.id}">${s.name}</div>`
    ).join('');
    snapBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      snapDropdown.classList.toggle('hidden');
      // 关闭维度下拉
      document.getElementById('dim-dropdown')?.classList.add('hidden');
      document.getElementById('map-type-popover')?.classList.add('hidden');
    });
    snapDropdown.querySelectorAll('.snapshot-item').forEach(item => {
      item.addEventListener('click', () => {
        switchSnapshot(item.dataset.snapshot);
        snapDropdown.classList.add('hidden');
      });
    });
  }

  // 维度下拉
  const dimBtn = document.getElementById('dim-btn');
  const dimDropdown = document.getElementById('dim-dropdown');
  dimBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    dimDropdown.classList.toggle('hidden');
    snapDropdown?.classList.add('hidden');
    document.getElementById('map-type-popover')?.classList.add('hidden');
  });
  dimDropdown.querySelectorAll('.dim-item').forEach(item => {
    item.addEventListener('click', () => {
      switchDimension(parseInt(item.dataset.dim));
      dimDropdown.classList.add('hidden');
    });
  });
  document.addEventListener('click', () => {
    dimDropdown.classList.add('hidden');
    snapDropdown?.classList.add('hidden');
    document.getElementById('map-type-popover')?.classList.add('hidden');
  });

  // Tab 切换
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
      document.getElementById('tab-' + btn.dataset.tab).classList.remove('hidden');
    });
  });

  // 右下角 Leaflet zoom 控件已提供 +/- (Apple 矮药丸形), 无需自定义按钮

  // 指南针按钮: Leaflet 不支持旋转, 点击后重置到初始视野 (fitBounds)
  // 不改变当前 zoom, 只回到快照默认视野
  document.getElementById('compass-btn')?.addEventListener('click', () => {
    if (!MCMap.map || !MCMap.currentSnapshot) return;
    const b = MCMap.currentSnapshot.bounds;
    MCMap.map.flyToBounds(
      [[-b.max_z, b.min_x], [-b.min_z, b.max_x]],
      { duration: 0.5 }
    );
  });

  // 地图类型按钮: 弹出菜单 (仅"标准"可用)
  const mapTypeBtn = document.getElementById('map-type-btn');
  const mapTypePopover = document.getElementById('map-type-popover');
  if (mapTypeBtn && mapTypePopover) {
    mapTypeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      mapTypePopover.classList.toggle('hidden');
      // 关闭其他下拉
      document.getElementById('dim-dropdown')?.classList.add('hidden');
      document.getElementById('snapshot-dropdown')?.classList.add('hidden');
    });
    // 菜单项点击 (禁用项忽略)
    mapTypePopover.querySelectorAll('.map-type-item').forEach(item => {
      item.addEventListener('click', (e) => {
        e.stopPropagation();
        if (item.classList.contains('disabled')) return;
        mapTypePopover.querySelectorAll('.map-type-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        mapTypePopover.classList.add('hidden');
      });
    });
  }

  // 定位按钮: 调用浏览器 geolocation, 标记用户位置 (Apple 蓝点)
  document.getElementById('locate-btn')?.addEventListener('click', () => {
    if (!MCMap.map) return;
    if (!navigator.geolocation) {
      alert('浏览器不支持定位');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        // 注意: 浏览器 geolocation 返回的是真实世界经纬度, 与 MC 坐标无关
        // 这里仅作为功能演示, 标记在地图中心附近
        const center = MCMap.map.getCenter();
        if (MCMap.userLocationMarker) {
          MCMap.userLocationMarker.setLatLng(center);
        } else {
          MCMap.userLocationMarker = L.marker(center, {
            icon: L.divIcon({
              className: '',
              html: '<div class="mc-user-location"></div>',
              iconSize: [16, 16],
              iconAnchor: [8, 8],
            }),
          }).addTo(MCMap.map);
        }
        MCMap.map.flyTo(center, 0, { duration: 0.5 });
      },
      (err) => {
        alert('定位失败: ' + err.message);
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  });

  // 全屏
  document.getElementById('fullscreen-btn').addEventListener('click', () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  });
}

function updateDimButton() {
  const el = document.getElementById('dim-label');
  if (el) el.textContent = DIM_NAME[MCMap.currentDim] ?? MCMap.currentDim;
}

function updateSnapshotLabel() {
  const el = document.getElementById('snapshot-label');
  if (el && MCMap.currentSnapshot) el.textContent = MCMap.currentSnapshot.name;
}

// Minecraft 真实坐标 → Leaflet LatLng
function mcToLatLng(x, z) {
  return [-z, x];
}

// Leaflet LatLng → Minecraft 真实坐标
function latLngToMc(latlng) {
  return { x: Math.round(latlng.lng), z: Math.round(-latlng.lat) };
}

window.addEventListener('DOMContentLoaded', initMap);

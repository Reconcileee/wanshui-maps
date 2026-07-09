// Xaero 路径点: 从 /api/waypoints 加载, 显示为 Apple 大头针 (使用原始颜色)
// 坐标映射: MC (x, z) → Leaflet LatLng [-z, x]

const MCWaypoint = {
  waypoints: [],
  markers: [],
};

async function loadWaypoints() {
  const all = await fetchJSON('data/waypoints.json');
  MCWaypoint.waypoints = all.filter(w => w.dim === 0);
  // 等待地图初始化完成
  if (!MCMap.map) {
    setTimeout(loadWaypoints, 200);
    return;
  }
  renderWaypoints();
}

function renderWaypoints() {
  // 清除旧标记
  MCWaypoint.markers.forEach(m => m.remove());
  MCWaypoint.markers = [];
  if (!MCMap.map) return;

  for (const wp of MCWaypoint.waypoints) {
    const marker = L.marker(mcToLatLng(wp.x, wp.z), {
      icon: L.divIcon({
        className: '',
        html: `<div class="mc-poi-marker mc-waypoint" style="--pin-color:${wp.color}"><span>${wp.initials}</span></div>`,
        iconSize: [28, 36],
        iconAnchor: [14, 36],
      }),
      title: wp.name,
    });
    marker.on('click', () => showWaypointDetail(wp));
    marker.addTo(MCMap.map);
    MCWaypoint.markers.push(marker);
  }
}

function showWaypointDetail(wp) {
  const card = document.getElementById('poi-detail');
  const content = document.getElementById('detail-content');
  content.innerHTML = `
    <div class="detail-header">
      <strong style="font-size:17px;">${wp.name}</strong>
    </div>
    <div class="detail-body">
      <div class="detail-row"><span class="dr-label">坐标</span><span>x=${wp.x}, y=${wp.y}, z=${wp.z}</span></div>
      <div class="detail-row"><span class="dr-label">维度</span><span>${DIM_NAME[wp.dim] ?? wp.dim}</span></div>
      <div class="detail-row"><span class="dr-label">服务器</span><span>${wp.server}</span></div>
    </div>
    <div class="detail-actions">
      <button onclick="MCMap.map.setView(mcToLatLng(${wp.x},${wp.z}),0);">跳转</button>
      <button onclick="setRouteEndpoint('from',${wp.dim},${wp.x},${wp.z},'${wp.name}')">设为起点</button>
      <button onclick="setRouteEndpoint('to',${wp.dim},${wp.x},${wp.z},'${wp.name}')">设为终点</button>
    </div>
  `;
  card.classList.remove('hidden');
}

window.addEventListener('DOMContentLoaded', loadWaypoints);

// 搜索框: 实时联想 + 回车跳转
const MCSearch = {
  debounceTimer: null,
};

function initSearch() {
  const input = document.getElementById('search-input');
  const suggest = document.getElementById('search-suggest');

  // 实时联想 (防抖 200ms)
  input.addEventListener('input', () => {
    clearTimeout(MCSearch.debounceTimer);
    const q = input.value.trim();
    if (!q) {
      suggest.classList.add('hidden');
      return;
    }
    MCSearch.debounceTimer = setTimeout(() => doSuggest(q), 200);
  });

  // 回车搜索
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      suggest.classList.add('hidden');
      doSearch(input.value.trim());
    }
  });

  // 点击外部关闭联想
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-box')) suggest.classList.add('hidden');
  });
}

async function doSuggest(q) {
  const suggest = document.getElementById('search-suggest');
  const pois = MCPoi.pois;
  const q_lower = q.toLowerCase();
  const matched = pois.filter(p =>
    p.name.toLowerCase().includes(q_lower) ||
    p.desc.toLowerCase().includes(q_lower)
  ).slice(0, 8);

  if (matched.length === 0) {
    suggest.classList.add('hidden');
    return;
  }

  suggest.innerHTML = matched.map(p => `
    <div class="suggest-item" data-poi-id="${p.id}">
      <div class="si-name">${p.name}</div>
      <div class="si-coord">${DIM_NAME[p.dim] ?? p.dim} · x=${p.x}, z=${p.z}</div>
    </div>
  `).join('');

  suggest.querySelectorAll('.suggest-item').forEach(item => {
    item.onclick = () => {
      const poi = pois.find(p => p.id === item.dataset.poiId);
      if (poi) {
        if (poi.dim !== MCMap.currentDim) switchDimension(poi.dim);
        MCMap.map.setView(mcToLatLng(poi.x, poi.z), MCMap.dimMeta.max_zoom);
        showPoiDetail(poi);
        suggest.classList.add('hidden');
        document.getElementById('search-input').value = poi.name;
      }
    };
  });
  suggest.classList.remove('hidden');
}

// 客户端搜索: 复刻后端 /api/search 逻辑 (坐标解析 + 文本匹配)
function doSearch(q) {
  if (!q) return;
  const pois = MCPoi.pois;
  // 坐标解析: "512,512" 或 "x=512,z=512"
  let result = null;
  const q_stripped = q.trim();
  try {
    const parts = q_stripped.replace('x=', '').replace('z=', '').split(',');
    if (parts.length === 2) {
      const x = parseInt(parts[0].trim(), 10);
      const z = parseInt(parts[1].trim(), 10);
      if (!Number.isNaN(x) && !Number.isNaN(z)) {
        const nearby = pois.filter(p => Math.abs(p.x - x) < 100 && Math.abs(p.z - z) < 100).slice(0, 5);
        result = { type: 'coordinate', x, z, dim: 0, pois_nearby: nearby };
      }
    }
  } catch (e) { /* 忽略, 走文本搜索 */ }

  if (!result) {
    const q_lower = q.toLowerCase();
    const matched = pois.filter(p =>
      p.name.toLowerCase().includes(q_lower) ||
      (p.desc || '').toLowerCase().includes(q_lower)
    );
    result = { type: 'poi', results: matched };
  }

  if (result.type === 'coordinate') {
    if (result.dim !== MCMap.currentDim) switchDimension(result.dim);
    MCMap.map.setView(mcToLatLng(result.x, result.z), MCMap.dimMeta.max_zoom);
    if (result.pois_nearby.length > 0) showPoiDetail(result.pois_nearby[0]);
  } else {
    if (result.results.length === 0) {
      alert('未找到匹配地点');
      return;
    }
    const poi = result.results[0];
    if (poi.dim !== MCMap.currentDim) switchDimension(poi.dim);
    MCMap.map.setView(mcToLatLng(poi.x, poi.z), MCMap.dimMeta.max_zoom);
    showPoiDetail(poi);
  }
}

window.addEventListener('DOMContentLoaded', () => {
  const wait = setInterval(() => {
    if (MCMap.map && MCPoi.pois.length > 0) {
      clearInterval(wait);
      initSearch();
    }
  }, 100);
});

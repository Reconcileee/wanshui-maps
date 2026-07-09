# Minecraft 在线地图

将 Minecraft 存档 / 多人游戏地图搬到浏览器的全栈 Web 应用，提供地图浏览、多时间快照切换、地点（POI）管理与搜索、A\* 路径规划功能，界面风格参照 Apple 地图（深色模式 + 磨砂玻璃控件 + 药丸形按钮）。

## 功能特性

- **地图浏览**：基于游戏内导出的 1024×1024 PNG 瓦片（1px=1block），支持负坐标。
- **缩放范围**：`minZoom=-4`（≈0.06x 缩远看大范围）到 `maxZoom=5`（≈32x 放大看细节），`zoomSnap=0.5` 半级缩放，滚轮 + 药丸形 +/- 按钮 + 右侧工具栏按钮三种方式。
- **多快照切换**：按导出时间组织多个地图快照，右上角时钟按钮切换查看不同时间点的世界状态。
- **POI 管理**：地标 / 资源 / 玩家 / 传送门四类标记，支持列表浏览、类别筛选、详情查看、增删改查。标记采用 Apple 大头针样式（水滴形 + 中心白点），颜色按类别区分（红/橙/蓝/紫）。
- **Xaero 路径点**：自动扫描 `waypoint_source/` 下所有服务器的 Xaero minimap 路径点，按 `(name, x, y, z)` 去重，跳过死亡点（`gui.xaero_deathpoint_old`），保留原始颜色显示为 Apple 大头针。
- **搜索**：文本搜索（名称 / 描述）+ 坐标跳转（输入 `x,z` 直接定位）。
- **路径规划**：同维度内 A\* 寻路（4 方向、避开障碍），主世界 ↔ 下界跨维度联动（经传送门、1:8 坐标映射）。
- **Apple 地图风格 UI**：深色模式（`#242424`）+ 两级液态玻璃（卡片 `blur(50px)` + `rgba(0,0,0,0.6)`，控件 `blur(30px)` + `rgba(18,18,18,0.6)`，精确取自 Apple `shell.css` 与 `frame.html`）+ SF Pro 字体 + 控件 0.5px 细边框 + 图标透明度 0.55/0.85。控件尺寸精确匹配 Apple：指南针 48px 圆形、地图类型+定位 45×24px 横向药丸行、zoom 48×24px 矮药丸、搜索框聚焦 1px outline 蓝边、搜索列表 `#000`+`blur(15px)`、popover `#363636`+10px 圆角。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.13 + FastAPI + Uvicorn |
| 前端 | 原生 HTML/CSS/JS + [Leaflet 1.9.4](https://leafletjs.com/)（无框架） |
| 瓦片数据源 | 游戏内导出的 PNG 图片（放入 `map_source/` 即自动识别） |
| 图像处理 | Pillow（PIL） |

## 目录结构

```
minecraft_map/
├── backend/                 # FastAPI 后端
│   ├── main.py              # 入口：注册路由 + 托管前端静态文件
│   ├── data_loader.py       # 数据加载（dimensions/pois/portals/players）
│   ├── snapshot.py          # 快照扫描：遍历 map_source/ 建瓦片索引与 offset
│   ├── tile_server.py       # 瓦片端点 /api/tiles/{snapshot_id}/{z}/{x}/{y}.png
│   ├── waypoint.py          # Xaero 路径点解析：扫描 waypoint_source/ 去重
│   ├── pois.py              # POI CRUD + 搜索
│   └── routing.py           # A* 路径规划 + 跨维度传送门联动
├── frontend/
│   ├── index.html           # 地图页面（Apple 风格浮动布局）
│   ├── css/style.css
│   └── js/
│       ├── map.js           # Leaflet 地图核心：CRS + 瓦片层 + 快照/维度切换 + 缩放
│       ├── poi.js           # POI 标记 + 列表 + 详情卡
│       ├── waypoint.js      # Xaero 路径点标记 + 详情卡
│       ├── search.js        # 搜索 + 坐标跳转
│       └── routing.js       # 路线规划 UI
├── map_source/              # 地图快照源数据（用户放入）
│   └── YYYY-MM-DD_HH.MM.SS/ # 每个目录是一个快照
│       └── {n}_{n}_x{mc_x}_z{mc_z}.png  # 1024×1024 瓦片
├── waypoint_source/         # Xaero 路径点源数据（用户放入）
│   └── Multiplayer_<server>/ # 按服务器分目录
│       ├── dim%0/            # 维度目录 (dim%0=主世界, dim%-1=下界)
│       │   └── mw$<hash>_1.txt  # Xaero 路径点文件
│       └── config.txt        # Xaero 配置（忽略）
├── data/                    # JSON 数据
│   ├── dimensions.json      # 维度元数据
│   ├── pois.json            # POI 列表
│   ├── portals.json         # 传送门列表
│   └── players.json         # 玩家列表
├── scripts/                 # 工具脚本
│   ├── extract_xaero_cache.py   # （旧）Xaero cache.xaero → PNG 瓦片
│   └── verify_tiles.py          # （旧）瓦片有效性验证
├── 1.19.2TOBU0405/              # 原始 Minecraft 存档 + Xaero 缓存源（归档）
└── start.bat / start.ps1        # 启动脚本
```

## 快速开始

### 环境依赖

- Python 3.13+
- 依赖：`fastapi`、`uvicorn`、`pillow`

### 安装

```powershell
pip install fastapi uvicorn pillow
```

### 启动服务

```powershell
# 方式 1：批处理脚本
.\start.bat

# 方式 2：PowerShell 脚本
.\start.ps1

# 方式 3：直接运行
uvicorn backend.main:app --port 8000
```

启动后浏览器访问 [http://127.0.0.1:8000](http://127.0.0.1:8000)。

### 添加新的地图快照

1. 在游戏内导出地图为 PNG 图片（1024×1024，文件名格式 `{n}_{n}_x{mc_x}_z{mc_z}.png`）。
2. 在 `map_source/` 下新建目录，目录名为导出时间 `YYYY-MM-DD_HH.MM.SS`（如 `2026-07-09_15.49.33`）。
3. 将所有 PNG 放入该目录。
4. 刷新页面，右上角时钟按钮即可切换到新快照。

后端启动时会自动扫描 `map_source/` 下所有符合命名规则的目录，计算每个快照的瓦片索引、网格偏移和 bounds，无需重启。

### 添加 Xaero 路径点

1. 找到 Xaero minimap 的路径点目录（通常在 `.minecraft/XaeroWaypoints/Multiplayer_<server>/`）。
2. 将整个 `Multiplayer_<server>/` 目录复制到 `waypoint_source/` 下。
3. 刷新页面，路径点会自动显示在地图上（按 `(name, x, y, z)` 去重，跳过死亡点）。

路径点颜色使用 Xaero 原始颜色（16 色调色板），显示为 Apple 大头针样式。

## API 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/dimensions` | 维度元数据列表 |
| GET | `/api/snapshots` | 快照列表（含 bounds/offset/max_zoom） |
| GET | `/api/tiles/{snapshot_id}/{z}/{x}/{y}.png` | 瓦片图片（1024×1024，支持负坐标） |
| GET | `/api/pois` | POI 列表（可按 dim/category 筛选） |
| GET | `/api/pois/{id}` | 单个 POI 详情 |
| POST | `/api/pois` | 新增 POI |
| GET | `/api/search?q=` | 搜索（文本或 `x,z` 坐标） |
| GET | `/api/route` | 路径规划（A* + 传送门联动） |
| GET | `/api/portals` | 传送门列表 |
| GET | `/api/players` | 玩家列表 |
| GET | `/api/waypoints?dim=` | Xaero 路径点列表（已去重，跳过死亡点，可按 dim 筛选） |
| GET | `/api/health` | 健康检查 |

### 瓦片坐标映射

- **原生 zoom**：仅 `zoom=0`（1px=1block），更高 zoom 由 Leaflet 放大渲染。
- **瓦片尺寸**：1024×1024 像素，覆盖 1024×1024 方块。
- **网格偏移**：导出图 mc 坐标可能不对齐 1024 原点（如 z=-3584 = -3.5×1024），快照元数据中 `offset_x`/`offset_z` 记录此偏移，瓦片查找与 CRS 变换均需应用。
- **映射公式**：`mc_x = x * 1024 + offset_x`，`mc_z = y * 1024 + offset_z`
- **无 TMS 翻转**：y=0 在顶部（北方向）。
- **稀疏瓦片**：缺失瓦片返回 1×1 透明 PNG 占位图，避免 404 刷屏。

### 坐标系转换

Minecraft `(x, z)` ↔ Leaflet LatLng：
- `mc → latlng`：`lat = -z`，`lng = x`（北=上）
- `latlng → mc`：`x = lng`，`z = -lat`

CRS 变换加入 offset 使瓦片网格与导出图原点对齐：
```js
L.transformation(baseScale, offset_x, -baseScale, -offset_z)
// baseScale = 1 / 2^max_zoom
```

### 缩放范围

地图 zoom 范围扩展到 `[-4, 5]`，覆盖用户期望的 0.05x ~ 20x：

| zoom | 含义 | 倍率 | 瓦片来源 |
| --- | --- | --- | --- |
| -4 | 缩远看大范围 | ≈0.06x | 复用 zoom=0 缩小 |
| 0 | 原生分辨率 | 1x (1px=1block) | 原生瓦片 |
| 5 | 放大看细节 | ≈32x | 复用 zoom=0 放大 |

- `maxNativeZoom = minNativeZoom = snapshot.max_zoom`（=0），非原生 zoom 复用原生瓦片缩放
- `zoomSnap: 0.5` 允许半级缩放，滚轮体验更顺滑
- 三种缩放方式：右下角药丸形 +/- 控件、右侧工具栏 +/- 按钮、鼠标滚轮

## UI 控件（Apple 地图风格）

| 位置 | 控件 | 说明 |
| --- | --- | --- |
| 左上角 | 磨砂搜索框 + tab 面板 | 搜索地点/坐标，路线规划与 POI 列表切换 |
| 右上角 | 维度按钮（药丸） | 切换主世界/下界/末地（仅筛 POI） |
| 右上角 | 快照按钮（药丸） | 切换地图快照时间 |
| 右上角 | 指南针按钮（圆形） | 点击重置朝北（`flyTo` 回到默认 zoom） |
| 右上角 | 地图类型按钮（圆形） | 弹出菜单：标准/卫星/混合（仅标准可用） |
| 右上角 | +/- 按钮（圆形） | 放大/缩小 |
| 右下角 | 药丸形 +/- 控件 | Leaflet 原生 zoom 控件，样式改为药丸形 |
| 右下角 | 定位按钮（圆形） | 调用浏览器 geolocation，标记当前位置（Apple 蓝点） |
| 右下角 | 全屏按钮（圆形） | 切换全屏模式 |
| 左下角 | 坐标显示（磨砂） | 实时显示鼠标所在 MC 坐标与当前维度 |

**视觉风格**：深色模式（`--bg: #242424`，参照 Apple Maps `shell.css .mw-dark`）+ 两级液态玻璃（卡片级 `blur(50px)` + `rgba(0,0,0,0.6)`，控件级 `blur(30px)` + `rgba(18,18,18,0.6)`，精确取自 Apple `shell.css .mw-card` 与 `frame.html mk-dark-mode`，无 `saturate`）+ SF Pro 字体 + Apple system blue（`#0a84ff`）。控件有 0.5px 细边框（`box-shadow: 0 0 0 0.5px rgba(255,255,255,0.05)`），图标透明度 0.55（hover 0.85）。POI 标记为 Apple 大头针样式（水滴形 + 中心白点，颜色按类别区分）。用户位置标记为 Apple 蓝点（带脉冲动画）。

## 数据格式

### 快照元数据（`/api/snapshots` 返回）

```json
[
  {
    "id": "2026-07-09_15.49.33",
    "name": "2026-07-09 15:49",
    "date": "2026-07-09 15:49:33",
    "tile_count": 429,
    "tile_size": 1024,
    "max_zoom": 0,
    "offset_x": 0,
    "offset_z": 512,
    "bounds": { "min_x": -26624, "max_x": 24576, "min_z": -13824, "max_z": 10752 }
  }
]
```

### pois.json

```json
[
  {
    "id": "poi_0",
    "name": "t1",
    "dim": 0,
    "x": -23066,
    "z": -1438,
    "y": 69,
    "category": "landmark",
    "icon": "flag",
    "desc": "103.39.66.4"
  }
]
```

### 路径点（`/api/waypoints` 返回）

```json
[
  {
    "id": "wp_0",
    "name": "t1",
    "initials": "T",
    "x": -23066,
    "y": 69,
    "z": -1438,
    "color": "#404040",
    "dim": 0,
    "server": "Multiplayer_103.39.66.4"
  }
]
```

## GitHub Pages 部署

项目支持静态化部署到 GitHub Pages，无需后端。静态站点由 `build_static.py` 生成到 `tobu4th/` 目录。

**线上地址**：https://reconcileee.github.io/wanshui-maps/tobu4th

### 构建静态站点

```powershell
python build_static.py
```

产物结构：
- `tobu4th/index.html` + `css/` + `js/` — 前端（相对路径，兼容子路径部署）
- `tobu4th/data/*.json` — 静态数据（dimensions/pois/players/portals + 动态生成的 snapshots/waypoints）
- `tobu4th/tiles/<snapshot_id>/0/<x>/<y>.webp` — 瓦片（按 offset 对齐网格，**无损 WebP** 格式）

### 瓦片格式：无损 WebP

为加速 GitHub Pages 传输，静态站点的瓦片采用**无损 WebP** 格式（Pillow `lossless=True`），相比 PNG 平均减小约 37.5% 体积（本项目 242MB → 151MB），且无画质损失。

- 前端 `map.js` 瓦片 URL 后缀为 `.webp`
- 本地 FastAPI 开发仍用 PNG（`tile_server.py` 原样返回 PNG），WebP 仅用于静态站点
- 重新构建后需提交 `tobu4th/` 并推送，GitHub Pages 会自动重新部署

### 部署配置

- `.nojekyll` — 跳过 Jekyll 处理（必需，否则 `_` 开头的文件被忽略）
- 根 `index.html` — 重定向到 `tobu4th/`
- `.gitignore` — 排除 MC 游戏实例、反编译源码、原始瓦片源（`map_source/`）、Xaero 路径点源等

## 许可

本项目仅用于个人学习与 Minecraft 社区地图展示。

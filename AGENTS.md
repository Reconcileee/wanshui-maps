# AGENT.md

本文件为 AI 编程助手（agent）提供项目上下文与开发约定，帮助 agent 快速理解项目结构、避免重复踩坑。

## 项目概述

Minecraft 在线地图全栈应用。后端 FastAPI 服务瓦片与 API，前端 Leaflet 渲染地图。瓦片数据源来自游戏内导出的 1024×1024 PNG 图片（放入 `map_source/` 自动识别），按导出时间组织为多个"快照"，可在前端切换查看不同时间点的世界状态。前端 UI 采用 Apple 地图风格（深色模式 + 磨砂玻璃控件 + 药丸形/圆形按钮）。Xaero 路径点从 `waypoint_source/` 自动扫描，去重后显示为 Apple 大头针。

旧的 Xaero `cache.xaero` 解析方案已归档到 `scripts/extract_xaero_cache.py`（不再使用，但保留作为参考）。

## 开发约定

**每次修改项目后必须同步更新 AGENT.md**，记录新增的文件、架构变更、新的坑点。

## 关键架构约束

### 1. 快照系统（当前数据源）

- **位置**：`map_source/{snapshot_id}/*.png`
- **snapshot_id**：目录名，格式 `YYYY-MM-DD_HH.MM.SS`（如 `2026-07-09_15.49.33`）
- **瓦片文件名**：`{n}_{n}_x{mc_x}_z{mc_z}.png`，1024×1024 像素，1px=1block
- **mc_x / mc_z**：瓦片左上角对应的 Minecraft 方块坐标（可为负数）
- **原生 zoom**：仅 `zoom=0`（1px=1block），更高 zoom 由 Leaflet 放大渲染
- **扫描入口**：`backend/snapshot.py` 的 `get_snapshots()`（lru_cache 缓存，按时间倒序）
- **离群点处理**：`|mc_x| > 100000` 视为离群点，不计入主区域 bounds，但瓦片仍可按坐标访问

**不要把 tile 坐标 (x, y) 与 Minecraft 方块坐标 (mc_x, mc_z) 混淆**。tile 坐标是 Leaflet 整数网格，mc 坐标是方块绝对坐标，二者通过 `mc_x = x * 1024 + offset_x` 转换。

### 2. 网格偏移（offset）—— 关键坑点

导出图的 mc 坐标**不一定对齐 1024 原点**。例如本项目的快照中，所有主区域瓦片的 z 坐标偏移 512（如 `-3584 = -4×1024 + 512`），而 x 坐标对齐 0。

- **offset 计算**：取主区域首个 tile 的 `mc_x % 1024` 和 `mc_z % 1024`
- **应用位置（两处必须同步）**：
  1. `backend/tile_server.py` 瓦片查找：`mc_x = x * TILE_PX + snap["offset_x"]`
  2. `frontend/js/map.js` CRS transformation：`L.transformation(baseScale, offset_x, -baseScale, -offset_z)`
- **MC 坐标系本身不变**：`mcToLatLng`/`latLngToMc` 不需要 offset，因为 offset 只影响 tile 网格对齐，不影响真实方块坐标

**症状**：若漏掉 offset，所有主区域瓦片会返回 1×1 透明占位图（70 字节），地图一片空白。

### 3. 坐标映射（前端 `map.js`）

- Minecraft `(x, z)` → Leaflet LatLng：`[-z, x]`（北=上）
- Leaflet LatLng → Minecraft：`x = lng`，`z = -lat`
- CRS 变换：`L.transformation(baseScale, offset_x, -baseScale, -offset_z)`，其中 `baseScale = 1 / 2^max_zoom`
- `tileSize = 1024`，`tms = false`，`maxNativeZoom = minNativeZoom = max_zoom`（仅原生 zoom 0）

### 3.1 缩放范围（zoom range）

地图 zoom 范围扩展到 `[-4, 5]`，覆盖 0.06x ~ 32x：

- `minZoom: -4`（≈0.06x 缩远）、`maxZoom: 5`（≈32x 放大）、`zoomSnap: 0.5`（半级缩放）
- tileLayer 配置：`maxNativeZoom = minNativeZoom = snapshot.max_zoom`（=0），非原生 zoom 复用 zoom=0 瓦片缩放
- **关键**：tileLayer 的 `minZoom`/`maxZoom` 必须与 map 的 `minZoom`/`maxZoom` 一致，否则缩放时瓦片层会消失
- 三种缩放方式：右下角 Leaflet 原生 zoom 控件（`L.control.zoom`）、右侧工具栏自定义 +/- 按钮、鼠标滚轮

### 4. 维度系统（`data/dimensions.json`）

当前仅含主世界（id=0）。维度切换**仅更新 currentDim + POI/routing 筛选**，不重建地图（因瓦片源只有主世界快照，下界/末地无对应瓦片）。

### 5. POI 数据

POI 坐标为 Minecraft 真实坐标（含负数，如 `x=-23066`）。部分 POI 超出当前瓦片覆盖范围（远端地标），属正常现象——前端 `setMaxBounds` 留 50% padding 允许平移到 bounds 外。

### 6. 稀疏瓦片处理

`tile_server.py` 对有效 zoom 内缺失的瓦片返回 1×1 透明 PNG（70 字节 base64），**不返回 404**。否则 Leaflet 填充视口时会疯狂刷 404。透明 PNG 定义：

```python
TRANSPARENT_PNG = base64.b64decode(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNkYPhfDwAChwGA60l6gAAAAABJRU5ErkJggg=="
)
```

### 6.1 空白地块背景色

Leaflet 默认瓦片容器背景为蓝色，导致无图片源的地块显示蓝色。解决方案：CSS 将 `.leaflet-container` 和 `.leaflet-tile` 背景设为 `transparent !important`，使空白地块显示 `#map` 的深色背景 `#242424`。

### 6.2 指南针按钮（`compass-btn`）

Leaflet 不支持地图旋转，指南针按钮的实际行为是 `flyToBounds` 回到快照默认视野。**不要用 `flyTo(center, 0)`**，这会强制设 zoom=0（100% 缩放），应使用 `flyToBounds` 保持当前 zoom 或用 `flyTo(center, currentZoom)`。

### 6.3 Xaero 路径点系统（`waypoint.py` + `waypoint.js`）

- **位置**：`waypoint_source/Multiplayer_<server>/dim%<dim>/mw$<hash>_1.txt`
- **文件格式**：`waypoint:name:initials:x:y:z:color:disabled:type:set:rotate_on_tp:tp_yaw:visibility_type`
- **dim 目录**：`dim%0` = 主世界，`dim%-1` = 下界，`dim%1` = 末地（URL 编码的 `%`）
- **去重**：按 `(name, x, y, z)` 合并，同坐标同名只保留一条
- **跳过**：`gui.xaero_deathpoint_old`（死亡点，数量大且无意义）、`gui.xaero_default`（默认类型）
- **颜色**：Xaero 16 色调色板（`XAERO_COLORS` 数组），路径点自带 color 字段（0-15 索引）
- **前端展示**：Apple 大头针样式，通过 `--pin-color` 内联样式设置颜色（与 POI 的 `cat-*` 类不同）
- **API**：`/api/waypoints?dim=0`，可按维度筛选
- **初始化时序**：`waypoint.js` 的 `loadWaypoints` 在 DOMContentLoaded 触发，但需等待 `MCMap.map` 初始化完成后才能渲染标记（用 `setTimeout` 轮询）

### 7. Apple 地图风格 UI（`style.css` + `index.html` + `map.js`）

前端 UI 参照 Apple 地图深色模式实现（配色值精确取自 Apple `shell.css` 的 `.mw-dark` + `frame.html` 的 `mk-dark-mode`）：

**液态玻璃（核心，两级模糊，无 saturate）**：
- **卡片级** `--blur-card: blur(50px)` + `--panel: rgba(0,0,0,0.6)`（`#0009`）：搜索框、面板、详情卡、下拉菜单、suggest 列表（取自 shell.css `.mw-card`）
- **控件级** `--blur-control: blur(30px)` + `--panel-control: rgba(18,18,18,0.6)`（`#12121299`）：圆形按钮、Leaflet zoom 控件、坐标显示、比例尺（取自 frame.html `mk-controls`）
- **关键**：Apple 原版**没有 `saturate(180%)`**，只用纯 `blur()`。之前错误添加了 saturate 导致效果失真
- **控件细边框**：`--shadow-control: 0 0 0 0.5px rgba(255,255,255,0.05)`（Apple `mk-controls` 的 box-shadow）
- **控件状态**：默认 `rgba(18,18,18,0.6)`、按压 `rgba(42,42,42,0.6)`、聚焦 `rgba(12,49,89,0.6)` + 蓝边 `0 0 0 2px rgb(0,124,255)`
- **图标透明度**：默认 `opacity: 0.55`，hover/active `0.85`，禁用 `0.2`（仅图标，非整个按钮）

**控件精确尺寸（取自 frame.html mk-* shadow DOM）**：
- **指南针** `.tool-compass`：48×48px 圆形（Apple `mk-compass`），北方针 `#ff453a`，表盘 `fill-opacity:0.12`，刻度 `0.64`
- **地图类型+定位** `.tool-pill-row`：横向药丸行，共享一个背景，每按钮 45×24px（Apple `mk-top-right-controls`），中间 0.5px 分隔线
- **zoom 控件** `.leaflet-control-zoom`：48×24px 横向矮药丸（Apple `mk-zoom-controls`），`flex-direction: row`，每半按钮 24×24px，圆角 12px
- **搜索框聚焦**：`outline: 1px solid var(--accent)`（Apple 用 outline，非 box-shadow）
- **搜索列表**：`background: #000` + `blur(15px)`（Apple `mw-search-list` 深色）
- **popover**：`#363636` + `border: 1px solid #5a5c64` + `border-radius: 10px`（Apple `mk-popover`）
- **搜索图标**：16×16px，颜色 `--text-secondary`（Apple `--secondary-label`）

**CSS 变量**（`style.css :root`）：
- `--bg: #242424`（body 背景）、`--panel: rgba(0,0,0,0.6)`（卡片）、`--panel-control: rgba(18,18,18,0.6)`（控件）
- `--search-bar: rgba(0,0,0,0.4)`（搜索栏 `#0006`）、`--panel-solid: #1d1d1f`（popover）
- `--accent: #0a84ff`、`--border: rgba(84,84,88,0.55)`、`--radius-md: 16px`

**POI 大头针颜色**（`style.css` + `poi.js CATEGORY_COLOR`，两处必须一致）：
| 类别 | 类名 | 颜色 |
| --- | --- | --- |
| 地标 | `.cat-landmark` | `#ff453a`（红，Apple 默认） |
| 资源 | `.cat-resource` | `#ff9f0a`（橙） |
| 玩家 | `.cat-player` | `#0a84ff`（蓝） |
| 传送门 | `.cat-portal` | `#bf5af2`（紫） |

**右侧工具栏按钮顺序**（`index.html .map-tools`）：
1. 维度按钮（药丸，带下拉）
2. 快照按钮（药丸，带下拉）
3. 指南针按钮（圆形，`compass-btn`，点击 `flyTo` 回到默认 zoom=0）
4. 地图类型按钮（圆形，`map-type-btn`，弹出 `.map-type-popover` 菜单，仅"标准"可用）
5. +/- 按钮（圆形，`zoom-in-btn`/`zoom-out-btn`）
6. 定位按钮（圆形，`locate-btn`，调用 `navigator.geolocation`，标记 `.mc-user-location` 蓝点带脉冲动画）
7. 全屏按钮（圆形，`fullscreen-btn`）

**右下角**：Leaflet 原生 zoom 控件（`L.control.zoom({ position: 'bottomright' })`），CSS 改为药丸形。

**坑点**：
- `.tool-btn-wrap` 需 `position: relative` 作为 `.map-type-popover`（`position: absolute`）的定位上下文
- 所有下拉/弹出菜单的 `document.addEventListener('click')` 需统一关闭所有打开的菜单（维度/快照/地图类型）
- Leaflet zoom 控件不要用 `position: absolute !important` 覆盖定位，改用 `.leaflet-bottom.leaflet-right` 设置位置
- `CATEGORY_COLOR`（`poi.js`）与 `.mc-poi-marker.cat-*`（`style.css`）的颜色必须一致，否则列表小圆点和大头针颜色不匹配

## 开发约定

### 代码风格

- Python：类型注解 + 简洁文档字符串（中文）
- JS：无框架，原生 ES6+，模块通过全局对象通信（`MCMap`、`MCPoi` 等）
- 注释语言：中文

### 启动与验证

```powershell
# 启动服务
uvicorn backend.main:app --port 8000

# 验证 API
curl.exe -s http://127.0.0.1:8000/api/snapshots
# 应返回 [{id, name, offset_x, offset_z, bounds, ...}]

# 验证主区域瓦片返回真实图片 (size 应为几十 KB 而非 70 字节)
curl.exe -s -o NUL -w "%{size_download}" http://127.0.0.1:8000/api/tiles/2026-07-09_15.49.33/0/0/0.png
```

**注意**：
- PowerShell 中 `curl` 是 `Invoke-WebRequest` 的别名，参数不兼容。测试时**必须用 `curl.exe`**。
- PowerShell 会吞 `$variable`，所以测试命令里不要用 `$` 开头的 PowerShell 变量。
- 多条 curl 用 `;` 分隔，不要用 `&`（PowerShell 中 `&` 是调用操作符）。
- 修改后端代码后，需手动停掉旧 uvicorn 进程再重启（除非用 `--reload`）：
  ```powershell
  Get-NetTCPConnection -LocalPort 8000 | Select -ExpandProperty OwningProcess -Unique | % { Stop-Process -Id $_ -Force }
  ```

### 添加新快照

1. 在 `map_source/` 下新建目录 `YYYY-MM-DD_HH.MM.SS`
2. 放入导出的 PNG（文件名符合 `{n}_{n}_x{mc_x}_z{mc_z}.png`）
3. 重启服务（清掉 `get_snapshots` 的 lru_cache）或刷新页面

## 关键文件索引

| 文件 | 作用 |
| --- | --- |
| `backend/main.py` | FastAPI 入口，注册路由，托管前端，`/api/snapshots` + `/api/waypoints` 端点 |
| `backend/snapshot.py` | 快照扫描：遍历 `map_source/`，建瓦片索引、计算 offset/bounds（按时间倒序，最新在前） |
| `backend/tile_server.py` | 瓦片端点 `/api/tiles/{snapshot_id}/{z}/{x}/{y}.png`，应用 offset |
| `backend/waypoint.py` | Xaero 路径点解析：扫描 `waypoint_source/`，去重 + 跳过死亡点 + 颜色映射 |
| `backend/data_loader.py` | 数据加载（dimensions/pois/portals/players） |
| `backend/pois.py` | POI CRUD + 搜索 |
| `backend/routing.py` | A* 寻路 + 跨维度传送门联动 |
| `frontend/js/map.js` | 地图核心：CRS（含 offset）+ 瓦片层 + 快照/维度切换 + 缩放范围 [-4,5] + 指南针/地图类型/定位按钮逻辑 |
| `frontend/js/poi.js` | POI 标记（Apple 大头针）+ 列表 + 详情卡 + 类别筛选（含 `CATEGORY_COLOR` 颜色映射） |
| `frontend/js/waypoint.js` | Xaero 路径点标记（Apple 大头针 + 原始颜色）+ 详情卡 |
| `frontend/js/search.js` | 搜索与坐标跳转 |
| `frontend/js/routing.js` | 路线规划 UI |
| `frontend/css/style.css` | Apple 地图深色风格（配色取自 shell.css .mw-dark）：磨砂玻璃 blur(50px) + 药丸形/圆形按钮 + SF Pro 字体 + Apple 大头针标记 + 列表分隔线 + 透明瓦片背景 |
| `map_source/{snapshot_id}/` | 用户放入的快照 PNG 数据 |
| `waypoint_source/Multiplayer_<server>/` | 用户放入的 Xaero 路径点数据 |
| `data/dimensions.json` | 维度元数据 |
| `data/pois.json` | POI 列表 |
| `data/portals.json` | 传送门列表 |
| `scripts/extract_xaero_cache.py` | （归档）旧 Xaero cache.xaero 解析器 |
| `build_static.py` | 生成 GH Pages 静态站点到 `tobu4th/`：复制前端 + 烘焙 JSON + 瓦片转无损 WebP |
| `.nojekyll` | GH Pages 跳过 Jekyll 处理（必需） |
| `index.html`（根） | 重定向到 `tobu4th/` |
| `.gitignore` | 排除 MC 游戏实例、反编译、map_source、waypoint_source 等 |

## 已知坑点（避免重复踩）

1. **网格偏移（最大坑）**：导出图 mc 坐标可能不对齐 1024 原点。必须两处同步应用 offset：`tile_server.py` 的瓦片查找 + `map.js` 的 CRS transformation。漏一处即导致地图空白或坐标错位。

2. **稀疏瓦片 404 刷屏**：有效 zoom 内缺失瓦片必须返回透明 PNG，**不能返回 404**。Leaflet 会主动请求视口内所有 tile，404 会疯狂刷日志。

3. **快照 lru_cache**：`snapshot.py` 的 `get_snapshots()` 用 `@lru_cache()` 缓存，新增快照目录后需重启服务才生效。不要在请求处理中修改快照数据。

4. **PowerShell 语法**：
   - 不支持 `||` 作为语句分隔符
   - `curl` 是别名，必须用 `curl.exe`
   - `$variable` 会被 PowerShell 吞掉，测试命令避免使用
   - 多命令用 `;` 分隔，不用 `&`

5. **不要用 Playwright 做代码审查**（用户偏好）。

6. **瓦片坐标可为负**：文件名中 mc_x/mc_z 可为负数，URL 路径中的 tile 坐标 x/y 也可为负数，FastAPI 路由需正确处理（当前实现已支持）。

7. **维度切换不重建地图**：当前瓦片源只有主世界，`switchDimension` 只改 `currentDim` 并刷新 POI/routing 筛选，不调用 `loadSnapshot`。若未来支持多维度瓦片，需重构此处。

8. **Apple 地图 HTML 无法本地运行**：项目目录下保存的 Apple 地图 `index.html` 依赖 Apple CDN 的 JS 和鉴权 token，无法本地运行。Apple Maps 的 3D/Look Around/卫星图/真旋转在 Leaflet 不可实现，仅复刻视觉风格（磨砂玻璃 + 药丸/圆形按钮 + 深色模式）和部分功能（定位/地图类型占位/指南针重置朝北）。

9. **缩放范围与 tileLayer 配置**：tileLayer 的 `minZoom`/`maxZoom` 必须与 map 一致（当前均为 -4 到 5），否则在边界 zoom 瓦片层会消失。`maxNativeZoom = minNativeZoom = max_zoom`（=0）确保非原生 zoom 复用原生瓦片。

10. **下拉菜单互斥**：维度、快照、地图类型三个下拉/弹出菜单需互斥——打开一个时关闭其他。`initToolbar` 中的 `document.addEventListener('click')` 统一关闭所有，各按钮的 `click` handler 需 `stopPropagation` 并手动关闭其他菜单。

11. **静态站点瓦片格式（WebP）**：`build_static.py` 将 PNG 转为**无损 WebP**（Pillow `lossless=True`）以加速 GH Pages 传输（平均减小约 37.5%）。前端 `map.js` 瓦片 URL 后缀为 `.webp`。本地 FastAPI 开发仍用 PNG（`tile_server.py` 原样返回）。修改瓦片相关逻辑时需同时注意两套路径：本地 `.png`（`tile_server.py`）与静态 `.webp`（`build_static.py` 输出 + `map.js` 引用）。重新构建静态站点后需提交 `tobu4th/` 并推送，GH Pages 才会更新。

12. **GitHub Pages 子路径部署**：项目部署在 `https://reconcileee.github.io/wanshui-maps/tobu4th`（含子路径 `/wanshui-maps/tobu4th`），前端所有资源引用必须用**相对路径**（如 `css/style.css`、`js/map.js`、`data/pois.json`、`tiles/...`），不能用绝对路径 `/css/...`。`.nojekyll` 必须存在，否则 Jekyll 会忽略 `_` 开头的文件/目录。

13. **Cloudflare Pages 部署（推荐, 国内访问更快）**：除 GitHub Pages 外，项目同时部署到 Cloudflare Pages（访问地址 `https://wanshui-maps.pages.dev/tobu4th/`）。CF 在全球含亚太有 CDN 节点，国内访问速度优于 GH Pages。部署命令：`npx wrangler@latest pages deploy tobu4th --project-name wanshui-maps --commit-dirty=true --branch main`。首次需 `wrangler login` + `pages project create`。相对路径设计同时兼容两种部署。CF Pages 首次部署后可能出现短暂 522（CDN 同步中），等待 1-2 分钟后恢复。

14. **wrangler OAuth 登录**：`wrangler login` 通过 OAuth 浏览器流程授权，回调到 `localhost:8976/oauth/callback`。非交互环境（如 CI）无法使用，需改用 `CLOUDFLARE_API_TOKEN` 环境变量。登录后凭证保存在 `C:\Users\<user>\AppData\Roaming\xdg.config\.wrangler\`。

## 用户偏好

- 沟通语言：中文
- 部署偏好：免费方案（如 Hugging Face Spaces）
- 开发方式：顺序开发（先实现核心功能再扩展）
- 代码审查：**不要使用 Playwright**

## 开发流程参考

遵循 `CLAUDE.md` 中的约定：
1. **先思考再编码**：明确假设，不确定就问
2. **简单优先**：最小代码解决问题，不做投机性抽象
3. **外科手术式修改**：只改必须改的，不顺手重构
4. **目标驱动**：定义可验证的成功标准，循环直到通过

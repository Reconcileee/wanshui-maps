# Minecraft 在线网页地图 — 设计文档

> 日期: 2026-07-08
> 风格参考: map.gaode.com (高德地图)
> 目标: 为 Minecraft 存档/多人游戏制作在线网页地图，含地图索引与导航系统

## 1. 目标与范围

为 Minecraft 玩家提供类高德地图的网页地图体验：
- 瓦片底图渲染（类高德栅格地图）
- POI 地点索引（收藏夹式）
- 坐标 + 名称搜索
- A* 跨维度路径规划（含传送门联动）
- 多维度切换（主世界/下界/末地）+ 玩家位置显示

## 2. 三阶段渐进

1. **演示阶段（本次实现）**: 模拟 Xaero 格式示例数据 + 完整 UI/索引/导航
2. 上传阶段: 接入真实 region 文件解析
3. 服务器阶段: WebSocket 实时推送玩家位置

## 3. 技术栈

- 后端: Python 3.10+ / FastAPI / uvicorn / Pillow (瓦片生成)
- 前端: Leaflet 1.9 + 原生 JS (不引入框架)
- 部署: 本地优先（暂不部署）
- 坐标映射: Minecraft (x, z) ↔ 瓦片 (tile_x, tile_z)，1 块 = 1 像素 @ 最高缩放

## 4. 架构

```
浏览器 (Leaflet + 高德风格 UI)
    │ HTTP
FastAPI 后端
    /api/tiles/{dim}/{z}/{x}/{y}.png   按维度服务瓦片
    /api/pois                           POI CRUD
    /api/search?q=                      搜索 POI
    /api/walkable/{dim}                 可行走性网格 (A* 用)
    /api/portals                        传送门对
    /api/route?from=&to=                A* 跨维度寻路
    /api/dimensions                     维度列表
    /api/players                        玩家位置
数据层
    data/xaeroworldmap/<world>/tile_<dim>/  瓦片 (模拟 Xaero 格式)
    data/pois.json
    data/portals.json
    data/players.json
    data/walkable_<dim>.json
```

## 5. 演示数据生成

脚本 `scripts/gen_demo_data.py` 生成:
- 主世界 64×64 块: 草地/水/沙/石头/树林色块
- 下界 16×16 块: 地狱岩/熔岩/灵魂沙
- 末地 32×32 块: 末地石/虚空
- 2 对传送门 (主世界↔下界, 1:8 坐标映射)
- 8 个 POI (spawn、村庄×2、矿井、基地×2、神庙、要塞)
- 3 个示例玩家 (含维度、坐标、朝向)
- walkable 网格 (草地/沙可走，水/熔岩/石头为障碍)

## 6. A* + 传送门联动算法

1. 起点维度内 A* 搜索到最近传送门 A
2. 传送到对应维度 (主世界→下界: ÷8; 下界→主世界: ×8)
3. 目标维度内 A* 搜索到终点或下一传送门
4. 若终点跨维度，重复 2-3
5. 返回分段路径 + 总代价 + 传送点

代价函数: 欧氏距离 + 传送门固定开销 (10)
障碍: water, lava, stone (演示阶段); 真实数据按方块 ID 判定

## 7. 前端 UI (高德风格)

### 布局
- 顶栏: 搜索框 (圆角白底) + 图层切换 + 设置
- 左侧栏 260px: 维度切换、POI 类别筛选、路径规划面板
- 地图区: Leaflet 瓦片 + 矢量叠加
- 右下: 缩放 +/- 控件 (高德位置)
- 左下: 比例尺 + 坐标显示

### 视觉规范
- 主色 #1890ff (高德蓝)
- 路径线 #0084ff
- 传送门 #722ed1
- POI 类别色: 地标红 #f5222d / 资源黄 #faad14 / 玩家绿 #52c41a / 传送门紫 #722ed1
- 字体: 系统无衬线

### 交互
- 点击地图: 显示坐标 + 可设为起点/终点
- 点击 POI: 弹详情卡 (名称/坐标/描述/设为起点/设为终点/跳转)
- 搜索: 实时联想 + 回车跳转
- 维度切换: 切换瓦片层 + POI 过滤
- 路径结果: 高亮折线 + 分段标签

## 8. 目录结构

```
minecraft_map/
├── docs/design.md
├── backend/
│   ├── main.py              FastAPI 入口
│   ├── tile_server.py       瓦片服务
│   ├── pois.py              POI API
│   ├── routing.py           A* + 传送门
│   └── data_loader.py       数据加载
├── frontend/
│   ├── index.html
│   ├── css/style.css        高德风格
│   └── js/
│       ├── map.js           Leaflet 初始化
│       ├── poi.js           POI 交互
│       ├── search.js        搜索
│       └── routing.js       路径规划 UI
├── scripts/gen_demo_data.py
├── data/                    演示数据 (生成)
└── requirements.txt
```

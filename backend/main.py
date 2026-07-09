"""FastAPI 入口: 整合所有 API 路由 + 托管前端静态文件。

启动: uvicorn backend.main:app --reload --port 8000
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from . import data_loader, snapshot, waypoint
from .tile_server import router as tile_router
from .pois import router as poi_router
from .routing import router as route_router

app = FastAPI(title="Minecraft 在线地图", version="0.1.0")

# 瓦片路由: 挂在根路径, 与前端静态相对路径 tiles/{id}/{z}/{x}/{y}.png 一致
# (本地动态从 map_source 计算; GH Pages 静态由 build_static.py 预生成同名文件)
app.include_router(tile_router, prefix="")
app.include_router(poi_router, prefix="/api")
app.include_router(route_router, prefix="/api")


@app.get("/api/dimensions")
def dimensions():
    return data_loader.get_dimensions()


@app.get("/api/snapshots")
def snapshots():
    """地图快照列表 (按导出时间), 每个含 bounds/tile_size/max_zoom 供前端建图"""
    return snapshot.snapshots_public()


@app.get("/api/players")
def players(dim: int | None = None):
    ps = data_loader.get_players()
    if dim is not None:
        ps = [p for p in ps if p["dim"] == dim]
    return ps


@app.get("/api/waypoints")
def waypoints(dim: int | None = None):
    """Xaero 路径点列表 (已去重, 跳过死亡点), 可按 dim 筛选"""
    wps = waypoint.get_waypoints()
    if dim is not None:
        wps = [w for w in wps if w["dim"] == dim]
    return wps


@app.get("/api/health")
def health():
    return {"status": "ok"}


# 前端静态文件 (在 frontend/ 目录)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


# 前端用静态相对路径 data/*.json 取数据。dimensions/pois/players/portals 是
# 磁盘文件, 由 StaticFiles 直接服务; snapshots/waypoints 是动态计算的, 单独建路由。
# 注意: 这两个动态路由必须声明在 /data 挂载之前, 否则会被 StaticFiles 抢先匹配。
@app.get("/data/snapshots.json")
def data_snapshots():
    return snapshot.snapshots_public()


@app.get("/data/waypoints.json")
def data_waypoints():
    return waypoint.get_waypoints()


# 静态资源: /css, /js, /data (JSON)
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

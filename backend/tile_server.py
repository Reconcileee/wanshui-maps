"""按快照服务地图瓦片 PNG。URL: /api/tiles/{snapshot_id}/{z}/{x}/{y}.png

数据源: map_source/{snapshot_id}/*.png (1024x1024, 1px=1block)
坐标映射: Leaflet tile 坐标 (x,y) → MC (x*1024, y*1024), 北=上, 无 TMS 翻转。
稀疏瓦片处理: 缺失瓦片返回透明 PNG 占位图, 避免 Leaflet 填充视口时 404 刷屏。
"""
import base64

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from .snapshot import TILE_PX, get_snapshot

router = APIRouter()

# 1x1 透明 PNG (RGBA), 浏览器会拉伸到 tileSize 填充瓦片槽
TRANSPARENT_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNkYPhfDwAChwGA60l6gAAAAABJRU5ErkJggg=="
)


@router.get("/tiles/{snapshot_id}/{z}/{x}/{y}.png")
def get_tile(snapshot_id: str, z: int, x: int, y: int):
    snap = get_snapshot(snapshot_id)
    if snap is None:
        raise HTTPException(404, f"未知快照: {snapshot_id}")

    # 仅原生 zoom 0 有真实瓦片; z>0 由 Leaflet 用 z=0 放大 (后端不会收到 z>0 请求)
    if z < 0 or z > snap["max_zoom"]:
        raise HTTPException(404, f"zoom 越界: {z}")

    # tile 坐标 → MC 坐标 (每瓦片覆盖 1024x1024 方块, 加网格偏移对齐导出图原点)
    mc_x = x * TILE_PX + snap["offset_x"]
    mc_z = y * TILE_PX + snap["offset_z"]

    path = snap["tiles"].get((mc_x, mc_z))
    if path is None:
        # 稀疏瓦片: 返回透明占位图而非 404
        return Response(TRANSPARENT_PNG, media_type="image/png")
    return FileResponse(path, media_type="image/png")

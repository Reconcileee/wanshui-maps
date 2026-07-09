"""地图快照管理: 扫描 map_source/ 下按时间命名的目录, 每个目录是一个导出快照。

文件名格式: {n}_{n}_x{mc_x}_z{mc_z}.png (1024x1024, 1px=1block)
坐标映射: Leaflet tile 坐标 (x,y) → MC (x*1024, y*1024), 北=上, 无 TMS 翻转。
bounds 计算: 排除 |x|>100000 的离群点, 使 fitBounds 聚焦主区域; 离群点瓦片仍可按坐标访问。
"""
import re
from datetime import datetime
from pathlib import Path
from functools import lru_cache

MAP_SOURCE_DIR = Path(__file__).resolve().parent.parent / "map_source"
TILE_PX = 1024          # 每张瓦片 1024x1024 像素
BLOCKS_PER_TILE = 1024  # 1px=1block, 每瓦片覆盖 1024x1024 方块
MAX_NATIVE_ZOOM = 0      # 仅原生 zoom 0 (1px=1block), 更高 zoom 由 Leaflet 放大
OUTLIER_X = 100000       # |mc_x| 超过此值视为离群点, 不计入主区域 bounds

_FILE_RE = re.compile(r"^\d+_\d+_x(-?\d+)_z(-?\d+)\.png$")


def _parse_dir_name(name: str) -> datetime | None:
    """目录名 YYYY-MM-DD_HH.MM.SS → datetime, 失败返回 None"""
    try:
        return datetime.strptime(name, "%Y-%m-%d_%H.%M.%S")
    except ValueError:
        return None


@lru_cache()
def get_snapshots() -> list[dict]:
    """返回所有快照, 按时间倒序。每个含瓦片索引(内部用 tiles 字段)。"""
    snapshots: list[dict] = []
    if not MAP_SOURCE_DIR.exists():
        return snapshots

    for d in MAP_SOURCE_DIR.iterdir():
        if not d.is_dir():
            continue
        dt = _parse_dir_name(d.name)
        if dt is None:
            continue

        tiles: dict[tuple[int, int], Path] = {}
        for f in d.glob("*.png"):
            m = _FILE_RE.match(f.name)
            if not m:
                continue
            mc_x, mc_z = int(m.group(1)), int(m.group(2))
            tiles[(mc_x, mc_z)] = f

        if not tiles:
            continue

        # 主区域 bounds 排除 x 离群点, 使 fitBounds 聚焦主区域
        main_tiles = [(mx, mz) for (mx, mz) in tiles if abs(mx) < OUTLIER_X]
        main_xs = [mx for mx, _ in main_tiles]
        main_zs = [mz for _, mz in main_tiles]

        # 瓦片网格偏移: 图片 mc 坐标 mod 1024 应一致 (导出图可能不对齐原点),
        # 取主区域首个 tile 的 offset, CRS 与瓦片查找均用此偏移对齐图片网格。
        sx, sz = main_tiles[0]
        offset_x = sx % TILE_PX
        offset_z = sz % TILE_PX

        snapshots.append({
            "id": d.name,
            "name": dt.strftime("%Y-%m-%d %H:%M"),
            "date": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "tile_count": len(tiles),
            "tile_size": TILE_PX,
            "max_zoom": MAX_NATIVE_ZOOM,
            "offset_x": offset_x,
            "offset_z": offset_z,
            "bounds": {
                "min_x": min(main_xs),
                "max_x": max(main_xs) + BLOCKS_PER_TILE,
                "min_z": min(main_zs),
                "max_z": max(main_zs) + BLOCKS_PER_TILE,
            },
            "tiles": tiles,  # 内部字段, 不返回给前端
        })

    # 按时间倒序 (最新在前)
    snapshots.sort(key=lambda s: s["id"], reverse=True)
    return snapshots


def get_snapshot(snapshot_id: str) -> dict | None:
    """按 id 查单个快照 (含 tiles 索引)。"""
    for s in get_snapshots():
        if s["id"] == snapshot_id:
            return s
    return None


def snapshots_public() -> list[dict]:
    """返回给前端的快照列表 (去掉内部 tiles 字段)。"""
    return [
        {k: v for k, v in s.items() if k != "tiles"}
        for s in get_snapshots()
    ]

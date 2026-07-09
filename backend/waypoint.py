"""Xaero 路径点解析: 扫描 waypoint_source/ 下所有服务器的路径点文件。

文件格式 (Xaero minimap/worldmap waypoint):
  waypoint:name:initials:x:y:z:color:disabled:type:set:rotate_on_tp:tp_yaw:visibility_type

目录结构:
  waypoint_source/
    Multiplayer_<server>/
      dim%<dim>/                  # dim%0 = 主世界, dim%-1 = 下界, dim%1 = 末地
        mw$<hash>_1.txt
      config.txt                   # 忽略

去重: 按 (name, x, y, z) 合并, 同坐标同名只保留一条。
跳过: gui.xaero_deathpoint_old (死亡点, 数量大且无意义)。
"""
import re
from pathlib import Path
from functools import lru_cache

WAYPOINT_SOURCE_DIR = Path(__file__).resolve().parent.parent / "waypoint_source"

# Xaero 颜色索引 → hex (Xaero minimap 默认 16 色调色板)
XAERO_COLORS = [
    "#ffffff",  # 0  white
    "#ff0000",  # 1  red
    "#ff8000",  # 2  orange
    "#ffff00",  # 3  yellow
    "#80ff00",  # 4  lime
    "#00ff00",  # 5  green
    "#00ff80",  # 6  aqua
    "#00ffff",  # 7  cyan
    "#0080ff",  # 8  blue
    "#0000ff",  # 9  dark blue
    "#8000ff",  # 10 purple
    "#ff00ff",  # 11 magenta
    "#ff0080",  # 12 pink
    "#808080",  # 13 gray
    "#404040",  # 14 dark gray
    "#000000",  # 15 black
]

_DIM_RE = re.compile(r"dim%(-?\d+)")
_WP_RE = re.compile(r"^waypoint:([^:]*):([^:]*):(-?\d+):(-?\d+):(-?\d+):(\d+)")

# 跳过的路径点名 (无意义)
_SKIP_NAMES = {"gui.xaero_deathpoint_old", "gui.xaero_default"}


@lru_cache()
def get_waypoints() -> list[dict]:
    """扫描所有服务器的路径点文件, 返回去重后的路径点列表。"""
    if not WAYPOINT_SOURCE_DIR.exists():
        return []

    seen: set[tuple[str, int, int, int]] = set()
    waypoints: list[dict] = []
    wp_id = 0

    for server_dir in WAYPOINT_SOURCE_DIR.iterdir():
        if not server_dir.is_dir():
            continue
        for dim_dir in server_dir.iterdir():
            if not dim_dir.is_dir():
                continue
            m = _DIM_RE.match(dim_dir.name)
            if m is None:
                continue
            dim = int(m.group(1))
            for txt in dim_dir.glob("mw*.txt"):
                for line in txt.read_text(encoding="utf-8", errors="ignore").splitlines():
                    m2 = _WP_RE.match(line)
                    if not m2:
                        continue
                    name = m2.group(1)
                    if name in _SKIP_NAMES:
                        continue
                    x, y, z = int(m2.group(3)), int(m2.group(4)), int(m2.group(5))
                    color_idx = int(m2.group(6))
                    key = (name, x, y, z)
                    if key in seen:
                        continue
                    seen.add(key)
                    waypoints.append({
                        "id": f"wp_{wp_id}",
                        "name": name,
                        "initials": m2.group(2),
                        "x": x,
                        "y": y,
                        "z": z,
                        "color": XAERO_COLORS[color_idx] if 0 <= color_idx < len(XAERO_COLORS) else "#ff0000",
                        "dim": dim,
                        "server": server_dir.name,
                    })
                    wp_id += 1

    return waypoints

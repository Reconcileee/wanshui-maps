"""生成 GitHub Pages 静态站点到 tobu4th/。

产物结构 (部署后访问 https://<user>.github.io/wanshui-maps/tobu4th/):
  tobu4th/
    index.html, css/, js/         ← 复制自 frontend/ (已改为静态相对路径)
    data/*.json                    ← dimensions/pois/players/portals 复制, snapshots/waypoints 动态生成
    tiles/<snapshot_id>/0/<x>/<y>.png  ← 由 map_source 重命名而来 (offset 对齐)

瓦片坐标映射与 backend/tile_server.py 一致:
  mc_x = x * TILE_PX + offset_x  →  x = (mc_x - offset_x) // TILE_PX
  mc_z = y * TILE_PX + offset_z  →  y = (mc_z - offset_z) // TILE_PX
原生瓦片仅 z=0 (max_native_zoom=0), 更高/更低 zoom 由 Leaflet 复用 z=0 缩放, 故只生成 0/。

用法: python build_static.py
"""
import json
import shutil
from pathlib import Path

from backend import snapshot, waypoint
from backend.snapshot import TILE_PX

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "tobu4th"


def _copy_tree(src: Path, dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def build():
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    # 1. 前端 (已改为静态相对路径)
    shutil.copy(FRONTEND_DIR / "index.html", OUT_DIR / "index.html")
    _copy_tree(FRONTEND_DIR / "css", OUT_DIR / "css")
    _copy_tree(FRONTEND_DIR / "js", OUT_DIR / "js")

    # 2. 静态 JSON 数据
    (OUT_DIR / "data").mkdir(parents=True, exist_ok=True)
    for name in ("dimensions", "pois", "players", "portals"):
        shutil.copy(DATA_DIR / f"{name}.json", OUT_DIR / "data" / f"{name}.json")
    _write_json(OUT_DIR / "data" / "snapshots.json", snapshot.snapshots_public())
    _write_json(OUT_DIR / "data" / "waypoints.json", waypoint.get_waypoints())

    # 3. 瓦片: map_source → tiles/<id>/0/<x>/<y>.png (按 offset 对齐网格)
    snapshots = snapshot.get_snapshots()
    total_tiles = 0
    for snap in snapshots:
        out_tile_dir = OUT_DIR / "tiles" / snap["id"] / "0"
        ox, oz = snap["offset_x"], snap["offset_z"]
        for (mc_x, mc_z), src_path in snap["tiles"].items():
            tx = (mc_x - ox) // TILE_PX
            ty = (mc_z - oz) // TILE_PX
            dest = out_tile_dir / str(tx) / f"{ty}.png"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src_path, dest)
            total_tiles += 1

    print(f"构建完成: {OUT_DIR}")
    print(f"  快照数: {len(snapshots)}")
    print(f"  瓦片总数: {total_tiles}")
    for snap in snapshots:
        print(f"  - {snap['id']}: {len(snap['tiles'])} 瓦片, "
              f"offset=({snap['offset_x']},{snap['offset_z']}), "
              f"max_zoom={snap['max_zoom']}")


if __name__ == "__main__":
    build()

"""生成演示数据: 模拟 Xaero World Map 格式的瓦片 + POI/传送门/玩家/walkable。

运行: python scripts/gen_demo_data.py
输出到 data/ 目录。
"""
import json
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw

# ---------- 配置 ----------
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TILE_DIR = DATA_DIR / "xaeroworldmap" / "DemoWorld"
TILE_SIZE = 256  # Leaflet 标准瓦片大小

# 维度: (dim_id, name, world_size_blocks, max_zoom, base_color)
# max_zoom 满足 256 * 2^max_zoom >= world_size
# 所有维度统一 1024x1024, max_zoom=2, 以便共享 CRS 变换 (0.25, 0, -0.25, 0)
DIMENSIONS = [
    {"id": 0, "name": "主世界", "size": 1024, "max_zoom": 2},
    {"id": -1, "name": "下界", "size": 1024, "max_zoom": 2},
    {"id": 1, "name": "末地", "size": 1024, "max_zoom": 2},
]

# 地形色块 (R,G,B)
TERRAIN = {
    "grass":      (124, 189, 107),  # 草地
    "water":      (64, 120, 200),   # 水
    "sand":       (218, 197, 142),  # 沙地
    "stone":      (130, 130, 130),  # 石头/山
    "forest":     (76, 124, 76),    # 树林
    "netherrack": (110, 40, 40),    # 地狱岩
    "lava":       (220, 100, 30),   # 熔岩
    "soul_sand":  (90, 70, 50),     # 灵魂沙
    "end_stone":  (220, 215, 180),  # 末地石
    "void":       (20, 20, 20),     # 虚空
}

# 可行走性: True=可走, False=障碍
WALKABLE = {
    "grass": True, "water": False, "sand": True, "stone": False, "forest": True,
    "netherrack": True, "lava": False, "soul_sand": True,
    "end_stone": True, "void": False,
}

random.seed(42)


def gen_terrain(dim_id: int, size: int) -> list[list[str]]:
    """生成地形类型网格 size×size。"""
    grid = [[None] * size for _ in range(size)]

    if dim_id == 0:  # 主世界
        # 基础草地
        for x in range(size):
            for z in range(size):
                grid[x][z] = "grass"
        # 水湖 (3个)
        for cx, cz, r in [(200, 200, 80), (700, 300, 60), (500, 800, 100)]:
            for x in range(max(0, cx - r), min(size, cx + r)):
                for z in range(max(0, cz - r), min(size, cz + r)):
                    if (x - cx) ** 2 + (z - cz) ** 2 < r * r:
                        grid[x][z] = "water"
        # 沙滩 (水边)
        for x in range(size):
            for z in range(size):
                if grid[x][z] == "grass":
                    for dx, dz in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, nz = x + dx, z + dz
                        if 0 <= nx < size and 0 <= nz < size and grid[nx][nz] == "water":
                            grid[x][z] = "sand"
                            break
        # 山脉 (石头)
        for cx, cz, r in [(150, 700, 90), (850, 850, 70)]:
            for x in range(max(0, cx - r), min(size, cx + r)):
                for z in range(max(0, cz - r), min(size, cz + r)):
                    if (x - cx) ** 2 + (z - cz) ** 2 < r * r:
                        grid[x][z] = "stone"
        # 树林 (随机斑块)
        for _ in range(15):
            cx, cz = random.randint(0, size - 1), random.randint(0, size - 1)
            r = random.randint(20, 50)
            for x in range(max(0, cx - r), min(size, cx + r)):
                for z in range(max(0, cz - r), min(size, cz + r)):
                    if (x - cx) ** 2 + (z - cz) ** 2 < r * r and grid[x][z] == "grass":
                        if random.random() < 0.7:
                            grid[x][z] = "forest"

    elif dim_id == -1:  # 下界
        for x in range(size):
            for z in range(size):
                grid[x][z] = "netherrack"
        # 熔岩湖
        for cx, cz, r in [(300, 300, 120), (760, 700, 90), (200, 800, 70)]:
            for x in range(max(0, cx - r), min(size, cx + r)):
                for z in range(max(0, cz - r), min(size, cz + r)):
                    if (x - cx) ** 2 + (z - cz) ** 2 < r * r:
                        grid[x][z] = "lava"
        # 灵魂沙
        for _ in range(12):
            cx, cz = random.randint(0, size - 1), random.randint(0, size - 1)
            r = random.randint(30, 60)
            for x in range(max(0, cx - r), min(size, cx + r)):
                for z in range(max(0, cz - r), min(size, cz + r)):
                    if (x - cx) ** 2 + (z - cz) ** 2 < r * r and grid[x][z] == "netherrack":
                        grid[x][z] = "soul_sand"

    elif dim_id == 1:  # 末地
        for x in range(size):
            for z in range(size):
                grid[x][z] = "void"
        # 中央末地岛
        cx, cz = size // 2, size // 2
        r = 180
        for x in range(max(0, cx - r), min(size, cx + r)):
            for z in range(max(0, cz - r), min(size, cz + r)):
                if (x - cx) ** 2 + (z - cz) ** 2 < r * r:
                    grid[x][z] = "end_stone"
        # 小岛
        for ox, oz, r in [(cx + 260, cz, 60), (cx - 240, cz + 120, 50), (cx + 80, cz - 260, 45)]:
            for x in range(max(0, ox - r), min(size, ox + r)):
                for z in range(max(0, oz - r), min(size, oz + r)):
                    if (x - ox) ** 2 + (z - oz) ** 2 < r * r:
                        grid[x][z] = "end_stone"

    return grid


def terrain_to_image(grid: list[list[str]], size: int) -> Image.Image:
    """地形网格 → PIL Image。"""
    img = Image.new("RGB", (size, size))
    px = img.load()
    for x in range(size):
        for z in range(size):
            px[x, z] = TERRAIN[grid[x][z]]
    return img


def slice_tiles(img: Image.Image, dim_id: int, size: int, max_zoom: int):
    """将完整地形图切片为瓦片金字塔，存到 tile_<dim>/<z>/<x>/<y>.png (TMS y-flipped)。"""
    out = TILE_DIR / f"tile_{dim_id}"
    out.mkdir(parents=True, exist_ok=True)

    for z in range(max_zoom + 1):
        tiles_per_side = 2 ** z
        # 该 zoom 下整图像素 = tiles_per_side * TILE_SIZE
        full_px = tiles_per_side * TILE_SIZE
        scaled = img.resize((full_px, full_px), Image.NEAREST)
        zdir = out / str(z)
        zdir.mkdir(exist_ok=True)
        for tx in range(tiles_per_side):
            xdir = zdir / str(tx)
            xdir.mkdir(exist_ok=True)
            for ty in range(tiles_per_side):
                # TMS: y 轴翻转
                tms_y = tiles_per_side - 1 - ty
                box = (tx * TILE_SIZE, tms_y * TILE_SIZE, (tx + 1) * TILE_SIZE, (tms_y + 1) * TILE_SIZE)
                tile = scaled.crop(box)
                tile.save(xdir / f"{ty}.png")


def gen_walkable(grid, size, dim_id):
    """地形网格 → walkable 网格 (布尔值二维数组)。"""
    w = [[WALKABLE[grid[x][z]] for z in range(size)] for x in range(size)]
    (DATA_DIR / f"walkable_{dim_id}.json").write_text(
        json.dumps({"size": size, "grid": w}), encoding="utf-8"
    )


def gen_pois():
    """8 个 POI。"""
    pois = [
        {"id": "poi_spawn",      "name": "出生点",   "dim": 0,  "x": 512, "z": 512, "category": "landmark", "icon": "flag", "desc": "世界出生点"},
        {"id": "poi_village1",   "name": "草原村",   "dim": 0,  "x": 300, "z": 400, "category": "landmark", "icon": "home", "desc": "NPC 村庄"},
        {"id": "poi_village2",   "name": "河边镇",   "dim": 0,  "x": 750, "z": 250, "category": "landmark", "icon": "home", "desc": "河边村庄"},
        {"id": "poi_mine",       "name": "废弃矿井", "dim": 0,  "x": 850, "z": 700, "category": "resource", "icon": "pick", "desc": "矿物资源点"},
        {"id": "poi_base1",      "name": "主基地",   "dim": 0,  "x": 600, "z": 600, "category": "landmark", "icon": "star", "desc": "玩家主基地"},
        {"id": "poi_base2",      "name": "分基地",   "dim": 0,  "x": 200, "z": 800, "category": "landmark", "icon": "star", "desc": "玩家分基地"},
        {"id": "poi_temple",     "name": "沙漠神庙", "dim": 0,  "x": 400, "z": 150, "category": "resource", "icon": "chest", "desc": "宝箱资源"},
        {"id": "poi_fortress",   "name": "下界要塞", "dim": -1, "x": 200, "z": 200, "category": "landmark", "icon": "castle", "desc": "下界要塞"},
        {"id": "poi_end_city",   "name": "末地城",   "dim": 1,  "x": 560, "z": 480, "category": "resource", "icon": "chest", "desc": "末地城堡"},
    ]
    (DATA_DIR / "pois.json").write_text(json.dumps(pois, ensure_ascii=False, indent=2), encoding="utf-8")
    return pois


def gen_portals():
    """2 对传送门 (主世界 ↔ 下界, 1:8 坐标映射)。"""
    portals = [
        {"overworld": {"x": 400, "z": 400}, "nether": {"x": 50, "z": 50}},
        {"overworld": {"x": 800, "z": 200}, "nether": {"x": 100, "z": 25}},
    ]
    (DATA_DIR / "portals.json").write_text(json.dumps(portals, ensure_ascii=False, indent=2), encoding="utf-8")
    return portals


def gen_players():
    """3 个示例玩家。"""
    players = [
        {"id": "p1", "name": "Steve",  "dim": 0,  "x": 515, "z": 510, "yaw": 90,  "world": "DemoWorld"},
        {"id": "p2", "name": "Alex",   "dim": 0,  "x": 300, "z": 405, "yaw": 180, "world": "DemoWorld"},
        {"id": "p3", "name": "Notch",  "dim": -1, "x": 205, "z": 195, "yaw": 270, "world": "DemoWorld"},
    ]
    (DATA_DIR / "players.json").write_text(json.dumps(players, ensure_ascii=False, indent=2), encoding="utf-8")
    return players


def gen_dimensions_meta():
    (DATA_DIR / "dimensions.json").write_text(
        json.dumps(DIMENSIONS, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"输出目录: {DATA_DIR}")

    for d in DIMENSIONS:
        dim_id, size, max_zoom = d["id"], d["size"], d["max_zoom"]
        print(f"生成 {d['name']} ({size}x{size}, zoom 0-{max_zoom})...")
        grid = gen_terrain(dim_id, size)
        img = terrain_to_image(grid, size)
        # 保存完整图 (调试用)
        img.save(DATA_DIR / f"terrain_{dim_id}.png")
        slice_tiles(img, dim_id, size, max_zoom)
        gen_walkable(grid, size, dim_id)

    print("生成 POI/传送门/玩家/维度元数据...")
    gen_pois()
    gen_portals()
    gen_players()
    gen_dimensions_meta()

    print("完成。瓦片目录:", TILE_DIR)


if __name__ == "__main__":
    main()

"""验证生成的瓦片: 检查文件大小、非透明像素比例、地图边界"""
from pathlib import Path
from PIL import Image
import json

TILES_DIR = Path(r"d:\aiide_project\trae_project\projects\minecraft_map\frontend\tiles\xaero")

stats = {}
all_coords = []

for level_dir in sorted(TILES_DIR.iterdir()):
    if not level_dir.is_dir():
        continue
    level = level_dir.name
    level_tiles = []

    for png_path in sorted(level_dir.glob("*.png")):
        name = png_path.stem
        parts = name.split("_")
        if len(parts) != 2:
            continue
        tx, tz = int(parts[0]), int(parts[1])
        level_tiles.append((tx, tz))

        img = Image.open(png_path)
        w, h = img.size

        # 检查非透明像素
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        bbox = img.getbbox()  # 非 None 说明有非透明像素
        pixels = img.load()
        non_empty = 0
        total = w * h
        # 采样检查 (每 10 个像素)
        for y in range(0, h, 10):
            for x in range(0, w, 10):
                if pixels[x, y][3] > 0:
                    non_empty += 1
        sampled_total = len(range(0, h, 10)) * len(range(0, w, 10))
        fill_ratio = non_empty / sampled_total if sampled_total > 0 else 0

        if level not in stats:
            stats[level] = {
                'count': 0,
                'sizes': set(),
                'fill_ratios': [],
                'coords': []
            }
        stats[level]['count'] += 1
        stats[level]['sizes'].add((w, h))
        stats[level]['fill_ratios'].append(fill_ratio)
        stats[level]['coords'].append((tx, tz))
        all_coords.append((int(level), tx, tz))

    if level_tiles:
        xs = [c[0] for c in level_tiles]
        zs = [c[1] for c in level_tiles]
        print(f"\nLevel {level}: {len(level_tiles)} tiles")
        print(f"  X range: {min(xs)} to {max(xs)}")
        print(f"  Z range: {min(zs)} to {max(zs)}")
        print(f"  Tile sizes: {stats[level]['sizes']}")
        avg_fill = sum(stats[level]['fill_ratios']) / len(stats[level]['fill_ratios'])
        print(f"  Avg fill ratio: {avg_fill:.2%}")

# 整体统计
print(f"\n{'='*50}")
print(f"Total tiles: {sum(s['count'] for s in stats.values())}")
print(f"Levels: {sorted(stats.keys())}")

# 检查 level 3 (最详细) 的瓦片
if '3' in stats:
    print(f"\nLevel 3 details (most detailed):")
    for tx, tz in sorted(stats['3']['coords']):
        png_path = TILES_DIR / '3' / f"{tx}_{tz}.png"
        img = Image.open(png_path)
        bbox = img.getbbox()
        print(f"  ({tx},{tz}): size={img.size}, has_content={bbox is not None}")

# 保存坐标范围供后端使用
bounds = {}
for level, s in stats.items():
    xs = [c[0] for c in s['coords']]
    zs = [c[1] for c in s['coords']]
    bounds[level] = {
        'min_x': min(xs), 'max_x': max(xs),
        'min_z': min(zs), 'max_z': max(zs),
        'count': s['count']
    }

bounds_path = TILES_DIR / "bounds.json"
with open(bounds_path, 'w') as f:
    json.dump(bounds, f, indent=2)
print(f"\nBounds saved to: {bounds_path}")

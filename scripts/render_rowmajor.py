"""直接渲染 cache tile，假设行优先排列

对于接近满的 tile，行优先应该能给出合理的结果
"""
import zipfile
from pathlib import Path
from PIL import Image
import re

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

TILE_CHUNKS = 24
TILE_PX = TILE_CHUNKS * 16  # 384

def parse_filename(name):
    m = re.match(r'(-?\d+)_(-?\d+)\.xwmc', name)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None

def find_pixel_start(raw):
    pos = 16
    last_biome_end = 16
    while True:
        idx = raw.find(b'minecraft:', pos)
        if idx == -1:
            break
        if idx > 0:
            slen = raw[idx-1]
            if 10 <= slen <= 64:
                name = raw[idx:idx+slen].decode('utf-8', errors='replace')
                if name.startswith('minecraft:'):
                    last_biome_end = idx + slen
                    pos = last_biome_end
                    continue
        pos = idx + 1
    px_start = last_biome_end
    while px_start < len(raw) and raw[px_start] == 0:
        px_start += 1
    return px_start

def render_tile_rowmajor(level, tx, tz):
    path = BASE / str(level) / f"{tx}_{tz}.xwmc"
    if not path.exists():
        print(f"Not found: {path}")
        return None
    
    with zipfile.ZipFile(path) as z:
        raw = z.read("cache.xaero")
    
    px_start = find_pixel_start(raw)
    pixel_data = raw[px_start:]
    
    # 计算最多多少个完整 chunk
    n_chunks = len(pixel_data) // 1024
    print(f"Tile ({tx},{tz}): px_start={px_start}, total_pixel_data={len(pixel_data)}, n_chunks={n_chunks}")
    
    # 行优先渲染
    img = Image.new('RGBA', (TILE_PX, TILE_PX), (0, 0, 0, 0))
    
    for ci in range(min(n_chunks, TILE_CHUNKS * TILE_CHUNKS)):
        cx = ci % TILE_CHUNKS
        cz = ci // TILE_CHUNKS
        chunk_off = ci * 1024
        chunk_data = pixel_data[chunk_off:chunk_off + 1024]
        if len(chunk_data) < 1024:
            break
        for py in range(16):
            for px in range(16):
                idx = (py * 16 + px) * 4
                a, r, g, b = chunk_data[idx], chunk_data[idx+1], chunk_data[idx+2], chunk_data[idx+3]
                abs_x = cx * 16 + px
                abs_y = cz * 16 + py
                img.putpixel((abs_x, abs_y), (r, g, b, a))
    
    out_path = OUT / f"rowmajor_l{level}_{tx}_{tz}.png"
    img.save(out_path)
    print(f"  Saved: {out_path}")
    return img

# 渲染 cache/1 中最大的几个文件
level1 = BASE / "1"
tiles = []
for f in level1.glob("*.xwmc"):
    c = parse_filename(f.name)
    if c:
        with zipfile.ZipFile(f) as z:
            raw = z.read("cache.xaero")
        tiles.append((len(raw), c))

tiles.sort(reverse=True)
print(f"Top 5 largest tiles in cache/1:")
for size, c in tiles[:5]:
    print(f"  {c}: {size} bytes")

# 渲染最大的那个
if tiles:
    size, (tx, tz) = tiles[0]
    print(f"\nRendering largest tile ({tx},{tz}):")
    render_tile_rowmajor(1, tx, tz)
    
    # 也渲染它右边的 tile（如果有的话）
    right_tile = (tx + 1, tz)
    right_path = BASE / "1" / f"{right_tile[0]}_{right_tile[1]}.xwmc"
    if right_path.exists():
        print(f"\nRendering right neighbor {right_tile}:")
        render_tile_rowmajor(1, right_tile[0], right_tile[1])

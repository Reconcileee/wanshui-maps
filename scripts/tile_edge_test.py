"""渲染所有 cache/1 tiles 并拼接成完整地图

假设:
- tile = 24x24 chunks = 384x384 像素
- chunks 按行优先排列 (row-major), 空 chunks 跳过
- 不对，chunks 数量不同，说明是稀疏的

让我换个思路: 
假设 tile = 24x24 chunks
chunks 数据按顺序存储，只有有数据的 chunks
trailing metadata 包含每个 chunk 的 (cx, cz)

如果我能从 trailing data 中解析出坐标，那就完美了。

让我用另一种方法验证: 
- 取两个相邻的 tiles (比如 0_0 和 1_0)
- 假设 chunks 按行优先排列
- 检查 0_0 的右边缘和 1_0 的左边缘是否匹配
- 如果匹配，说明排列正确
"""
import zipfile
from pathlib import Path
from PIL import Image
import re

CACHE_BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

TILE_CHUNKS = 24
TILE_PX = TILE_CHUNKS * 16  # 384

def parse_filename(name):
    m = re.match(r'(-?\d+)_(-?\d+)\.xwmc', name)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None

def get_pixel_start(raw):
    """找到 pixel data 的起始位置"""
    pos = 16
    last_end = 16
    while True:
        idx = raw.find(b'minecraft:', pos)
        if idx == -1:
            break
        if idx > 0:
            slen = raw[idx-1]
            if 10 <= slen <= 64:
                name = raw[idx:idx+slen].decode('utf-8', errors='replace')
                if name.startswith('minecraft:'):
                    last_end = idx + slen
                    pos = last_end
                    continue
        pos = idx + 1
    # 跳过 0 字节
    while last_end < len(raw) and raw[last_end] == 0:
        last_end += 1
    return last_end

def read_cache_tile(path):
    """读取一个 cache tile，返回 (pixel_data, n_chunks)"""
    with zipfile.ZipFile(path) as z:
        raw = z.read("cache.xaero")
    px_start = get_pixel_start(raw)
    pixel_data = raw[px_start:]
    # 去掉 trailing metadata? 先不管，直接用
    n_chunks = len(pixel_data) // 1024
    return pixel_data[:n_chunks*1024], n_chunks

def render_tile_rowmajor(pixel_data, n_chunks):
    """按行优先渲染，前 n_chunks 个填充，剩下的空"""
    img = Image.new('RGBA', (TILE_PX, TILE_PX), (0, 0, 0, 0))
    for ci in range(min(n_chunks, TILE_CHUNKS * TILE_CHUNKS)):
        chunk_off = ci * 1024
        cx = ci % TILE_CHUNKS
        cz = ci // TILE_CHUNKS
        for py in range(16):
            for px in range(16):
                idx = chunk_off + (py * 16 + px) * 4
                if idx + 3 < len(pixel_data):
                    a, r, g, b = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
                    abs_x = cx * 16 + px
                    abs_y = cz * 16 + py
                    if abs_x < TILE_PX and abs_y < TILE_PX:
                        img.putpixel((abs_x, abs_y), (r, g, b, a))
    return img

# 找几个相邻的 tiles 来测试
level1 = CACHE_BASE / "1"
tiles = {}
for f in level1.glob("*.xwmc"):
    c = parse_filename(f.name)
    if c:
        tiles[c] = f

print(f"Found {len(tiles)} tiles in cache/1")

# 找相邻的 tile 对
tile_list = sorted(tiles.keys())
print(f"Tile coordinates: {tile_list}")

# 选一对相邻的 tiles (比如 0_0 和 1_0)
if (0, 0) in tiles and (1, 0) in tiles:
    print("\n=== Testing edge matching between (0,0) and (1,0) ===")
    pd0, n0 = read_cache_tile(tiles[(0, 0)])
    pd1, n1 = read_cache_tile(tiles[(1, 0)])
    print(f"  Tile (0,0): {n0} chunks")
    print(f"  Tile (1,0): {n1} chunks")
    
    img0 = render_tile_rowmajor(pd0, n0)
    img1 = render_tile_rowmajor(pd1, n1)
    
    # 比较右边缘和左边缘
    # img0 的右边缘 (x=383) vs img1 的左边缘 (x=0)
    match_count = 0
    total = 0
    for y in range(TILE_PX):
        p0 = img0.getpixel((TILE_PX-1, y))
        p1 = img1.getpixel((0, y))
        if p0[3] > 0 and p1[3] > 0:  # 都不透明
            total += 1
            if p0 == p1:
                match_count += 1
    
    print(f"  Edge match: {match_count}/{total} pixels")
    if total > 0:
        print(f"  Match rate: {match_count/total*100:.1f}%")
    
    # 也保存拼接后的图片
    combined = Image.new('RGBA', (TILE_PX * 2, TILE_PX), (0, 0, 0, 0))
    combined.paste(img0, (0, 0))
    combined.paste(img1, (TILE_PX, 0))
    combined.save(OUT / "combined_0_0_and_1_0.png")
    print(f"  Saved combined image")

# 现在让我们尝试另一个假设: chunks 按 Z 字形排列，或按列优先
# 或者: trailing metadata 的坐标就是每个 chunk 的 cx, cz (1 byte each)
# 让我试试从 pixel_data 后面找坐标

# 先看看 0_0.xwmc 的 trailing 大小
print("\n=== Trailing metadata analysis for (0,0) ===")
with zipfile.ZipFile(tiles[(0, 0)]) as z:
    raw = z.read("cache.xaero")
px_start = get_pixel_start(raw)
print(f"pixel_start: {px_start}")
print(f"total size: {len(raw)}")

# 试试不同的 n_chunks，看哪个对应的 trailing 有合理的坐标
for n_chunks_guess in range(550, 576):
    trail_size = len(raw) - px_start - n_chunks_guess * 1024
    if trail_size < n_chunks_guess * 2:
        continue  # 坐标数据至少要 2 bytes per chunk
    
    trailing = raw[px_start + n_chunks_guess * 1024:]
    # 假设 trailing 最后是坐标数据 (2 bytes per chunk)
    coord_size = n_chunks_guess * 2
    if len(trailing) >= coord_size:
        coords_data = trailing[-coord_size:]
        valid = sum(1 for b in coords_data if b < TILE_CHUNKS)
        if valid >= coord_size * 0.9:  # 90% 以上是有效坐标
            print(f"  n_chunks={n_chunks_guess}, trail_size={trail_size}, valid_coords={valid}/{coord_size} ({valid/coord_size*100:.0f}%)")

import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

def read_xwmc(level, tx, tz):
    path = BASE / str(level) / f"{tx}_{tz}.xwmc"
    with zipfile.ZipFile(path) as z:
        return z.read("cache.xaero")

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

TILE_CHUNKS = 24
TILE_PX = TILE_CHUNKS * 16

def get_chunks(level, tx, tz):
    raw = read_xwmc(level, tx, tz)
    px_start = find_pixel_start(raw)
    pixel_data = raw[px_start:]
    n_chunks = len(pixel_data) // 1024
    chunks = []
    for ci in range(n_chunks):
        chunk_off = ci * 1024
        chunks.append(pixel_data[chunk_off:chunk_off + 1024])
    return chunks

def render_with_coords(chunks, coords):
    """用给定的坐标列表渲染瓦片"""
    img = Image.new('RGBA', (TILE_PX, TILE_PX), (0, 0, 0, 0))
    for ci, chunk_data in enumerate(chunks):
        if ci >= len(coords):
            break
        cx, cz = coords[ci]
        if cx < 0 or cx >= TILE_CHUNKS or cz < 0 or cz >= TILE_CHUNKS:
            continue
        for py in range(16):
            for px in range(16):
                idx = (py * 16 + px) * 4
                if idx + 3 < len(chunk_data):
                    a, r, g, b = chunk_data[idx], chunk_data[idx+1], chunk_data[idx+2], chunk_data[idx+3]
                    abs_x = cx * 16 + px
                    abs_y = cz * 16 + py
                    img.putpixel((abs_x, abs_y), (r, g, b, a))
    return img

# 用 0_5 和 1_5 来测试
chunks0 = get_chunks(1, 0, 5)
chunks1 = get_chunks(1, 1, 5)
print(f"Tile (0,5): {len(chunks0)} chunks")
print(f"Tile (1,5): {len(chunks1)} chunks")

# 方法1: 行优先排列
def row_major_coords(n):
    coords = []
    for i in range(n):
        cx = i % TILE_CHUNKS
        cz = i // TILE_CHUNKS
        coords.append((cx, cz))
    return coords

img0_row = render_with_coords(chunks0, row_major_coords(len(chunks0)))
img1_row = render_with_coords(chunks1, row_major_coords(len(chunks1)))

# 比较右边缘和左边缘
def compare_edges(img_left, img_right):
    match = 0
    total = 0
    for y in range(TILE_PX):
        pl = img_left.getpixel((TILE_PX-1, y))
        pr = img_right.getpixel((0, y))
        if pl[3] > 0 and pr[3] > 0:
            total += 1
            if pl == pr:
                match += 1
    return match, total

match, total = compare_edges(img0_row, img1_row)
print(f"\nRow-major: {match}/{total} matches ({match/total*100:.1f}%)" if total > 0 else "\nRow-major: no overlap")

# 保存图片
img0_row.save(OUT / "rowmajor_0_5.png")
img1_row.save(OUT / "rowmajor_1_5.png")

# 方法2: 试试从 trailing 数据中找坐标
print("\n=== Trying to find coords in trailing data ===")
raw = read_xwmc(1, 0, 5)
px_start = find_pixel_start(raw)
pixel_data = raw[px_start:]
n_chunks = len(chunks0)
trail_size = len(pixel_data) - n_chunks * 1024
trailing = pixel_data[n_chunks * 1024:]
print(f"trail_size = {trail_size}")

# 试试坐标在 trailing 的末尾，每个坐标 2 字节
if trail_size >= n_chunks * 2:
    coord_bytes = trailing[-n_chunks*2:]
    coords_end = []
    for i in range(n_chunks):
        cx = coord_bytes[i*2]
        cz = coord_bytes[i*2 + 1]
        coords_end.append((cx, cz))
    
    valid = sum(1 for cx, cz in coords_end if 0 <= cx < TILE_CHUNKS and 0 <= cz < TILE_CHUNKS)
    print(f"  2B from end: {valid}/{n_chunks} valid")
    
    if valid > n_chunks * 0.8:
        img_end = render_with_coords(chunks0, coords_end)
        img_end.save(OUT / "coords_end_0_5.png")
        print(f"  Saved coords_end_0_5.png")

# 试试坐标在 trailing 的开头
if trail_size >= n_chunks * 2:
    coord_bytes = trailing[:n_chunks*2]
    coords_start = []
    for i in range(n_chunks):
        cx = coord_bytes[i*2]
        cz = coord_bytes[i*2 + 1]
        coords_start.append((cx, cz))
    
    valid = sum(1 for cx, cz in coords_start if 0 <= cx < TILE_CHUNKS and 0 <= cz < TILE_CHUNKS)
    print(f"  2B from start: {valid}/{n_chunks} valid")

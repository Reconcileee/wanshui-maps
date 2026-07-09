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

def render_tile_rowmajor(level, tx, tz):
    """假设 chunk 按行优先排列 (填满后换行)"""
    raw = read_xwmc(level, tx, tz)
    px_start = find_pixel_start(raw)
    pixel_data = raw[px_start:]
    
    n_chunks = len(pixel_data) // 1024
    print(f"  n_chunks = {n_chunks}")
    
    img = Image.new('RGBA', (TILE_PX, TILE_PX), (0, 0, 0, 0))
    
    for ci in range(n_chunks):
        # 行优先: cx = ci % 24, cz = ci // 24
        cx = ci % TILE_CHUNKS
        cz = ci // TILE_CHUNKS
        if cz >= TILE_CHUNKS:
            break
        
        chunk_off = ci * 1024
        chunk_data = pixel_data[chunk_off:chunk_off + 1024]
        if len(chunk_data) < 1024:
            break
        
        for py in range(16):
            for px in range(16):
                idx = (py * 16 + px) * 4
                if idx + 3 < len(chunk_data):
                    a, r, g, b = chunk_data[idx], chunk_data[idx+1], chunk_data[idx+2], chunk_data[idx+3]
                    abs_x = cx * 16 + px
                    abs_y = cz * 16 + py
                    img.putpixel((abs_x, abs_y), (r, g, b, a))
    
    return img

# 渲染两个相邻的 tile (0,0) 和 (1,0)，比较它们的边缘
print("Rendering tile (0,0)...")
img0 = render_tile_rowmajor(1, 0, 0)
out0 = OUT / "edge_test_0_0_rowmajor.png"
img0.save(out0)
print(f"  Saved to {out0}")

print("\nRendering tile (1,0)...")
try:
    img1 = render_tile_rowmajor(1, 1, 0)
    out1 = OUT / "edge_test_1_0_rowmajor.png"
    img1.save(out1)
    print(f"  Saved to {out1}")
    
    # 比较右边缘和左边缘
    print("\n=== Edge comparison ===")
    match_count = 0
    total = 0
    for y in range(TILE_PX):
        p0 = img0.getpixel((TILE_PX-1, y))
        p1 = img1.getpixel((0, y))
        if p0[3] > 0 and p1[3] > 0:  # 都不透明
            total += 1
            if p0 == p1:
                match_count += 1
    
    if total > 0:
        print(f"  Matching pixels: {match_count}/{total} ({match_count/total*100:.1f}%)")
    else:
        print(f"  No overlapping opaque pixels")
except Exception as e:
    print(f"  Error: {e}")

# 也试试反向填充 (从下往上，从右往左)
print("\n\n=== Testing reverse fill ===")
def render_tile_reverse(level, tx, tz):
    raw = read_xwmc(level, tx, tz)
    px_start = find_pixel_start(raw)
    pixel_data = raw[px_start:]
    
    n_chunks = len(pixel_data) // 1024
    
    img = Image.new('RGBA', (TILE_PX, TILE_PX), (0, 0, 0, 0))
    
    for ci in range(n_chunks):
        # 反向: 从右下角开始
        pos_from_end = n_chunks - 1 - ci
        cx = TILE_CHUNKS - 1 - (pos_from_end % TILE_CHUNKS)
        cz = TILE_CHUNKS - 1 - (pos_from_end // TILE_CHUNKS)
        if cx < 0 or cz < 0:
            break
        
        chunk_off = ci * 1024
        chunk_data = pixel_data[chunk_off:chunk_off + 1024]
        if len(chunk_data) < 1024:
            break
        
        for py in range(16):
            for px in range(16):
                idx = (py * 16 + px) * 4
                if idx + 3 < len(chunk_data):
                    a, r, g, b = chunk_data[idx], chunk_data[idx+1], chunk_data[idx+2], chunk_data[idx+3]
                    abs_x = cx * 16 + px
                    abs_y = cz * 16 + py
                    img.putpixel((abs_x, abs_y), (r, g, b, a))
    
    return img

try:
    img0_rev = render_tile_reverse(1, 0, 0)
    img1_rev = render_tile_reverse(1, 1, 0)
    
    out0_rev = OUT / "edge_test_0_0_reverse.png"
    out1_rev = OUT / "edge_test_1_0_reverse.png"
    img0_rev.save(out0_rev)
    img1_rev.save(out1_rev)
    
    # 比较边缘
    match_count = 0
    total = 0
    for y in range(TILE_PX):
        p0 = img0_rev.getpixel((TILE_PX-1, y))
        p1 = img1_rev.getpixel((0, y))
        if p0[3] > 0 and p1[3] > 0:
            total += 1
            if p0 == p1:
                match_count += 1
    
    if total > 0:
        print(f"  Reverse fill matching: {match_count}/{total} ({match_count/total*100:.1f}%)")
except Exception as e:
    print(f"  Error: {e}")

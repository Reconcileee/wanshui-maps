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

def analyze_and_render(level, tx, tz):
    raw = read_xwmc(level, tx, tz)
    px_start = find_pixel_start(raw)
    data_after = len(raw) - px_start
    
    print(f"\n=== {level}/{tx}_{tz}.xwmc ===")
    print(f"  data_after_px: {data_after}")
    
    # 找最可能的 n_chunks: n*1026 <= data_after, 且坐标都在 0-23 范围
    best = None
    for n in range(1, min(600, data_after // 1024 + 1)):
        pixel_bytes = n * 1024
        trail_size = data_after - pixel_bytes
        
        # 坐标在 trailing 末尾，2 bytes per coord
        if trail_size >= n * 2:
            coord_start = data_after - n * 2
            coord_bytes = raw[px_start + pixel_bytes:][-n*2:]
            valid = 0
            coords = []
            for i in range(n):
                cx = coord_bytes[i*2]
                cz = coord_bytes[i*2 + 1]
                coords.append((cx, cz))
                if 0 <= cx < TILE_CHUNKS and 0 <= cz < TILE_CHUNKS:
                    valid += 1
            
            if valid == n:
                unique = len(set(coords))
                if unique == n:
                    # 完美！所有坐标有效且唯一
                    score = 1000 + n
                    if best is None or score > best[0]:
                        best = (score, n, coords, 'end_2B')
    
    if best:
        score, n, coords, mode = best
        print(f"  BEST: n={n}, mode={mode}, all coords valid and unique")
        print(f"  First 10 coords: {coords[:10]}")
        
        # 渲染
        pixel_data = raw[px_start:px_start + n*1024]
        img = Image.new('RGBA', (TILE_PX, TILE_PX), (0, 0, 0, 0))
        for ci in range(n):
            cx, cz = coords[ci]
            chunk_off = ci * 1024
            for py in range(16):
                for px in range(16):
                    idx = chunk_off + (py * 16 + px) * 4
                    if idx + 3 < len(pixel_data):
                        a, r, g, b = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
                        abs_x = cx * 16 + px
                        abs_y = cz * 16 + py
                        img.putpixel((abs_x, abs_y), (r, g, b, a))
        
        out_path = OUT / f"final_l{level}_{tx}_{tz}.png"
        img.save(out_path)
        print(f"  Saved to {out_path}")
        return img, coords
    else:
        print(f"  No perfect match found")
        return None, None

# 测试多个文件
print("Testing level 3...")
img00, coords00 = analyze_and_render(3, 0, 0)
img01, coords01 = analyze_and_render(3, 0, 1)
img10, coords10 = analyze_and_render(3, 1, 0)
img11, coords11 = analyze_and_render(3, 1, 1)

print("\n\nTesting level 1...")
analyze_and_render(1, 0, 0)
analyze_and_render(1, 8, 7)

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

raw = read_xwmc(3, 0, 0)
px_start = find_pixel_start(raw)
print(f"px_start = {px_start}")

# 假设: 在 biome palette 和像素数据之间有一个 chunk 索引表
# 索引表包含 n_chunks 个条目，每个条目描述一个 chunk 的位置

# 先试试: 索引表在前面，后面跟着像素数据
# 每个索引条目可能是: cx (1B), cz (1B), offset (2B)? size (2B)?
# 或者: chunk 坐标 + 像素数据偏移

# 让我们试试: 在 px_start 之后先有 n_chunks 个坐标对 (cx, cz)
# 然后才是像素数据

# 试试不同的 n_chunks
print("\n=== Testing coords-first layout ===")
for n_chunks in range(10, 50):
    coord_bytes = n_chunks * 2  # cx, cz
    pixel_offset = px_start + coord_bytes
    pixel_bytes = n_chunks * 1024
    total_needed = pixel_offset + pixel_bytes
    
    if total_needed > len(raw):
        continue
    
    # 检查坐标是否都在 0-23 范围内
    coords_data = raw[px_start:px_start + coord_bytes]
    valid = 0
    coords = []
    for i in range(n_chunks):
        cx = coords_data[i*2]
        cz = coords_data[i*2 + 1]
        if 0 <= cx < 24 and 0 <= cz < 24:
            valid += 1
            coords.append((cx, cz))
    
    if valid == n_chunks:
        # 所有坐标都有效，检查是否有重复
        unique = len(set(coords))
        print(f"  n={n_chunks}: all coords valid, unique={unique}")
        if unique == n_chunks:
            print(f"    *** PERFECT *** coords: {coords[:10]}...")
            
            # 渲染看看
            pixel_data = raw[pixel_offset:pixel_offset + pixel_bytes]
            img = Image.new('RGBA', (24*16, 24*16), (0, 0, 0, 0))
            for ci in range(n_chunks):
                cx, cz = coords[ci]
                chunk_off = ci * 1024
                for py in range(16):
                    for px in range(16):
                        idx = chunk_off + (py * 16 + px) * 4
                        if idx + 3 < len(pixel_data):
                            a, r, g, b = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
                            abs_x = cx * 16 + px
                            abs_y = cz * 16 + py
                            if 0 <= abs_x < 24*16 and 0 <= abs_y < 24*16:
                                img.putpixel((abs_x, abs_y), (r, g, b, a))
            
            out_path = OUT / f"coords_first_n{n_chunks}.png"
            img.save(out_path)
            print(f"    Saved to {out_path}")

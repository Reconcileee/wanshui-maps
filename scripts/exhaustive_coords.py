"""穷举法找 cache.xaero 中的坐标数据

假设:
- n_chunks 个 chunk
- 每个 chunk 坐标 (cx, cz) 各 1 byte
- 坐标范围 0-23
- 找连续 n_chunks*2 字节都在 0-23 范围内的位置

从文件末尾往前找
"""
import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

TILE_CHUNKS = 24
TILE_PX = TILE_CHUNKS * 16

def read_xwmc(path):
    with zipfile.ZipFile(path) as z:
        return z.read("cache.xaero")

def get_pixel_start(raw):
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
    while last_end < len(raw) and raw[last_end] == 0:
        last_end += 1
    return last_end

# 先分析 cache/3/0_0.xwmc (最小，最快)
raw = read_xwmc(BASE / "3" / "0_0.xwmc")
print(f"Total size: {len(raw)}")

pixel_start = get_pixel_start(raw)
print(f"Pixel start: {pixel_start}")

# 试不同的 n_chunks
for n_chunks in range(35, 50):
    pd_end = pixel_start + n_chunks * 1024
    if pd_end >= len(raw):
        continue
    trailing = raw[pd_end:]
    trail_size = len(trailing)
    
    # 在 trailing 中找连续 n_chunks*2 字节都 <= 23 的
    coord_size = n_chunks * 2
    for offset in range(trail_size - coord_size + 1):
        chunk = trailing[offset:offset+coord_size]
        valid = all(b < TILE_CHUNKS for b in chunk)
        if valid:
            print(f"\n*** FOUND *** n_chunks={n_chunks}, coord_offset_in_trailing={offset}")
            print(f"  trail_size={trail_size}, pd_end={pd_end}")
            
            # 解析坐标
            coords = []
            for i in range(n_chunks):
                cx = chunk[i*2]
                cz = chunk[i*2+1]
                coords.append((cx, cz))
            
            print(f"  First 10 coords: {coords[:10]}")
            print(f"  cx range: {min(c[0] for c in coords)} - {max(c[0] for c in coords)}")
            print(f"  cz range: {min(c[1] for c in coords)} - {max(c[1] for c in coords)}")
            print(f"  Unique cx: {len(set(c[0] for c in coords))}")
            print(f"  Unique cz: {len(set(c[1] for c in coords))}")
            print(f"  Unique pairs: {len(set(coords))}")
            
            # 渲染
            pixel_data = raw[pixel_start:pd_end]
            min_cx = min(c[0] for c in coords)
            max_cx = max(c[0] for c in coords)
            min_cz = min(c[1] for c in coords)
            max_cz = max(c[1] for c in coords)
            w = (max_cx - min_cx + 1) * 16
            h = (max_cz - min_cz + 1) * 16
            
            if w <= 512 and h <= 512:
                img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
                for ci, (cx, cz) in enumerate(coords):
                    chunk_off = ci * 1024
                    if chunk_off + 1024 > len(pixel_data):
                        break
                    for py in range(16):
                        for px in range(16):
                            idx = chunk_off + (py * 16 + px) * 4
                            if idx + 3 < len(pixel_data):
                                a, r, g, b = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
                                abs_x = (cx - min_cx) * 16 + px
                                abs_y = (cz - min_cz) * 16 + py
                                if abs_x < w and abs_y < h:
                                    img.putpixel((abs_x, abs_y), (r, g, b, a))
                
                out_file = OUT / f"l3_n{n_chunks}_off{offset}.png"
                img.save(out_file)
                print(f"  Saved: {out_file.name} ({w}x{h})")

# 也试试坐标是 4 字节 (cx u16, cz u16)
print("\n\n=== Trying 4-byte coordinates (u16 BE) ===")
raw = read_xwmc(BASE / "3" / "0_0.xwmc")
pixel_start = get_pixel_start(raw)

for n_chunks in range(35, 50):
    pd_end = pixel_start + n_chunks * 1024
    if pd_end >= len(raw):
        continue
    trailing = raw[pd_end:]
    coord_size = n_chunks * 4
    if len(trailing) < coord_size:
        continue
    
    # 从末尾取
    coords_data = trailing[-coord_size:]
    valid = 0
    coords = []
    for i in range(n_chunks):
        cx = (coords_data[i*4] << 8) | coords_data[i*4+1]
        cz = (coords_data[i*4+2] << 8) | coords_data[i*4+3]
        coords.append((cx, cz))
        if cx < TILE_CHUNKS and cz < TILE_CHUNKS:
            valid += 1
    
    if valid >= n_chunks * 0.8:  # 80% 有效
        print(f"  n_chunks={n_chunks}: valid={valid}/{n_chunks}")
        print(f"    cx range: {min(c[0] for c in coords)} - {max(c[0] for c in coords)}")
        print(f"    cz range: {min(c[1] for c in coords)} - {max(c[1] for c in coords)}")

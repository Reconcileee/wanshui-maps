"""系统地解决 chunk 坐标解析问题

策略:
1. 从小文件 (cache/3/0_0.xwmc, ~40 chunks) 入手
2. 尝试不同的坐标格式 (1-byte, 2-byte, signed/unsigned)
3. 用坐标渲染 tile，验证合理性
"""
import zipfile
from pathlib import Path
from PIL import Image
import struct

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

TILE_CHUNKS = 24
TILE_PX = TILE_CHUNKS * 16

def read_xwmc(path):
    with zipfile.ZipFile(path) as z:
        return z.read("cache.xaero")

def find_pixel_start(raw):
    """找到 pixel data 起始位置 - 扫描所有 biome 字符串后第一个非零字节"""
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

def analyze_file(level, tx, tz):
    """分析一个 cache 文件"""
    path = BASE / str(level) / f"{tx}_{tz}.xwmc"
    if not path.exists():
        print(f"File not found: {path}")
        return None
    
    raw = read_xwmc(path)
    px_start = find_pixel_start(raw)
    total_after_px = len(raw) - px_start
    
    print(f"\n=== cache/{level}/{tx}_{tz}.xwmc ===")
    print(f"  total size: {len(raw)}")
    print(f"  px_start: {px_start}")
    print(f"  data after px_start: {total_after_px} bytes")
    
    # 尝试不同的 n_chunks
    best = None
    for n_chunks in range(1, 600):
        pixel_bytes = n_chunks * 1024
        if pixel_bytes > total_after_px:
            break
        trail_size = total_after_px - pixel_bytes
        
        # trailing 至少要 n_chunks 字节 (坐标数据)
        if trail_size < n_chunks:
            continue
        
        trailing = raw[px_start + pixel_bytes:]
        
        # 尝试 1: 2 bytes per chunk (cx, cz), unsigned, 从末尾取
        if trail_size >= n_chunks * 2:
            coord_bytes = trailing[-n_chunks*2:]
            valid = 0
            coords = []
            for i in range(n_chunks):
                cx = coord_bytes[i*2]
                cz = coord_bytes[i*2 + 1]
                if 0 <= cx < TILE_CHUNKS and 0 <= cz < TILE_CHUNKS:
                    valid += 1
                    coords.append((cx, cz))
            if valid == n_chunks:
                # 检查坐标是否有重复
                unique = len(set(coords))
                if unique == n_chunks:
                    score = 100
                    if best is None or score > best[0]:
                        best = (score, n_chunks, '2b_unsigned_end', coords)
                    print(f"  n={n_chunks}: 2B unsigned from END, all valid, unique={unique}")
        
        # 尝试 2: 2 bytes per chunk, signed, 从末尾取
        if trail_size >= n_chunks * 2:
            coord_bytes = trailing[-n_chunks*2:]
            valid = 0
            coords = []
            for i in range(n_chunks):
                cx = coord_bytes[i*2]
                cz = coord_bytes[i*2 + 1]
                if cx >= 128: cx -= 256
                if cz >= 128: cz -= 256
                if -TILE_CHUNKS <= cx < TILE_CHUNKS and -TILE_CHUNKS <= cz < TILE_CHUNKS:
                    valid += 1
                    coords.append((cx, cz))
            if valid == n_chunks and n_chunks > 30:
                unique = len(set(coords))
                print(f"  n={n_chunks}: 2B signed from END, valid={valid}, unique={unique}")
        
        # 尝试 3: 2 bytes per chunk, 从开头取
        if trail_size >= n_chunks * 2:
            coord_bytes = trailing[:n_chunks*2]
            valid = 0
            coords = []
            for i in range(n_chunks):
                cx = coord_bytes[i*2]
                cz = coord_bytes[i*2 + 1]
                if 0 <= cx < TILE_CHUNKS and 0 <= cz < TILE_CHUNKS:
                    valid += 1
                    coords.append((cx, cz))
            if valid == n_chunks:
                unique = len(set(coords))
                if unique == n_chunks:
                    print(f"  n={n_chunks}: 2B unsigned from START, all valid, unique={unique}")
    
    if best:
        print(f"\n  BEST: n_chunks={best[1]}, mode={best[2]}")
        return best
    return None

def render_with_coords(level, tx, tz, n_chunks, coords):
    """用坐标渲染 tile"""
    path = BASE / str(level) / f"{tx}_{tz}.xwmc"
    raw = read_xwmc(path)
    px_start = find_pixel_start(raw)
    pixel_data = raw[px_start:px_start + n_chunks*1024]
    
    img = Image.new('RGBA', (TILE_PX, TILE_PX), (0, 0, 0, 0))
    
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
                    if 0 <= abs_x < TILE_PX and 0 <= abs_y < TILE_PX:
                        img.putpixel((abs_x, abs_y), (r, g, b, a))
    
    out_path = OUT / f"rendered_l{level}_{tx}_{tz}.png"
    img.save(out_path)
    print(f"  Saved: {out_path}")
    return img

# 先分析最小的文件
print("=== Analyzing cache/3 files ===")
result = analyze_file(3, 0, 0)

if result:
    score, n_chunks, mode, coords = result
    render_with_coords(3, 0, 0, n_chunks, coords)

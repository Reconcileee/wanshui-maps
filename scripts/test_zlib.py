import zipfile
from pathlib import Path
import zlib
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

# 尝试用 zlib 解压从 px_start 开始的数据
compressed_data = raw[px_start:]
print(f"Compressed data size: {len(compressed_data)}")
print(f"First 4 bytes: {compressed_data[:4].hex()}")

try:
    decompressed = zlib.decompress(compressed_data)
    print(f"Decompressed size: {len(decompressed)}")
    
    # 试试是不是 ARGB 像素数据
    n_pixels = len(decompressed) // 4
    rem = len(decompressed) % 4
    print(f"Pixels: {n_pixels}, remainder: {rem}")
    
    # 试试不同的尺寸
    for w in [64, 80, 96, 128, 160, 256, 384, 512]:
        h = n_pixels // w
        if h < 1:
            continue
        actual = w * h
        actual_bytes = actual * 4
        rem_bytes = len(decompressed) - actual_bytes
        
        img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        for y in range(h):
            for x in range(w):
                idx = (y * w + x) * 4
                if idx + 3 < len(decompressed):
                    a, r, g, b = decompressed[idx], decompressed[idx+1], decompressed[idx+2], decompressed[idx+3]
                    img.putpixel((x, y), (r, g, b, a))
        
        # 统计不透明像素
        opaque = sum(1 for y in range(h) for x in range(w) if img.getpixel((x, y))[3] > 0)
        if opaque > 50:
            out_path = OUT / f"zlib_l3_0_0_{w}x{h}.png"
            img.save(out_path)
            print(f"  {w}x{h}: opaque={opaque}, saved to {out_path.name}")
    
except Exception as e:
    print(f"zlib decompress failed: {e}")

# 也试试 deflate (raw)
try:
    decompressed = zlib.decompress(compressed_data, -15)
    print(f"\nRaw deflate decompressed size: {len(decompressed)}")
except Exception as e:
    print(f"Raw deflate failed: {e}")

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

TILE_PX = 384  # 24 chunks * 16 pixels

def decode_rle(data, width, height):
    """尝试 RLE 解码: count (1 byte) + ARGB (4 bytes)"""
    pixels = []
    pos = 0
    while pos < len(data) and len(pixels) < width * height:
        count = data[pos]
        pos += 1
        if pos + 3 >= len(data):
            break
        a, r, g, b = data[pos], data[pos+1], data[pos+2], data[pos+3]
        pos += 4
        for _ in range(count):
            pixels.append((r, g, b, a))
            if len(pixels) >= width * height:
                break
    
    if len(pixels) < width * height:
        print(f"  Warning: only {len(pixels)} pixels (need {width*height})")
    
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    for i, (r, g, b, a) in enumerate(pixels):
        x = i % width
        y = i // width
        if y < height:
            img.putpixel((x, y), (r, g, b, a))
    return img

# 用 cache/3/0_0.xwmc 测试
raw = read_xwmc(3, 0, 0)
px_start = find_pixel_start(raw)
pixel_data = raw[px_start:]
print(f"pixel_data size: {len(pixel_data)}")

# 尝试不同的尺寸
print("\n=== RLE decode attempts ===")
for w, h in [(96, 96), (128, 128), (192, 192), (256, 256), (384, 384)]:
    try:
        img = decode_rle(pixel_data, w, h)
        opaque = sum(1 for y in range(h) for x in range(w) if img.getpixel((x, y))[3] > 0)
        if opaque > 50:
            out_path = OUT / f"rle_l3_{w}x{h}.png"
            img.save(out_path)
            print(f"  {w}x{h}: opaque={opaque}, saved")
    except Exception as e:
        print(f"  {w}x{h}: error - {e}")

# 也试试 BGRA 顺序
print("\n=== RLE with BGRA order ===")
def decode_rle_bgra(data, width, height):
    pixels = []
    pos = 0
    while pos < len(data) and len(pixels) < width * height:
        count = data[pos]
        pos += 1
        if pos + 3 >= len(data):
            break
        b, g, r, a = data[pos], data[pos+1], data[pos+2], data[pos+3]
        pos += 4
        for _ in range(count):
            pixels.append((r, g, b, a))
            if len(pixels) >= width * height:
                break
    
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    for i, (r, g, b, a) in enumerate(pixels):
        x = i % width
        y = i // width
        if y < height:
            img.putpixel((x, y), (r, g, b, a))
    return img

for w, h in [(96, 96), (128, 128), (192, 192), (256, 256), (384, 384)]:
    try:
        img = decode_rle_bgra(pixel_data, w, h)
        opaque = sum(1 for y in range(h) for x in range(w) if img.getpixel((x, y))[3] > 0)
        if opaque > 50:
            out_path = OUT / f"rle_bgra_l3_{w}x{h}.png"
            img.save(out_path)
            print(f"  {w}x{h}: opaque={opaque}, saved")
    except Exception as e:
        print(f"  {w}x{h}: error - {e}")

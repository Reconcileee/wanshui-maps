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

# 用 cache/1/0_0.xwmc (大文件) 来分析
raw = read_xwmc(1, 0, 0)
px_start = find_pixel_start(raw)
print(f"px_start = {px_start}")
print(f"total = {len(raw)}")
pixel_data = raw[px_start:]
print(f"pixel_data size = {len(pixel_data)}")

# 打印前 256 字节
print("\n=== First 256 bytes of pixel_data ===")
for i in range(0, min(256, len(pixel_data)), 16):
    chunk = pixel_data[i:i+16]
    hex_str = ' '.join(f'{b:02x}' for b in chunk)
    print(f"  off {i:4d}: {hex_str}")

# 试试第一个 chunk (1024 字节 = 16x16 ARGB)
print("\n=== First chunk (16x16) ===")
chunk0 = pixel_data[:1024]
img0 = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
for y in range(16):
    for x in range(16):
        idx = (y * 16 + x) * 4
        if idx + 3 < len(chunk0):
            a, r, g, b = chunk0[idx], chunk0[idx+1], chunk0[idx+2], chunk0[idx+3]
            img0.putpixel((x, y), (r, g, b, a))

out0 = OUT / "chunk0_first.png"
img0.save(out0)
print(f"Saved chunk0 to {out0}")

# 统计不透明像素
opaque = sum(1 for y in range(16) for x in range(16) if img0.getpixel((x, y))[3] > 0)
print(f"Opaque pixels in chunk0: {opaque}/256")

# 看看第 100 个 chunk
chunk100_off = 100 * 1024
if chunk100_off + 1024 <= len(pixel_data):
    print(f"\n=== Chunk 100 ===")
    chunk100 = pixel_data[chunk100_off:chunk100_off+1024]
    img100 = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for y in range(16):
        for x in range(16):
            idx = (y * 16 + x) * 4
            if idx + 3 < len(chunk100):
                a, r, g, b = chunk100[idx], chunk100[idx+1], chunk100[idx+2], chunk100[idx+3]
                img100.putpixel((x, y), (r, g, b, a))
    
    out100 = OUT / "chunk100.png"
    img100.save(out100)
    print(f"Saved chunk100 to {out100}")
    opaque = sum(1 for y in range(16) for x in range(16) if img100.getpixel((x, y))[3] > 0)
    print(f"Opaque pixels in chunk100: {opaque}/256")

# 计算总 chunk 数
n_chunks = len(pixel_data) // 1024
rem = len(pixel_data) % 1024
print(f"\nTotal chunks: {n_chunks}, remainder: {rem} bytes")

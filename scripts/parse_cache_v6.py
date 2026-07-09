"""验证 ARGB 假设: 搜索已知 biome 颜色模式"""
import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

f = BASE / "3" / "0_0.xwmc"
with zipfile.ZipFile(f) as z:
    raw = z.read("cache.xaero")

# palette 占 16-254, 然后 254 开始是 pixel_data
# 但 254-256 是 00 00, 可能是 chunk header
pixel_data = raw[254:]
print(f"pixel_data: {len(pixel_data)} bytes, first 32: {pixel_data[:32].hex()}")

# 已知 biome 颜色 (R, G, B) - 来自 gen_real_data.py
biome_colors = {
    "deep_ocean": (30, 60, 140),
    "ocean": (40, 80, 160),
    "cold_ocean": (50, 90, 170),
    "beach": (220, 210, 160),
    "taiga": (70, 110, 90),
    "river": (80, 140, 180),
    "desert": (220, 200, 140),
    "badlands": (170, 140, 90),
    "deep_cold_ocean": (40, 70, 150),
    "stony_shore": (130, 130, 130),
    "windswept_hills": (140, 140, 130),
}

# 在 pixel_data 中搜索这些颜色 (ARGB 顺序: A R G B)
print("\n--- searching for biome colors (ARGB) ---")
for name, (r, g, b) in biome_colors.items():
    # 搜索 R G B 模式 (alpha 任意)
    pattern = bytes([r, g, b])
    positions = []
    start = 0
    while True:
        pos = pixel_data.find(pattern, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + 1
        if len(positions) > 5:
            break
    if positions:
        print(f"  {name} ({r},{g},{b}): found at {positions[:5]}")

# 也搜索 RGBA 顺序 (R G B A)
print("\n--- searching for biome colors (RGBA) ---")
for name, (r, g, b) in biome_colors.items():
    pattern = bytes([r, g, b])
    positions = []
    start = 0
    while True:
        pos = pixel_data.find(pattern, start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + 1
        if len(positions) > 5:
            break
    if positions:
        print(f"  {name} ({r},{g},{b}): found at {positions[:5]}")

# 看 pixel_data 中出现频率最高的 4-byte 模式
print("\n--- most common 4-byte patterns ---")
from collections import Counter
patterns = Counter()
for i in range(0, len(pixel_data) - 3, 4):
    p = pixel_data[i:i+4]
    patterns[p] += 1
print(f"top 10 patterns:")
for p, c in patterns.most_common(10):
    a, r, g, b = p[0], p[1], p[2], p[3]
    print(f"  ARGB({a:3d},{r:3d},{g:3d},{b:3d}) = #{a:02x}{r:02x}{g:02x}{b:02x}: {c}")

# 直接尝试渲染: 跳过第 1 字节, 剩 41056 / 4 = 10264 像素
# 尝试 16x641 (不整除), 试 128x80=10240 (剩 24 像素)
print("\n--- render attempts ---")
# 假设: 跳过第 1 字节 (chunk count?), 然后 40 chunks * 16x16 = 40960 bytes
# 但 41056 - 40960 = 96 bytes 剩余, 不对
# 假设: 直接 41056 bytes ARGB = 10264 像素, 渲染 16x641 (取 10240 像素)
pd = pixel_data[1:1 + 10264 * 4]  # 跳过第 1 字节
print(f"rendering {len(pd)//4} pixels")

# 尝试 16x641
img = Image.new('RGBA', (16, 641), (0, 0, 0, 0))
for i in range(min(10264, 16*641)):
    a, r, g, b = pd[i*4], pd[i*4+1], pd[i*4+2], pd[i*4+3]
    img.putpixel((i % 16, i // 16), (r, g, b, a))
img.save(OUT / "render_16x641.png")

# 尝试 32x321 (10272, 取 10264)
img = Image.new('RGBA', (32, 321), (0, 0, 0, 0))
for i in range(min(10264, 32*321)):
    a, r, g, b = pd[i*4], pd[i*4+1], pd[i*4+2], pd[i*4+3]
    img.putpixel((i % 32, i // 32), (r, g, b, a))
img.save(OUT / "render_32x321.png")

# 尝试把 41057 bytes 直接当 ARGB (不跳过), 10264 像素, 16x641
pd2 = pixel_data[:10264 * 4]
img = Image.new('RGBA', (16, 641), (0, 0, 0, 0))
for i in range(10264):
    a, r, g, b = pd2[i*4], pd2[i*4+1], pd2[i*4+2], pd2[i*4+3]
    img.putpixel((i % 16, i // 16), (r, g, b, a))
img.save(OUT / "render_raw_16x641.png")

# 关键: 如果格式是 40 chunks * 16x16 = 40960 bytes ARGB + 97 bytes trailing
# 那 40 chunks 排列成 8x5 = 40, 16*8=128 x 16*5=80
print("\n--- render as 8x5 chunks (128x80) ---")
pd3 = pixel_data[:40960]  # 40 chunks * 1024 bytes
img = Image.new('RGBA', (128, 80), (0, 0, 0, 0))
for i in range(40960 // 4):  # 10240 pixels
    a, r, g, b = pd3[i*4], pd3[i*4+1], pd3[i*4+2], pd3[i*4+3]
    # 8 chunks per row, 5 rows
    chunk_idx = i // 256  # 0-39
    in_chunk = i % 256
    cx = chunk_idx % 8
    cz = chunk_idx // 8
    px = in_chunk % 16
    py = in_chunk // 16
    abs_x = cx * 16 + px
    abs_y = cz * 16 + py
    img.putpixel((abs_x, abs_y), (r, g, b, a))
img.save(OUT / "render_8x5chunks_128x80.png")

# 也试 10x4 chunks (160x64)
print("--- render as 10x4 chunks (160x64) ---")
img = Image.new('RGBA', (160, 64), (0, 0, 0, 0))
for i in range(10240):
    a, r, g, b = pd3[i*4], pd3[i*4+1], pd3[i*4+2], pd3[i*4+3]
    chunk_idx = i // 256
    in_chunk = i % 256
    cx = chunk_idx % 10
    cz = chunk_idx // 10
    px = in_chunk % 16
    py = in_chunk // 16
    abs_x = cx * 16 + px
    abs_y = cz * 16 + py
    img.putpixel((abs_x, abs_y), (r, g, b, a))
img.save(OUT / "render_10x4chunks_160x64.png")

print(f"\nsaved PNGs to {OUT}")

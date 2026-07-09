import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

def read_region(tx, tz):
    path = BASE / f"{tx}_{tz}.zip"
    with zipfile.ZipFile(path) as z:
        return z.read("region.xaero")

raw = read_region(0, 0)
print(f"Total size: {len(raw)} bytes")

# 详细分析 offset 900000 附近的区域
# 假设: 每个 chunk 有 256 字节的 biome 数据 (16x16)
# 一个 region 有 32x32 = 1024 个 chunks
# biome 数据总大小 = 1024 * 256 = 262144 字节

# 找 biome 数据的起始位置
print("\n=== Looking for biome data section ===")

# 从 offset 900000 开始，看看 256*1024 = 262144 字节后的数据
biome_start = 900000
# 先看看 900000 附近的数据
print(f"\nData around 900000:")
for i in range(900000 - 32, 900000 + 256 + 32, 16):
    if i < 0 or i + 16 > len(raw):
        continue
    chunk = raw[i:i+16]
    marker = " <-- start" if i == 900000 else ""
    print(f"  {i:6d}: {chunk.hex()}{marker}")

# 试试: biome 数据从 900000 开始，每个 chunk 256 字节，32x32 chunks
# 渲染为 512x512 (32 chunks * 16 pixels)
biome_start = 900000
biome_size = 32 * 32 * 256  # 262144
biome_data = raw[biome_start:biome_start + biome_size]

print(f"\nBiome data: {len(biome_data)} bytes")
print(f"Unique values: {sorted(set(biome_data[:10000]))[:20]}")

# 渲染为 512x512 (32 chunks * 16 pixels per chunk)
biome_colors = [
    (0, 0, 112),      # 0: deep_ocean
    (0, 0, 80),       # 1: ocean
    (32, 32, 160),    # 2: cold_ocean
    (250, 240, 160),  # 3: beach
    (11, 112, 96),    # 4: taiga
    (0, 128, 255),    # 5: river
    (250, 200, 80),   # 6: desert
    (217, 69, 21),    # 7: badlands
    (0, 0, 144),      # 8: deep_cold_ocean
    (160, 160, 160),  # 9: stony_shore
    (96, 96, 96),     # 10: windswept_hills
    (34, 139, 34),    # 11: forest
    (85, 107, 47),    # 12: swamp
    (50, 150, 50),    # 13: plains
    (200, 200, 50),   # 14: savanna
    (255, 255, 255),  # 15: snow
]

img = Image.new('RGB', (512, 512), (0, 0, 0))
for chunk_z in range(32):
    for chunk_x in range(32):
        chunk_idx = chunk_z * 32 + chunk_x
        chunk_off = chunk_idx * 256
        chunk_data = biome_data[chunk_off:chunk_off + 256]
        if len(chunk_data) < 256:
            continue
        for py in range(16):
            for px in range(16):
                b = chunk_data[py * 16 + px]
                color = biome_colors[b % len(biome_colors)] if b < 30 else (b, b, b)
                abs_x = chunk_x * 16 + px
                abs_y = chunk_z * 16 + py
                if abs_x < 512 and abs_y < 512:
                    img.putpixel((abs_x, abs_y), color)

out_path = OUT / "region_biome_512x512.png"
img.save(out_path)
print(f"Saved biome map to {out_path}")

# 看看 biome 数据后面是什么（应该是 height 数据）
height_start = biome_start + biome_size
print(f"\n=== Height data starts at {height_start} ===")
if height_start + 262144 <= len(raw):
    height_data = raw[height_start:height_start + 262144]
    min_h = min(height_data)
    max_h = max(height_data)
    avg_h = sum(height_data) / len(height_data)
    print(f"Height range: {min_h} - {max_h}, avg: {avg_h:.1f}")
    
    # 渲染 height map
    img_h = Image.new('RGB', (512, 512), (0, 0, 0))
    for chunk_z in range(32):
        for chunk_x in range(32):
            chunk_idx = chunk_z * 32 + chunk_x
            chunk_off = chunk_idx * 256
            chunk_data = height_data[chunk_off:chunk_off + 256]
            if len(chunk_data) < 256:
                continue
            for py in range(16):
                for px in range(16):
                    h = chunk_data[py * 16 + px]
                    v = min(255, max(0, (h - 40) * 3))
                    abs_x = chunk_x * 16 + px
                    abs_y = chunk_z * 16 + py
                    if abs_x < 512 and abs_y < 512:
                        img_h.putpixel((abs_x, abs_y), (v, v, v))
    
    out_h = OUT / "region_height_512x512.png"
    img_h.save(out_h)
    print(f"Saved height map to {out_h}")

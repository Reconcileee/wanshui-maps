"""检查 offset 1782784 附近的数据

看看那里的数据分布
"""
import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

f = BASE / "0_0.zip"
with zipfile.ZipFile(f) as z:
    raw = z.read("region.xaero")

# 看看 offset 1782784 前后的数据
offset = 1782784

# 打印 256 字节
print(f"Data at offset {offset}:")
print(f"First 64 bytes: {list(raw[offset:offset+64])}")

# 看看值分布
data = raw[offset:offset+65536]
hist = {}
for b in data:
    hist[b] = hist.get(b, 0) + 1

print(f"\nValue distribution (top 20):")
for val, count in sorted(hist.items(), key=lambda x: -x[1])[:20]:
    print(f"  value {val:3d}: {count:5d} ({count/len(data)*100:5.1f}%)")

# 试试把这些数据当成 256x256 的灰度图
img = Image.new('L', (256, 256), 0)
for y in range(256):
    for x in range(256):
        idx = y * 256 + x
        if idx < len(data):
            img.putpixel((x, y), data[idx])

img.save(OUT / "biome_candidate_256x256.png")
print(f"\nSaved 256x256 grayscale image")

# 也试试 512x512 (但数据只有 65536 字节 = 256x256)
# 如果是 4 bits per pixel，那就是 512x256

# 试试当成 biome color map (11 种颜色)
biome_colors = [
    (0, 0, 112),     # 0: deep_ocean
    (0, 0, 80),      # 1: ocean
    (32, 32, 160),    # 2: cold_ocean
    (250, 240, 160),  # 3: beach
    (11, 112, 96),     # 4: taiga
    (0, 128, 255),    # 5: river
    (250, 200, 80),    # 6: desert
    (217, 69, 21),     # 7: badlands
    (0, 0, 144),       # 8: deep_cold_ocean
    (160, 160, 160),   # 9: stony_shore
    (96, 96, 96),      # 10: windswept_hills
]

img_color = Image.new('RGB', (256, 256), (0, 0, 0))
for y in range(256):
    for x in range(256):
        idx = y * 256 + x
        if idx < len(data):
            b = data[idx]
            if b < len(biome_colors):
                img_color.putpixel((x, y), biome_colors[b])

img_color.save(OUT / "biome_candidate_color_256x256.png")
print("Saved color version")

# 等等，之前我们发现 biome 有 11 种，但值分布的前几名有哪些？
# 让我看看是不是 4-bit (每字节两个 biome index)
print("\n\n=== Trying 4-bit per pixel (2 per byte) ===")
# 高 4 位和低 4 位分开
high_nibbles = [b >> 4 for b in data]
low_nibbles = [b & 0x0f for b in data]

high_hist = {}
for b in high_nibbles:
    high_hist[b] = high_hist.get(b, 0) + 1
print("High nibble distribution (top 10):")
for val, count in sorted(high_hist.items(), key=lambda x: -x[1])[:10]:
    print(f"  value {val}: {count} ({count/len(data)*100:.1f}%)")

low_hist = {}
for b in low_nibbles:
    low_hist[b] = low_hist.get(b, 0) + 1
print("\nLow nibble distribution (top 10):")
for val, count in sorted(low_hist.items(), key=lambda x: -x[1])[:10]:
    print(f"  value {val}: {count} ({count/len(data)*100:.1f}%)")

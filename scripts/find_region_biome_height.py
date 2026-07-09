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
print(f"Total size: {len(raw)}")

# 找 biome 数据区域 - 滑动窗口找大部分值在 0-10 的区域
print("\n=== Scanning for biome data (values 0-10) ===")
window_size = 65536  # 256x256
best_ratio = 0
best_pos = 0
for pos in range(0, len(raw) - window_size, 4096):
    window = raw[pos:pos+window_size]
    count = sum(1 for b in window if b <= 10)
    ratio = count / window_size
    if ratio > best_ratio:
        best_ratio = ratio
        best_pos = pos
    if ratio > 0.8:
        print(f"  Found at {pos}: {ratio*100:.1f}%")

print(f"\nBest: pos={best_pos}, ratio={best_ratio*100:.1f}%")

# 看看最佳位置周围的数据
if best_pos > 0:
    data = raw[best_pos:best_pos + 65536]
    print(f"\n=== Data at best position ===")
    print(f"First 32 bytes: {data[:32].hex()}")
    print(f"Unique values: {sorted(set(data[:1000]))[:20]}")
    
    # 试试渲染为 256x256 的 biome map
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
        (34, 34, 34),     # 11: ?
        (45, 45, 45),     # 12: ?
    ]
    
    # 试试不同的尺寸
    for size in [256, 512]:
        img = Image.new('RGB', (size, size), (0, 0, 0))
        n_pixels = min(len(data), size * size)
        for i in range(n_pixels):
            x = i % size
            y = i // size
            b = data[i]
            if b < len(biome_colors):
                img.putpixel((x, y), biome_colors[b])
            else:
                img.putpixel((x, y), (b * 20, b * 10, b * 5))
        
        out_path = OUT / f"region_biome_{size}x{size}.png"
        img.save(out_path)
        print(f"  Saved {size}x{size} to {out_path}")
    
    # 也看看 best_pos 之后的数据，找 height map
    print(f"\n=== Looking for height data after biome ===")
    height_start = best_pos + 65536
    if height_start + 65536 <= len(raw):
        height_data = raw[height_start:height_start + 65536]
        min_h = min(height_data)
        max_h = max(height_data)
        avg_h = sum(height_data) / len(height_data)
        print(f"  Height range: {min_h} - {max_h}, avg: {avg_h:.1f}")
        
        # 渲染 height map
        img_h = Image.new('RGB', (256, 256), (0, 0, 0))
        for i in range(min(len(height_data), 256*256)):
            x = i % 256
            y = i // 256
            h = height_data[i]
            # 映射为灰度
            v = min(255, max(0, int((h - 40) * 3)))
            img_h.putpixel((x, y), (v, v, v))
        
        out_h = OUT / "region_height_256x256.png"
        img_h.save(out_h)
        print(f"  Saved height map to {out_h}")

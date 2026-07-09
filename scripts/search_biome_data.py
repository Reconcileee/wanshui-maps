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

# 找 biome 数据: 滑动窗口，值在 0-10 范围内的比例高，且有 256x256 或 512x512 等规整尺寸
print("\n=== Searching for biome data ===")
candidates = []

# 试试不同的窗口大小
for window_size in [256*256, 512*512, 16*16, 32*32]:
    for pos in range(0, len(raw) - window_size, 1024):
        window = raw[pos:pos+window_size]
        # 统计值在 0-20 范围内的比例（biome + 一些余量）
        count = sum(1 for b in window if b <= 20)
        ratio = count / window_size
        if ratio > 0.9:
            # 检查 unique values 的数量
            unique = len(set(window))
            if 5 <= unique <= 20:
                candidates.append((ratio, pos, window_size, unique))

candidates.sort(reverse=True)
print(f"Found {len(candidates)} candidates")
for i, (ratio, pos, size, unique) in enumerate(candidates[:10]):
    print(f"  [{i}] pos={pos}, size={size}, ratio={ratio*100:.1f}%, unique={unique}")

# 渲染前几个候选
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
    (120, 80, 200),   # 13: ?
    (200, 200, 50),   # 14: ?
    (255, 255, 255),  # 15: snow
]

for i, (ratio, pos, size, unique) in enumerate(candidates[:5]):
    data = raw[pos:pos+size]
    # 试试不同的尺寸
    for w in [256, 512, 1024]:
        h = size // w
        if h < 10 or w * h != size:
            continue
        img = Image.new('RGB', (w, h), (0, 0, 0))
        for y in range(h):
            for x in range(w):
                idx = y * w + x
                b = data[idx]
                if b < len(biome_colors):
                    img.putpixel((x, y), biome_colors[b])
                else:
                    img.putpixel((x, y), (b, b, b))
        
        out_path = OUT / f"biome_candidate_{i}_{w}x{h}.png"
        img.save(out_path)
        print(f"  Saved {out_path.name}")

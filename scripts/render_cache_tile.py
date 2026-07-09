"""从 region.xaero 中提取 biome 数据并渲染地图

策略：
1. 每个 region zip 对应 512x512 blocks
2. 在 region.xaero 中找到 biome 数据
3. 用 biome 颜色渲染 512x512 的 PNG
4. 把所有 region 拼接成完整地图

关键: 找到 biome 数据的位置和格式
假设: biome data 是 512x512 = 262144 字节，每字节一个 biome index
"""
import zipfile
import io
from pathlib import Path
from nbtlib import Compound
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

# biome 颜色映射 (简化版)
BIOME_COLORS = {
    'minecraft:ocean': (0, 0, 112),
    'minecraft:deep_ocean': (0, 0, 80),
    'minecraft:cold_ocean': (32, 32, 160),
    'minecraft:deep_cold_ocean': (0, 0, 144),
    'minecraft:frozen_ocean': (112, 160, 208),
    'minecraft:deep_frozen_ocean': (64, 96, 160),
    'minecraft:warm_ocean': (0, 160, 192),
    'minecraft:lukewarm_ocean': (0, 128, 176),
    'minecraft:deep_lukewarm_ocean': (0, 96, 144),
    'minecraft:river': (0, 128, 255),
    'minecraft:frozen_river': (160, 208, 240),
    'minecraft:beach': (250, 240, 160),
    'minecraft:stone_shore': (160, 160, 160),
    'minecraft:desert': (250, 200, 80),
    'minecraft:badlands': (217, 69, 21),
    'minecraft:plains': (141, 179, 96),
    'minecraft:forest': (5, 102, 33),
    'minecraft:taiga': (11, 112, 96),
    'minecraft:swamp': (7, 249, 178),
    'minecraft:mangrove_swamp': (50, 90, 50),
    'minecraft:jungle': (83, 125, 49),
    'minecraft:savanna': (189, 178, 95),
    'minecraft:windswept_hills': (96, 96, 96),
    'minecraft:stony_peaks': (128, 128, 128),
    'minecraft:meadow': (100, 180, 100),
    'minecraft:cherry_grove': (255, 180, 200),
    'minecraft:dark_forest': (64, 80, 23),
    'minecraft:birch_forest': (48, 116, 68),
    'minecraft:old_growth_birch_forest': (60, 130, 80),
    'minecraft:spruce_forest': (70, 120, 90),
    'minecraft:snowy_plains': (255, 255, 255),
    'minecraft:ice_spikes': (200, 240, 255),
    'minecraft:snowy_taiga': (80, 140, 150),
    'minecraft:mushroom_fields': (255, 0, 255),
    'minecraft:the_void': (0, 0, 0),
    'minecraft:nether_wastes': (128, 0, 0),
    'minecraft:soul_sand_valley': (80, 50, 30),
    'minecraft:crimson_forest': (200, 0, 50),
    'minecraft:warped_forest': (0, 150, 150),
    'minecraft:basalt_deltas': (80, 80, 80),
    'minecraft:the_end': (128, 128, 200),
    'minecraft:end_highlands': (160, 160, 220),
    'minecraft:end_midlands': (140, 140, 210),
    'minecraft:small_end_islands': (100, 100, 180),
    'minecraft:end_barrens': (150, 150, 200),
}

def get_biome_color(biome_name):
    return BIOME_COLORS.get(biome_name, (128, 128, 128))

def read_region(path):
    with zipfile.ZipFile(path) as z:
        return z.read("region.xaero")

def find_biome_palette(raw):
    """找到 biome 列表 (palette)"""
    biomes = []
    pos = 0
    while True:
        idx = raw.find(b'minecraft:', pos)
        if idx == -1:
            break
        if idx > 0:
            slen = raw[idx-1]
            if 10 <= slen <= 64:
                name = raw[idx:idx+slen].decode('utf-8', errors='replace')
                if name.startswith('minecraft:') and name not in biomes:
                    biomes.append(name)
        pos = idx + 1
    return biomes

# 选一个 region 文件来分析
region_file = BASE / "0_0.zip"
raw = read_region(region_file)
print(f"Region size: {len(raw)} bytes")

# 找 biome palette (所有出现的 biome 名称)
all_biomes = find_biome_palette(raw)
print(f"\nUnique biomes found: {len(all_biomes)}")
for b in all_biomes:
    print(f"  {b}")

# 现在找 biome 数据
# 假设 biome data 是 262144 字节，在文件的某个位置
# 让我们找最后一个 biome 字符串结束的位置
last_pos = 0
pos = 0
while True:
    idx = raw.find(b'minecraft:', pos)
    if idx == -1:
        break
    if idx > 0:
        slen = raw[idx-1]
        if 10 <= slen <= 64:
            name = raw[idx:idx+slen].decode('utf-8', errors='replace')
            if name.startswith('minecraft:'):
                last_pos = idx + slen
    pos = idx + 1

print(f"\nLast biome string ends at: {last_pos}")
print(f"Data after last biome: {len(raw) - last_pos} bytes")

# 如果 biome data 是 1 字节/block, 262144 字节
# 那 2111535 - last_pos = ?
# 之前算的 last_pos = 1877852, 2111535 - 1877852 = 233683
# 233683 < 262144，不够

# 那可能 biome data 是 4 bits/block? 262144 * 0.5 = 131072 bytes
# 233683 > 131072，可能

# 或者 biome data 在文件中间？
# 让我们换个思路: 每 chunk 有自己的 biome 数据
# 32x32 = 1024 chunks, 每 chunk 256 bytes biome (16x16, 1 byte/block)
# 1024 * 256 = 262144 bytes (和之前一样)

# 但 biome 字符串散布在整个文件中，说明每 chunk 有自己的 biome palette
# 如果是这样，每 chunk 的数据是:
# - chunk header
# - biome palette (NBT 或字符串)
# - biome data (16x16)
# - block state data
# - height data
# ...

# 这太复杂了。让我换个更简单的方法:
# 直接用 cache.xaero 的像素数据，假设 chunks 是按行优先排列的，
# 从左到右从上到下，遇到空 chunk 就跳过

# 不，让我试试另一种方法: 
# 假设 tile = 512x512 像素 (和 region 一样)
# cache/1: 最高分辨率 = 512x512 = 262144 像素 = 1048576 bytes
# 但 cache/1/0_0.xwmc 只有 574578 字节，不够

# cache/2: 256x256 = 65536 像素 = 262144 bytes
# 但 cache/2/0_0.xwmc 有 164410 字节，也不够

# 所以 tile 不是 512x512

# 让我试试 384x384 (24 chunks * 16 px):
# 384*384 = 147456 像素 = 589824 bytes
# cache/1/0_0.xwmc 有 574578 字节，接近！
# 574578 ≈ 589824，差了约 15000 字节 (header + missing chunks)

# 560 chunks * 1024 = 573440
# 574578 - 573440 = 1138 bytes (header + trailing)
# 1138 bytes 合理！

# 所以 tile = 24x24 chunks = 384x384 像素
# 但只有 560 个 chunks 有数据 (576 - 16 = 560, 缺 16 个)

# 如果 chunks 按行优先排列，空的 chunks 直接跳过
# 那 560 个有数据的 chunks 是哪些？

# 让我假设: 前 N 个 chunks 有数据，后面的没有
# 560 = 23 行 + 8 个 = 前 23 行满 + 第 24 行前 8 个
# 不对，23*24 = 552, 560-552 = 8

# 让我试试按 24x24 行优先排列，只放 560 个 chunks
# 看看渲染结果对不对
print("\n=== Rendering cache/1/0_0.xwmc as 24x24 chunks (row-major, first 560) ===")

cache_path = BASE / "cache" / "1" / "0_0.xwmc"
with zipfile.ZipFile(cache_path) as z:
    cache_raw = z.read("cache.xaero")

# 找 pixel_start
first_minecraft = cache_raw.find(b'minecraft:')
pixel_start = first_minecraft
while pixel_start < len(cache_raw):
    idx = cache_raw.find(b'minecraft:', pixel_start)
    if idx == -1:
        break
    if idx > 0:
        slen = cache_raw[idx-1]
        if 10 <= slen <= 64:
            name = cache_raw[idx:idx+slen].decode('utf-8', errors='replace')
            if name.startswith('minecraft:'):
                pixel_start = idx + slen
                continue
    break

# 跳过 0 字节
while pixel_start < len(cache_raw) and cache_raw[pixel_start] == 0:
    pixel_start += 1

print(f"pixel_start: {pixel_start}")
pixel_data = cache_raw[pixel_start:]
n_chunks = len(pixel_data) // 1024
print(f"n_chunks: {n_chunks}")

# 渲染为 24x24 chunks (384x384 像素)，前 n_chunks 个有数据
TILE_CHUNKS = 24
TILE_PX = TILE_CHUNKS * 16
img = Image.new('RGBA', (TILE_PX, TILE_PX), (0, 0, 0, 0))

for ci in range(min(n_chunks, TILE_CHUNKS * TILE_CHUNKS)):
    chunk_off = ci * 1024
    cx = ci % TILE_CHUNKS
    cz = ci // TILE_CHUNKS
    for py in range(16):
        for px in range(16):
            idx = chunk_off + (py * 16 + px) * 4
            if idx + 3 < len(pixel_data):
                a, r, g, b = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
                abs_x = cx * 16 + px
                abs_y = cz * 16 + py
                if abs_x < TILE_PX and abs_y < TILE_PX:
                    img.putpixel((abs_x, abs_y), (r, g, b, a))

out_file = OUT / "cache1_0_0_24x24_rowmajor.png"
img.save(out_file)
print(f"Saved: {out_file}")

# 也试试从右下角开始（反向填充）
img2 = Image.new('RGBA', (TILE_PX, TILE_PX), (0, 0, 0, 0))
for ci in range(min(n_chunks, TILE_CHUNKS * TILE_CHUNKS)):
    chunk_off = ci * 1024
    # 从右下角往左上角填充
    idx_from_end = TILE_CHUNKS * TILE_CHUNKS - 1 - ci
    cx = idx_from_end % TILE_CHUNKS
    cz = idx_from_end // TILE_CHUNKS
    for py in range(16):
        for px in range(16):
            idx = chunk_off + (py * 16 + px) * 4
            if idx + 3 < len(pixel_data):
                a, r, g, b = pixel_data[idx], pixel_data[idx+1], pixel_data[idx+2], pixel_data[idx+3]
                abs_x = cx * 16 + px
                abs_y = cz * 16 + py
                if abs_x < TILE_PX and abs_y < TILE_PX:
                    img2.putpixel((abs_x, abs_y), (r, g, b, a))

out_file2 = OUT / "cache1_0_0_24x24_reverse.png"
img2.save(out_file2)
print(f"Saved: {out_file2}")

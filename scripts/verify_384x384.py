"""分析 chunk 坐标和 tile 坐标系统

观察:
- cache/3/ 有 7 个 .xwmc 文件
- cache/2/ 有 10 个 .xwmc 文件
- cache/1/ 有 21 个 .xwmc 文件

文件名是 tile 坐标, 如 0_0.xwmc = tile (0,0)

每个 tile 包含的像素数:
- cache/3: ~10263 像素 = ~40 chunks (每 chunk 16x16)
- cache/2: ~41034 像素 = ~160 chunks
- cache/1: ~143564 像素 = ~560 chunks

比例: cache/2 = 4x cache/3, cache/1 = 3.5x cache/2 (不太对)
实际: 143564 / 41034 = 3.5

但文件数量比例: cache/2 (10) vs cache/3 (7) = 1.43x
cache/1 (21) vs cache/2 (10) = 2.1x

这可能是因为稀疏存储 - 只有探索过的区域才有数据

每个 tile 是 24x24 chunks? (byte 2-3 = 0x18 = 24)
24 * 24 = 576 chunks per tile
576 * 256 = 147456 像素
cache/1/0_0.xwmc 有 143564 像素, 接近 147456!
差值 = 147456 - 143564 = 3892 像素 = 973 字节 = 因为有未探索的 chunks (稀疏)

验证:
- 24x24 chunks = 576 chunks
- 576 * 256 = 147456 像素
- 147456 * 4 bytes ARGB = 589824 bytes
- cache/1/0_0.xwmc total = 574578 bytes, 接近但略少 (因为稀疏, 用 RLE?)

但等一下, 如果是稀疏存储 + RLE, 那格式就不是简单的 ARGB 数组
让我验证: cache/1/0_0.xwmc 的 pixel_data 大小 574257 bytes
如果是 143564 像素 ARGB = 574256 bytes, + 1 extra
143564 像素 = 560.8 chunks, 不是整数

让我重新计算: 143564 像素, 每 chunk 256, 那 143564 / 256 = 560.796875
不是整数, 说明不是简单的 chunks x 256

可能格式: 每个 tile 是 24*24 = 576 chunks, 但只有部分有数据 (稀疏)
chunk 坐标 + chunk 数据 (RLE 或 ARGB)

让我看看 pixel_data 的结构
"""
import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

# 详细分析 cache/1/0_0.xwmc
fn = BASE / "1" / "0_0.xwmc"
with zipfile.ZipFile(fn) as z:
    raw = z.read("cache.xaero")

print(f"total size: {len(raw)}")

# 找 palette 末尾
first_mc = raw.find(b'minecraft:')
print(f"first 'minecraft:' at {first_mc}")

# 解析 palette
palette_start = first_mc - 1  # length byte
off = palette_start
biomes = []
while off < len(raw):
    slen = raw[off]
    if slen < 10 or slen > 64:
        # 检查是否还有 minecraft:
        if raw[off+1:].find(b'minecraft:') >= 0:
            off += 1
            continue
        break
    name = raw[off+1:off+1+slen].decode('utf-8', errors='replace')
    if not name.startswith('minecraft:'):
        break
    biomes.append(name)
    off += 1 + slen

# 跳过末尾 0
pixel_start = off
while pixel_start < len(raw) and raw[pixel_start] == 0:
    pixel_start += 1

print(f"biomes: {len(biomes)}")
print(f"pixel_start: {pixel_start}")
print(f"pixel_data size: {len(raw) - pixel_start}")

pixel_data = raw[pixel_start:]
n_pixels = len(pixel_data) // 4
print(f"pixels: {n_pixels}")

# 关键: 检查前 100 字节是否像 chunk header + ARGB
print(f"\nfirst 64 bytes of pixel_data:")
for i in range(0, 64, 8):
    print(f"  {i:4d}: {' '.join(f'{b:02x}' for b in pixel_data[i:i+8])}")

# 试试: 2-byte chunk count?
# 如果 count 是 2 bytes, 然后是 chunk 列表
# 576 chunks * 1024 = 589824, 不对

# 或者: 1-byte count per row?
# 让我看前 4 字节作为 int
count32 = (pixel_data[0] << 24) | (pixel_data[1] << 16) | (pixel_data[2] << 8) | pixel_data[3]
count16 = (pixel_data[0] << 8) | pixel_data[1]
print(f"\npixel_data[0:4] as int32: {count32}")
print(f"pixel_data[0:2] as int16: {count16}")
print(f"pixel_data[0]: {pixel_data[0]}")

# 如果是 576 chunks, 每 chunk 1 byte biome index = 576 bytes
# 但 pixel_data 有 574257 bytes, 太大了

# 试试 RLE: 1 byte count + 3 bytes RGB
# 总像素数 = sum of all counts
total_pixels = 0
off_pd = 0
runs = 0
while off_pd + 4 <= len(pixel_data) and runs < 1000:
    count = pixel_data[off_pd]
    if count == 0 and runs > 0:
        # 遇到 0 可能是结束或 padding
        break
    total_pixels += count
    runs += 1
    off_pd += 4

print(f"\nRLE decode (first 1000 runs):")
print(f"  runs: {runs}")
print(f"  total pixels: {total_pixels}")
print(f"  used bytes: {off_pd}")

# 如果总像素 = 147456 (24*24 chunks * 256), 那就是完整 tile
# 但我们只有前 1000 runs, 看不到全貌

# 让我解码全部
total_pixels = 0
off_pd = 0
runs = 0
while off_pd + 4 <= len(pixel_data):
    count = pixel_data[off_pd]
    if count == 0 and total_pixels > 0:
        break
    total_pixels += count
    runs += 1
    off_pd += 4

print(f"\nRLE decode (full until count=0):")
print(f"  runs: {runs}")
print(f"  total pixels: {total_pixels}")
print(f"  used bytes: {off_pd}")
print(f"  remaining bytes: {len(pixel_data) - off_pd}")

# 如果 total_pixels = 147456, 那就是 24x24 chunks 的完整 tile
# 比例检查:
# cache/3: 10263 像素? 不对, 让我重新算 cache/3
fn3 = BASE / "3" / "0_0.xwmc"
with zipfile.ZipFile(fn3) as z:
    raw3 = z.read("cache.xaero")
first3 = raw3.find(b'minecraft:')
pal_start3 = first3 - 1
off3 = pal_start3
while off3 < len(raw3):
    slen = raw3[off3]
    if slen < 10 or slen > 64:
        if raw3[off3+1:].find(b'minecraft:') >= 0:
            off3 += 1
            continue
        break
    off3 += 1 + slen
px_start3 = off3
while px_start3 < len(raw3) and raw3[px_start3] == 0:
    px_start3 += 1
pd3 = raw3[px_start3:]
print(f"\ncache/3/0_0.xwmc:")
print(f"  pixel_data: {len(pd3)} bytes")
# RLE 解码
tp3 = 0
o3 = 0
rn3 = 0
while o3 + 4 <= len(pd3):
    c = pd3[o3]
    if c == 0 and tp3 > 0:
        break
    tp3 += c
    rn3 += 1
    o3 += 4
print(f"  RLE pixels: {tp3}, runs: {rn3}, used: {o3} bytes")

# 验证 cache/2
fn2 = BASE / "2" / "0_0.xwmc"
with zipfile.ZipFile(fn2) as z:
    raw2 = z.read("cache.xaero")
first2 = raw2.find(b'minecraft:')
pal_start2 = first2 - 1
off2 = pal_start2
while off2 < len(raw2):
    slen = raw2[off2]
    if slen < 10 or slen > 64:
        if raw2[off2+1:].find(b'minecraft:') >= 0:
            off2 += 1
            continue
        break
    off2 += 1 + slen
px_start2 = off2
while px_start2 < len(raw2) and raw2[px_start2] == 0:
    px_start2 += 1
pd2 = raw2[px_start2:]
print(f"\ncache/2/0_0.xwmc:")
print(f"  pixel_data: {len(pd2)} bytes")
tp2 = 0
o2 = 0
rn2 = 0
while o2 + 4 <= len(pd2):
    c = pd2[o2]
    if c == 0 and tp2 > 0:
        break
    tp2 += c
    rn2 += 1
    o2 += 4
print(f"  RLE pixels: {tp2}, runs: {rn2}, used: {o2} bytes")

# 如果都是 147456 = 24*24*256, 那就对了
# 比例: cache/1 最详细, cache/2 是 cache/1 的 1/4 分辨率, cache/3 是 1/16
# 但像素数相同, 说明是同一区域不同 zoom level, 每 tile 都是 24*24 chunks?
# 不对, zoom level 不同, chunk 大小应该不同

# 等等, 我可能搞反了
# Xaero 的 tile 坐标系: 每个 tile 覆盖的区域随 zoom level 变化
# zoom 0 (最详细): 每个 tile 1 chunk? 不对
# 让我重新想

# 如果每个 tile 都是 24 chunks x 24 chunks
# 每 chunk 16x16 像素 = 384x384 像素 per tile
# cache/1 每像素 1 个 MC block?
# cache/2 每像素 2 个 MC block? (zoom out 2x)
# cache/3 每像素 4 个 MC block? (zoom out 4x)
# 这样像素数应该相同, 但代表的世界坐标范围不同

# 验证: 147456 = 384 * 384 = 24*16 * 24*16
# 对! 384x384 像素 = 147456 像素
# 正好 = 24 chunks * 16 px/chunk 每边

print(f"\n=== Verification ===")
print(f"384 * 384 = {384 * 384}")
print(f"24 * 16 = {24 * 16}")
print(f"cache/1 total pixels: {total_pixels}")
print(f"match: {total_pixels == 384 * 384}")

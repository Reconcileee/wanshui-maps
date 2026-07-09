"""深入分析 cache.xaero 的像素数据格式。

策略:
1. 完整 dump palette 之后的所有字节
2. 统计字节模式 (4字节对齐? 2字节? 1字节?)
3. 找出重复模式 (chunk 边界)
4. 尝试多种 chunk 大小假设
"""
import zipfile
import struct
from pathlib import Path
from collections import Counter

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

f = BASE / "3" / "0_0.xwmc"
with zipfile.ZipFile(f) as z:
    raw = z.read("cache.xaero")

print(f"total: {len(raw)} bytes")

# 头部 + palette 解析
biome_count = (raw[12] << 8) | raw[13]
off = 16
biomes = []
for i in range(biome_count):
    slen = raw[off]
    off += 1
    name = raw[off:off+slen].decode('utf-8', errors='replace')
    biomes.append(name)
    off += slen
    # 跳过 00 00 分隔
    while off + 1 < len(raw) and raw[off] == 0 and raw[off+1] == 0:
        off += 2
        break

pixel_start = off
pixel_data = raw[pixel_start:]
print(f"\npixel_start={pixel_start}, pixel_data_size={len(pixel_data)}")
print(f"first 128 hex: {pixel_data[:128].hex()}")

# 统计 byte 分布
counter = Counter(pixel_data)
print(f"\nbyte frequency (top 10):")
for b, c in counter.most_common(10):
    print(f"  0x{b:02x} ({b:3d}): {c}")

# 统计 4-byte 对齐模式
print(f"\n--- 4-byte aligned analysis ---")
n4 = len(pixel_data) // 4
print(f"4-byte groups: {n4}, remainder: {len(pixel_data) % 4}")

# 统计每 4 字节中第一个字节 (可能是 alpha)
alpha_counter = Counter()
for i in range(0, len(pixel_data) - 3, 4):
    alpha_counter[pixel_data[i]] += 1
print(f"first byte of each 4-byte group (top 5):")
for b, c in alpha_counter.most_common(5):
    print(f"  0x{b:02x}: {c}")

# 统计每 4 字节中最后一个字节 (也可能是 alpha)
alpha_counter2 = Counter()
for i in range(0, len(pixel_data) - 3, 4):
    alpha_counter2[pixel_data[i+3]] += 1
print(f"last byte of each 4-byte group (top 5):")
for b, c in alpha_counter2.most_common(5):
    print(f"  0x{b:02x}: {c}")

# 统计 00 00 出现的位置 (可能是 chunk 分隔)
print(f"\n--- 00 00 pattern scan ---")
zeros = []
i = 0
while i < len(pixel_data) - 1:
    if pixel_data[i] == 0 and pixel_data[i+1] == 0:
        # 找连续 0
        start = i
        while i < len(pixel_data) and pixel_data[i] == 0:
            i += 1
        zeros.append((start, i - start))
    else:
        i += 1
print(f"zero runs (start, length) - first 20:")
for z in zeros[:20]:
    print(f"  offset {z[0]} (pixel+{z[0]}), len {z[1]}")
print(f"total zero runs: {len(zeros)}")

# 假设: cache.xaero 是按 chunk 存储, 每 chunk 有 cx, cz 坐标 + 16x16 ARGB 数据
# 试 cx, cz 各 1 字节, 数据 256*4=1024 字节, 总 1026 字节 per chunk
# 41057 / 1026 = 40.01 -> 40 chunks + 17 bytes 剩余
# 不太对. 试试其他格式

# 假设: 每 chunk 16x16=256 像素, 每像素 RGB (3 字节), 总 768 bytes per chunk
# 41057 / 768 = 53.46 -> 不整除

# 假设: 每 chunk 头 4 字节 (cx, cz 各 2 字节) + 256 bytes biome index (1 byte per pixel)
# 41057 / 260 = 157.91 -> 不整除

# 假设: cache 是稀疏 chunk 列表, 每 chunk:
#   varint cx, varint cz, then 256 bytes data
# 这种格式我们需要找 chunk 边界. 让我们看 zero run 是否是分隔

# 假设: 直接是 16x16 region 的 downsampled 颜色, 每像素 ARGB
# 16*16*4 = 1024, 41057/1024 = 40.09 -> 不对

# 假设: 32x32 region, 每像素 ARGB, 32*32*4 = 4096, 41057/4096 = 10.02 -> 不对

# 假设: chunk 数 + 每 chunk 数据. 看第一个字节
print(f"\n--- first byte analysis ---")
print(f"first byte: {pixel_data[0]} (0x{pixel_data[0]:02x})")
print(f"first 4 bytes: {list(pixel_data[:4])}")

# 看 41057 - N(数据) 的关系
# 如果有 chunk count 头: 41057 - 1 = 41056, /4 = 10264, /1024 = 10.02
# 41057 - 2 = 41055, /4 = 10263.75
# 41056 / 1024 = 40.09 -> 40 chunks (剩 16 bytes)
# 41056 / 1026 = 40.01 -> 40 chunks of (2+1024)

# 让我数: 41057 = 40 * 1024 + 97
# 41057 = 40 * 1026 + 17
# 41057 = 41 * 1001 + 16 (not clean)
# 41057 = 1024 * 40 + 97 = 40960 + 97

# 97 字节是什么? 可能是 chunk 坐标列表
# 40 chunks * 2 bytes (cx, cz) = 80, 剩 17 bytes
# 40 chunks * 4 bytes = 160, 不够

# 或者: 头部有 chunk count + chunk 列表, 然后是数据
# 但 41057 - 41056 = 1, 看不出

# 让我看最后 32 字节
print(f"\nlast 32 hex: {pixel_data[-32:].hex()}")
print(f"last 32 dec: {list(pixel_data[-32:])}")

# 让我看是否有 chunk 边界: 256*4=1024 ARGB, 找每 1024 字节的模式
print(f"\n--- 1024-byte chunk boundaries ---")
for i in range(0, min(5*1024, len(pixel_data)), 1024):
    print(f"  offset {i}: {pixel_data[i:i+8].hex()} ... {pixel_data[i+1020:i+1024].hex() if i+1024 <= len(pixel_data) else 'N/A'}")

# 看是否每 4 字节都是合理的颜色 (RGB 0-255, alpha 0 or 255)
print(f"\n--- 4-byte ARGB color check (first 20) ---")
for i in range(0, min(20*4, len(pixel_data)), 4):
    if i + 4 <= len(pixel_data):
        a, r, g, b = pixel_data[i], pixel_data[i+1], pixel_data[i+2], pixel_data[i+3]
        print(f"  ARGB({a:3d},{r:3d},{g:3d},{b:3d}) = #{a:02x}{r:02x}{g:02x}{b:02x}")

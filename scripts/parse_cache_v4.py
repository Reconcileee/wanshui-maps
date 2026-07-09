"""改进的 cache.xaero 解析器 - 多假设尝试生成 PNG"""
import zipfile
import struct
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

f = BASE / "3" / "0_0.xwmc"
with zipfile.ZipFile(f) as z:
    raw = z.read("cache.xaero")

print(f"=== {f.name} ===")
print(f"total: {len(raw)} bytes")
print(f"first 32 hex: {raw[:32].hex()}")
print(f"first 32 dec: {list(raw[:32])}")

# 头部 16 字节
print(f"\nheader (16 bytes):")
print(f"  bytes 0-1: {raw[0]:02x} {raw[1]:02x} = {raw[0]<<8|raw[1]}")
print(f"  bytes 2-3: {raw[2]:02x} {raw[3]:02x} = {raw[2]<<8|raw[3]}")
print(f"  bytes 4-7: {raw[4]:02x}{raw[5]:02x}{raw[6]:02x}{raw[7]:02x}")
print(f"  bytes 8-9: {raw[8]:02x} {raw[9]:02x}")
print(f"  bytes 10-11: {raw[10]:02x} {raw[11]:02x}")
print(f"  bytes 12-13: {raw[12]:02x} {raw[13]:02x} = {(raw[12]<<8)|raw[13]} (biome count?)")
print(f"  bytes 14-15: {raw[14]:02x} {raw[15]:02x}")

# 改进的 palette 解析: 严格验证 minecraft: 前缀
def parse_palette_strict(raw, start):
    """严格解析 palette, 每个字符串必须以 minecraft: 开头"""
    off = start
    biomes = []
    while off < len(raw):
        # 跳过 00 分隔
        while off < len(raw) and raw[off] == 0:
            off += 1
        if off >= len(raw):
            break
        slen = raw[off]
        if slen < 10 or slen > 64:  # minecraft:X 至少 11 字符
            break
        if off + 1 + slen > len(raw):
            break
        name = raw[off+1:off+1+slen].decode('utf-8', errors='replace')
        if not name.startswith('minecraft:'):
            break
        biomes.append(name)
        off += 1 + slen
    return biomes, off

biomes, palette_end = parse_palette_strict(raw, 16)
print(f"\nstrict palette parse: {len(biomes)} biomes, end at offset {palette_end}")
for i, b in enumerate(biomes):
    print(f"  [{i}] {b}")

pixel_data = raw[palette_end:]
print(f"\npixel_data: {len(pixel_data)} bytes")
print(f"first 32 hex: {pixel_data[:32].hex()}")

# 尝试假设 1: 直接 4 字节 ARGB 流, 渲染为不同尺寸
print("\n--- Hypothesis 1: raw ARGB stream ---")
n_pixels = len(pixel_data) // 4
print(f"  total pixels: {n_pixels}")
# 尝试几个尺寸
for w, h in [(256, 256), (16, 16), (32, 32), (64, 64), (128, 128)]:
    if w * h <= n_pixels:
        print(f"  try {w}x{h} = {w*h} pixels (use {w*h*4} bytes)")
        img = Image.new('RGBA', (w, h))
        for i in range(w * h):
            if i * 4 + 3 < len(pixel_data):
                a, r, g, b = pixel_data[i*4], pixel_data[i*4+1], pixel_data[i*4+2], pixel_data[i*4+3]
                img.putpixel((i % w, i // w), (r, g, b, a))
        img.save(OUT / f"h1_{w}x{h}.png")

# 尝试假设 2: 跳过开头 1-2 字节, 然后是 ARGB 流
print("\n--- Hypothesis 2: skip 1-2 bytes header then ARGB ---")
for skip in [1, 2, 3, 4]:
    pd = pixel_data[skip:]
    n = len(pd) // 4
    if n == 256:  # 16x16
        print(f"  skip {skip}: {n} pixels = 16x16!")
        img = Image.new('RGBA', (16, 16))
        for i in range(n):
            a, r, g, b = pd[i*4], pd[i*4+1], pd[i*4+2], pd[i*4+3]
            img.putpixel((i % 16, i // 16), (r, g, b, a))
        img.save(OUT / f"h2_skip{skip}_16x16.png")

# 尝试假设 3: chunk 列表, 每 chunk 2 字节头 + 1024 字节 ARGB
print("\n--- Hypothesis 3: chunk list (cx,cz + 1024 bytes) ---")
chunk_size = 2 + 1024  # 2 byte header + 16x16 ARGB
n_chunks = len(pixel_data) // chunk_size
remainder = len(pixel_data) % chunk_size
print(f"  chunk_size={chunk_size}, n_chunks={n_chunks}, remainder={remainder}")

# 尝试假设 4: chunk 列表, 每 chunk 4 字节头 + 1024 字节 ARGB
print("\n--- Hypothesis 4: chunk list (4 byte header + 1024 bytes) ---")
chunk_size = 4 + 1024
n_chunks = len(pixel_data) // chunk_size
remainder = len(pixel_data) % chunk_size
print(f"  chunk_size={chunk_size}, n_chunks={n_chunks}, remainder={remainder}")

# 尝试假设 5: 检查是否每 1024 字节有 chunk 边界 (颜色突变)
print("\n--- Hypothesis 5: scan for chunk boundaries ---")
# 看 1024 字节边界的颜色
for i in range(0, min(10*1024, len(pixel_data)), 1024):
    if i + 4 <= len(pixel_data):
        a, r, g, b = pixel_data[i], pixel_data[i+1], pixel_data[i+2], pixel_data[i+3]
        print(f"  offset {i}: ARGB({a},{r},{g},{b})")

# 尝试假设 6: 文件其实是 40 个 chunks, 每 chunk 1024 bytes ARGB + 末尾 97 bytes 元数据
print("\n--- Hypothesis 6: 40 chunks * 1024 bytes + trailing metadata ---")
n_chunks = 40
chunk_data_size = 1024
total_chunk_data = n_chunks * chunk_data_size
trailing = len(pixel_data) - total_chunk_data
print(f"  40 chunks * 1024 = {total_chunk_data}, trailing = {trailing} bytes")
print(f"  trailing hex: {pixel_data[total_chunk_data:total_chunk_data+64].hex()}")
print(f"  trailing dec: {list(pixel_data[total_chunk_data:total_chunk_data+64])}")

# 假设 7: 末尾是 chunk 坐标列表 (cx, cz)
# 40 chunks * 2 bytes = 80, 但 trailing=97, 不匹配
# 但如果是 varint, 平均 ~2.4 bytes/chunk
print(f"\n--- Hypothesis 7: trailing is chunk coord list ---")
# 看末尾 97 字节, 尝试解析为 varint pairs
trailing_data = pixel_data[total_chunk_data:]
print(f"  trailing ({len(trailing_data)} bytes):")
i = 0
coords = []
while i < len(trailing_data):
    # varint: 7 bits per byte, MSB=1 表示继续
    val = 0
    shift = 0
    while i < len(trailing_data):
        b = trailing_data[i]
        i += 1
        val |= (b & 0x7f) << shift
        shift += 7
        if (b & 0x80) == 0:
            break
    # zigzag decode
    val = (val >> 1) ^ -(val & 1)
    coords.append(val)
    if len(coords) <= 20:
        print(f"    varint[{len(coords)}] = {val}")
print(f"  total varints: {len(coords)}")

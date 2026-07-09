"""连续 RLE + trailing metadata 分析

发现:
- 整个 pixel_data 是连续 RLE, 没有固定 chunk 边界
- 40 chunks * 256 = 10240 像素只用了 588 bytes
- 剩下 ~40469 bytes 是 trailing metadata
- 这意味着 trailing 很大, 可能包含 chunk 坐标 + 其他数据

等一下, 这不对。RLE 编码怎么可能只用 588 bytes 存 10240 像素?
每个 RLE 条目 4 bytes, 平均每个 run = 10240/(588/4) = 10240/147 = ~70 像素
如果是纯色区域多, 是可能的。但 40 chunks 16x16, 每个 chunk 平均 3-4 个 RLE 条目, 合理

但如果只有 588 bytes RLE 数据, 那剩下 40469 bytes 是什么?
这看起来太大了。让我验证: 是不是我漏了什么?
"""
import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")
OUT = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\scripts\debug_png")
OUT.mkdir(exist_ok=True)

f = BASE / "3" / "0_0.xwmc"
with zipfile.ZipFile(f) as z:
    raw = z.read("cache.xaero")

pixel_data = raw[254:]
print(f"pixel_data size: {len(pixel_data)}")

# 解码前 10240 像素 (40 chunks * 256)
def decode_rle_full(data, max_pixels=10240):
    pixels = []
    off = 0
    runs = []
    while off < len(data) and len(pixels) < max_pixels:
        if off + 4 > len(data):
            break
        count = data[off]
        if count == 0:
            break
        r, g, b = data[off+1], data[off+2], data[off+3]
        runs.append((count, r, g, b))
        for _ in range(min(count, max_pixels - len(pixels))):
            pixels.append((r, g, b))
        off += 4
    return pixels, off, runs

pixels, off, runs = decode_rle_full(pixel_data, 10240)
print(f"Decoded {len(pixels)} pixels from {off} bytes ({len(runs)} runs)")
print(f"First 10 runs: {runs[:10]}")

# 渲染前 10240 像素为 10x4 chunks (160x64)
img = Image.new('RGB', (10*16, 4*16), (0, 0, 0))
for i, (r, g, b) in enumerate(pixels):
    chunk_idx = i // 256
    in_chunk = i % 256
    cx = chunk_idx % 10
    cz = chunk_idx // 10
    px = cx * 16 + (in_chunk % 16)
    py = cz * 16 + (in_chunk // 16)
    if px < img.width and py < img.height:
        img.putpixel((px, py), (r, g, b))
img.save(OUT / "continuous_rle_10x4.png")
print(f"saved: continuous_rle_10x4.png")

# 也渲染 8x5
img2 = Image.new('RGB', (8*16, 5*16), (0, 0, 0))
for i, (r, g, b) in enumerate(pixels):
    chunk_idx = i // 256
    in_chunk = i % 256
    cx = chunk_idx % 8
    cz = chunk_idx // 8
    px = cx * 16 + (in_chunk % 16)
    py = cz * 16 + (in_chunk // 16)
    if px < img2.width and py < img2.height:
        img2.putpixel((px, py), (r, g, b))
img2.save(OUT / "continuous_rle_8x5.png")
print(f"saved: continuous_rle_8x5.png")

# 关键: 后面的 40469 bytes 是什么?
# 让我看看 offset 588 之后的数据
trailing = pixel_data[off:]
print(f"\ntrailing size: {len(trailing)} bytes")
print(f"first 64 hex: {trailing[:64].hex()}")
print(f"first 64 dec: {list(trailing[:64])}")

# 让我检查: trailing 开头是否有 00 00 分隔?
# 或者 trailing 是另一种数据格式?

# 重要线索: cache/3/ 是 zoom level 3, 对应最高分辨率
# 每个 .xwmc 对应一个 region tile (在 Xaero 的坐标系中)
# 文件名 0_0.xwmc 表示 tile 坐标 (0, 0)
# 每个 tile 包含多个 chunks (在 Xaero 的概念中, 可能是 8x8 或其他)

# 让我搜索更多文件验证
print("\n=== Checking other files ===")
f2 = BASE / "3" / "-1_1.xwmc"
with zipfile.ZipFile(f2) as z:
    raw2 = z.read("cache.xaero")
print(f"{f2.name}: total={len(raw2)}")
# 找 palette end
# 先解析 biome count
biome_count2 = (raw2[12] << 8) | raw2[13]
print(f"  biome_count: {biome_count2}")

# 解析 palette
def find_palette_end(raw):
    off = 16
    biome_count = (raw[12] << 8) | raw[13]
    count = 0
    while off < len(raw) and count < biome_count:
        while off < len(raw) and raw[off] == 0:
            off += 1
        if off >= len(raw):
            break
        slen = raw[off]
        if slen < 10 or slen > 64:
            break
        if off + 1 + slen > len(raw):
            break
        name = raw[off+1:off+1+slen].decode('utf-8', errors='replace')
        if not name.startswith('minecraft:'):
            break
        count += 1
        off += 1 + slen
    # off 现在是最后一个 biome 字符串末尾
    # 后面可能有 00 00 分隔
    while off < len(raw) and raw[off] == 0:
        off += 1
    return off

pd_start2 = find_palette_end(raw2)
print(f"  palette_end: {pd_start2}")
pixel_data2 = raw2[pd_start2:]
print(f"  pixel_data size: {len(pixel_data2)}")

# 解码 RLE
pixels2, off2, runs2 = decode_rle_full(pixel_data2, 10240)
print(f"  decoded {len(pixels2)} pixels from {off2} bytes ({len(runs2)} runs)")

# 渲染
img3 = Image.new('RGB', (8*16, 5*16), (0, 0, 0))
for i, (r, g, b) in enumerate(pixels2):
    chunk_idx = i // 256
    in_chunk = i % 256
    cx = chunk_idx % 8
    cz = chunk_idx // 8
    px = cx * 16 + (in_chunk % 16)
    py = cz * 16 + (in_chunk // 16)
    if px < img3.width and py < img3.height:
        img3.putpixel((px, py), (r, g, b))
img3.save(OUT / "rle_-1_1_8x5.png")
print(f"  saved: rle_-1_1_8x5.png")

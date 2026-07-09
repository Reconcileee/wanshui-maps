"""解析 trailing metadata 找出 chunk 坐标

RLE 已验证: 每 chunk 1024 bytes, RLE 编码后正好 256 像素
40 chunks 用掉 40960 bytes, trailing 97 bytes

trailing 97 bytes 应该包含 chunk 坐标信息
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
trailing = pixel_data[40960:]  # 97 bytes

print(f"trailing: {len(trailing)} bytes")
print(f"hex: {trailing.hex()}")
print(f"dec: {list(trailing)}")

# 尝试解析: 4-byte header + 40 * (cx, cz) varint
# 或: 2-byte header + 40 * (cx, cz) 2-byte
# 97 = 1 + 40 * 2.4 -> 不像
# 97 = 17 + 40 * 2 = 97! 正好!
# 17 byte header + 40 * 2 byte (cx, cz)

print(f"\n--- 17-byte header + 40 * 2-byte coords ---")
header = trailing[:17]
coords_data = trailing[17:]
print(f"header (17 bytes): {list(header)}")
print(f"coords_data size: {len(coords_data)} = {len(coords_data)//2} pairs")

for i in range(40):
    cx = coords_data[i * 2]
    cz = coords_data[i * 2 + 1]
    if cx >= 128:
        cx -= 256
    if cz >= 128:
        cz -= 256
    print(f"  chunk {i:2d}: cx={cx:3d}, cz={cz:3d}")

# 也试试 25-byte header + 36 pairs? 不对
# 试试 1 byte count + 40 * 2-byte = 81 bytes, 剩 16 bytes
print(f"\n--- 16-byte header + 40 varint pairs ---")
# varint pair 平均 1.0125 bytes? 不太可能

# 让我看 2-byte 解析后的坐标是否有意义
# 如果 .xwmc 文件名是 0_0 (region 坐标), 那 chunk 坐标应该在 0-31 范围
# 但解析出的 cx/cz 有 12, 16, -128 等, 不太对

# 让我看是否是 4-byte per coord (int32)
print(f"\n--- 4-byte int32 coords ---")
# 97 / 8 = 12.125, 不对

# 等等, 让我重新数: 40 chunks, 每个 RLE 用多少 bytes?
# 之前: 每个 chunk 正好 256 像素, 平均用 4-304 bytes
# 40 chunks 总 RLE 数据大小?
def decode_rle(data, max_pixels=256):
    pixels = []
    off = 0
    while off < len(data) and len(pixels) < max_pixels:
        if off + 4 > len(data):
            break
        count = data[off]
        r, g, b = data[off+1], data[off+2], data[off+3]
        for _ in range(min(count, max_pixels - len(pixels))):
            pixels.append((r, g, b))
        off += 4
    return pixels, off

# 计算 40 个 chunk 实际用了多少 RLE bytes
total_rle = 0
chunk_sizes = []
for i in range(40):
    chunk_off = i * 1024
    chunk_data = pixel_data[chunk_off:chunk_off + 1024]
    pixels, used = decode_rle(chunk_data)
    chunk_sizes.append(used)
    total_rle += used
print(f"\nTotal RLE bytes used by 40 chunks: {total_rle}")
print(f"RLE sizes per chunk: {chunk_sizes}")

# 如果 RLE 数据是连续的, 总大小应该是 total_rle
# 但实际 chunk 之间有 1024 字节对齐 (剩余空间是 0)
# 让我看 trailing 是否从 pixel_data 的某个偏移开始 (不是 40960)

# 实际上: 如果每 chunk 用 < 1024 bytes, 剩下的空间是 0 padding
# 那 trailing metadata 应该在第 40 个 chunk 的 RLE 数据之后, 但在 1024 字节边界内
# 即: pixel_data 中, RLE 数据是连续的, 但每 chunk 最多 1024 bytes

# 让我检查: 连续的 RLE 流, 每个 chunk 256 像素, 共 40 个 chunk
# 总 RLE bytes = sum(chunk_sizes) = ?
print(f"\nsum of chunk sizes: {sum(chunk_sizes)}")
# sum = 2404 bytes
# 40960 - 2404 = 38556 bytes of padding? 不对

# 让我重新检查: 是不是整个 pixel_data 是连续的 RLE, 没有 chunk 边界?
# 连续 RLE: 总像素 = 41057 bytes / 4 = 10264 个 RLE 条目 (平均)
# 40 chunks * 256 = 10240 像素
# 41057 / 4 = 10264.25, 正好约 10264 个 RLE 条目
# 如果平均每个 run 1 像素, 那 10264 像素
# 但我们之前验证的 40 chunks 都正好 256 像素 = 10240 像素
# 差 24 像素 = 6 RLE 条目

# 等等, 我之前的 chunk 边界假设可能错了
# 让我重新: 整个 pixel_data 是连续 RLE + trailing metadata
total_rle_pixels = 0
off = 0
rle_entries = 0
while off < len(pixel_data) and total_rle_pixels < 10240 + 100:
    if off + 4 > len(pixel_data):
        break
    count = pixel_data[off]
    if count == 0:
        break
    r, g, b = pixel_data[off+1], pixel_data[off+2], pixel_data[off+3]
    total_rle_pixels += count
    rle_entries += 1
    off += 4
print(f"\nContinuous RLE: {rle_entries} entries, {total_rle_pixels} pixels, used {off} bytes")
print(f"10240 pixels (40*256) would need: ?")

# 如果总像素 = 10240 = 40 chunks * 256
# 那 metadata 从 off 开始, off = sum of RLE bytes
# 让我精确计算

def rle_decode_count(data, target_pixels):
    """解码 RLE 直到达到 target_pixels 像素, 返回使用的 bytes 数"""
    pixels = 0
    off = 0
    while off < len(data) and pixels < target_pixels:
        if off + 4 > len(data):
            break
        count = data[off]
        if pixels + count > target_pixels:
            # 部分使用
            needed = target_pixels - pixels
            off += 4  # 还是消耗完整的 RLE 条目
            pixels += needed
            break
        pixels += count
        off += 4
    return off, pixels

for n_chunks in [39, 40, 41, 42]:
    used, pixels = rle_decode_count(pixel_data, n_chunks * 256)
    print(f"  {n_chunks} chunks ({n_chunks*256} pixels): used {used} bytes, got {pixels} pixels, remainder={len(pixel_data)-used}")

# 如果是 40 chunks = 10240 像素, 用了 N bytes, trailing = 41057 - N
# trailing 应该包含 chunk 坐标信息

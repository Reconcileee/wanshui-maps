"""完整解析 cache.xaero v3"""
import zipfile
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

f = BASE / "3" / "0_0.xwmc"
with zipfile.ZipFile(f) as z:
    raw = z.read("cache.xaero")

print(f"total: {len(raw)}")

# 头部 16 字节, byte 12-13 = 00 0b = biome count (大端)
biome_count = (raw[12] << 8) | raw[13]
print(f"biome count: {biome_count}")

off = 16
biomes = []
for i in range(biome_count):
    if off >= len(raw):
        break
    slen = raw[off]
    off += 1
    if off + slen > len(raw):
        break
    name = raw[off:off+slen].decode('utf-8', errors='replace')
    biomes.append(name)
    off += slen
    # 跳过 00 00 分隔
    while off < len(raw) and raw[off] == 0 and off + 1 < len(raw) and raw[off+1] == 0:
        off += 2
        break  # 只跳一次

print(f"\nbiome palette ({len(biomes)}):")
for i, b in enumerate(biomes):
    print(f"  [{i}] {b}")

print(f"\nafter palette offset={off}")
print(f"next 64 hex: {raw[off:off+64].hex()}")
remaining = len(raw) - off
print(f"remaining: {remaining}")

# 像素数据: 检查是否是 chunk 块
# 每个 chunk 16x16 = 256 pixels
# 如果 4 bit per pixel (biome index), 1 byte = 2 pixels
# 41295 bytes / 128 = 322 chunks? 不合理
# 可能每个 chunk 前有坐标头

# 看像素数据结构: 可能是 chunk_count + chunks
# 每个 chunk: cx(1) cz(1) + 16x16 data?
# 41295 / (2 + 128) = 318... 不对

# 或者: 每个像素 1 byte (biome index), 16x16=256 per chunk
# 41295 / 256 = 161 chunks. 不对

# 让我看数据是否含 chunk 坐标头
# 假设: cx(1) cz(1) + data
# 如果 biome count=11, 需要 4 bit, 16x16/2 = 128 bytes per chunk
# (2 + 128) = 130 per chunk, 41295/130 = 317... 不对

# 可能数据是: layer_y + chunks
# 让我检查第一个字节是否像坐标
print(f"\nfirst pixel bytes: {raw[off:off+10].hex()}")
print(f"as decimals: {list(raw[off:off+10])}")

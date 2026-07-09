"""完整解析 cache.xaero: 头部 + biome palette (00 00 分隔) + 像素数据"""
import zipfile
from pathlib import Path

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

f = BASE / "3" / "0_0.xwmc"
with zipfile.ZipFile(f) as z:
    raw = z.read("cache.xaero")

print(f"total: {len(raw)}")
print(f"header 16: {raw[:16].hex()}")

# 头部: 00 01 00 18 XX XX XX XX XX 00 00 00 0b 00 00
# 0b = 11 = biome count?
biome_count = raw[12]
print(f"biome count (byte 12): {biome_count}")

# 偏移 16 开始 palette
off = 16
biomes = []
for i in range(biome_count):
    if off >= len(raw):
        break
    slen = raw[off]
    off += 1
    if slen == 0 or off + slen > len(raw):
        break
    name = raw[off:off+slen].decode('utf-8', errors='replace')
    biomes.append(name)
    off += slen
    # 跳过 00 00 分隔
    if off + 1 < len(raw) and raw[off] == 0 and raw[off+1] == 0:
        off += 2

print(f"\nbiome palette ({len(biomes)}):")
for i, b in enumerate(biomes):
    print(f"  [{i}] {b}")

print(f"\nafter palette offset={off}")
print(f"next 64 hex: {raw[off:off+64].hex()}")
print(f"remaining: {len(raw) - off}")

# 现在分析像素数据
# 如果 biome_count=11, 需要 4 bit per pixel
# 瓦片可能 16x16 chunks = 256, 或 16x16x16x16 = 65536 blocks
remaining = len(raw) - off
print(f"\nremaining={remaining}")
print(f"256*256={256*256}, 16*16={16*16}")
print(f"if 4bit: {remaining*2} pixels")
print(f"if 8bit: {remaining} pixels")

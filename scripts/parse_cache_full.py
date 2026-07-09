"""完整解析 cache.xaero: 头部 + biome palette + 像素数据"""
import zipfile, io, struct
from pathlib import Path
from PIL import Image

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

f = BASE / "3" / "0_0.xwmc"
with zipfile.ZipFile(f) as z:
    raw = z.read("cache.xaero")

print(f"total size: {len(raw)}")
print(f"first 32 hex: {raw[:32].hex()}")

# 手动解析
off = 0
# 头部: 00 01 00 18 ...
# 00 01 = ?
# 00 18 = 24
# 然后到 14 (biome 字符串开始)
# 找到第一个 0x14 前的字节
# first 32: 00 01 00 18 00 01 2a 61 9d ff 00 00 00 0b 00 00 14 6d 6f ...
# 0x14 在偏移 16

# 尝试解读头部
print(f"\nheader bytes: {' '.join(f'{b:02x}' for b in raw[:16])}")
# 00 01 00 18 00 01 2a 61 9d ff 00 00 00 0b 00 00
# 可能: 0001=version, 0018=24( tileSize? ), 00012a619d=? , ff=?, 0000000b=11(biome count?), 0000=?

# 假设偏移 16 开始 biome palette
off = 16
biomes = []
while off < len(raw):
    slen = raw[off]
    if slen == 0:
        # 可能是分隔符或结束
        # 检查下一个是否也是字符串
        if off + 1 < len(raw) and raw[off+1] > 0 and raw[off+1] < 64:
            off += 1
            continue
        else:
            break
    if slen > 64:  # 不像字符串长度
        break
    if off + 1 + slen > len(raw):
        break
    name = raw[off+1:off+1+slen].decode('utf-8', errors='replace')
    if not name.startswith('minecraft:'):
        break
    biomes.append(name)
    off += 1 + slen

print(f"\nbiome palette ({len(biomes)}):")
for i, b in enumerate(biomes):
    print(f"  [{i}] {b}")

print(f"\nafter palette, offset={off}, next 32 hex: {raw[off:off+32].hex()}")
print(f"remaining bytes: {len(raw) - off}")

# 如果 biome count = 11, 但我可能解析了更多
# 让我重新: 头部 0000000b = 11 个 biome
# 但我解析到的数量可能不同

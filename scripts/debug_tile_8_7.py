"""详细检查 tile (8,7) 的结构，看看为什么有这么多 chunks

可能原因:
1. pixel_start 算错了，把 biome 数据也算进 pixel_data 了
2. tile size 不是 24x24 chunks
3. 每 chunk 不是 1024 字节
"""
import zipfile
from pathlib import Path

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

def read_xwmc(path):
    with zipfile.ZipFile(path) as z:
        return z.read("cache.xaero")

raw = read_xwmc(BASE / "1" / "8_7.xwmc")
print(f"Total size: {len(raw)} bytes")

# 打印 header
print(f"\nHeader (16 bytes):")
print(f"  hex: {raw[:16].hex()}")
print(f"  dec: {list(raw[:16])}")

# 数所有 minecraft: 字符串
print(f"\n=== Counting 'minecraft:' strings ===")
count = 0
pos = 0
positions = []
while True:
    idx = raw.find(b'minecraft:', pos)
    if idx == -1:
        break
    positions.append(idx)
    count += 1
    pos = idx + 1
print(f"Found {count} 'minecraft:' strings")

# 前 20 个
print(f"\nFirst 20 positions:")
for i, idx in enumerate(positions[:20]):
    if idx > 0:
        slen = raw[idx-1]
        name = raw[idx:idx+min(slen, 40)].decode('utf-8', errors='replace')
        print(f"  {i}: offset={idx}, slen_byte={slen}, name={name[:30]}")

# 最后 10 个
print(f"\nLast 10 positions:")
for i, idx in enumerate(positions[-10:]):
    if idx > 0:
        slen = raw[idx-1]
        name = raw[idx:idx+min(slen, 40)].decode('utf-8', errors='replace')
        print(f"  {len(positions)-10+i}: offset={idx}, slen_byte={slen}, name={name[:30]}")

# 重新仔细找 biome palette
# biome 应该在 header 后面，以长度前缀的 minecraft:xxx 形式出现
print(f"\n\n=== Parsing biome palette from offset 16 ===")
off = 16
biomes = []
while off < len(raw):
    if off >= len(raw):
        break
    slen = raw[off]
    if slen == 0:
        off += 1
        continue
    if slen < 10 or slen > 64:
        # 检查是否是 00 00 分隔符
        if off + 1 < len(raw) and raw[off] == 0 and raw[off+1] == 0:
            off += 2
            continue
        break
    if off + 1 + slen > len(raw):
        break
    name = raw[off+1:off+1+slen].decode('utf-8', errors='replace')
    if not name.startswith('minecraft:'):
        break
    biomes.append((off, slen, name))
    end = off + 1 + slen
    print(f"  biome {len(biomes)-1}: offset={off}, len={slen}, name={name}, end={end}")
    off = end
    # 跳过 00 00 分隔
    skip = 0
    while off + 1 < len(raw) and raw[off] == 0 and raw[off+1] == 0:
        off += 2
        skip += 2
        if skip > 100:
            break

print(f"\nFound {len(biomes)} biomes in palette")
if biomes:
    last_end = biomes[-1][0] + 1 + biomes[-1][1]
    print(f"Last biome ends at: {last_end}")
    # 跳过末尾的 0
    px_start = last_end
    while px_start < len(raw) and raw[px_start] == 0:
        px_start += 1
    print(f"Pixel data starts at: {px_start}")
    print(f"Pixel data size: {len(raw) - px_start} bytes")
    print(f"At 1024 bytes/chunk = {(len(raw) - px_start) // 1024} chunks")

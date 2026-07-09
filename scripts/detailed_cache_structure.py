"""详细分析 cache.xaero 的结构

从 offset 240 到 300 字节逐字节打印
看看 biome 列表结束后到底是什么
"""
import zipfile
from pathlib import Path

BASE = Path(r"D:\aiide_project\trae_project\projects\minecraft_map\1.19.2TOBU0405\xaero\world-map\Multiplayer_frp-tag.com\null\mw$-615768317\cache")

def read_xwmc(path):
    with zipfile.ZipFile(path) as z:
        return z.read("cache.xaero")

raw = read_xwmc(BASE / "3" / "0_0.xwmc")
print(f"Total size: {len(raw)}")

# 打印 offset 240 - 280 的详细信息
print("\n=== Bytes 240-280 ===")
for i in range(240, min(280, len(raw))):
    b = raw[i]
    # 尝试打印为 ASCII
    ascii_char = chr(b) if 32 <= b < 127 else '.'
    print(f"  offset {i:3d}: 0x{b:02x} ({b:3d})  '{ascii_char}'")

# 也看看文件开头 16 字节
print("\n=== Header (first 16 bytes) ===")
for i in range(16):
    b = raw[i]
    print(f"  byte {i}: 0x{b:02x} ({b:3d})")

# 让我们重新解析 biome list
print("\n=== Re-parsing biome list ===")
offset = 16  # biome list 从 offset 16 开始?
biomes = []
for i in range(20):  # 最多 20 个
    if offset >= len(raw):
        break
    slen = raw[offset]
    if slen < 10 or slen > 64:
        print(f"  Stop at offset {offset}: invalid length {slen}")
        break
    if offset + 1 + slen > len(raw):
        break
    name = raw[offset+1:offset+1+slen].decode('utf-8', errors='replace')
    if not name.startswith('minecraft:'):
        print(f"  Stop at offset {offset}: not minecraft: {name[:20]}")
        break
    biomes.append((offset, slen, name))
    end = offset + 1 + slen
    print(f"  biome {i}: offset={offset}, len={slen}, name={name}, end={end}")
    
    # 看看 end 之后的字节
    next_bytes = raw[end:end+4]
    print(f"    next 4 bytes: {next_bytes.hex()} = {list(next_bytes)}")
    
    offset = end
    # 跳过分隔符 (00 00?)
    while offset < len(raw) and raw[offset] == 0:
        offset += 1
        if offset - end > 4:  # 最多跳过 4 个 0
            break

print(f"\nBiome list ends at approx offset: {offset}")
print(f"After biome list, next 16 bytes: {raw[offset:offset+16].hex()}")

# 现在让我们看看：如果 pixel data 从 offset 开始，那有多少字节？
pixel_data_size = len(raw) - offset
print(f"\nIf pixel_start={offset}:")
print(f"  pixel_data_size = {pixel_data_size}")
print(f"  n_chunks (1024 bytes each) = {pixel_data_size // 1024}")
print(f"  remainder = {pixel_data_size % 1024}")

# 等等，我之前的 pixel_start 是 256，但这里算出来 offset 可能不同
# 让我验证一下：如果每 chunk 1024 字节，N 个 chunks，
# trailing 应该有 N 个 chunk 的坐标信息
# 坐标可能有不同的编码方式
